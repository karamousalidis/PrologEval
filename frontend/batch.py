import streamlit as st
import asyncio
import csv
import io
import os
import re
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.llm_service import generate_openrouter_response_async, analyze_prolog_code
from core.prolog_evaluator import extract_prolog_code, save_generated_code, DANGEROUS_PATTERNS


def _check_code_safety(code: str) -> Optional[str]:
    """Returns an error message if code contains dangerous patterns, else None."""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return f"Blocked: dangerous pattern '{pattern}' found in generated code."
    return None


def _run_single_query_subprocess(code: str, query: str, timeout: int = 15) -> Dict[str, Any]:
    """Runs a single Prolog query in an isolated swipl subprocess."""
    clean_query = query.strip().rstrip('.')
    
    # Write code to a unique temp file
    temp_path = os.path.join("temp", f"subproc_{os.getpid()}_{id(query) % 100000}.pl")
    save_generated_code(code, temp_path)
    
    # Goal: consult file, run query, write result, halt
    goal = (
        f"consult('{temp_path}'), "
        f"(catch(({clean_query}), _Err, fail) "
        f"-> write('__PASS__') "
        f"; write('__FAIL__')), "
        f"halt"
    )
    
    try:
        result = subprocess.run(
            ['swipl', '-q', '-g', goal, '-t', 'halt'],
            capture_output=True, text=True, timeout=timeout,
        )
        out = result.stdout.strip()
        passed = '__PASS__' in out
        
        return {
            "query": query,
            "success": passed,
            "solutions": [{}] if passed else [],
            "error": None if passed else (result.stderr.strip()[:200] or "Query returned false"),
            "passed": passed,
        }
    except subprocess.TimeoutExpired:
        return {"query": query, "success": False, "solutions": [], "error": "Query timed out", "passed": False}
    except FileNotFoundError:
        return {"query": query, "success": False, "solutions": [], "error": "swipl not found in PATH", "passed": False}
    except Exception as e:
        return {"query": query, "success": False, "solutions": [], "error": str(e), "passed": False}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _run_test_queries(code: str, queries: List[str], **_kwargs) -> List[Dict[str, Any]]:
    """Runs test queries against generated code using isolated subprocesses."""
    # Security check first
    safety_error = _check_code_safety(code)
    if safety_error:
        return [{"query": q, "success": False, "solutions": [], "error": safety_error, "passed": False} for q in queries]
    
    return [_run_single_query_subprocess(code, q) for q in queries]


def _build_metrics_row(prompt: str, model_name: str, result: Dict[str, Any],
                       test_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Builds a flat metrics dict from a generation result."""
    if "error" in result:
        return {
            "prompt": prompt,
            "model": model_name,
            "status": "error",
            "error": result["error"],
        }
    
    clean_code = extract_prolog_code(result["text"])
    quality = analyze_prolog_code(clean_code)
    r_score = result.get("readability_score", "N/A")
    
    row = {
        "prompt": prompt,
        "model": model_name,
        "status": "ok",
        "time_s": round(result["time_taken"], 2),
        "tokens_in": result.get("tokens_prompt", 0),
        "tokens_out": result.get("tokens_completion", 0),
        "readability": round(r_score, 2) if isinstance(r_score, (int, float)) else r_score,
        "loc": quality["lines_of_code"],
        "predicates": quality["predicate_count"],
        "clauses": quality["clause_count"],
        "comment_ratio": quality["comment_ratio"],
        "recursion": quality["uses_recursion"],
        "builtins": ", ".join(quality.get("builtin_predicates", [])),
        "code": clean_code,
    }
    
    if test_results is not None:
        total = len(test_results)
        passed = sum(1 for t in test_results if t["passed"])
        row["tests_passed"] = passed
        row["tests_total"] = total
        row["test_results"] = test_results
    
    return row


def _generate_csv(rows: List[Dict[str, Any]]) -> str:
    """Generates a CSV string from a list of metric rows."""
    if not rows:
        return ""
    output = io.StringIO()
    fieldnames = [k for k in rows[0].keys() if k not in ("code", "test_results")]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _generate_batch_report(rows: List[Dict[str, Any]], models: List[str]) -> str:
    """Generates a Markdown report from batch results."""
    report = []
    report.append("# PrologEval Batch Benchmark Report")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Models:** {', '.join(models)}")
    report.append(f"**Prompts evaluated:** {len(set(r['prompt'] for r in rows))}")
    report.append("")

    # Summary table
    report.append("## Summary Matrix")
    report.append("")
    has_tests = any("tests_passed" in r for r in rows)
    header = "| Prompt | " + " | ".join(models) + " |"
    separator = "|--------|" + "|".join(["-----" for _ in models]) + "|"
    report.append(header)
    report.append(separator)

    rows_by_key = {(r["prompt"], r["model"]): r for r in rows}
    prompts_seen = list(dict.fromkeys(r["prompt"] for r in rows))

    for prompt in prompts_seen:
        cells = []
        for model in models:
            r = rows_by_key.get((prompt, model), {})
            if r.get("status") == "error":
                cells.append("❌ Error")
            elif r:
                cell = f"{r['time_s']}s / {r['tokens_in'] + r['tokens_out']}tok / {r['readability']}"
                if "tests_passed" in r:
                    cell += f" / {r['tests_passed']}/{r['tests_total']}✓"
                cells.append(cell)
            else:
                cells.append("—")
        short_prompt = prompt[:50] + ("…" if len(prompt) > 50 else "")
        report.append(f"| {short_prompt} | " + " | ".join(cells) + " |")

    report.append("")
    report.append("---")
    report.append("## Detailed Results")

    for prompt in prompts_seen:
        report.append(f"\n### {prompt}")
        for model in models:
            r = rows_by_key.get((prompt, model))
            if not r:
                continue
            report.append(f"\n#### {model}")
            if r.get("status") == "error":
                report.append(f"**Error:** {r.get('error', 'Unknown')}")
                continue
            report.append(f"| Metric | Value |")
            report.append(f"|--------|-------|")
            report.append(f"| Time | {r['time_s']}s |")
            report.append(f"| Tokens (In/Out) | {r['tokens_in']}/{r['tokens_out']} |")
            report.append(f"| Readability | {r['readability']} |")
            report.append(f"| Lines of Code | {r['loc']} |")
            report.append(f"| Predicates | {r['predicates']} |")
            report.append(f"| Comment Ratio | {r['comment_ratio']}% |")
            report.append(f"| Recursion | {'Yes' if r['recursion'] else 'No'} |")
            if r.get("builtins"):
                report.append(f"| Built-ins | {r['builtins']} |")
            if "tests_passed" in r:
                report.append(f"| Tests Passed | {r['tests_passed']}/{r['tests_total']} |")
                for t in r.get("test_results", []):
                    icon = "✅" if t["passed"] else "❌"
                    report.append(f"  - {icon} `{t['query']}` {'→ ' + str(t['solutions'][:3]) if t['passed'] else '→ ' + str(t.get('error', 'failed'))}")
            report.append(f"\n```prolog\n{r['code']}\n```")
        report.append("\n---")

    return "\n".join(report)


def display_batch_benchmark(suggested_prompts: List[str], prompt_template: str,
                            available_models: Dict[str, Dict[str, Any]],
                            test_queries: Optional[Dict[str, List[str]]] = None) -> None:
    """Renders the batch benchmark UI: model/prompt selection, execution, and results."""
    if test_queries is None:
        test_queries = {}
    
    st.subheader("Batch Benchmark Configuration")

    # Model selection — no limit
    selected_models = st.multiselect(
        "Select models to benchmark:",
        list(available_models.keys()),
        default=list(available_models.keys()),
        key="batch_models",
    )

    # Prompt selection
    use_all = st.checkbox("Use all suggested prompts", value=True, key="batch_all_prompts")
    if use_all:
        selected_prompts = suggested_prompts
    else:
        selected_prompts = st.multiselect(
            "Select prompts:",
            suggested_prompts,
            default=suggested_prompts[:1] if suggested_prompts else [],
            key="batch_prompts",
        )

    # Custom prompt addition
    custom = st.text_input("Add a custom prompt (optional):", key="batch_custom")
    if custom:
        selected_prompts = list(selected_prompts) + [custom]

    # Auto-test toggle
    prompts_with_tests = [p for p in selected_prompts if p in test_queries]
    run_auto_tests = st.checkbox(
        f"Auto-run predefined test queries ({len(prompts_with_tests)}/{len(selected_prompts)} prompts have tests)",
        value=len(prompts_with_tests) > 0,
        key="batch_auto_test",
    )

    total_runs = len(selected_prompts) * len(selected_models)
    st.caption(f"**{total_runs}** generations ({len(selected_prompts)} prompts × {len(selected_models)} models)")

    if total_runs > 2:
        st.warning(
            f"⚠️ Running **{total_runs} generations** will consume a significant amount of API tokens "
            f"and may take several minutes to complete. Consider selecting fewer models or prompts "
            f"if you want a quicker run."
        )

    # Run button
    if st.button("Run Benchmark", type="primary", disabled=(total_runs == 0)):
        if not selected_models:
            st.error("Please select at least one model.")
            return
        if not selected_prompts:
            st.error("Please select at least one prompt.")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()
        completed = 0
        all_rows: List[Dict[str, Any]] = []

        async def run_batch():
            nonlocal completed
            for prompt in selected_prompts:
                manipulated = prompt_template.replace("{{user_prompt}}", prompt)
                
                tasks = [
                    generate_openrouter_response_async(
                        available_models[m]["id"],
                        manipulated,
                        params=available_models[m].get("params"),
                    )
                    for m in selected_models
                ]
                status_text.text(f"Generating: {prompt[:60]}…")
                results = await asyncio.gather(*tasks)

                for model_name, result in zip(selected_models, results):
                    # Run auto-tests if enabled and queries exist
                    tr = None
                    if run_auto_tests and prompt in test_queries and "error" not in result:
                        clean_code = extract_prolog_code(result["text"])
                        status_text.text(f"Testing: {model_name} × {prompt[:40]}…")
                        tr = _run_test_queries(
                            clean_code, test_queries[prompt],
                        )
                    
                    row = _build_metrics_row(prompt, model_name, result, test_results=tr)
                    all_rows.append(row)
                    completed += 1
                    progress_bar.progress(completed / total_runs)

        asyncio.run(run_batch())
        progress_bar.progress(1.0)
        status_text.text(f"Benchmark complete — {total_runs} generations finished.")

        st.session_state.batch_results = all_rows
        st.session_state.batch_result_models = selected_models
        st.session_state.batch_result_prompts = selected_prompts

    # ── Render results if available ──────────────────────────────────
    if "batch_results" not in st.session_state:
        return

    all_rows = st.session_state.batch_results
    selected_models_display = st.session_state.batch_result_models
    selected_prompts_display = st.session_state.batch_result_prompts
    has_tests = any("tests_passed" in r for r in all_rows)

    st.divider()
    st.subheader("Results Matrix")
    if has_tests:
        st.caption("Cells show **time / readability / tests passed**. Expand rows for full details.")
    else:
        st.caption("Cells show **time / readability**. Expand rows for full details.")

    # Build summary matrix
    rows_by_key = {(r["prompt"], r["model"]): r for r in all_rows}
    prompts_seen = list(dict.fromkeys(r["prompt"] for r in all_rows))

    matrix_data = []
    for prompt in prompts_seen:
        row_dict = {"Prompt": prompt[:60] + ("…" if len(prompt) > 60 else "")}
        for model in selected_models_display:
            r = rows_by_key.get((prompt, model), {})
            if r.get("status") == "error":
                row_dict[model] = "❌ Error"
            elif r:
                cell = f"{r['time_s']}s / {r['tokens_in'] + r['tokens_out']}tok / {r['readability']}"
                if "tests_passed" in r:
                    cell += f" / {r['tests_passed']}/{r['tests_total']}✓"
                row_dict[model] = cell
            else:
                row_dict[model] = "—"
        matrix_data.append(row_dict)

    st.dataframe(matrix_data, width="stretch", hide_index=True)

    # Detailed expandable results per prompt
    st.subheader("Detailed Results")
    for p_idx, prompt in enumerate(prompts_seen):
        short = prompt[:70] + ("…" if len(prompt) > 70 else "")
        with st.expander(short, expanded=False):
            cols = st.columns(len(selected_models_display))
            for col_idx, model in enumerate(selected_models_display):
                r = rows_by_key.get((prompt, model))
                if not r:
                    continue
                with cols[col_idx]:
                    st.markdown(f"**{model}**")
                    if r.get("status") == "error":
                        st.error(r.get("error", "Unknown error"))
                        continue
                    
                    m_cols = st.columns(3)
                    m_cols[0].metric("Time", f"{r['time_s']}s")
                    m_cols[1].metric("Readability", r["readability"])
                    m_cols[2].metric("LOC", r["loc"])
                    st.caption(f"Tokens: {r['tokens_in']}/{r['tokens_out']} · Predicates: {r['predicates']} · Clauses: {r['clauses']} · Recursion: {'✓' if r['recursion'] else '✗'}")
                    if r.get("builtins"):
                        st.caption(f"Built-ins: {r['builtins']}")
                    
                    # Auto-test results
                    if "test_results" in r and r["test_results"]:
                        passed = r["tests_passed"]
                        total = r["tests_total"]
                        if passed == total:
                            st.success(f"Tests: {passed}/{total} passed")
                        elif passed > 0:
                            st.warning(f"Tests: {passed}/{total} passed")
                        else:
                            st.error(f"Tests: 0/{total} passed")
                        for t in r["test_results"]:
                            icon = "✅" if t["passed"] else "❌"
                            label = f"{icon} `{t['query']}`"
                            if t["passed"] and t["solutions"]:
                                sol = t["solutions"][0]
                                if sol == {}:
                                    label += " → `true`"
                                else:
                                    label += f" → `{sol}`"
                            elif t.get("error"):
                                label += f" → {t['error'][:80]}"
                            st.markdown(label)
                    
                    # Generated code
                    with st.container(height=300):
                        st.code(r["code"], language="prolog")
                    
                    # Ad-hoc query input
                    safe_key = f"p{p_idx}_m{col_idx}"
                    adhoc_query = st.text_input(
                        "Run a query:",
                        placeholder="e.g., fibonacci(5, X)",
                        key=f"adhoc_{safe_key}",
                    )
                    if st.button("Run", key=f"adhoc_run_{safe_key}"):
                        if adhoc_query:
                            adhoc_results = _run_test_queries(
                                r["code"], [adhoc_query],
                            )
                            t = adhoc_results[0]
                            if t["passed"]:
                                st.success(f"✅ {len(t['solutions'])} solution(s)")
                                for s in t["solutions"]:
                                    st.code("true." if s == {} else str(s))
                            elif t["success"] and not t["solutions"]:
                                st.warning("Query returned false (no solutions).")
                            else:
                                st.error(f"Error: {t.get('error', 'Unknown')}")
                        else:
                            st.warning("Enter a query first.")

    # Export buttons
    st.divider()
    export_cols = st.columns(2)
    with export_cols[0]:
        report_md = _generate_batch_report(all_rows, selected_models_display)
        st.download_button(
            "Download Markdown Report",
            data=report_md,
            file_name=f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            key="batch_dl_md",
            width="stretch",
        )
    with export_cols[1]:
        csv_data = _generate_csv(all_rows)
        st.download_button(
            "Download CSV",
            data=csv_data,
            file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="batch_dl_csv",
            width="stretch",
        )

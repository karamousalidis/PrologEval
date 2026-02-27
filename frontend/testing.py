import streamlit as st
from core.prolog_evaluator import run_prolog_query
from core.utils import analyze_prolog_code


def _render_test_section_for_model(model_name: str):
    """Renders a self-contained query input + button + results for a single model."""
    file_path = st.session_state.generated_paths.get(model_name)
    if not file_path:
        return

    st.divider()
    st.markdown(f"**Test {model_name}**")

    # Use unique keys so each model's widgets are independent
    safe_key = model_name.replace(" ", "_")
    user_query = st.text_input("Prolog query:", placeholder="e.g., member(X, [1,2,3])", key=f"query_{safe_key}")

    if st.button("Run Query", key=f"run_{safe_key}"):
        if user_query:
            success, results, error_msg, metrics = run_prolog_query(
                user_query, file_path=file_path, session_id=st.session_state.session_id
            )

            # Analyze code quality statically
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code_content = f.read()
                static_metrics = analyze_prolog_code(code_content)
            except Exception:
                static_metrics = None

            if not success:
                st.error(f"Error: {error_msg}")
            elif not results:
                st.warning("Query returned false (no solutions found).")
            else:
                st.success(f"Query returned true with {len(results)} solution(s):")
                for idx, res in enumerate(results):
                    st.write(f"**Solution {idx + 1}:**")
                    if res == {}:
                        st.code("true.")
                    else:
                        st.code(res)

                if metrics or static_metrics:
                    st.divider()
                    st.markdown("### Evaluation Metrics")
                    mcols = st.columns(2)
                    with mcols[0]:
                        if metrics:
                            st.markdown("#### Execution Performance")
                            st.metric("LIPS", f"{metrics.get('lips', 0):.0f}")
                            st.metric("Inferences", metrics.get("inferences", 0))
                            st.metric("Execution Time (s)", f"{metrics.get('cputime', 0):.4f}")
                            st.markdown("#### Memory Stacks (bytes)")
                            st.metric("Local Stack", metrics.get("local_stack_used_bytes", 0))
                            st.metric("Global Stack", metrics.get("global_stack_used_bytes", 0))
                            st.metric("Trail Stack", metrics.get("trail_stack_used_bytes", 0))

                    with mcols[1]:
                        if static_metrics:
                            st.markdown("#### Code Quality")
                            st.metric("Clause Count", static_metrics.get("clause_count", 0))
                            st.metric("Avg Subgoals/Rule", f"{static_metrics.get('average_subgoals', 0):.1f}")
                            st.metric("Left Recursion Alerts", static_metrics.get("left_recursion_count", 0))
        else:
            st.warning("Please enter a query first.")


def display_test_generated_code(base_generated_code_path: str) -> None:
    """Renders the PySwip testing section beneath each model's output."""
    if "model_results" not in st.session_state or not st.session_state.model_results:
        return

    model_names = list(st.session_state.model_results.keys())

    if len(model_names) == 1:
        _render_test_section_for_model(model_names[0])
    else:
        cols = st.columns(2)
        for idx, model_name in enumerate(model_names):
            with cols[idx]:
                _render_test_section_for_model(model_name)

import os
import time
import re
import logging
import subprocess
from typing import Dict, Any, Set
import openai
import textstat


# Query SWI-Prolog at module load time for the complete set of built-in predicate names
def _load_swipl_builtins() -> Set[str]:
    """Queries SWI-Prolog for all built-in predicate names."""
    try:
        result = subprocess.run(
            [
                "swipl",
                "-q",
                "-t",
                "halt",
                "-g",
                "predicate_property(system:P, built_in), functor(P,Name,_), write(Name), nl, fail ; true",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        names = set(result.stdout.strip().split("\n"))
        names.discard("")
        logging.info(f"Loaded {len(names)} built-in predicates from SWI-Prolog.")
        return names
    except Exception as e:
        logging.warning(f"Could not query SWI-Prolog for built-ins: {e}. Using fallback list.")
        return {
            "member",
            "append",
            "length",
            "reverse",
            "sort",
            "findall",
            "write",
            "writeln",
            "nl",
            "format",
            "maplist",
            "between",
            "succ",
        }


_SWIPL_BUILTINS = _load_swipl_builtins()


# Initialize OpenRouter Client
def get_async_client() -> openai.AsyncOpenAI:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    return openai.AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY, max_retries=3, timeout=60.0
    )


def extract_prolog_comments(text: str) -> str:
    """Match single-line comments (%) and block comments (/* ... */)"""
    single_line_comments = re.findall(r"%(.*)", text)
    block_comments = re.findall(r"/\*(.*?)\*/", text, re.DOTALL)

    all_comments = " ".join(single_line_comments) + " " + " ".join(block_comments)
    return all_comments.strip()


def analyze_prolog_code(code: str) -> Dict[str, Any]:
    """Analyzes Prolog code and returns quality metrics."""
    lines = code.split("\n")

    # Lines of Code (non-empty, non-comment)
    comment_lines = 0
    code_lines = 0
    in_block_comment = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if in_block_comment:
            comment_lines += 1
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("/*"):
            comment_lines += 1
            if "*/" not in stripped:
                in_block_comment = True
            continue
        if stripped.startswith("%"):
            comment_lines += 1
            continue
        code_lines += 1

    total_meaningful = code_lines + comment_lines
    comment_ratio = (comment_lines / total_meaningful * 100) if total_meaningful > 0 else 0

    # Predicate definitions: lines starting with a lowercase letter followed by ( or :-
    predicate_heads = re.findall(r"^([a-z][a-zA-Z0-9_]*)\s*[\(:]", code, re.MULTILINE)
    # Filter out directives
    directives = {"use_module", "module", "ensure_loaded", "dynamic", "discontiguous", "multifile"}
    predicate_heads = [p for p in predicate_heads if p not in directives]

    unique_predicates = set(predicate_heads)
    clause_count = len(predicate_heads)
    predicate_count = len(unique_predicates)

    # Recursion detection: check if any predicate name appears in its own body
    uses_recursion = False
    # Find all rules (head :- body)
    rules = re.findall(r"^([a-z][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:-\s*(.*?)\.", code, re.MULTILINE | re.DOTALL)
    for pred_name, body in rules:
        if re.search(r"\b" + re.escape(pred_name) + r"\s*\(", body):
            uses_recursion = True
            break

    # Built-in predicate detection using the dynamically loaded set from SWI-Prolog
    # Find all predicate-like calls in the code and intersect with known builtins
    all_calls = set(re.findall(r"\b([a-z][a-zA-Z0-9_]*)\s*\(", code))
    # Also catch nullary builtins like nl, true, fail
    all_calls.update(re.findall(r"\b([a-z][a-zA-Z0-9_]*)\b", code))
    found_builtins = sorted(all_calls & _SWIPL_BUILTINS - unique_predicates)

    return {
        "lines_of_code": code_lines,
        "predicate_count": predicate_count,
        "clause_count": clause_count,
        "comment_ratio": round(comment_ratio, 1),
        "uses_recursion": uses_recursion,
        "builtin_predicates": found_builtins,
    }


async def generate_openrouter_response_async(
    model_id: str, prompt: str, params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Generates an asynchronous response from OpenRouter."""
    client = get_async_client()
    try:
        start_time = time.time()

        api_kwargs: Dict[str, Any] = {"model": model_id, "messages": [{"role": "user", "content": prompt}]}

        # Only send params that differ from defaults (avoids type issues with strict providers)
        _defaults = {
            "temperature": 1.0,
            "top_p": 1.0,
            "max_tokens": 4096,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }
        if params:
            for key, default_val in _defaults.items():
                val = params.get(key)
                if val is not None and val != default_val:
                    api_kwargs[key] = int(val) if key == "max_tokens" else float(val)

        completion = await client.chat.completions.create(**api_kwargs)
        end_time = time.time()

        response_message = completion.choices[0].message
        response_text = response_message.content if response_message.content else ""

        prompt_tokens = completion.usage.prompt_tokens if completion.usage else 0
        completion_tokens = completion.usage.completion_tokens if completion.usage else 0

        comments = extract_prolog_comments(response_text)
        readability = textstat.flesch_reading_ease(comments) if comments else "N/A (No comments found)"  # type: ignore

        return {
            "text": response_text,
            "time_taken": end_time - start_time,
            "tokens_prompt": prompt_tokens,
            "tokens_completion": completion_tokens,
            "readability_score": readability,
        }
    except Exception as e:
        logging.error(f"Error generating OpenRouter response (async): {e}", exc_info=True)
        return {"error": f"Error generating response: {str(e)}"}

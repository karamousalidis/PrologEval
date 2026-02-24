import streamlit as st
import asyncio
from typing import Dict, Any, Callable
from core.llm_service import generate_openrouter_response_async
from frontend.code_generation import manage_models_dialog


def _render_evaluation_result(gen_model_name: str, evaluator_name: str, eval_result: Dict[str, Any]):
    st.markdown(f"#### {evaluator_name} → {gen_model_name}")
    if "error" in eval_result:
        st.error(eval_result["error"])
    else:
        eval_cols = st.columns(2)
        eval_cols[0].metric("Time Taken", f"{eval_result['time_taken']:.2f}s")
        eval_cols[1].metric("Tokens (Input/Output)", f"{eval_result['tokens_prompt']}/{eval_result['tokens_completion']}")
        st.text_area(f"Eval {evaluator_name} {gen_model_name}:", eval_result["text"], height=400, disabled=True, label_visibility="collapsed")


def handle_evaluation(evaluation_template: str, available_models: Dict[str, Dict[str, Any]], on_change_callback: Callable) -> None:
    """Handles the evaluation prompt logic with up to 2 evaluator models."""
    st.divider()
    st.subheader("Evaluate the AI Output")
    
    default_eval = [list(available_models.keys())[0]] if available_models else []
    selected_evaluators = st.multiselect("Choose up to 2 evaluator models:", list(available_models.keys()), default=default_eval, max_selections=2, key="eval_multiselect")

    if st.button("Manage Models", help="Add or remove models from your configuration", key="eval_manage_btn"):
        manage_models_dialog(available_models, on_change_callback)

    if st.button("Evaluate Output"):
        if "model_results" not in st.session_state or not st.session_state.model_results:
            st.error("No output available to evaluate. Generate text first.")
        elif not selected_evaluators:
            st.error("Please select at least one evaluator model.")
        else:
            st.subheader("Evaluation Results")
            
            # For each generated model's code, evaluate with each selected evaluator
            gen_model_names = list(st.session_state.model_results.keys())
            
            async def evaluate_all():
                tasks = []
                for evaluator_name in selected_evaluators:
                    evaluator_id = available_models[evaluator_name]["id"]
                    evaluator_params = available_models[evaluator_name].get("params")
                    for gen_model in gen_model_names:
                        generated_text = st.session_state.model_results[gen_model]["text"]
                        final_eval_prompt = evaluation_template.replace("{{generated_code}}", generated_text)
                        tasks.append(generate_openrouter_response_async(evaluator_id, final_eval_prompt, params=evaluator_params))
                return await asyncio.gather(*tasks)
                
            with st.spinner(f"Evaluating with {', '.join(selected_evaluators)}..."):
                all_results = asyncio.run(evaluate_all())
            
            # Unpack results: evaluators × generated models
            result_idx = 0
            if len(selected_evaluators) == 1:
                evaluator_name = selected_evaluators[0]
                if len(gen_model_names) == 1:
                    _render_evaluation_result(gen_model_names[0], evaluator_name, all_results[0])
                else:
                    cols = st.columns(2)
                    for idx, gen_model in enumerate(gen_model_names):
                        with cols[idx]:
                            _render_evaluation_result(gen_model, evaluator_name, all_results[idx])
            else:
                cols = st.columns(2)
                for eval_idx, evaluator_name in enumerate(selected_evaluators):
                    with cols[eval_idx]:
                        for gen_model in gen_model_names:
                            _render_evaluation_result(gen_model, evaluator_name, all_results[result_idx])
                            result_idx += 1

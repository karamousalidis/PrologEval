import streamlit as st
import asyncio
from core import utils
from typing import Dict, Any, List, Tuple, Callable
from core.llm_service import generate_openrouter_response_async
from core.prolog_evaluator import extract_prolog_code, save_generated_code, run_prolog_query

def display_sidebar() -> None:
    """Renders the session history in the sidebar."""
    st.sidebar.title("Session History")

    if not st.session_state.history:
        st.sidebar.info("No generations yet.")
    else:
        for i, record in enumerate(reversed(st.session_state.history)):
            models_str = ", ".join(record.get('models', [record.get('model', 'Unknown')]))
            with st.sidebar.expander(f"Run {len(st.session_state.history) - i}: {models_str}"):
                st.write(f"**Prompt:** {record.get('user_prompt', '')[:50]}...")
                
                # Support legacy single-model format and new dual-model format
                results = record.get('results', {record.get('model', 'Unknown'): record})
                
                for model_name, res in results.items():
                    if len(results) > 1:
                        st.markdown(f"**{model_name}**")
                        
                    if "error" in res:
                        st.error(res["error"])
                        continue
                        
                    st.write(f"Time Taken: {res.get('time_taken', 0):.2f}s")
                    st.write(f"Tokens: {res.get('tokens_prompt', '?')}/{res.get('tokens_completion', '?')}")
                    
                    r_score = res.get('readability_score', 'N/A')
                    if isinstance(r_score, (float, int)):
                        r_score = f"{r_score:.2f}"
                    st.write(f"Readability Score: {r_score}")
                    
                    gen_text = res.get('generated_text', res.get('text', ''))
                    st.download_button(
                        label=f"Download {model_name} Code",
                        data=gen_text,
                        file_name=f"generated_code_{model_name.replace(' ', '_')}_{len(st.session_state.history) - i}.pl",
                        mime="text/plain",
                        key=f"dl_btn_{i}_{model_name}",
                        use_container_width=True
                    )
        
        st.sidebar.divider()
        if st.sidebar.button("Clear History", use_container_width=True):
            st.session_state.history = []
            st.rerun()

def display_user_input(suggested_prompts: List[str], prompt_template: str) -> Tuple[str, str]:
    """Renders the prompt input section."""
    st.subheader("Enter Your Prompt")
    user_prompt = st.text_area("Enter a prompt:", placeholder="Type your request here...")
    suggested = st.selectbox("Or select a suggested prompt:", [""] + suggested_prompts)

    manipulated_prompt = ""

    if suggested:
        user_prompt = suggested

    if user_prompt:
        manipulated_prompt = prompt_template.replace("{{user_prompt}}", user_prompt)

    st.subheader("Modified Prompt")
    st.text_area("Prompt Sent to Model:", manipulated_prompt, height=200, disabled=True)
    
    return user_prompt, manipulated_prompt

@st.dialog("Manage Models")
def manage_models_dialog(available_models: Dict[str, str], on_change_callback: Callable) -> None:
    tab1, tab2 = st.tabs(["Add New", "Remove"])
    
    with tab1:
        st.write("Add a custom model from OpenRouter.")
        name = st.text_input("Name:", placeholder="Llama 3")
        model_id = st.text_input("OpenRouter ID:", placeholder="meta-llama/llama-3-8b")
        if st.button("Save New Model"):
            if name and model_id:
                available_models[name] = model_id
                on_change_callback(available_models)
                st.success(f"Added {name}!")
                st.rerun()
            else:
                st.error("Please fill out both fields.")
                
    with tab2:
        st.write("Select a model to remove from the list.")
        model_to_remove = st.selectbox("Select model:", [""] + list(available_models.keys()))
        if st.button("Delete Selected Model", type="primary"):
            if model_to_remove and str(model_to_remove) in available_models: 
                name_ref = str(model_to_remove)
                del available_models[name_ref]
                on_change_callback(available_models)
                st.rerun()
            else:
                st.warning("Please select a valid model to remove.")

def display_model_selection(available_models: Dict[str, str], on_change_callback: Callable) -> List[str]:
    """Renders the AI model multi-selection."""
    st.subheader("Select up to two Generative AI Models")
    
    default_selection = [list(available_models.keys())[0]] if available_models else []
    selected = st.multiselect("Choose up to 2 models:", list(available_models.keys()), default=default_selection, max_selections=2)

    if st.button("Manage Models", help="Add or remove models from your configuration"):
        manage_models_dialog(available_models, on_change_callback)
            
    return selected

def handle_generation(user_prompt: str, manipulated_prompt: str, selected_models: List[str], available_models: Dict[str, str], base_generated_code_path: str) -> None:
    """Handles the Generation button click and updates session state."""
    if st.button("Generate Output"):
        if not user_prompt:
            st.error("Please enter a prompt first.")
        elif not selected_models:
            st.error("Please select at least one model.")
        else:
            st.subheader("AI Generated Output")
            
            with st.spinner(f"Generating output using {', '.join(selected_models)}..."):
                async def fetch_all():
                    tasks = [generate_openrouter_response_async(available_models[m], manipulated_prompt) for m in selected_models]
                    return await asyncio.gather(*tasks)
                
                results = asyncio.run(fetch_all())
                
                st.session_state.model_results = {}
                st.session_state.generated_paths = {}
                history_results = {}
                
                for idx, (model_name, result) in enumerate(zip(selected_models, results)):
                    history_results[model_name] = result
                    if "error" in result:
                        st.error(f"{model_name}: {result['error']}")
                    else:
                        st.session_state.model_results[model_name] = result
                        
                        file_path = base_generated_code_path.replace(".pl", f"_{idx}.pl")
                        st.session_state.generated_paths[model_name] = file_path
                        
                        clean_code = extract_prolog_code(result["text"])
                        save_generated_code(clean_code, file_path=file_path)
                
                if history_results:
                    st.session_state.history.append({
                        "models": selected_models,
                        "user_prompt": user_prompt,
                        "results": history_results
                    })

def _render_metrics_and_output_for_model(model_name: str, result: Dict[str, Any]):
    st.markdown(f"### {model_name}")
    cols = st.columns(4)
    cols[0].metric("Time Taken", f"{result['time_taken']:.2f}s")
    cols[1].metric("Tokens (Input/Output)", f"{result['tokens_prompt']}/{result['tokens_completion']}")
    
    r_score = result.get('readability_score', 'N/A')
    if isinstance(r_score, (float, int)):
        r_score = f"{r_score:.2f}"
    cols[2].metric("Readability", r_score)

    st.write("**Generated Output:**")
    st.code(result["text"], language="prolog")

    st.download_button(
        label=f"Download Prolog Code",
        data=result["text"],
        file_name=f"generated_code_{model_name.replace(' ', '_')}.pl",
        mime="text/plain",
        key=f"dl_main_{model_name}",
        use_container_width=True
    )

def display_metrics_and_output() -> None:
    """Renders the generation metrics and generated output text area."""
    if "model_results" not in st.session_state or not st.session_state.model_results:
        return
        
    model_names = list(st.session_state.model_results.keys())
    
    if len(model_names) == 1:
        _render_metrics_and_output_for_model(model_names[0], st.session_state.model_results[model_names[0]])
    else:
        cols = st.columns(2)
        for idx, model_name in enumerate(model_names):
            with cols[idx]:
                _render_metrics_and_output_for_model(model_name, st.session_state.model_results[model_name])

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
            success, results, error_msg = run_prolog_query(user_query, file_path=file_path, session_id=st.session_state.session_id)
            
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

def handle_evaluation(evaluation_template: str, available_models: Dict[str, str], on_change_callback: Callable) -> None:
    """Handles the evaluation prompt logic with up to 2 evaluator models."""
    st.divider()
    st.subheader("Evaluate the AI Output")
    
    default_eval = [list(available_models.keys())[0]] if available_models else []
    
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
                    evaluator_id = available_models[evaluator_name]
                    for gen_model in gen_model_names:
                        generated_text = st.session_state.model_results[gen_model]["text"]
                        final_eval_prompt = evaluation_template.replace("{{generated_code}}", generated_text)
                        tasks.append(generate_openrouter_response_async(evaluator_id, final_eval_prompt))
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

def _render_evaluation_result(gen_model_name: str, evaluator_name: str, eval_result: Dict[str, Any]):
    st.markdown(f"#### {evaluator_name} → {gen_model_name}")
    if "error" in eval_result:
        st.error(eval_result["error"])
    else:
        eval_cols = st.columns(2)
        eval_cols[0].metric("Time Taken", f"{eval_result['time_taken']:.2f}s")
        eval_cols[1].metric("Tokens (Input/Output)", f"{eval_result['tokens_prompt']}/{eval_result['tokens_completion']}")
        st.text_area(f"Eval {evaluator_name} {gen_model_name}:", eval_result["text"], height=400, disabled=True, label_visibility="collapsed")


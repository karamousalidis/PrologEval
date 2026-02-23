import streamlit as st
from core import utils
from typing import Dict, Any, List, Tuple, Callable
from core.llm_service import generate_openrouter_response
from core.prolog_evaluator import extract_prolog_code, save_generated_code, run_prolog_query

def display_sidebar() -> None:
    """Renders the session history in the sidebar."""
    st.sidebar.title("Session History")

    if st.sidebar.button("Clear History"):
        st.session_state.history = []
        st.rerun()

    if not st.session_state.history:
        st.sidebar.info("No generations yet.")
    else:
        for i, record in enumerate(reversed(st.session_state.history)):
            with st.sidebar.expander(f"Run {len(st.session_state.history) - i}: {record['model']}"):
                st.write(f"**Prompt:** {record['user_prompt'][:50]}...")
                st.write(f"**Time Taken:** {record['time_taken']:.2f}s")
                st.write(f"**Tokens (Prompt/Completion):** {record['tokens_prompt']} / {record['tokens_completion']}")
                
                r_score = record.get('readability_score', 'N/A')
                if isinstance(r_score, (float, int)):
                    r_score = f"{r_score:.2f}"
                st.write(f"**Readability Score:** {r_score}")
                
                st.download_button(
                    label="Download this output",
                    data=record['generated_text'],
                    file_name=f"generated_code_run_{len(st.session_state.history) - i}.pl",
                    mime="text/plain",
                    key=f"dl_btn_{i}"
                )

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

def display_model_selection(available_models: Dict[str, str], on_change_callback: Callable) -> str:
    """Renders the AI model radio selection."""
    st.subheader("Select a Generative AI Model")
    
    selected = st.radio("Choose a model:", list(available_models.keys())) # type: ignore

    if st.button("Manage Models", help="Add or remove models from your configuration"):
        manage_models_dialog(available_models, on_change_callback)
            
    return str(selected)

def handle_generation(user_prompt: str, manipulated_prompt: str, selected_model: str, available_models: Dict[str, str], generated_code_path: str) -> None:
    """Handles the Generation button click and updates session state."""
    if st.button("Generate Output"):
        if not user_prompt:
            st.error("Please enter a prompt first.")
        else:
            st.subheader("AI Generated Output")
            model_id = available_models[selected_model]
            
            with st.spinner(f"Generating output using {selected_model}..."):
                result = generate_openrouter_response(model_id, manipulated_prompt)
                
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.session_state.generated_text = result["text"]
                    st.session_state.metrics = result
                    
                    st.session_state.history.append({
                        "model": selected_model,
                        "user_prompt": user_prompt,
                        "generated_text": result["text"],
                        "time_taken": result["time_taken"],
                        "tokens_prompt": result["tokens_prompt"],
                        "tokens_completion": result["tokens_completion"],
                        "readability_score": result["readability_score"]
                    })
                    
                    clean_code = extract_prolog_code(st.session_state.generated_text)
                    save_generated_code(clean_code, file_path=generated_code_path)

def display_metrics_and_output() -> None:
    """Renders the generation metrics and generated output text area."""
    if not st.session_state.generated_text:
        return

    if "metrics" in st.session_state:
        cols = st.columns(4)
        cols[0].metric("Time Taken", f"{st.session_state.metrics['time_taken']:.2f}s")
        cols[1].metric("Prompt Tokens", st.session_state.metrics['tokens_prompt'])
        cols[2].metric("Completion Tokens", st.session_state.metrics['tokens_completion'])
        
        r_score = st.session_state.metrics.get('readability_score', 'N/A')
        if isinstance(r_score, (float, int)):
            r_score = f"{r_score:.2f}"
        cols[3].metric("Comment Readability", r_score)

    st.write("**Generated Output:**")
    st.code(st.session_state.generated_text, language="prolog")

    st.download_button(
        label="Download Prolog Code",
        data=st.session_state.generated_text,
        file_name="generated_code.pl",
        mime="text/plain"
    )

def display_test_generated_code(generated_code_path: str) -> None:
    """Renders the PySwip testing section."""
    if not st.session_state.generated_text:
        return

    st.subheader("Test Generated Code")
    user_query = st.text_input("Enter a Prolog query (e.g., member(X, [1, 2, 3])):")
    
    if st.button("Run Query"):
        if user_query:
            success, results, error_msg = run_prolog_query(user_query, file_path=generated_code_path, session_id=st.session_state.session_id)
            
            if not success:
               st.error(f"Error executing query: {error_msg}")
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

def handle_evaluation(evaluation_template: str, available_models: Dict[str, str], on_change_callback: Callable) -> None:
    """Handles the evaluation prompt logic for a second LLM query."""
    st.divider()
    st.subheader("Evaluate the AI Output")
    
    selected_evaluator = st.radio("Choose an evaluator model:", list(available_models.keys())) # type: ignore
    
    if st.button("Manage Models", help="Add or remove models from your configuration", key="eval_manage_btn"):
        manage_models_dialog(available_models, on_change_callback)

    if st.button("Evaluate Output"):
        if not st.session_state.generated_text:
            st.error("No output available to evaluate. Generate text first.")
        else:
            st.subheader("Evaluation Result")

            final_evaluation_prompt = evaluation_template.replace("{{generated_code}}", str(st.session_state.generated_text))
            
            # Since selected_evaluator is strongly typed to Optional[Any], let's confirm it's a valid string key
            if not isinstance(selected_evaluator, str) or selected_evaluator not in available_models:
                st.error("Invalid evaluator selected.")
                return

            evaluator_id = available_models[selected_evaluator]
            
            with st.spinner(f"Evaluating output using {selected_evaluator}..."):
                eval_result = generate_openrouter_response(evaluator_id, final_evaluation_prompt)
                
                if "error" in eval_result:
                    evaluation_result = eval_result["error"]
                    st.error(evaluation_result)
                else:
                    evaluation_result = eval_result["text"]
                    
                    st.write("### Evaluation Metrics")
                    eval_cols = st.columns(3)
                    eval_cols[0].metric("Time Taken", f"{eval_result['time_taken']:.2f}s")
                    eval_cols[1].metric("Prompt Tokens", eval_result['tokens_prompt'])
                    eval_cols[2].metric("Completion Tokens", eval_result['tokens_completion'])

            st.text_area("Evaluation Result:", evaluation_result, height=400, disabled=True)

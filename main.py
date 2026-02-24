import streamlit as st
from dotenv import load_dotenv
import sys
import os
import uuid
from core import utils
from frontend import ui

# Load environmental variables
load_dotenv()

# Set wide layout and initialize sidebar state to collapsed
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# Initialize Session History
if "history" not in st.session_state:
    st.session_state.history = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

try:
    # Load configurations
    config = utils.load_config(file_path="config/config.yaml")
    paths = config.get("paths", {})
    
    # Load dynamic models from XML
    models_xml_path = paths.get("models_xml", "models.xml")
    # Migrate: if old flat format (str values) is cached, force reload
    if "available_models" in st.session_state:
        first_val = next(iter(st.session_state.available_models.values()), None)
        if isinstance(first_val, str):
            del st.session_state["available_models"]
    if "available_models" not in st.session_state:
        st.session_state.available_models = utils.load_models_xml(models_xml_path)
    available_models = st.session_state.available_models
    
    def update_models(new_models: dict) -> None:
        """Callback to save models and update state."""
        st.session_state.available_models = new_models
        utils.save_models_xml(new_models, models_xml_path)
    
    # Load required file text data
    prompt_file_path = paths.get("prompt", "prompt.txt")
    suggested_prompts = utils.load_suggested_prompts(prompt_file_path)
    
    manipulation_file_path = paths.get("modified_prompt", "modified_prompt.txt")
    prompt_template = utils.load_text_from_file(manipulation_file_path)
    
    evaluation_file_path = paths.get("evaluation_prompt", "evaluation_prompt.txt")
    evaluation_template = utils.load_text_from_file(evaluation_file_path)
    
    test_queries_path = paths.get("test_queries", "prompts/test_queries.yaml")
    test_queries = utils.load_test_queries(test_queries_path)
    
    base_generated_code_path = paths.get("generated_code", "generated_code.pl")
    # Create session-specific filename
    filename, ext = os.path.splitext(base_generated_code_path)
    generated_code_path = f"{filename}_{st.session_state.session_id}{ext}"
except Exception as e:
    st.error(f"Initialization Error: {e}")
    st.stop()

# Streamlit UI Setup
st.title("Evaluating Gen. AI tools for logic programming")

ui.display_sidebar()

mode = st.radio("Mode", ["Single Prompt", "Batch Benchmark"], horizontal=True, key="app_mode")

if mode == "Single Prompt":
    user_prompt, manipulated_prompt = ui.display_user_input(suggested_prompts, prompt_template)

    selected_models = ui.display_model_selection(available_models, update_models)

    ui.handle_generation(user_prompt, manipulated_prompt, selected_models, available_models, generated_code_path)

    ui.display_metrics_and_output()

    ui.display_test_generated_code(generated_code_path)

    ui.handle_evaluation(evaluation_template, available_models, update_models)
else:
    ui.display_batch_benchmark(suggested_prompts, prompt_template, available_models, test_queries)
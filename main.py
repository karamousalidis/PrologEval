import streamlit as st
from dotenv import load_dotenv
import sys
import utils
import ui

# Load environmental variables
load_dotenv()

# Set wide layout and initialize sidebar state to collapsed
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# Initialize Session History
if "history" not in st.session_state:
    st.session_state.history = []
if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""

try:
    # Load configurations
    config = utils.load_config()
    available_models = config.get("models", {})
    paths = config.get("paths", {})
    
    # Load required file text data
    prompt_file_path = paths.get("prompt", "prompt.txt")
    suggested_prompts = utils.load_suggested_prompts(prompt_file_path)
    
    manipulation_file_path = paths.get("modified_prompt", "modified_prompt.txt")
    prompt_template = utils.load_text_from_file(manipulation_file_path)
    
    evaluation_file_path = paths.get("evaluation_prompt", "evaluation_prompt.txt")
    evaluation_template = utils.load_text_from_file(evaluation_file_path)
    
    generated_code_path = paths.get("generated_code", "generated_code.pl")
except Exception as e:
    st.error(f"Initialization Error: {e}")
    st.stop()

# Streamlit UI Setup
st.title("Evaluating Gen. AI tools for logic programming")

ui.display_sidebar()

user_prompt, manipulated_prompt = ui.display_user_input(suggested_prompts, prompt_template)

selected_model = ui.display_model_selection(available_models)

ui.handle_generation(user_prompt, manipulated_prompt, selected_model, available_models, generated_code_path)

ui.display_metrics_and_output()

ui.display_test_generated_code(generated_code_path)

ui.handle_evaluation(evaluation_template, available_models)
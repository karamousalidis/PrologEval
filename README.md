# AI Logic Programming Evaluator

This project is a Streamlit-based dashboard designed to evaluate the performance of various Generative AI models when prompted to write logic programming code (specifically Prolog).

## Features

- **Multi-Model Support**: Evaluate state-of-the-art models including:
  - Claude 3.5 Sonnet
  - Gemini 2.0 Flash
  - DeepSeek R1 & DeepSeek R1 Distill 70B
  - ChatGPT (GPT-3.5)
- **Unified API Routing**: All model requests are routed cleanly through the OpenRouter API key.
- **Detailed Metrics**: Every generation tracks:
  - **Time Taken**: Execution speed of the API call.
  - **Token Usage**: Both prompt and completion tokens.
  - **Readability**: Calculates a Flesch Reading Ease score for generated Prolog comments (`%` and `/* */`) using the `textstat` library.
- **Session History**: A collapsible sidebar keeps a log of all prompts, models, and metrics used during your current session.
- **Prolog Export**: Easily download the generated text as a `.pl` file, or rely on the automatic save to `generated_code.pl` in the project folder.
- **Test Generated Code**: Run Prolog queries directly from the UI using `pyswip`. The app connects to your local SWI-Prolog installation to evaluate the logic and return variable bindings instantly.

## Prerequisites

- Python 3.13+
- An [OpenRouter API Key](https://openrouter.ai/)
- SWI-Prolog (`swipl`) installed on your system (Required for backend query evaluation via PySwip).

## Setup Instructions

1. **Clone or Download the Repository**
2. **Create a Virtual Environment**: It is highly recommended to isolate your dependencies.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure Environment Variables**:
   Create a `.env` file in the root directory and add your OpenRouter key:
   ```env
   OPENROUTER_API_KEY="your_openrouter_api_key_here"
   ```

## Usage

1. Activate your virtual environment: 
   ```bash
   source .venv/bin/activate
   ```
2. Start the Streamlit application:
   ```bash
   streamlit run main.py
   ```
3. Open your browser and navigate to the URL provided in the terminal.
4. Enter a custom prompt or choose from the suggested list.
5. Select a model and click "Generate Output".

## Project Structure

- `core/`: Python backend and utility scripts.
  - `llm_service.py`: API communication with OpenRouter and text analytics.
  - `prolog_evaluator.py`: PySwip Prolog engine instance and query execution.
  - `utils.py`: General utility functions.
- `frontend/`: UI logic.
  - `ui.py`: Streamlit rendering components.
- `config/`: Configuration files.
  - `config.yaml`: Centralized configuration for file paths.
  - `models.xml`: Dynamic OpenRouter model mappings.
- `prompts/`: Text file templates for LLMs.
  - `prompt.txt`: Suggested prompts for the UI.
  - `modified_prompt.txt`: Template to wrap user input before querying.
  - `evaluation_prompt.txt`: Template for evaluating the generated output.
- `temp/`: Temporary session-specific generated Prolog files (`*.pl`).
- `main.py`: The entry point for the Streamlit application.
- `requirements.txt`: Python package dependencies.

# AI Logic Programming Evaluator

A Streamlit-based dashboard for evaluating how well various Generative AI models write logic programming code (Prolog). Compare outputs side-by-side, run Prolog queries live, and evaluate the generated code with a second AI model — all from one interface.

## Features

- **Side-by-Side Comparison**: Select up to **2 models** simultaneously. Outputs, metrics, and test results are displayed in parallel columns for instant comparison.
- **Async Generation**: When comparing two models, API calls are dispatched concurrently via `asyncio` for faster results.
- **Multi-Model Support**: All models are routed through the OpenRouter API. Add or remove models at any time via the built-in model manager.
- **Per-Model Parameter Configuration**: Each model can be individually configured with Temperature, Top P, and Max Tokens via the **Configure Parameters** tab in the model manager. Settings persist in `models.xml`.
- **Detailed Metrics**: Every generation tracks:
  - **Time Taken**: Execution speed of the API call.
  - **Token Usage**: Input and output token counts.
  - **Readability**: Flesch Reading Ease score for generated Prolog comments using `textstat`.
- **Code Quality Metrics**: Static analysis of generated Prolog code, displayed in a collapsible panel:
  - Lines of Code, Predicate Count, Clause Count, Comment Ratio, Recursion Detection
  - **Built-in Predicate Detection**: Dynamically queries SWI-Prolog for its full built-in predicate catalog at startup, then reports which standard library predicates the model used vs reimplemented.
  - Model parameters used for generation are displayed inline.
- **Export Comparison Report**: Download a structured Markdown report with all metrics, model parameters, code quality analysis, generated code, and evaluation results.
- **Live Prolog Testing**: Run Prolog queries directly from the UI using `pyswip`. Each model's output gets its own independent query input and results area.
- **Dual Evaluator Support**: Select up to 2 evaluator models to assess the generated code side-by-side, with async concurrent evaluation.
- **Static Analysis Security**: Generated code is scanned for dangerous patterns (shell commands, file I/O, `halt`, etc.) before execution — blocking unsafe operations while allowing standard Prolog I/O.
- **Session History**: A collapsible sidebar logs all prompts, models, and metrics. Download any past output as a `.pl` file.
- **Session Isolation**: Each browser session gets a unique ID, so multiple users can run queries concurrently without interference.
- **Dark Theme**: Dark mode enabled by default via `.streamlit/config.toml`. Users can toggle to light mode in Streamlit's Settings menu.
- **API Resilience**: Automatic retries (3 attempts) and 60-second timeout on OpenRouter API calls.

## Prerequisites

- Python 3.13+
- An [OpenRouter API Key](https://openrouter.ai/)
- SWI-Prolog (`swipl`) installed on your system (required for query evaluation via PySwip and built-in predicate detection)

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repo-url> && cd PrologEval
   ```

2. **Create a Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   OPENROUTER_API_KEY="your_openrouter_api_key_here"
   ```

## Usage

1. Activate your virtual environment:
   ```bash
   source .venv/bin/activate
   ```
2. Start the application:
   ```bash
   streamlit run main.py
   ```
3. Open the URL shown in the terminal.
4. Enter a custom prompt or choose from the suggested list.
5. Select 1 or 2 models and click **Generate Output**.
6. Expand **Code Quality Metrics** to see structural analysis and parameters used.
7. Test the generated code with Prolog queries directly in the UI.
8. Optionally evaluate the output using 1 or 2 evaluator models.
9. Click **Download Comparison Report** to export a full Markdown summary.
10. Configure per-model parameters via **Manage Models → Configure Parameters**.

## Project Structure

```
PrologEval/
├── core/                     # Python backend logic
│   ├── llm_service.py        #   Async OpenRouter API client, text analytics & code quality analysis
│   ├── prolog_evaluator.py   #   PySwip engine, static analysis & query execution
│   └── utils.py              #   Config loading, XML parsing, file helpers
├── frontend/                 # Streamlit UI
│   └── ui.py                 #   All rendering: sidebar, model selection, outputs, reports
├── config/                   # Configuration
│   ├── config.yaml           #   Centralized path settings
│   └── models.xml            #   Model mappings & per-model parameters
├── .streamlit/               # Streamlit configuration
│   └── config.toml           #   Theme settings (dark mode default)
├── prompts/                  # LLM prompt templates
│   ├── prompt.txt            #   Suggested prompts for the UI
│   ├── modified_prompt.txt   #   Wrapper template for user input
│   └── evaluation_prompt.txt #   Template for AI-based code evaluation
├── temp/                     # Session-specific generated .pl files
├── main.py                   # Entry point
├── requirements.txt          # Dependencies
└── .gitignore
```

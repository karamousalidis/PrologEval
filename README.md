# AI Logic Programming Evaluator

A Streamlit-based dashboard for evaluating how well various Generative AI models write logic programming code (Prolog). Compare outputs side-by-side, run Prolog queries live, and evaluate the generated code with a second AI model — all from one interface.

## Features

- **Side-by-Side Comparison**: Select up to **2 models** simultaneously. Outputs, metrics, and test results are displayed in parallel columns for instant comparison.
- **Async Generation**: When comparing two models, API calls are dispatched concurrently via `asyncio` for faster results.
- **Multi-Model Support**: All models are routed through the OpenRouter API. Add or remove models at any time via the built-in model manager.
- **Detailed Metrics**: Every generation tracks:
  - **Time Taken**: Execution speed of the API call.
  - **Token Usage**: Input and output token counts.
  - **Readability**: Flesch Reading Ease score for generated Prolog comments using `textstat`.
- **Live Prolog Testing**: Run Prolog queries directly from the UI using `pyswip`. Each model's output gets its own independent query input and results area.
- **Dual Evaluator Support**: Select up to 2 evaluator models to assess the generated code side-by-side, with async concurrent evaluation.
- **Static Analysis Security**: Generated code is scanned for dangerous patterns (shell commands, file I/O, `halt`, etc.) before execution — blocking unsafe operations while allowing standard Prolog I/O.
- **Session History**: A collapsible sidebar logs all prompts, models, and metrics. Download any past output as a `.pl` file.
- **Session Isolation**: Each browser session gets a unique ID, so multiple users can run queries concurrently without interference.

## Prerequisites

- Python 3.13+
- An [OpenRouter API Key](https://openrouter.ai/)
- SWI-Prolog (`swipl`) installed on your system (required for query evaluation via PySwip)

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
6. Test the generated code with Prolog queries directly in the UI.
7. Optionally evaluate the output using 1 or 2 evaluator models.

## Project Structure

```
PrologEval/
├── core/                     # Python backend logic
│   ├── llm_service.py        #   Async OpenRouter API client & text analytics
│   ├── prolog_evaluator.py   #   PySwip engine, static analysis & query execution
│   └── utils.py              #   Config loading, XML parsing, file helpers
├── frontend/                 # Streamlit UI
│   └── ui.py                 #   All rendering: sidebar, model selection, outputs
├── config/                   # Configuration
│   ├── config.yaml           #   Centralized path settings
│   └── models.xml            #   Dynamic OpenRouter model mappings
├── prompts/                  # LLM prompt templates
│   ├── prompt.txt            #   Suggested prompts for the UI
│   ├── modified_prompt.txt   #   Wrapper template for user input
│   └── evaluation_prompt.txt #   Template for AI-based code evaluation
├── temp/                     # Session-specific generated .pl files
├── main.py                   # Entry point
├── requirements.txt          # Dependencies
└── .gitignore
```

# AI Logic Programming Evaluator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Streamlit-based dashboard for evaluating how well various Generative AI models write logic programming code (Prolog). Compare outputs side-by-side, run Prolog queries live, and evaluate the generated code with a second AI model — all from one interface.

## Features

- **Side-by-Side Comparison**: Select up to **2 models** simultaneously. Outputs, metrics, and test results are displayed in parallel columns for instant comparison.
- **Async Generation**: When comparing two models, API calls are dispatched concurrently via `asyncio` for faster results.
- **Batch Benchmark Mode**: Switch to **Batch Benchmark** to run all suggested prompts (or a custom selection) against any number of models in one go. Includes automatic correctness testing via predefined queries (`prompts/test_queries.yaml`), ad-hoc query inputs per cell, a summary matrix with test pass rates, and Markdown/CSV export.
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

> **Tip:** Don't want to install SWI-Prolog locally? Use the [Docker setup](#docker-quick-start) instead.

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repo-url> && cd PrologEval
   ```

2. **Create a Virtual Environment & Install Dependencies**
   It is highly recommended to use [`uv`](https://docs.astral.sh/uv/getting-started/installation/) instead of standard `pip` for lightning-fast resolution and installation.
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   uv pip install .
   ```

4. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your OpenRouter API key.

## Docker Quick Start

The quickest way to get running — no need to install Python, SWI-Prolog, or any dependencies locally.

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

1. **Clone & configure**
   ```bash
   git clone <repo-url> && cd PrologEval
   cp .env.example .env
   # Edit .env and add your OpenRouter API key
   ```

2. **Build & run**
   ```bash
   docker compose up
   ```

3. **Open** [http://localhost:8501](http://localhost:8501)

To rebuild after changes:
```bash
docker compose up --build
```

## Testing & Linting

The `core/` backend logic translates into a fully mocked `pytest` suite (no SWI-Prolog or network required). The project uses `ruff` for code formatting and linting.

1. Install the development dependencies and setup git hooks:
   ```bash
   uv pip install -e ".[dev]"
   pre-commit install
   ```
2. Run the test suite:
   ```bash
   uv run pytest tests/ -v
   ```
3. Format and lint the code:
   ```bash
   uv run ruff format .
   uv run ruff check . --fix
   ```

## CI/CD

The project uses **GitHub Actions** (`.github/workflows/ci.yml`) which runs automatically on every push or pull request to `main` and `develop`:

| Job | What it does |
|-----|--------------|
| **Lint & Format** | Runs `ruff check` and `ruff format --check` |
| **Tests** | Installs SWI-Prolog, runs `pytest tests/ -v` |
| **Docker Build** | Verifies the Docker image builds successfully |

Jobs run sequentially (Lint → Tests → Docker). If linting fails, tests and Docker are skipped entirely.

## Usage

1. Activate your virtual environment:
   ```bash
   source .venv/bin/activate
   ```
2. Start the application:
   ```bash
   uv run streamlit run main.py
   ```
3. Open the URL shown in the terminal.
4. Choose a mode at the top: **Single Prompt** or **Batch Benchmark**.

### Single Prompt Mode
5. Enter a custom prompt or choose from the suggested list.
6. Select 1 or 2 models and click **Generate Output**.
7. Expand **Code Quality Metrics** to see structural analysis and parameters used.
8. Test the generated code with Prolog queries directly in the UI.
9. Optionally evaluate the output using 1 or 2 evaluator models.
10. Click **Download Comparison Report** to export a full Markdown summary.

### Batch Benchmark Mode
5. Select any number of models and prompts (all suggested prompts selected by default).
6. Toggle **Auto-run predefined test queries** to run correctness tests from `prompts/test_queries.yaml`.
7. Click **Run Benchmark** — models execute concurrently per prompt with a live progress bar.
8. Review the **Results Matrix** (time / tokens / readability / test pass rate per cell).
9. Expand individual prompts for detailed per-model metrics, code, and ad-hoc query testing.
10. Export results as **Markdown** or **CSV**.

## Query Testing Architecture

The application uses two different Prolog execution strategies depending on the mode:

### Single/Dual Mode — In-process via PySwip

Queries run inside a **shared global SWI-Prolog instance** via PySwip. Predicate isolation is achieved by regex-based name-prefixing (e.g. `fibonacci/2` → `sess_abc123_fibonacci/2`). This is fast (no process overhead) but can be fragile with complex multi-predicate programs where the regex misses internal cross-references.

### Batch Mode — Isolated `swipl` subprocesses

Each query spawns a **fresh `swipl` process** with its own clean namespace:

```
code + query → swipl -q -g "consult('file.pl'), query, halt" → stdout → PASS/FAIL
```

This eliminates namespace collisions, built-in predicate clashes, and regex fragility at the cost of ~100ms subprocess overhead per query.

| | Single/Dual Mode | Batch Mode |
|---|---|---|
| **Engine** | PySwip (in-process) | `swipl` subprocess |
| **Isolation** | Regex name-mangling | Process-level |
| **Predefined queries** | ❌ Manual only | ✅ Auto from `test_queries.yaml` |

## Project Structure

```
PrologEval/
├── core/                     # Python backend logic
│   ├── llm_service.py        #   Async OpenRouter API client, text analytics & code quality analysis
│   ├── prolog_evaluator.py   #   PySwip engine, static analysis & query execution
│   └── utils.py              #   Config loading, XML parsing, file helpers
├── frontend/                 # Streamlit UI
│   ├── ui.py                 #   Re-export shim (keeps main.py imports unchanged)
│   ├── sidebar.py            #   Session history sidebar
│   ├── code_generation.py    #   Prompt input, model management, generation, metrics & reports
│   ├── evaluation.py         #   AI-based code evaluation with dual evaluator support
│   ├── testing.py            #   Live Prolog query testing via PySwip
│   └── batch.py              #   Batch benchmark: matrix comparison, subprocess testing, CSV/MD export
├── config/                   # Configuration
│   ├── config.yaml           #   Centralized path settings
│   └── models.xml            #   Model mappings & per-model parameters
├── .streamlit/               # Streamlit configuration
│   └── config.toml           #   Theme settings (dark mode default)
├── prompts/                  # LLM prompt templates
│   ├── prompt.txt            #   Suggested prompts for the UI
│   ├── modified_prompt.txt   #   Wrapper template for user input
│   ├── evaluation_prompt.txt #   Template for AI-based code evaluation
│   └── test_queries.yaml     #   Predefined test queries for batch auto-testing
├── temp/                     # Session-specific generated .pl files
├── main.py                   # Entry point
├── pyproject.toml            # Project metadata & dependencies
├── Dockerfile                # Container image (Python 3.13 + SWI-Prolog)
├── docker-compose.yml        # One-command startup
├── .dockerignore             # Build context exclusions
├── .env.example              # Environment variable template
└── .gitignore
```

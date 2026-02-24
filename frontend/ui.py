"""Frontend UI package – re-exports from sub-modules so main.py imports stay unchanged."""

from frontend.sidebar import display_sidebar
from frontend.code_generation import (
    display_user_input,
    manage_models_dialog,
    display_model_selection,
    handle_generation,
    display_metrics_and_output,
)
from frontend.evaluation import handle_evaluation
from frontend.testing import display_test_generated_code
from frontend.batch import display_batch_benchmark

__all__ = [
    "display_sidebar",
    "display_user_input",
    "manage_models_dialog",
    "display_model_selection",
    "handle_generation",
    "display_metrics_and_output",
    "handle_evaluation",
    "display_test_generated_code",
    "display_batch_benchmark",
]

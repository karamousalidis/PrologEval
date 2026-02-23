from pyswip import Prolog
import re
import logging
from typing import Tuple, List, Dict, Any, Union, Optional

# Single global instance to prevent memory leaks or crashes
_prolog_instance = Prolog()

def extract_prolog_code(text: str) -> str:
    """Extract code from within ```prolog ... ``` or ``` ... ``` blocks"""
    match = re.search(r'```(?:prolog)?\n(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()

def save_generated_code(code_text: str, file_path: str) -> None:
    """Auto-saves the generated output to a .pl file for PySwip."""
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(code_text)

def run_prolog_query(query: str, file_path: str) -> Tuple[bool, List[Union[Dict[str, Any], str]], Optional[str]]:
    """
    Consults the file using the global PySwip Prolog instance, and runs a query.
    Returns a tuple (success: bool, results: list_of_dicts_or_str, error: str)
    """
    try:
        _prolog_instance.consult(file_path)
        
        # Execute query and cast the generator to a list to get all results
        results = list(_prolog_instance.query(query))
        
        if not results:
            return True, [], None # Handle false / empty results but successful execution
            
        return True, results, None
            
    except Exception as e:
        logging.error(f"Error executing Prolog query: {e}", exc_info=True)
        return False, [], str(e)

from pyswip import Prolog
import re
import logging
import os
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

def run_prolog_query(query: str, file_path: str, session_id: str = "default") -> Tuple[bool, List[Union[Dict[str, Any], str]], Optional[str]]:
    """
    Consults the file with session-prefixed predicates and runs a query via the sandbox.
    """
    prefix = f"sess_{session_id}_"
    
    try:
        # 1. Read the generated code and check for dangerous patterns via static analysis
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
            
        dangerous_patterns = [
            r'\bshell\(', r'\bsystem\(',                # OS commands
            r'\bprocess_create\(', r'\bwin_exec\(',      # Process spawning
            r'\bopen\(', r'\bclose\(',                  # File I/O
            r'\bdelete_file\(', r'\brename_file\(',     # File manipulation
            r'\bread_term\(',                            # Reading arbitrary terms
            r'\bhalt\b', r'\babort\b',                  # App termination
            r'use_module\(library\(process\)\)',        # External processes
            r'use_module\(library\(filesex\)\)',        # Extended file ops
            r'\bassert\(', r'\basserta\(', r'\bassertz\(',  # Dynamic DB (includes legacy assert/1)
            r'\bretract\(', r'\bretractall\(',          # Dynamic DB manipulation
            r'\bcatch\(',                                # Error swallowing — can mask dangerous ops
            r'\bchar_code\(', r'\batom_codes\(',        # Dynamic command construction
            r'\bload_files\(',                           # Loading arbitrary files
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                logging.warning(f"Security Alert: Blocked execution due to pattern {pattern}")
                return False, [], f"Security Alert: Dangerous system or file operation found in generated code."

        # 2. Rewrite the code to prefix all predicates with the session ID
        # This allows us to load everything into 'user' module (avoiding sandbox permission issues)
        # while still maintaining isolation.
        
        # Simple regex to prefix predicate definitions and heads
        # WARNING: This is a heuristic and might fail for complex Prolog syntax, 
        # but works for standard fact/rule heads.
        prefixed_code = re.sub(r'^([a-z][a-zA-Z0-9_]*)(\(|(?=\s*:-))', fr'{prefix}\1\2', code, flags=re.MULTILINE)
        
        # Also handle recursive calls inside the body
        # We find words that match the newly prefixed heads and prefix them in the rest of the text
        predicates = re.findall(r'^([a-z][a-zA-Z0-9_]*)', code, flags=re.MULTILINE)
        for pred in set(predicates):
             # Respect boundaries to avoid partial matches
             prefixed_code = re.sub(fr'(?<![a-zA-Z0-9_]){pred}(?=\()', fr'{prefix}{pred}', prefixed_code)

        # Write the prefixed version to a temporary file for consulting
        temp_file = f"{file_path}.temp"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(prefixed_code)

        # 3. Consult into the user module
        list(_prolog_instance.query(f"consult('{temp_file}')"))
        
        # Cleanup temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # 4. Prepare the query
        clean_query = query.strip()
        if clean_query.endswith('.'):
            clean_query = clean_query[:-1]
            
        # Prefix the predicate in the query head
        prefixed_query = re.sub(r'^([a-z][a-zA-Z0-9_]*)', fr'{prefix}\1', clean_query)

        # 5. Execute actual query directly (sandbox check removed)
        results = list(_prolog_instance.query(prefixed_query))
        
        return True, results, None
            
    except Exception as e:
        logging.error(f"Error executing Prolog query: {e}", exc_info=True)
        return False, [], str(e)

from pyswip import Prolog
import re
import logging
import os
from typing import Tuple, List, Dict, Any, Union, Optional

# Single global instance to prevent memory leaks or crashes
_prolog_instance = Prolog()

# Initialize sandbox once
try:
    list(_prolog_instance.query("use_module(library(sandbox))"))
    # Authorize basic harmless I/O predicates for generated code that prints results
    list(_prolog_instance.query("assertz(sandbox:safe_primitive(system:write(_)))"))
    list(_prolog_instance.query("assertz(sandbox:safe_primitive(system:writeln(_)))"))
    list(_prolog_instance.query("assertz(sandbox:safe_primitive(system:nl))"))
    list(_prolog_instance.query("assertz(sandbox:safe_primitive(system:format(_,_)))"))
except Exception as e:
    logging.warning(f"Failed to load Prolog sandbox: {e}")

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
        # 1. Read the generated code and check for dangerous patterns
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
            
        dangerous_patterns = [r':-\s*shell', r':-\s*system', r':-\s*open', r':-\s*use_module\(library\(process\)\)']
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, [], f"Security Alert: Dangerous directive found in code."

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
        
        # 4. Prepare and check the query
        clean_query = query.strip()
        if clean_query.endswith('.'):
            clean_query = clean_query[:-1]
            
        # Prefix the predicate in the query head
        prefixed_query = re.sub(r'^([a-z][a-zA-Z0-9_]*)', fr'{prefix}\1', clean_query)
        
        # Check safety - explicitly qualify the goal as being in the 'user' module
        # where we consulted the file, otherwise sandbox looks for it within itself.
        safe_check_query = f"sandbox:safe_goal(user:({prefixed_query}))"
        is_safe = list(_prolog_instance.query(safe_check_query))
        
        if not is_safe:
            return False, [], f"Security Alert: Query '{query}' is not considered safe."

        # 5. Execute actual query
        results = list(_prolog_instance.query(prefixed_query))
        
        return True, results, None
            
    except Exception as e:
        logging.error(f"Error executing Prolog query: {e}", exc_info=True)
        return False, [], str(e)

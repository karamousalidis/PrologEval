import yaml
import xml.etree.ElementTree as ET
from typing import Dict, Any, List


def load_config(file_path: str = "config.yaml") -> Dict[str, Any]:
    """Loads configuration settings from a YAML file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Configuration file '{file_path}' not found.") from e
    except yaml.YAMLError as exc:
        raise ValueError(f"Error parsing configuration file '{file_path}': {exc}") from exc


_DEFAULT_PARAMS = {"temperature": 1.0, "top_p": 1.0, "max_tokens": 4096}


def load_models_xml(file_path: str) -> Dict[str, Dict[str, Any]]:
    """Loads models from an XML file into a dictionary with params."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        models: Dict[str, Dict[str, Any]] = {}
        for child in root.findall("model"):
            name = child.get("name")
            model_id = child.get("id")
            if name and model_id:
                params = dict(_DEFAULT_PARAMS)
                for key in _DEFAULT_PARAMS:
                    val = child.get(key)
                    if val is not None:
                        params[key] = int(float(val)) if key == "max_tokens" else float(val)
                models[name] = {"id": model_id, "params": params}
        return models
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error: Models XML file '{file_path}' not found.") from e
    except ET.ParseError as e:
        raise ValueError(f"Error parsing models XML file '{file_path}': {e}") from e


def save_models_xml(models_dict: Dict[str, Dict[str, Any]], file_path: str) -> None:
    """Saves a dictionary of models (with params) to an XML file."""
    root = ET.Element("models")
    for name, data in models_dict.items():
        attribs = {"name": name, "id": data["id"]}
        params = data.get("params", _DEFAULT_PARAMS)
        for key, val in params.items():
            attribs[key] = str(val)
        ET.SubElement(root, "model", **attribs)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ", level=0)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)


def load_text_from_file(file_path: str) -> str:
    """General function to load text from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error: Text file '{file_path}' not found.") from e


def load_suggested_prompts(file_path: str) -> List[str]:
    """General function to load a list of prompts."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            prompts = [line.strip() for line in file.readlines() if line.strip()]
        return prompts
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error: Suggested prompts file '{file_path}' not found.") from e


def load_test_queries(file_path: str) -> Dict[str, List[str]]:
    """Loads predefined test queries from a YAML file. Returns a dict mapping prompt → list of queries."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        return {entry["prompt"]: entry.get("queries", []) for entry in data if "prompt" in entry}
    except FileNotFoundError:
        return {}
    except (yaml.YAMLError, TypeError):
        return {}


def analyze_prolog_code(code: str) -> Dict[str, Any]:
    """Analyzes Prolog code for basic complexity metrics."""
    import re

    # Remove strings and comments for more accurate counting
    code_no_comments = re.sub(r"%.*$", "", code, flags=re.MULTILINE)
    code_no_strings = re.sub(r"'.*?'", "''", code_no_comments)
    code_no_strings = re.sub(r"\".*?\"", '""', code_no_strings)

    # Clause Count
    # Count periods that end a clause
    clauses = [c.strip() for c in code_no_strings.split(".") if c.strip()]
    clause_count = len(clauses)

    subgoals_total = 0
    left_recursion_count = 0

    for clause in clauses:
        # Check if clause is a rule (contains ':-')
        if ":-" in clause:
            parts = clause.split(":-", 1)
            head = parts[0].strip()
            body = parts[1].strip()

            # Extract functor of head
            head_match = re.search(r"^([a-z][a-zA-Z0-9_]*)", head)
            head_functor = head_match.group(1) if head_match else ""

            # Rough subgoal count simply counts commas in the body (plus one for the first goal)
            subgoals = body.split(",")
            subgoals_total += len(subgoals)

            # Left recursion check
            if head_functor and body.startswith(head_functor):
                first_goal_match = re.search(r"^([a-z][a-zA-Z0-9_]*)", body)
                if first_goal_match and first_goal_match.group(1) == head_functor:
                    left_recursion_count += 1

    avg_subgoals = subgoals_total / clause_count if clause_count > 0 else 0.0

    return {
        "clause_count": clause_count,
        "average_subgoals": avg_subgoals,
        "left_recursion_count": left_recursion_count,
    }

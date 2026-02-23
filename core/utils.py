import os
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

def load_models_xml(file_path: str) -> Dict[str, str]:
    """Loads models from an XML file into a dictionary."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        models = {}
        for child in root.findall("model"):
            name = child.get("name")
            model_id = child.get("id")
            if name and model_id:
                models[name] = model_id
        return models
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error: Models XML file '{file_path}' not found.") from e
    except ET.ParseError as e:
        raise ValueError(f"Error parsing models XML file '{file_path}': {e}") from e

def save_models_xml(models_dict: Dict[str, str], file_path: str) -> None:
    """Saves a dictionary of models to an XML file with indentation."""
    root = ET.Element("models")
    for name, model_id in models_dict.items():
        ET.SubElement(root, "model", name=name, id=model_id)
        
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

import os
import yaml
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

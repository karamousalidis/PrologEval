"""Tests for core/utils.py — config loading, model XML I/O, text helpers."""
import pytest
import yaml
from core.utils import (
    load_config,
    load_models_xml,
    save_models_xml,
    load_text_from_file,
    load_suggested_prompts,
    load_test_queries,
    _DEFAULT_PARAMS,
)


# ── load_config ──────────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_load_valid_yaml(self, tmp_path):
        cfg = {"paths": {"prompt": "prompts/prompt.txt"}, "debug": True}
        f = tmp_path / "config.yaml"
        f.write_text(yaml.dump(cfg))

        result = load_config(str(f))
        assert result == cfg

    def test_empty_yaml_returns_empty_dict(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")

        assert load_config(str(f)) == {}

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_invalid_yaml_raises_value_error(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(":\n  - :\n  : bad: [")

        with pytest.raises(ValueError, match="Error parsing"):
            load_config(str(f))


# ── load_models_xml / save_models_xml ────────────────────────────────────────

class TestModelsXml:
    SAMPLE_MODELS = {
        "GPT-4o": {
            "id": "openai/gpt-4o",
            "params": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 2048},
        },
        "Claude": {
            "id": "anthropic/claude-3.5-sonnet",
            "params": {"temperature": 1.0, "top_p": 1.0, "max_tokens": 4096},
        },
    }

    def test_round_trip(self, tmp_path):
        f = tmp_path / "models.xml"
        save_models_xml(self.SAMPLE_MODELS, str(f))
        loaded = load_models_xml(str(f))

        assert loaded.keys() == self.SAMPLE_MODELS.keys()
        for name, data in self.SAMPLE_MODELS.items():
            assert loaded[name]["id"] == data["id"]
            assert loaded[name]["params"]["temperature"] == data["params"]["temperature"]
            assert loaded[name]["params"]["top_p"] == data["params"]["top_p"]
            assert loaded[name]["params"]["max_tokens"] == data["params"]["max_tokens"]

    def test_default_params_applied(self, tmp_path):
        """A model XML without explicit params should get the defaults."""
        xml = '<?xml version="1.0" ?>\n<models><model name="Test" id="test/id"/></models>'
        f = tmp_path / "models.xml"
        f.write_text(xml)

        loaded = load_models_xml(str(f))
        assert loaded["Test"]["params"] == _DEFAULT_PARAMS

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_models_xml("/nonexistent/models.xml")

    def test_invalid_xml_raises_value_error(self, tmp_path):
        f = tmp_path / "bad.xml"
        f.write_text("<models><model name='oops'")

        with pytest.raises(ValueError, match="Error parsing"):
            load_models_xml(str(f))


# ── load_text_from_file ──────────────────────────────────────────────────────

class TestLoadTextFromFile:
    def test_reads_content(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello world")

        assert load_text_from_file(str(f)) == "hello world"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_text_from_file("/nonexistent/file.txt")


# ── load_suggested_prompts ───────────────────────────────────────────────────

class TestLoadSuggestedPrompts:
    def test_loads_prompts(self, tmp_path):
        f = tmp_path / "prompts.txt"
        f.write_text("Write fibonacci\n\nWrite factorial\n")

        result = load_suggested_prompts(str(f))
        assert result == ["Write fibonacci", "Write factorial"]

    def test_blank_lines_filtered(self, tmp_path):
        f = tmp_path / "prompts.txt"
        f.write_text("\n\n  \nOnly this one\n  \n")

        assert load_suggested_prompts(str(f)) == ["Only this one"]

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_suggested_prompts("/nonexistent/prompts.txt")


# ── load_test_queries ────────────────────────────────────────────────────────

class TestLoadTestQueries:
    def test_loads_queries(self, tmp_path):
        data = [
            {"prompt": "fibonacci", "queries": ["fib(5, X)"]},
            {"prompt": "factorial", "queries": ["fact(5, X)", "fact(0, X)"]},
        ]
        f = tmp_path / "queries.yaml"
        f.write_text(yaml.dump(data))

        result = load_test_queries(str(f))
        assert result == {"fibonacci": ["fib(5, X)"], "factorial": ["fact(5, X)", "fact(0, X)"]}

    def test_missing_file_returns_empty(self):
        assert load_test_queries("/nonexistent/queries.yaml") == {}

    def test_malformed_yaml_returns_empty(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(":\n  - :\n  : bad: [")

        assert load_test_queries(str(f)) == {}

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")

        assert load_test_queries(str(f)) == {}

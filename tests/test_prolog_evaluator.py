"""Tests for core/prolog_evaluator.py — code extraction, saving, security patterns, query execution."""
import re
import pytest
from unittest.mock import patch, MagicMock
from core.prolog_evaluator import (
    extract_prolog_code,
    save_generated_code,
    DANGEROUS_PATTERNS,
)


# ── extract_prolog_code ──────────────────────────────────────────────────────

class TestExtractPrologCode:
    def test_prolog_fenced_block(self):
        text = "Here is code:\n```prolog\nfoo(X) :- bar(X).\n```\nDone."
        assert extract_prolog_code(text) == "foo(X) :- bar(X)."

    def test_generic_fenced_block(self):
        text = "```\nfoo(1).\n```"
        assert extract_prolog_code(text) == "foo(1)."

    def test_plain_text_returned_as_is(self):
        text = "foo(X) :- bar(X)."
        assert extract_prolog_code(text) == "foo(X) :- bar(X)."

    def test_strips_whitespace(self):
        text = "```prolog\n  hello(world).  \n```"
        assert extract_prolog_code(text) == "hello(world)."

    def test_case_insensitive_fence(self):
        text = "```PROLOG\nfoo(1).\n```"
        assert extract_prolog_code(text) == "foo(1)."


# ── save_generated_code ──────────────────────────────────────────────────────

class TestSaveGeneratedCode:
    def test_writes_content(self, tmp_path):
        f = tmp_path / "test.pl"
        save_generated_code("foo(1).\nbar(2).", str(f))

        assert f.read_text() == "foo(1).\nbar(2)."

    def test_overwrites_existing(self, tmp_path):
        f = tmp_path / "test.pl"
        f.write_text("old content")
        save_generated_code("new content", str(f))

        assert f.read_text() == "new content"


# ── DANGEROUS_PATTERNS ───────────────────────────────────────────────────────

class TestDangerousPatterns:
    """Ensure the security regex patterns catch known dangerous operations."""

    @pytest.mark.parametrize("dangerous_code", [
        "shell('rm -rf /')",
        "system('ls')",
        "process_create(path('/bin/sh'), [], [])",
        "open('file.txt', write, S)",
        "close(S)",
        "delete_file('important.pl')",
        "rename_file('a', 'b')",
        "halt",
        "abort",
        "use_module(library(process))",
        "use_module(library(filesex))",
        "load_files(['evil.pl'])",
    ])
    def test_pattern_catches_dangerous_code(self, dangerous_code):
        matched = any(
            re.search(pattern, dangerous_code, re.IGNORECASE)
            for pattern in DANGEROUS_PATTERNS
        )
        assert matched, f"No pattern matched: {dangerous_code}"

    @pytest.mark.parametrize("safe_code", [
        "fibonacci(0, 0).",
        "factorial(N, F) :- N > 0, N1 is N - 1, factorial(N1, F1), F is N * F1.",
        "write('hello'), nl.",
        "member(X, [1,2,3]).",
        "findall(X, between(1,10,X), L).",
    ])
    def test_pattern_allows_safe_code(self, safe_code):
        matched = any(
            re.search(pattern, safe_code, re.IGNORECASE)
            for pattern in DANGEROUS_PATTERNS
        )
        assert not matched, f"False positive on safe code: {safe_code}"


# ── run_prolog_query ─────────────────────────────────────────────────────────

class TestRunPrologQuery:
    """Mocks the Prolog instance so tests don't need SWI-Prolog installed."""

    @pytest.fixture
    def prolog_file(self, tmp_path):
        f = tmp_path / "test.pl"
        f.write_text("foo(1).\nfoo(2).\nbar(X) :- foo(X).")
        return str(f)

    @pytest.fixture
    def dangerous_file(self, tmp_path):
        f = tmp_path / "evil.pl"
        f.write_text("run :- shell('rm -rf /').")
        return str(f)

    def test_security_block(self, dangerous_file):
        """Dangerous code should be blocked before Prolog ever sees it."""
        from core.prolog_evaluator import run_prolog_query
        success, results, error = run_prolog_query("run.", dangerous_file)

        assert success is False
        assert "Security Alert" in error

    def test_successful_query(self, prolog_file):
        """Mock Prolog to simulate a successful consult and query."""
        mock_prolog = MagicMock()
        mock_prolog.query = MagicMock(return_value=iter([{"X": 1}]))

        with patch("core.prolog_evaluator._prolog_instance", mock_prolog):
            from core.prolog_evaluator import run_prolog_query
            success, results, error = run_prolog_query(
                "bar(X).", prolog_file, skip_prefix=True
            )

        assert success is True
        assert error is None

    def test_query_exception_returns_error(self, prolog_file):
        """Prolog exceptions should be caught and returned as an error string."""
        mock_prolog = MagicMock()
        mock_prolog.query = MagicMock(side_effect=Exception("existence_error"))

        with patch("core.prolog_evaluator._prolog_instance", mock_prolog):
            from core.prolog_evaluator import run_prolog_query
            success, results, error = run_prolog_query(
                "bar(X).", prolog_file, skip_prefix=True
            )

        assert success is False
        assert "existence_error" in error

    def test_trailing_dot_stripped(self, prolog_file):
        """Query trailing dot should be stripped before execution."""
        mock_prolog = MagicMock()
        mock_prolog.query = MagicMock(return_value=iter([]))

        with patch("core.prolog_evaluator._prolog_instance", mock_prolog):
            from core.prolog_evaluator import run_prolog_query
            run_prolog_query("foo(1).", prolog_file, skip_prefix=True)

        # The query passed to Prolog should NOT have a trailing dot
        call_args = mock_prolog.query.call_args_list
        # Second call is the actual query (first is consult)
        actual_query = call_args[1][0][0]
        assert not actual_query.endswith(".")

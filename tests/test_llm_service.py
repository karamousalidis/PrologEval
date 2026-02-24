"""Tests for core/llm_service.py — comment extraction, code analysis, async generation."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ── extract_prolog_comments ──────────────────────────────────────────────────


class TestExtractPrologComments:
    """Pure string function — no mocking needed."""

    def test_single_line_comments(self):
        from core.llm_service import extract_prolog_comments

        code = "% This is a comment\nfoo(X) :- bar(X).\n% Another comment"
        result = extract_prolog_comments(code)
        assert "This is a comment" in result
        assert "Another comment" in result

    def test_block_comments(self):
        from core.llm_service import extract_prolog_comments

        code = "/* Block comment here */\nfoo(X) :- bar(X)."
        result = extract_prolog_comments(code)
        assert "Block comment here" in result

    def test_mixed_comments(self):
        from core.llm_service import extract_prolog_comments

        code = "% Single\n/* Block */\nfoo(X)."
        result = extract_prolog_comments(code)
        assert "Single" in result
        assert "Block" in result

    def test_no_comments(self):
        from core.llm_service import extract_prolog_comments

        code = "foo(X) :- bar(X)."
        result = extract_prolog_comments(code)
        assert result == ""


# ── analyze_prolog_code ──────────────────────────────────────────────────────


class TestAnalyzePrologCode:
    """Patches _SWIPL_BUILTINS so tests don't need SWI-Prolog installed."""

    BUILTINS = {"member", "append", "length", "write", "nl", "findall", "between"}

    @pytest.fixture(autouse=True)
    def _patch_builtins(self):
        with patch("core.llm_service._SWIPL_BUILTINS", self.BUILTINS):
            yield

    def _analyze(self, code):
        from core.llm_service import analyze_prolog_code

        return analyze_prolog_code(code)

    def test_lines_of_code(self):
        code = "foo(1).\nfoo(2).\n% comment\n\nbar(X) :- foo(X)."
        result = self._analyze(code)
        assert result["lines_of_code"] == 3  # 2 facts + 1 rule (blank + comment excluded)

    def test_predicate_and_clause_count(self):
        code = "foo(1).\nfoo(2).\nbar(X) :- foo(X)."
        result = self._analyze(code)
        assert result["predicate_count"] == 2  # foo, bar
        assert result["clause_count"] == 3  # foo/1 x2, bar/1 x1

    def test_comment_ratio(self):
        code = "% comment\nfoo(1)."
        result = self._analyze(code)
        assert result["comment_ratio"] == 50.0

    def test_recursion_detected(self):
        code = "factorial(0, 1).\nfactorial(N, F) :- N > 0, N1 is N - 1, factorial(N1, F1), F is N * F1."
        result = self._analyze(code)
        assert result["uses_recursion"] is True

    def test_no_recursion(self):
        code = "greet :- write('hello'), nl."
        result = self._analyze(code)
        assert result["uses_recursion"] is False

    def test_builtin_detection(self):
        code = "go :- findall(X, member(X, [1,2,3]), L), write(L), nl."
        result = self._analyze(code)
        builtins = result["builtin_predicates"]
        assert "findall" in builtins
        assert "member" in builtins
        assert "write" in builtins
        assert "nl" in builtins

    def test_user_defined_not_listed_as_builtin(self):
        """If the user defines 'append', it shouldn't be listed as built-in usage."""
        code = "append([], L, L).\nappend([H|T], L, [H|R]) :- append(T, L, R)."
        result = self._analyze(code)
        assert "append" not in result["builtin_predicates"]

    def test_block_comment_counting(self):
        code = "/* line1\nline2\nline3 */\nfoo(1)."
        result = self._analyze(code)
        assert result["comment_ratio"] == 75.0  # 3 comment lines, 1 code line


# ── generate_openrouter_response_async ───────────────────────────────────────


class TestGenerateOpenrouterResponseAsync:
    @pytest.fixture(autouse=True)
    def _patch_builtins(self):
        """Patch builtins to avoid SWI-Prolog dependency at import time."""
        with patch("core.llm_service._load_swipl_builtins", return_value=set()):
            yield

    @pytest.mark.asyncio
    async def test_success_returns_dict(self):
        mock_message = MagicMock()
        mock_message.content = "foo(X) :- bar(X). % a comment"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch("core.llm_service.get_async_client", return_value=mock_client):
            from core.llm_service import generate_openrouter_response_async

            result = await generate_openrouter_response_async("test/model", "Write hello world in Prolog")

        assert "text" in result
        assert result["tokens_prompt"] == 10
        assert result["tokens_completion"] == 20
        assert "time_taken" in result
        assert "readability_score" in result

    @pytest.mark.asyncio
    async def test_error_returns_error_dict(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))

        with patch("core.llm_service.get_async_client", return_value=mock_client):
            from core.llm_service import generate_openrouter_response_async

            result = await generate_openrouter_response_async("test/model", "prompt")

        assert "error" in result
        assert "API down" in result["error"]

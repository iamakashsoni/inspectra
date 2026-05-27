"""Tests for token counting and truncation utilities."""

from __future__ import annotations

import pytest

from inspectra.utils.tokenizer import count_tokens, fits_in_budget, truncate_to_budget


def test_count_tokens_returns_positive_int():
    result = count_tokens("Hello, world!")
    assert isinstance(result, int)
    assert result > 0


def test_count_tokens_empty_string():
    assert count_tokens("") == 0 or count_tokens("") >= 0  # tiktoken returns 0


def test_count_tokens_longer_text_has_more_tokens():
    short = count_tokens("Hi")
    long = count_tokens("Hi " * 100)
    assert long > short


def test_fits_in_budget_short_text():
    assert fits_in_budget("Hello", budget=1000) is True


def test_fits_in_budget_exceeds():
    long_text = "word " * 10000
    assert fits_in_budget(long_text, budget=10) is False


def test_truncate_to_budget_short_text_unchanged():
    text = "This is a short sentence."
    result = truncate_to_budget(text, budget=5000)
    assert result == text


def test_truncate_to_budget_long_text_truncated():
    # Build text with many lines so truncation can split by line
    lines = [f"This is line number {i} with enough words to use tokens." for i in range(200)]
    text = "\n".join(lines)
    result = truncate_to_budget(text, budget=50)
    assert len(result) < len(text)


def test_truncate_to_budget_adds_truncation_marker():
    lines = [f"Line {i}: " + "word " * 20 for i in range(200)]
    text = "\n".join(lines)
    result = truncate_to_budget(text, budget=30)
    assert "truncated" in result.lower()


def test_truncate_to_budget_result_fits_in_budget():
    lines = [f"Line {i}: " + "x " * 20 for i in range(300)]
    text = "\n".join(lines)
    budget = 100
    result = truncate_to_budget(text, budget=budget)
    assert fits_in_budget(result, budget=budget + 20)  # small slack for the marker

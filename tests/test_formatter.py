# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Tests for the v2 formatter — verifies GitHub suggestion blocks are rendered
for code-like suggested fixes (the highest-impact UX change in v2).
"""

from inspectra.review.formatter import _looks_like_code, _render_suggested_fix, results_to_markdown
from inspectra.review.severity import ReviewIssue, ReviewResult, Severity


def test_looks_like_code_detects_multiline():
    assert _looks_like_code("def foo():\n    return 1") is True


def test_looks_like_code_detects_function():
    assert _looks_like_code("def foo(): pass") is True


def test_looks_like_code_rejects_prose():
    assert _looks_like_code("Use parameterized queries instead.") is False


def test_looks_like_code_rejects_empty():
    assert _looks_like_code("") is False


def test_render_suggested_fix_renders_code_as_suggestion_block():
    issue = ReviewIssue(
        title="SQL Injection",
        severity=Severity.CRITICAL,
        category="Security",
        explanation="bad",
        suggested_fix="cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
        file_path="auth/service.py",
        line_number=42,
    )
    out = _render_suggested_fix(issue)
    assert "```suggestion" in out
    assert "cursor.execute" in out


def test_render_suggested_fix_renders_prose_inline():
    issue = ReviewIssue(
        title="Missing docstring",
        severity=Severity.LOW,
        category="Maintainability",
        explanation="no docstring",
        suggested_fix="Add a one-line docstring describing what this function does.",
        file_path="foo.py",
        line_number=1,
    )
    out = _render_suggested_fix(issue)
    assert "```suggestion" not in out
    assert "Add a one-line docstring" in out


def test_results_to_markdown_includes_rule_id():
    issue = ReviewIssue(
        title="SQL Injection",
        severity=Severity.CRITICAL,
        category="Security",
        explanation="bad",
        suggested_fix="",
        file_path="foo.py",
        line_number=1,
        rule_id="SQL_INJECTION",
    )
    result = ReviewResult(file_path="foo.py", issues=[issue], summary="ok")
    md = results_to_markdown([result])
    assert "`SQL_INJECTION`" in md


def test_results_to_markdown_groups_by_severity():
    issues = [
        ReviewIssue(title="low", severity=Severity.LOW, explanation="low", file_path="f"),
        ReviewIssue(title="crit", severity=Severity.CRITICAL, explanation="crit", file_path="f"),
    ]
    result = ReviewResult(file_path="f", issues=issues, summary="ok")
    md = results_to_markdown([result])
    # Critical section should appear before Low section
    crit_pos = md.find("Critical Severity")
    low_pos = md.find("Low Severity")
    assert crit_pos < low_pos

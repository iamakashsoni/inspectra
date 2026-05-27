"""Tests for markdown formatter."""

import pytest

from inspectra.review.formatter import results_to_markdown, results_to_pr_comment
from inspectra.review.severity import ReviewIssue, ReviewResult, Severity


@pytest.fixture
def sample_results() -> list[ReviewResult]:
    return [
        ReviewResult(
            file_path="auth/service.py",
            summary="Contains a SQL injection vulnerability.",
            issues=[
                ReviewIssue(
                    title="SQL Injection",
                    severity=Severity.CRITICAL,
                    category="Security",
                    explanation="User input concatenated into SQL.",
                    suggested_fix="Use parameterized queries.",
                    file_path="auth/service.py",
                    line_number=42,
                ),
                ReviewIssue(
                    title="Missing timeout",
                    severity=Severity.MEDIUM,
                    category="Performance",
                    explanation="HTTP request has no timeout.",
                    file_path="auth/service.py",
                ),
            ],
        )
    ]


def test_markdown_contains_title(sample_results):
    md = results_to_markdown(sample_results)
    assert "Inspectra Code Review" in md


def test_markdown_contains_severities(sample_results):
    md = results_to_markdown(sample_results)
    assert "Critical" in md
    assert "Medium" in md


def test_markdown_contains_issue_title(sample_results):
    md = results_to_markdown(sample_results)
    assert "SQL Injection" in md


def test_markdown_empty_results():
    md = results_to_markdown([ReviewResult(file_path="clean.py")])
    assert "No issues found" in md


def test_pr_comment_contains_table(sample_results):
    comment = results_to_pr_comment(sample_results)
    assert "|" in comment  # markdown table
    assert "1" in comment  # critical count

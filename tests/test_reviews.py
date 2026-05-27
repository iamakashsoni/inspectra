"""Tests for GitHub PR review event decision logic."""

from __future__ import annotations

from inspectra.github.reviews import ReviewEvent, decide_review_event
from inspectra.review.severity import ReviewIssue, ReviewResult, Severity


def _result_with(*severities: Severity) -> ReviewResult:
    return ReviewResult(
        file_path="foo.py",
        issues=[
            ReviewIssue(title=f"Issue {i}", severity=s, explanation="x")
            for i, s in enumerate(severities)
        ],
    )


def test_no_issues_approves():
    assert decide_review_event([ReviewResult(file_path="clean.py")]) == ReviewEvent.APPROVE


def test_critical_requests_changes():
    assert (
        decide_review_event([_result_with(Severity.CRITICAL)])
        == ReviewEvent.REQUEST_CHANGES
    )


def test_high_requests_changes():
    assert (
        decide_review_event([_result_with(Severity.HIGH)])
        == ReviewEvent.REQUEST_CHANGES
    )


def test_medium_only_comments():
    assert (
        decide_review_event([_result_with(Severity.MEDIUM)])
        == ReviewEvent.COMMENT
    )


def test_low_only_comments():
    assert (
        decide_review_event([_result_with(Severity.LOW)])
        == ReviewEvent.COMMENT
    )


def test_info_only_comments():
    assert (
        decide_review_event([_result_with(Severity.INFO)])
        == ReviewEvent.COMMENT
    )


def test_mixed_critical_and_low_requests_changes():
    result = _result_with(Severity.CRITICAL, Severity.LOW)
    assert decide_review_event([result]) == ReviewEvent.REQUEST_CHANGES


def test_multiple_files_any_critical_requests_changes():
    results = [
        ReviewResult(file_path="clean.py"),
        _result_with(Severity.CRITICAL),
    ]
    assert decide_review_event(results) == ReviewEvent.REQUEST_CHANGES


def test_multiple_files_all_clean_approves():
    results = [
        ReviewResult(file_path="a.py"),
        ReviewResult(file_path="b.py"),
    ]
    assert decide_review_event(results) == ReviewEvent.APPROVE

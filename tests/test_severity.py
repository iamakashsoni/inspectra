"""Tests for severity models."""


from inspectra.review.severity import ReviewIssue, ReviewResult, Severity


def test_severity_from_string():
    assert Severity.from_string("critical") == Severity.CRITICAL
    assert Severity.from_string("HIGH") == Severity.HIGH
    assert Severity.from_string("unknown") == Severity.INFO


def test_severity_has_emoji():
    for s in Severity:
        assert s.emoji in ("🔴", "🟠", "🟡", "🔵", "⚪")


def test_review_result_counts():
    result = ReviewResult(
        file_path="foo.py",
        issues=[
            ReviewIssue(
                title="A",
                severity=Severity.CRITICAL,
                explanation="bad",
            ),
            ReviewIssue(
                title="B",
                severity=Severity.HIGH,
                explanation="also bad",
            ),
            ReviewIssue(
                title="C",
                severity=Severity.LOW,
                explanation="minor",
            ),
        ],
    )
    assert result.critical_count == 1
    assert result.high_count == 1
    assert result.has_issues is True


def test_review_result_empty():
    result = ReviewResult(file_path="clean.py")
    assert result.has_issues is False
    assert result.critical_count == 0

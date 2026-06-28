# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Tests for baseline suppression (Phase 2 #30)."""

import json
import tempfile
from pathlib import Path

from inspectra.review.baseline import (
    Baseline, Suppression, load_baseline, apply_baseline, save_baseline, add_suppression,
)
from inspectra.review.severity import ReviewIssue, ReviewResult, Severity


def _make_issue(rule_id="SQL_INJECTION", file_path="auth.py", line=42, severity=Severity.CRITICAL):
    return ReviewIssue(
        title="SQL Injection", severity=severity, category="Security",
        explanation="bad", suggested_fix="use param query",
        file_path=file_path, line_number=line, rule_id=rule_id,
    )


def test_baseline_matches_by_rule_id():
    baseline = Baseline(suppressions=[
        Suppression(rule_id="SQL_INJECTION"),
    ])
    issue = _make_issue(rule_id="SQL_INJECTION")
    assert baseline.matches(issue, "auth.py") is True


def test_baseline_does_not_match_different_rule_id():
    baseline = Baseline(suppressions=[
        Suppression(rule_id="SQL_INJECTION"),
    ])
    issue = _make_issue(rule_id="XSS")
    assert baseline.matches(issue, "auth.py") is False


def test_baseline_matches_case_insensitive():
    baseline = Baseline(suppressions=[
        Suppression(rule_id="sql_injection"),
    ])
    issue = _make_issue(rule_id="SQL_INJECTION")
    assert baseline.matches(issue, "auth.py") is True


def test_baseline_matches_with_file_filter():
    baseline = Baseline(suppressions=[
        Suppression(rule_id="SQL_INJECTION", file_path="auth.py"),
    ])
    # Matches in the specified file
    assert baseline.matches(_make_issue(), "auth.py") is True
    # Does NOT match in a different file
    assert baseline.matches(_make_issue(), "other.py") is False


def test_baseline_matches_with_line_filter():
    baseline = Baseline(suppressions=[
        Suppression(rule_id="SQL_INJECTION", file_path="auth.py", line_number=42),
    ])
    # Matches at the specified line
    assert baseline.matches(_make_issue(line=42), "auth.py") is True
    # Does NOT match at a different line
    assert baseline.matches(_make_issue(line=99), "auth.py") is False


def test_baseline_expired_suppression_ignored():
    from datetime import date, timedelta
    past = (date.today() - timedelta(days=1)).isoformat()
    baseline = Baseline(suppressions=[
        Suppression(rule_id="SQL_INJECTION", expires=past),
    ])
    # Expired suppression should NOT match
    assert baseline.matches(_make_issue(), "auth.py") is False


def test_baseline_future_expiry_still_matches():
    from datetime import date, timedelta
    future = (date.today() + timedelta(days=30)).isoformat()
    baseline = Baseline(suppressions=[
        Suppression(rule_id="SQL_INJECTION", expires=future),
    ])
    assert baseline.matches(_make_issue(), "auth.py") is True


def test_load_baseline_returns_empty_for_missing_file():
    baseline = load_baseline("/nonexistent/baseline.json")
    assert baseline.suppressions == []


def test_load_baseline_returns_empty_for_none():
    baseline = load_baseline(None)
    assert baseline.suppressions == []


def test_load_baseline_reads_json():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "baseline.json"
        path.write_text(json.dumps({
            "version": 1,
            "suppressions": [
                {"rule_id": "SQL_INJECTION", "file_path": "auth.py", "reason": "legacy"},
            ]
        }))
        baseline = load_baseline(path)
        assert len(baseline.suppressions) == 1
        assert baseline.suppressions[0].rule_id == "SQL_INJECTION"
        assert baseline.suppressions[0].file_path == "auth.py"
        assert baseline.suppressions[0].reason == "legacy"


def test_load_baseline_handles_corrupt_json():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "baseline.json"
        path.write_text("not valid json{{{")
        baseline = load_baseline(path)
        assert baseline.suppressions == []  # corrupt file → empty baseline, no crash


def test_apply_baseline_filters_matching_issues():
    baseline = Baseline(suppressions=[
        Suppression(rule_id="SQL_INJECTION"),
    ])
    results = [ReviewResult(
        file_path="auth.py",
        issues=[
            _make_issue(rule_id="SQL_INJECTION"),     # suppressed
            _make_issue(rule_id="XSS"),               # kept
        ],
        summary="ok",
    )]
    filtered, suppressed_count = apply_baseline(results, baseline)
    assert suppressed_count == 1
    assert len(filtered[0].issues) == 1
    assert filtered[0].issues[0].rule_id == "XSS"


def test_apply_baseline_with_no_suppressions():
    baseline = Baseline()  # empty
    results = [ReviewResult(
        file_path="auth.py",
        issues=[_make_issue()],
        summary="ok",
    )]
    filtered, suppressed_count = apply_baseline(results, baseline)
    assert suppressed_count == 0
    assert len(filtered[0].issues) == 1  # nothing suppressed


def test_save_and_load_roundtrip():
    baseline = Baseline(suppressions=[
        Suppression(rule_id="SQL_INJECTION", file_path="auth.py", line_number=42, reason="legacy"),
    ])
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "baseline.json"
        save_baseline(baseline, path)
        loaded = load_baseline(path)
        assert len(loaded.suppressions) == 1
        assert loaded.suppressions[0].rule_id == "SQL_INJECTION"
        assert loaded.suppressions[0].file_path == "auth.py"
        assert loaded.suppressions[0].line_number == 42
        assert loaded.suppressions[0].reason == "legacy"


def test_add_suppression_creates_file():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "baseline.json"
        add_suppression(path, rule_id="XSS", file_path="xss.py", reason="known FP")
        baseline = load_baseline(path)
        assert len(baseline.suppressions) == 1
        assert baseline.suppressions[0].rule_id == "XSS"
        assert baseline.suppressions[0].created_at != ""  # timestamp auto-filled


def test_add_suppression_appends_to_existing():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "baseline.json"
        add_suppression(path, rule_id="XSS")
        add_suppression(path, rule_id="SQL_INJECTION")
        baseline = load_baseline(path)
        assert len(baseline.suppressions) == 2

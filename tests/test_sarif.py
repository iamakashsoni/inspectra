"""Tests for SARIF output generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from inspectra.output.sarif import (
    _make_rule_id,
    _pascal_case,
    results_to_sarif,
    write_sarif_report,
)
from inspectra.review.severity import ReviewIssue, ReviewResult, Severity


@pytest.fixture
def sample_results() -> list[ReviewResult]:
    return [
        ReviewResult(
            file_path="auth/service.py",
            summary="Has a SQL injection flaw.",
            issues=[
                ReviewIssue(
                    title="SQL Injection",
                    severity=Severity.CRITICAL,
                    category="Security",
                    explanation="User input concatenated directly into SQL query.",
                    suggested_fix="Use parameterised queries.",
                    file_path="auth/service.py",
                    line_number=42,
                ),
                ReviewIssue(
                    title="Missing Timeout",
                    severity=Severity.MEDIUM,
                    category="Performance",
                    explanation="HTTP request has no timeout.",
                    file_path="auth/service.py",
                    line_number=None,
                ),
            ],
        ),
        ReviewResult(
            file_path="api/client.py",
            summary="Looks fine.",
            issues=[],
        ),
    ]


def test_sarif_schema_version(sample_results):
    doc = results_to_sarif(sample_results)
    assert doc["version"] == "2.1.0"
    assert "$schema" in doc


def test_sarif_has_runs(sample_results):
    doc = results_to_sarif(sample_results)
    assert len(doc["runs"]) == 1


def test_sarif_tool_name(sample_results):
    doc = results_to_sarif(sample_results)
    driver = doc["runs"][0]["tool"]["driver"]
    assert driver["name"] == "Inspectra"
    assert "version" in driver


def test_sarif_rules_registered(sample_results):
    doc = results_to_sarif(sample_results)
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    rule_ids = {r["id"] for r in rules}
    # Two distinct rules from two distinct issues
    assert len(rule_ids) == 2


def test_sarif_results_count(sample_results):
    doc = results_to_sarif(sample_results)
    results = doc["runs"][0]["results"]
    # Two issues in sample_results (api/client.py has none)
    assert len(results) == 2


def test_sarif_critical_maps_to_error(sample_results):
    doc = results_to_sarif(sample_results)
    results = doc["runs"][0]["results"]
    error_results = [r for r in results if r["level"] == "error"]
    assert len(error_results) >= 1


def test_sarif_medium_maps_to_warning(sample_results):
    doc = results_to_sarif(sample_results)
    results = doc["runs"][0]["results"]
    warning_results = [r for r in results if r["level"] == "warning"]
    assert len(warning_results) >= 1


def test_sarif_error_level_for_critical(sample_results):
    doc = results_to_sarif(sample_results)
    results = doc["runs"][0]["results"]
    error_results = [r for r in results if r["level"] == "error"]
    assert len(error_results) >= 1


def test_sarif_location_has_uri(sample_results):
    doc = results_to_sarif(sample_results)
    for result in doc["runs"][0]["results"]:
        uri = result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        assert uri  # non-empty


def test_sarif_line_number_in_region(sample_results):
    doc = results_to_sarif(sample_results)
    results = doc["runs"][0]["results"]
    # The SQL Injection issue has line_number=42
    has_region = any(
        "region" in r["locations"][0]["physicalLocation"]
        for r in results
    )
    assert has_region


def test_sarif_suggested_fix_in_message(sample_results):
    doc = results_to_sarif(sample_results)
    results = doc["runs"][0]["results"]
    sql_result = next(
        r for r in results if "parameteris" in r["message"]["text"].lower()
        or "SQL" in r["message"]["text"]
    )
    assert "Suggested fix" in sql_result["message"]["text"]


def test_sarif_empty_results():
    doc = results_to_sarif([])
    assert doc["runs"][0]["results"] == []
    assert doc["runs"][0]["tool"]["driver"]["rules"] == []


def test_sarif_duplicate_rule_ids_deduplicated():
    """Same issue type across two files should only register the rule once."""
    results = [
        ReviewResult(
            file_path="a.py",
            issues=[
                ReviewIssue(
                    title="SQL Injection",
                    severity=Severity.HIGH,
                    category="Security",
                    explanation="Problem in a.py",
                )
            ],
        ),
        ReviewResult(
            file_path="b.py",
            issues=[
                ReviewIssue(
                    title="SQL Injection",
                    severity=Severity.HIGH,
                    category="Security",
                    explanation="Same problem in b.py",
                )
            ],
        ),
    ]
    doc = results_to_sarif(results)
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1  # deduplicated
    assert len(doc["runs"][0]["results"]) == 2  # but two findings


def test_write_sarif_report(sample_results, tmp_path):
    out = tmp_path / "review.sarif"
    returned_path = write_sarif_report(sample_results, output_path=out)
    assert returned_path == out
    assert out.exists()
    # Must be valid JSON
    doc = json.loads(out.read_text())
    assert doc["version"] == "2.1.0"


def test_make_rule_id():
    rule_id = _make_rule_id("Security", "SQL Injection")
    assert rule_id.startswith("INSP/SEC/")
    assert "SQL" in rule_id


def test_make_rule_id_unknown_category():
    rule_id = _make_rule_id("", "Some Bug")
    assert rule_id.startswith("INSP/GEN/")


def test_pascal_case():
    assert _pascal_case("sql injection") == "SqlInjection"
    assert _pascal_case("Missing Timeout") == "MissingTimeout"
    assert _pascal_case("x") == "X"

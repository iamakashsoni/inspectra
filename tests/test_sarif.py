# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Tests for the stable SARIF rule ID logic."""

from inspectra.review.severity import ReviewIssue, ReviewResult, Severity
from inspectra.output.sarif import _stable_rule_id, results_to_sarif


def test_rule_id_uses_llm_provided_value():
    issue = ReviewIssue(
        title="SQL Injection", severity=Severity.CRITICAL, category="Security",
        explanation="bad", file_path="f.py", rule_id="SQL_INJECTION",
    )
    assert _stable_rule_id(issue) == "INSP/SEC/SQL_INJECTION"


def test_rule_id_normalizes_llm_value():
    issue = ReviewIssue(
        title="SQL Injection", severity=Severity.CRITICAL, category="Security",
        explanation="bad", file_path="f.py", rule_id="sql-injection",
    )
    assert _stable_rule_id(issue) == "INSP/SEC/SQL_INJECTION"


def test_rule_id_falls_back_to_canonical_map():
    issue = ReviewIssue(
        title="XSS", severity=Severity.HIGH, category="Security",
        explanation="bad", file_path="f.py", rule_id="",
    )
    assert _stable_rule_id(issue) == "INSP/SEC/XSS"


def test_rule_id_falls_back_to_hash_for_unknown_titles():
    issue1 = ReviewIssue(
        title="Weird custom issue", severity=Severity.MEDIUM, category="Bugs",
        explanation="bad", file_path="f.py", rule_id="",
    )
    issue2 = ReviewIssue(
        title="Weird custom issue", severity=Severity.MEDIUM, category="Bugs",
        explanation="bad", file_path="f.py", rule_id="",
    )
    # Same title → same hash → same rule ID (stable)
    assert _stable_rule_id(issue1) == _stable_rule_id(issue2)


def test_sarif_document_structure():
    issue = ReviewIssue(
        title="SQL Injection", severity=Severity.CRITICAL, category="Security",
        explanation="bad", suggested_fix="use param query",
        file_path="f.py", line_number=42, rule_id="SQL_INJECTION",
    )
    result = ReviewResult(file_path="f.py", issues=[issue], summary="ok")
    doc = results_to_sarif([result])

    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["name"] == "Inspectra"
    assert doc["runs"][0]["tool"]["driver"]["rules"][0]["id"] == "INSP/SEC/SQL_INJECTION"
    assert doc["runs"][0]["results"][0]["ruleId"] == "INSP/SEC/SQL_INJECTION"
    assert doc["runs"][0]["results"][0]["level"] == "error"
    assert doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 42


def test_sarif_dedupes_rules():
    """Two issues with the same rule_id produce ONE rule entry but TWO results."""
    issues = [
        ReviewIssue(title="A", severity=Severity.HIGH, category="Security",
                    explanation="x", file_path="f.py", line_number=1, rule_id="R1"),
        ReviewIssue(title="B", severity=Severity.HIGH, category="Security",
                    explanation="y", file_path="f.py", line_number=2, rule_id="R1"),
    ]
    result = ReviewResult(file_path="f.py", issues=issues, summary="ok")
    doc = results_to_sarif([result])
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    results = doc["runs"][0]["results"]
    assert len(rules) == 1
    assert len(results) == 2

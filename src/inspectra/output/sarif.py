# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""SARIF (Static Analysis Results Interchange Format) export.

Phase 1 change: rule IDs are now stable. The LLM provides a `rule_id` directly
(e.g. "SQL_INJECTION") and we use it as-is. If absent, we fall back to a hash
of the normalized title so the same finding phrased differently across runs
doesn't create two rule IDs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from inspectra.review.severity import ReviewResult, Severity

_SARIF_LEVEL: dict[Severity, str] = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "none",
}

_SECURITY_SEVERITY: dict[Severity, str] = {
    Severity.CRITICAL: "9.0",
    Severity.HIGH: "7.0",
    Severity.MEDIUM: "5.0",
    Severity.LOW: "3.0",
    Severity.INFO: "1.0",
}

_TOOL_VERSION = "0.2.0"
_TOOL_URI = "https://github.com/iamakashsoni/inspectra"

# Canonical names for common findings — keeps rule IDs stable across LLM phrasings
_CANONICAL_RULES: dict[str, str] = {
    "sql injection": "SQL_INJECTION",
    "xss": "XSS",
    "cross-site scripting": "XSS",
    "hardcoded secret": "HARDCODED_SECRET",
    "hardcoded credential": "HARDCODED_SECRET",
    "hardcoded password": "HARDCODED_SECRET",
    "command injection": "COMMAND_INJECTION",
    "path traversal": "PATH_TRAVERSAL",
    "missing error handling": "MISSING_ERROR_HANDLING",
    "unused import": "UNUSED_IMPORT",
    "unused variable": "UNUSED_VARIABLE",
    "race condition": "RACE_CONDITION",
    "deadlock": "DEADLOCK",
}


def _stable_rule_id(issue) -> str:
    """Return a stable rule ID, preferring the LLM-provided one."""
    if issue.rule_id:
        # Normalize: uppercase, replace spaces with underscores
        rid = issue.rule_id.upper().replace(" ", "_").replace("-", "_")
        prefix = (issue.category or "GEN")[:3].upper()
        return f"INSP/{prefix}/{rid}"

    # Fall back to canonical mapping, then to a hash
    normalized = (issue.title or "").lower().strip()
    canonical = _CANONICAL_RULES.get(normalized)
    if canonical:
        prefix = (issue.category or "GEN")[:3].upper()
        return f"INSP/{prefix}/{canonical}"

    h = hashlib.sha256(normalized.encode()).hexdigest()[:8]
    prefix = (issue.category or "GEN")[:3].upper()
    return f"INSP/{prefix}/HASH{h}"


def results_to_sarif(results: list[ReviewResult]) -> dict:
    """Convert ReviewResult objects to a SARIF 2.1.0 document."""
    rules: list[dict] = []
    rule_ids_seen: set[str] = set()
    runs_results: list[dict] = []

    for review_result in results:
        for issue in review_result.issues:
            rule_id = _stable_rule_id(issue)

            if rule_id not in rule_ids_seen:
                rule_ids_seen.add(rule_id)
                rules.append({
                    "id": rule_id,
                    "name": rule_id.split("/")[-1],
                    "shortDescription": {"text": issue.title},
                    "fullDescription": {"text": issue.explanation},
                    "helpUri": _TOOL_URI,
                    "properties": {
                        "tags": [issue.category],
                        "security-severity": _SECURITY_SEVERITY[issue.severity],
                    },
                })

            location: dict = {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": issue.file_path or review_result.file_path,
                        "uriBaseId": "%SRCROOT%",
                    }
                }
            }
            if issue.line_number:
                location["physicalLocation"]["region"] = {"startLine": issue.line_number}

            runs_results.append({
                "ruleId": rule_id,
                "level": _SARIF_LEVEL[issue.severity],
                "message": {
                    "text": issue.explanation
                    + (f"\n\nSuggested fix: {issue.suggested_fix}" if issue.suggested_fix else "")
                },
                "locations": [location],
            })

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Inspectra",
                    "version": _TOOL_VERSION,
                    "informationUri": _TOOL_URI,
                    "rules": rules,
                }
            },
            "results": runs_results,
        }],
    }


def write_sarif_report(
    results: list[ReviewResult],
    output_path: Path | str = "inspectra.sarif",
) -> Path:
    output_path = Path(output_path)
    doc = results_to_sarif(results)
    output_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return output_path

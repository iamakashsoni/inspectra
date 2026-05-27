"""
SARIF (Static Analysis Results Interchange Format) export.

SARIF v2.1.0 — compatible with GitHub Code Scanning.
Reference: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

from __future__ import annotations

import json
from pathlib import Path

from inspectra.review.severity import ReviewResult, Severity

# Map our severity levels to SARIF notification levels
_SARIF_LEVEL: dict[Severity, str] = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "none",
}

# Map severity to SARIF security-severity score (CVSS-ish, for GitHub filtering)
_SECURITY_SEVERITY: dict[Severity, str] = {
    Severity.CRITICAL: "9.0",
    Severity.HIGH: "7.0",
    Severity.MEDIUM: "5.0",
    Severity.LOW: "3.0",
    Severity.INFO: "1.0",
}

_TOOL_VERSION = "0.1.0"
_TOOL_URI = "https://github.com/your-org/inspectra"


def results_to_sarif(results: list[ReviewResult]) -> dict:
    """
    Convert ReviewResult objects to a SARIF 2.1.0 document (as a dict).

    The dict can be serialised to JSON and uploaded to GitHub Code Scanning.
    """
    rules: list[dict] = []
    rule_ids_seen: set[str] = set()
    runs_results: list[dict] = []

    for review_result in results:
        for issue in review_result.issues:
            rule_id = _make_rule_id(issue.category, issue.title)

            # Register the rule once
            if rule_id not in rule_ids_seen:
                rule_ids_seen.add(rule_id)
                rules.append(
                    {
                        "id": rule_id,
                        "name": _pascal_case(issue.title),
                        "shortDescription": {"text": issue.title},
                        "fullDescription": {"text": issue.explanation},
                        "helpUri": _TOOL_URI,
                        "properties": {
                            "tags": [issue.category],
                            "security-severity": _SECURITY_SEVERITY[issue.severity],
                        },
                    }
                )

            # Build the result entry
            location: dict = {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": issue.file_path or review_result.file_path,
                        "uriBaseId": "%SRCROOT%",
                    }
                }
            }

            if issue.line_number:
                location["physicalLocation"]["region"] = {
                    "startLine": issue.line_number
                }

            result_entry: dict = {
                "ruleId": rule_id,
                "level": _SARIF_LEVEL[issue.severity],
                "message": {
                    "text": issue.explanation
                    + (f"\n\nSuggested fix: {issue.suggested_fix}" if issue.suggested_fix else "")
                },
                "locations": [location],
            }
            runs_results.append(result_entry)

    sarif_doc = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Inspectra",
                        "version": _TOOL_VERSION,
                        "informationUri": _TOOL_URI,
                        "rules": rules,
                    }
                },
                "results": runs_results,
            }
        ],
    }

    return sarif_doc


def write_sarif_report(
    results: list[ReviewResult],
    output_path: Path | str = "inspectra.sarif",
) -> Path:
    """Serialise SARIF document to a file and return the path."""
    output_path = Path(output_path)
    doc = results_to_sarif(results)
    output_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return output_path


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_rule_id(category: str, title: str) -> str:
    """Convert category + title into a compact rule ID like INSP/SEC001."""
    prefix = (category or "GEN")[:3].upper()
    slug = "".join(c for c in title if c.isalnum())[:20]
    return f"INSP/{prefix}/{slug}"


def _pascal_case(text: str) -> str:
    return "".join(word.capitalize() for word in text.split())

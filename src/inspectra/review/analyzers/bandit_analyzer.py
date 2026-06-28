# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Bandit analyzer — Python security linter."""

from __future__ import annotations

import json
import shutil
import subprocess

from inspectra.review.analyzers.base import AnalyzerFinding, BaseAnalyzer
from inspectra.utils.logger import logger

# Map Bandit severity levels to our severity levels
_SEVERITY_MAP = {
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}


class BanditAnalyzer(BaseAnalyzer):
    """Runs Bandit on Python files and converts findings to AnalyzerFinding."""
    name = "bandit"
    supported_languages = ["python"]

    @staticmethod
    def is_available() -> bool:
        """Return True if the `bandit` CLI is on PATH."""
        return shutil.which("bandit") is not None

    def analyze(
        self,
        file_path: str,
        full_content: str,
        diff_text: str,
    ) -> list[AnalyzerFinding]:
        if not self.is_available():
            return []

        # Run Bandit on the file content via stdin
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-q", "-"],
                input=full_content,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Bandit timed out on %s", file_path)
            return []
        except Exception as exc:
            logger.warning("Bandit failed on %s: %s", file_path, exc)
            return []

        if result.returncode not in (0, 1):
            # Bandit returns 0 (no issues) or 1 (issues found).
            # Other codes indicate a tool error.
            logger.debug("Bandit exited %d on %s", result.returncode, file_path)
            return []

        try:
            data = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return []

        findings: list[AnalyzerFinding] = []
        for issue in data.get("results", []):
            findings.append(AnalyzerFinding(
                rule_id=f"BANDIT/{issue.get('test_id', 'UNKNOWN')}",
                severity=_SEVERITY_MAP.get(issue.get("issue_severity", ""), "info"),
                category="Security",
                title=issue.get("issue_text", "Bandit finding")[:80],
                explanation=issue.get("issue_text", ""),
                file_path=file_path,
                line_number=issue.get("line_number"),
                suggested_fix="",
                analyzer_name=self.name,
                confidence=issue.get("issue_confidence", "MEDIUM").lower(),
            ))
        return findings

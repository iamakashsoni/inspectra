"""Semgrep analyzer — multi-language static analysis.

Wraps the `semgrep` CLI tool. Supports many languages (Python, JS, TS, Go,
Java, Ruby, etc.). Findings are fed into the LLM prompt.

Semgrep is NOT a hard dependency — if not installed, this analyzer
silently no-ops. Install via `pip install semgrep` to enable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from inspectra.review.analyzers.base import AnalyzerFinding, BaseAnalyzer
from inspectra.utils.logger import logger

# Map Semgrep severity to our severity levels
_SEVERITY_MAP = {
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
}


class SemgrepAnalyzer(BaseAnalyzer):
    """Runs Semgrep on a file and converts findings to AnalyzerFinding."""
    name = "semgrep"
    supported_languages: list[str] = []  # all languages

    @staticmethod
    def is_available() -> bool:
        """Return True if the `semgrep` CLI is on PATH."""
        return shutil.which("semgrep") is not None

    def analyze(
        self,
        file_path: str,
        full_content: str,
        diff_text: str,
    ) -> list[AnalyzerFinding]:
        if not self.is_available():
            return []

        # Semgrep needs a file path, not stdin. Write to a temp file.
        # We use the original extension so Semgrep can detect the language.
        suffix = Path(file_path).suffix or ".txt"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(full_content)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [
                    "semgrep", "scan",
                    "--config", "auto",       # use the default ruleset
                    "--json", "--quiet",
                    "--no-rewrite-rule-ids",
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Semgrep timed out on %s", file_path)
            return []
        except Exception as exc:
            logger.warning("Semgrep failed on %s: %s", file_path, exc)
            return []
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if result.returncode not in (0, 1):
            logger.debug("Semgrep exited %d on %s", result.returncode, file_path)
            return []

        try:
            data = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return []

        findings: list[AnalyzerFinding] = []
        for issue in data.get("results", []):
            # Semgrep rule IDs look like "python.lang.security.audit.dangerous-subprocess-use"
            rule_id = issue.get("check_id", "unknown")
            severity = _SEVERITY_MAP.get(
                issue.get("extra", {}).get("severity", ""), "info"
            )
            message = issue.get("extra", {}).get("message", "")
            findings.append(AnalyzerFinding(
                rule_id=f"SEMGREP/{rule_id}",
                severity=severity,
                category="Security",  # Semgrep's default rules are mostly security
                title=message[:80] if message else "Semgrep finding",
                explanation=message,
                file_path=file_path,
                line_number=issue.get("start", {}).get("line"),
                suggested_fix="",
                analyzer_name=self.name,
                confidence="high",  # Semgrep rules are typically precise
            ))
        return findings

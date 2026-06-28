# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Registry for analyzer plugins.

Maintains a list of analyzers and routes files to the right ones based on
language detection. Supports both built-in analyzers and third-party plugins
registered via setuptools entry points.
"""

from __future__ import annotations

from inspectra.review.analyzers.base import AnalyzerFinding, BaseAnalyzer
from inspectra.utils.language import detect_language
from inspectra.utils.logger import logger


class AnalyzerRegistry:
    """Manages a collection of analyzers and routes files appropriately."""

    def __init__(self) -> None:
        self._analyzers: list[BaseAnalyzer] = []

    def register(self, analyzer: BaseAnalyzer) -> None:
        """Register an analyzer instance."""
        self._analyzers.append(analyzer)
        logger.debug("Registered analyzer: %s (languages: %s)", analyzer.name, analyzer.supported_languages)

    def for_language(self, language: str | None) -> list[BaseAnalyzer]:
        """Return all analyzers that support the given language."""
        return [a for a in self._analyzers if a.supports(language)]

    def all(self) -> list[BaseAnalyzer]:
        """Return all registered analyzers."""
        return list(self._analyzers)

    def analyze_file(
        self,
        file_path: str,
        full_content: str,
        diff_text: str,
    ) -> list[AnalyzerFinding]:
        """Run all applicable analyzers on a file and return combined findings."""
        language = detect_language(file_path)
        applicable = self.for_language(language)
        if not applicable:
            return []

        findings: list[AnalyzerFinding] = []
        for analyzer in applicable:
            try:
                analyzer_findings = analyzer.analyze(file_path, full_content, diff_text)
                findings.extend(analyzer_findings)
                if analyzer_findings:
                    logger.debug(
                        "Analyzer %s found %d issue(s) in %s",
                        analyzer.name, len(analyzer_findings), file_path,
                    )
            except Exception as exc:
                # An analyzer crash should never block the review
                logger.warning("Analyzer %s crashed on %s: %s", analyzer.name, file_path, exc)
        return findings


def build_default_registry() -> AnalyzerRegistry:
    """Build a registry with all built-in analyzers.

    Third-party analyzers (Bandit, Semgrep) are registered ONLY if their
    CLI tool is available on PATH — otherwise they're skipped silently.
    """
    registry = AnalyzerRegistry()

    # Always-register: built-in regex analyzer (no external deps)
    from inspectra.review.analyzers.regex_analyzer import RegexAnalyzer
    registry.register(RegexAnalyzer())

    # Optional: Bandit (Python security) — only if installed
    try:
        from inspectra.review.analyzers.bandit_analyzer import BanditAnalyzer
        if BanditAnalyzer.is_available():
            registry.register(BanditAnalyzer())
    except ImportError:
        pass

    # Optional: Semgrep (multi-language) — only if installed
    try:
        from inspectra.review.analyzers.semgrep_analyzer import SemgrepAnalyzer
        if SemgrepAnalyzer.is_available():
            registry.register(SemgrepAnalyzer())
    except ImportError:
        pass

    return registry

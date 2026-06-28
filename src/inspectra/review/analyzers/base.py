# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Base class and data model for deterministic analyzers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AnalyzerFinding:
    """A single finding from a deterministic analyzer."""
    rule_id: str                  # e.g. "BANDIT/B608", "REGEX/EVAL", "SEMGREP/python.lang.security"
    severity: str                 # critical|high|medium|low|info
    category: str                 # Security|Bugs|Performance|...
    title: str
    explanation: str
    file_path: str
    line_number: int | None = None
    suggested_fix: str = ""
    analyzer_name: str = ""       # Which analyzer produced this (e.g. "bandit", "regex")
    confidence: str = "medium"    # low|medium|high — analyzer's own confidence


class BaseAnalyzer(ABC):
    """Base class for all deterministic analyzers.

    Subclasses set `name` and `supported_languages` as CLASS ATTRIBUTES (not
    instance attributes), then implement `analyze()`.

    Note: this is NOT a dataclass because dataclass fields with default_factory
    would shadow class-attribute overrides in subclasses. Using plain class
    attributes lets each subclass simply declare `name = "my_analyzer"` and
    `supported_languages = ["python"]` at class level.
    """
    name: str = "base"
    supported_languages: list[str] = []  # Empty list = runs on any language

    @abstractmethod
    def analyze(
        self,
        file_path: str,
        full_content: str,
        diff_text: str,
    ) -> list[AnalyzerFinding]:
        """Analyze a file and return findings.

        Args:
            file_path: Path to the file being analyzed.
            full_content: The complete current content of the file.
            diff_text: The unified diff for this file (only changed lines).

        Returns:
            List of AnalyzerFinding objects.
        """
        ...

    def supports(self, language: str | None) -> bool:
        """Return True if this analyzer can run on the given language."""
        if not self.supported_languages:
            return True  # No restriction — runs on any language
        return language in self.supported_languages

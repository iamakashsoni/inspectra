"""Severity levels and the ReviewIssue data model."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def emoji(self) -> str:
        return {
            Severity.CRITICAL: "🔴",
            Severity.HIGH: "🟠",
            Severity.MEDIUM: "🟡",
            Severity.LOW: "🔵",
            Severity.INFO: "⚪",
        }[self]

    @property
    def rich_style(self) -> str:
        return {
            Severity.CRITICAL: "bold red",
            Severity.HIGH: "bold orange1",
            Severity.MEDIUM: "bold yellow",
            Severity.LOW: "bold blue",
            Severity.INFO: "dim",
        }[self]

    @classmethod
    def from_string(cls, value: str) -> Severity:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.INFO


class ReviewIssue(BaseModel):
    """A single code review finding."""

    title: str
    severity: Severity
    category: str = "General"
    explanation: str
    suggested_fix: str = ""
    file_path: str = ""
    line_number: int | None = None

    @property
    def display_title(self) -> str:
        return f"{self.severity.emoji} [{self.severity.value.upper()}] {self.title}"


class ReviewResult(BaseModel):
    """Aggregated review result for a single diff chunk."""

    file_path: str
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str = ""

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HIGH)

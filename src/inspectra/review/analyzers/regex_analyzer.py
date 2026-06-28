# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Built-in regex analyzer — no external dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass

from inspectra.review.analyzers.base import AnalyzerFinding, BaseAnalyzer


@dataclass
class _Pattern:
    rule_id: str
    severity: str
    category: str
    title: str
    explanation: str
    pattern: str
    languages: list[str]   # Empty list = applies to all languages
    suggested_fix: str = ""


# Curated set of high-signal, low-false-positive patterns.
# Each pattern is anchored to a specific code construct to minimize noise.
_PATTERNS: list[_Pattern] = [
    # ── Security ─────────────────────────────────────────────────────────────
    _Pattern(
        rule_id="REGEX/EVAL",
        severity="high",
        category="Security",
        title="Use of eval()",
        explanation="eval() executes arbitrary code. If the input is user-controlled, this is a critical security vulnerability. Even if not currently exploitable, it's a maintenance hazard.",
        pattern=r"\beval\s*\(",
        languages=["python", "javascript", "typescript"],
        suggested_fix="Replace eval() with a safer alternative: ast.literal_eval() for literal parsing, or a proper parser for expressions.",
    ),
    _Pattern(
        rule_id="REGEX/PICKLE_LOADS",
        severity="high",
        category="Security",
        title="Use of pickle.loads() on untrusted input",
        explanation="pickle.loads() can execute arbitrary code during deserialization. Never use it on untrusted input.",
        pattern=r"\bpickle\.loads?\s*\(",
        languages=["python"],
        suggested_fix="Use JSON or a safe serialization format. If you must use pickle, only load data you produced yourself.",
    ),
    _Pattern(
        rule_id="REGEX/SUBPROCESS_SHELL_TRUE",
        severity="high",
        category="Security",
        title="subprocess with shell=True",
        explanation="shell=True with user input enables shell injection. Use shell=False (the default) and pass args as a list.",
        pattern=r"subprocess\.(run|call|Popen|check_output|check_call)\s*\([^)]*shell\s*=\s*True",
        languages=["python"],
        suggested_fix="subprocess.run(['cmd', 'arg1', 'arg2'])  # shell=False, args as list",
    ),
    _Pattern(
        rule_id="REGEX/HARDCODED_SECRET",
        severity="medium",
        category="Security",
        title="Possible hardcoded secret/API key",
        explanation="A string literal assigned to a variable named like a secret (password, api_key, token, secret) is a credential leak risk. Even if this is a test value, it sets a bad precedent.",
        pattern=r"(?i)(password|api_?key|secret|token|auth)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        languages=[],  # All languages
        suggested_fix="Load secrets from environment variables or a secrets manager. Never commit real credentials.",
    ),
    _Pattern(
        rule_id="REGEX/SQL_STRING_FORMAT",
        severity="critical",
        category="Security",
        title="SQL query built with string formatting",
        explanation="Building SQL queries with f-strings, .format(), or % opens the door to SQL injection. Use parameterized queries.",
        pattern=r"(execute|executemany)\s*\(\s*[f'\"]|(execute|executemany)\s*\(\s*[^,)]*\.format\(",
        languages=["python"],
        suggested_fix="cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
    ),
    _Pattern(
        rule_id="REGEX/DANGEROUSLY_SET_INNER_HTML",
        severity="high",
        category="Security",
        title="dangerouslySetInnerHTML usage",
        explanation="React's dangerouslySetInnerHTML bypasses XSS protection. Only use it with sanitized input.",
        pattern=r"dangerouslySetInnerHTML",
        languages=["javascript", "typescript"],
        suggested_fix="Use a sanitization library like DOMPurify before setting innerHTML, or render content as text nodes.",
    ),

    # ── Bugs ─────────────────────────────────────────────────────────────────
    _Pattern(
        rule_id="REGEX/BARE_EXCEPT",
        severity="medium",
        category="Bugs",
        title="Bare 'except:' clause",
        explanation="Bare except catches everything including SystemExit, KeyboardInterrupt, and GeneratorExit. This hides bugs and makes the program hard to interrupt.",
        pattern=r"^\s*except\s*:",
        languages=["python"],
        suggested_fix="except Exception:  # or catch the specific exception type",
    ),
    _Pattern(
        rule_id="REGEX/MUTABLE_DEFAULT_ARG",
        severity="medium",
        category="Bugs",
        title="Mutable default argument",
        explanation="Mutable default arguments (list, dict, set) are shared across all calls to the function. Mutations persist between calls, causing surprising behavior.",
        pattern=r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|\{\}|\(\s*\))",
        languages=["python"],
        suggested_fix="def foo(x=None):\n    if x is None:\n        x = []",
    ),

    # ── Performance ──────────────────────────────────────────────────────────
    _Pattern(
        rule_id="REGEX/LIST_IN_FOR",
        severity="low",
        category="Performance",
        title="Calling list.append() in a hot loop without pre-allocation",
        explanation="For very large loops, pre-allocating a list is faster than repeated append() calls. Not always worth fixing, but worth flagging for hot paths.",
        pattern=r"for\s+\w+\s+in\s+range\s*\(\s*\d{4,}\s*\):[^}]*\.append\s*\(",
        languages=["python"],
        suggested_fix="[None] * n  # pre-allocate, then assign by index",
    ),
]


class RegexAnalyzer(BaseAnalyzer):
    """Built-in regex-based analyzer. Always available, no external deps."""
    name = "regex"
    supported_languages: list[str] = []  # [] = all languages

    def analyze(
        self,
        file_path: str,
        full_content: str,
        diff_text: str,
    ) -> list[AnalyzerFinding]:
        from inspectra.utils.language import detect_language
        language = detect_language(file_path)

        findings: list[AnalyzerFinding] = []
        lines = full_content.splitlines(keepends=False)

        for pat in _PATTERNS:
            # Skip if pattern is language-specific and doesn't match this file
            if pat.languages and language not in pat.languages:
                continue

            try:
                regex = re.compile(pat.pattern)
            except re.error:
                continue

            for line_no, line in enumerate(lines, start=1):
                if regex.search(line):
                    findings.append(AnalyzerFinding(
                        rule_id=pat.rule_id,
                        severity=pat.severity,
                        category=pat.category,
                        title=pat.title,
                        explanation=pat.explanation,
                        file_path=file_path,
                        line_number=line_no,
                        suggested_fix=pat.suggested_fix,
                        analyzer_name=self.name,
                        confidence="medium",
                    ))
        return findings

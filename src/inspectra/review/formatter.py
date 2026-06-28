# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Format ReviewResult objects into human-readable outputs."""

from __future__ import annotations

from inspectra.review.severity import ReviewResult, Severity

_SEVERITY_ORDER = [
    Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO,
]

# Tokens that indicate a single-line fix is code (not prose).
# `-`/`+` are excluded because prose lists start with them.
_SINGLE_LINE_CODE_STARTS = (
    "def ", "class ", "import ", "from ", "if ", "for ", "while ", "return ",
    "try:", "with ", "async ", "await ", "var ", "let ", "const ", "func ",
    "pub ", "package ", "use ", "#!/", "@",
)


def _looks_like_code(fix: str) -> bool:
    """Return True if the suggested fix looks like code rather than prose."""
    fix = fix.strip()
    if not fix:
        return False
    if "\n" in fix:
        return True  # multi-line fixes are always code
    if fix.startswith(_SINGLE_LINE_CODE_STARTS):
        return True
    if fix.endswith((";", "}", ")")) and len(fix) > 10:
        return True
    return False


def _render_suggested_fix(issue) -> str:
    """Render a suggested_fix as a GitHub suggestion block when it looks like code."""
    if not issue.suggested_fix:
        return ""
    fix = issue.suggested_fix.strip()
    if _looks_like_code(fix):
        return f"\n**Suggested fix:**\n\n```suggestion\n{fix}\n```\n"
    return f"\n**Suggested fix:** {fix}\n"


def results_to_markdown(results: list[ReviewResult], pr_summary: str = "") -> str:
    """Render all ReviewResults as a Markdown report."""
    lines: list[str] = ["# 🔍 Inspectra Code Review\n"]

    if pr_summary:
        lines += ["## Overview\n", pr_summary, "\n---\n"]

    all_issues = [issue for r in results for issue in r.issues]
    if not all_issues:
        lines.append("✅ **No issues found.** The diff looks good!\n")
        return "\n".join(lines)

    for severity in _SEVERITY_ORDER:
        group = [i for i in all_issues if i.severity == severity]
        if not group:
            continue
        lines.append(f"## {severity.emoji} {severity.value.title()} Severity\n")
        for issue in group:
            lines.append(f"### {issue.title}\n")
            if issue.rule_id:
                lines.append(f"**Rule:** `{issue.rule_id}`\n")
            if issue.file_path:
                loc = f"`{issue.file_path}`"
                if issue.line_number:
                    loc += f" — Line {issue.line_number}"
                lines.append(f"**Location:** {loc}\n")
            lines.append(f"**Category:** {issue.category}\n")
            lines.append(f"{issue.explanation}\n")
            lines.append(_render_suggested_fix(issue))
            lines.append("---\n")

    lines.append("## 📋 File Summaries\n")
    for result in results:
        if result.summary:
            lines.append(f"### `{result.file_path}`\n")
            lines.append(f"{result.summary}\n")

    return "\n".join(lines)


def results_to_pr_comment(results: list[ReviewResult], pr_summary: str = "") -> str:
    """Generate a PR comment body with a summary table."""
    total = sum(len(r.issues) for r in results)
    critical = sum(r.critical_count for r in results)
    high = sum(r.high_count for r in results)

    header = (
        "<!-- inspectra:summary -->\n"
        "## 🔍 Inspectra Review\n\n"
        f"| Files Reviewed | Total Issues | Critical | High |\n"
        f"|---|---|---|---|\n"
        f"| {len(results)} | {total} | {critical} | {high} |\n\n"
    )
    body = results_to_markdown(results, pr_summary)
    return header + body

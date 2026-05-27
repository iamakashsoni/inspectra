"""Format ReviewResult objects into human-readable outputs."""

from __future__ import annotations

from inspectra.review.severity import ReviewResult, Severity

_SEVERITY_ORDER = [
    Severity.CRITICAL,
    Severity.HIGH,
    Severity.MEDIUM,
    Severity.LOW,
    Severity.INFO,
]


def results_to_markdown(results: list[ReviewResult], pr_summary: str = "") -> str:
    """Render all ReviewResults as a Markdown report."""
    lines: list[str] = ["# 🔍 Inspectra Code Review\n"]

    if pr_summary:
        lines += ["## Overview\n", pr_summary, "\n---\n"]

    # Collect all issues sorted by severity
    all_issues = [issue for r in results for issue in r.issues]

    if not all_issues:
        lines.append("✅ **No issues found.** The diff looks good!\n")
        return "\n".join(lines)

    # Group by severity
    for severity in _SEVERITY_ORDER:
        group = [i for i in all_issues if i.severity == severity]
        if not group:
            continue

        lines.append(f"## {severity.emoji} {severity.value.title()} Severity\n")

        for issue in group:
            lines.append(f"### {issue.title}\n")
            if issue.file_path:
                loc = f"`{issue.file_path}`"
                if issue.line_number:
                    loc += f" — Line {issue.line_number}"
                lines.append(f"**Location:** {loc}\n")
            lines.append(f"**Category:** {issue.category}\n")
            lines.append(f"{issue.explanation}\n")
            if issue.suggested_fix:
                lines.append(f"**Suggested Fix:**\n\n{issue.suggested_fix}\n")
            lines.append("---\n")

    # Per-file summaries
    lines.append("## 📋 File Summaries\n")
    for result in results:
        if result.summary:
            lines.append(f"### `{result.file_path}`\n")
            lines.append(f"{result.summary}\n")

    return "\n".join(lines)


def results_to_pr_comment(results: list[ReviewResult], pr_summary: str = "") -> str:
    """Generate a PR comment body (subset of full markdown for brevity)."""
    total = sum(len(r.issues) for r in results)
    critical = sum(r.critical_count for r in results)
    high = sum(r.high_count for r in results)

    header = (
        "## 🔍 Inspectra Review\n\n"
        f"| Files Reviewed | Total Issues | Critical | High |\n"
        f"|---|---|---|---|\n"
        f"| {len(results)} | {total} | {critical} | {high} |\n\n"
    )

    body = results_to_markdown(results, pr_summary)
    return header + body

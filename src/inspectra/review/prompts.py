"""Prompt templates for code review."""

from __future__ import annotations

from inspectra.config.settings import ReviewCategories

_SYSTEM_CONTEXT = """\
You are Inspectra, an AI code review assistant that behaves like a senior software engineer.

Your responsibilities:
- Review ONLY the changed code shown in the diff
- Detect real bugs, security vulnerabilities, and performance issues
- Flag maintainability and architectural concerns
- Avoid trivial nitpicks (formatting, style, naming unless severe)
- Suggest concrete fixes wherever possible
- Be concise and actionable
"""

_REVIEW_CATEGORIES_TEMPLATE = """\
Focus on these categories (only include if enabled):
{categories}
"""

_OUTPUT_FORMAT = """\
Respond ONLY with a JSON object matching this schema (no markdown fences):

{
  "summary": "<one paragraph summary of the overall diff quality>",
  "issues": [
    {
      "title": "<short issue title>",
      "severity": "<critical|high|medium|low|info>",
      "category": "<Security|Bugs|Performance|Maintainability
      |Architecture|Concurrency|Scalability>",
      "explanation": "<clear explanation of the problem>",
      "suggested_fix": "<concrete code or description of fix>",
      "file_path": "<file path>",
      "line_number": <integer or null>
    }
  ]
}

If there are no issues, return an empty issues array with a positive summary.
"""


def build_review_prompt(
    file_path: str,
    diff_text: str,
    categories: ReviewCategories | None = None,
) -> str:
    """Build a full review prompt for a single file diff chunk."""

    enabled: list[str] = []
    if categories:
        mapping = {
            "Security": categories.security,
            "Bugs": categories.bugs,
            "Performance": categories.performance,
            "Maintainability": categories.maintainability,
            "Architecture": categories.architecture,
            "Concurrency": categories.concurrency,
            "Scalability": categories.scalability,
        }
        enabled = [name for name, active in mapping.items() if active]
    else:
        enabled = ["Security", "Bugs", "Performance", "Maintainability", "Architecture"]

    categories_str = "\n".join(f"- {c}" for c in enabled)

    return f"""{_SYSTEM_CONTEXT}

{_REVIEW_CATEGORIES_TEMPLATE.format(categories=categories_str)}

File under review: {file_path}

Git diff (unified format):
```diff
{diff_text}
```

{_OUTPUT_FORMAT}"""


def build_pr_summary_prompt(file_results_summary: str) -> str:
    """Build a prompt to generate a high-level PR summary from individual file results."""
    return f"""\
You are Inspectra, an AI code review assistant.

Below are the individual file review results for a pull request.
Write a concise, helpful PR-level summary (3-5 sentences) that covers:
- Overall code quality
- Most critical findings
- Recommended actions before merging

Individual results:
{file_results_summary}

Respond with plain markdown text only. No JSON.
"""

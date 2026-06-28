# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Cross-file consistency check (second review pass)."""

from __future__ import annotations

import json

from inspectra.llm.base import BaseLLMProvider, LLMRequest
from inspectra.review.context_builder import extract_changed_signatures
from inspectra.review.severity import ReviewIssue, Severity
from inspectra.utils.logger import logger


# Schema for the cross-file pass — same shape as the main review but simpler
_CROSS_FILE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "info"]},
                    "category": {"type": "string"},
                    "explanation": {"type": "string"},
                    "suggested_fix": {"type": "string"},
                    "file_path": {"type": "string"},
                    "line_number": {"type": ["integer", "null"]},
                    "rule_id": {"type": "string"},
                },
                "required": ["title", "severity", "category", "explanation"],
            },
        },
    },
    "required": ["summary", "issues"],
}


_CROSS_FILE_PROMPT_TEMPLATE = """\
You are Inspectra, performing a cross-file consistency review.

Below are the signatures of symbols that CHANGED in this PR, organized by file.
Your job: find inconsistencies BETWEEN files that the per-file review would miss.

Look for:
1. Signature mismatches — a function's signature changed in one file but callers in other files weren't updated
2. Type mismatches — caller passes a different type than the callee expects
3. Missing call-site updates — a deleted/renamed function still referenced elsewhere
4. Error handling gaps — a callee now raises a new exception but callers don't handle it
5. Dead code — a function was deleted but is still imported/called elsewhere

DO NOT report per-file issues (those were already caught in the first pass).
ONLY report issues that span multiple files.

Changed signatures per file:
{signatures}

Respond ONLY with a JSON object matching this schema (no markdown fences):

{{
  "summary": "<one paragraph summary of cross-file consistency>",
  "issues": [
    {{
      "title": "<short issue title>",
      "severity": "<critical|high|medium|low|info>",
      "category": "<Bugs|Architecture|Maintainability>",
      "explanation": "<what's inconsistent and why it matters>",
      "suggested_fix": "<concrete fix>",
      "file_path": "<the file that needs to change>",
      "line_number": <integer or null>,
      "rule_id": "<stable rule ID, e.g. CROSS_FILE_SIGNATURE_MISMATCH>"
    }}
  ]
}}

If there are no cross-file issues, return an empty issues array.
"""


async def run_cross_file_review(
    provider: BaseLLMProvider,
    file_diffs: dict[str, str],
) -> list[ReviewIssue]:
    """Run the second-pass cross-file consistency review.

    Args:
        provider: The LLM provider to use.
        file_diffs: {file_path: diff_text} for all changed files.

    Returns:
        List of ReviewIssue objects for cross-file problems.
    """
    if len(file_diffs) < 2:
        # Cross-file review only makes sense with 2+ files
        logger.debug("Skipping cross-file review — only %d file(s) changed", len(file_diffs))
        return []

    # Extract changed signatures from each file's diff
    all_signatures: dict[str, list[str]] = {}
    for file_path, diff_text in file_diffs.items():
        sigs = extract_changed_signatures(file_path, diff_text, max_signatures=10)
        if sigs:
            all_signatures[file_path] = sigs

    if not all_signatures:
        logger.debug("No changed signatures found — skipping cross-file review")
        return []

    # Format the signatures block
    sig_lines: list[str] = []
    for file_path, sigs in all_signatures.items():
        sig_lines.append(f"\n{file_path}:")
        for sig in sigs:
            sig_lines.append(f"  {sig}")

    prompt = _CROSS_FILE_PROMPT_TEMPLATE.format(
        signatures="\n".join(sig_lines),
    )

    try:
        response = await provider.complete(LLMRequest(
            user_prompt=prompt,
            system_prompt=provider.system_prompt,
            json_schema=_CROSS_FILE_SCHEMA,
            temperature=0.2,
            max_tokens=4096,
        ))
    except Exception as exc:
        logger.warning("Cross-file review failed: %s", exc)
        return []

    return _parse_cross_file_response(response.text)


def _parse_cross_file_response(raw: str) -> list[ReviewIssue]:
    """Parse the cross-file review JSON response into ReviewIssue objects."""
    import re

    cleaned = raw.strip()
    # Strip markdown fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("Cross-file review returned invalid JSON: %s", exc)
        return []

    issues: list[ReviewIssue] = []
    for item in data.get("issues", []):
        try:
            issues.append(ReviewIssue(
                title=item.get("title", "Cross-file issue"),
                severity=Severity.from_string(item.get("severity", "info")),
                category=item.get("category", "Architecture"),
                explanation=item.get("explanation", ""),
                suggested_fix=item.get("suggested_fix", ""),
                file_path=item.get("file_path", ""),
                line_number=item.get("line_number"),
                rule_id=item.get("rule_id", "CROSS_FILE"),
            ))
        except Exception as exc:
            logger.debug("Skipping malformed cross-file issue: %s — %s", item, exc)

    return issues

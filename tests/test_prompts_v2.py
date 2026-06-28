"""Tests for the v2 prompt builder — verifies the rubric, few-shot, and
PROMPT_VERSION stamp are present so cache invalidation works correctly.
"""

from inspectra.config.settings import ReviewCategories
from inspectra.review.prompts import (
    PROMPT_VERSION,
    REVIEW_JSON_SCHEMA,
    build_review_prompt,
    build_pr_summary_prompt,
    build_corrective_prompt,
)


def test_prompt_includes_version_stamp():
    """The PROMPT_VERSION must appear in the prompt text so cache keys
    derived from sha256(prompt) auto-invalidate on prompt bumps."""
    p = build_review_prompt("foo.py", "+pass\n")
    assert f"prompt_version={PROMPT_VERSION}" in p


def test_prompt_includes_severity_rubric():
    """The rubric must be present so LLMs calibrate severity consistently."""
    p = build_review_prompt("foo.py", "+pass\n")
    assert "Severity Rubric" in p
    assert "critical" in p
    assert "Must fix before merge" in p


def test_prompt_includes_few_shot_example():
    """The good-finding example must be present."""
    p = build_review_prompt("foo.py", "+pass\n")
    assert "SQL Injection" in p
    assert "DO NOT DO THIS" in p


def test_prompt_includes_output_format():
    p = build_review_prompt("foo.py", "+pass\n")
    assert "Respond ONLY with a JSON object" in p
    assert "rule_id" in p


def test_prompt_respects_disabled_categories():
    cats = ReviewCategories(security=False, bugs=True, performance=False,
                            maintainability=False, architecture=False,
                            concurrency=False, scalability=False)
    p = build_review_prompt("foo.py", "+pass\n", cats)
    assert "- Bugs" in p
    assert "- Security" not in p
    assert "- Performance" not in p


def test_prompt_includes_language_hint():
    p = build_review_prompt("src/main.py", "+pass\n")
    assert "language: python" in p
    p2 = build_review_prompt("src/main.ts", "+pass\n")
    assert "language: typescript" in p2


def test_json_schema_has_required_fields():
    """The JSON schema must include rule_id (new in v2) for stable SARIF IDs."""
    props = REVIEW_JSON_SCHEMA["properties"]["issues"]["items"]["properties"]
    assert "rule_id" in props
    assert "title" in props
    assert "severity" in props
    assert "suggested_fix" in props
    required = REVIEW_JSON_SCHEMA["properties"]["issues"]["items"]["required"]
    assert "title" in required
    assert "severity" in required


def test_pr_summary_prompt_is_plain_text():
    p = build_pr_summary_prompt("File: foo.py\nSummary: ok")
    assert "PR-level summary" in p
    assert "No JSON" in p


def test_corrective_prompt_mentions_error():
    p = build_corrective_prompt("original", "Expecting ','", "bad json {")
    assert "Expecting ','" in p
    assert "valid JSON" in p

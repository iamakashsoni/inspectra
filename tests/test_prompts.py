"""Tests for prompt generation."""

from __future__ import annotations

from inspectra.config.settings import ReviewCategories
from inspectra.review.prompts import build_pr_summary_prompt, build_review_prompt


def test_build_review_prompt_contains_file_path():
    prompt = build_review_prompt("auth/service.py", "some diff text")
    assert "auth/service.py" in prompt


def test_build_review_prompt_contains_diff():
    prompt = build_review_prompt("foo.py", "some diff text")
    assert "some diff text" in prompt


def test_build_review_prompt_requests_json():
    prompt = build_review_prompt("foo.py", "diff")
    assert "JSON" in prompt


def test_build_review_prompt_includes_enabled_categories():
    cats = ReviewCategories(
        security=True,
        bugs=True,
        performance=False,
        maintainability=False,
        architecture=False,
        concurrency=False,
        scalability=False,
    )
    prompt = build_review_prompt("foo.py", "diff", categories=cats)
    # The categories list section uses "- Category" bullet format
    assert "- Security" in prompt
    assert "- Bugs" in prompt
    assert "- Performance" not in prompt  # disabled; not in bullet list


def test_build_review_prompt_all_categories_disabled():
    cats = ReviewCategories(
        security=False,
        bugs=False,
        performance=False,
        maintainability=False,
        architecture=False,
        concurrency=False,
        scalability=False,
    )
    prompt = build_review_prompt("foo.py", "diff", categories=cats)
    # Prompt should still be generated; category section just empty
    assert "foo.py" in prompt


def test_build_review_prompt_no_categories_uses_defaults():
    prompt = build_review_prompt("foo.py", "diff", categories=None)
    # Default set includes these
    assert "Security" in prompt
    assert "Bugs" in prompt


def test_build_pr_summary_prompt_contains_file_data():
    summary_input = (
        "File: auth/service.py\nSummary: Has SQL injection.\n"
        "Issues:\n  - [CRITICAL] SQLi"
    )
    prompt = build_pr_summary_prompt(summary_input)
    assert "auth/service.py" in prompt
    assert "SQL injection" in prompt


def test_build_pr_summary_prompt_asks_for_markdown():
    prompt = build_pr_summary_prompt("some results")
    assert "markdown" in prompt.lower()


def test_prompt_describes_senior_engineer_role():
    prompt = build_review_prompt("foo.py", "diff")
    assert "senior" in prompt.lower() or "engineer" in prompt.lower()


def test_prompt_schema_has_required_fields():
    prompt = build_review_prompt("foo.py", "diff")
    for field in ("title", "severity", "explanation", "suggested_fix", "file_path"):
        assert field in prompt

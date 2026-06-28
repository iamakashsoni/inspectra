# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Tests for prompt context blocks (#16, #17, #18, #22, #24)."""

from inspectra.config.settings import ReviewCategories
from inspectra.review.analyzers.base import AnalyzerFinding
from inspectra.review.prompts import build_review_prompt, PROMPT_VERSION


def test_prompt_with_file_context_includes_block():
    """When full_file_context is provided, the prompt includes a 'Full file content' block."""
    prompt = build_review_prompt(
        "test.py", "+pass\n",
        full_file_context="def foo():\n    return 1\n",
    )
    assert "Full file content" in prompt
    assert "def foo" in prompt
    assert "```python" in prompt


def test_prompt_without_file_context_omits_block():
    """When full_file_context is None, no 'Full file content' block appears."""
    prompt = build_review_prompt("test.py", "+pass\n")
    assert "Full file content" not in prompt


def test_prompt_with_pr_intent_includes_block():
    prompt = build_review_prompt(
        "test.py", "+pass\n",
        pr_intent="This PR adds a new /api/users endpoint for user lookup.",
    )
    assert "PR Intent" in prompt
    assert "/api/users" in prompt


def test_prompt_without_pr_intent_omits_block():
    prompt = build_review_prompt("test.py", "+pass\n")
    assert "PR Intent" not in prompt


def test_prompt_with_related_changes_includes_block():
    related = [
        "auth/service.py:42  def get_user(conn, user_id):",
        "api/routes.py:10  def list_users():",
    ]
    prompt = build_review_prompt(
        "test.py", "+pass\n",
        related_changes=related,
    )
    assert "Other files changed" in prompt
    assert "auth/service.py" in prompt
    assert "api/routes.py" in prompt
    assert "caller/callee" in prompt


def test_prompt_without_related_changes_omits_block():
    prompt = build_review_prompt("test.py", "+pass\n")
    assert "Other files changed" not in prompt


def test_prompt_with_analyzer_findings_includes_block():
    findings = [
        AnalyzerFinding(
            rule_id="BANDIT/B608", severity="high", category="Security",
            title="SQL injection", explanation="bad",
            file_path="test.py", line_number=42, analyzer_name="bandit",
        ),
    ]
    prompt = build_review_prompt(
        "test.py", "+pass\n",
        analyzer_findings=findings,
    )
    assert "Deterministic analyzer" in prompt
    assert "BANDIT/B608" in prompt
    assert "SQL injection" in prompt
    assert "CONFIRM" in prompt
    assert "FP:" in prompt


def test_prompt_without_analyzer_findings_omits_block():
    prompt = build_review_prompt("test.py", "+pass\n")
    assert "Deterministic analyzer" not in prompt


def test_prompt_with_language_rules_includes_block():
    from inspectra.utils.language_rules import get_language_rules
    rules = get_language_rules("test.py")  # Python rules
    prompt = build_review_prompt(
        "test.py", "+pass\n",
        language_rules=rules,
    )
    assert "Python-specific" in prompt
    assert "pickle.loads" in prompt
    assert "shell=True" in prompt


def test_prompt_without_language_rules_omits_block():
    prompt = build_review_prompt("test.py", "+pass\n")
    # Without language_rules, the prompt shouldn't contain language-specific hints
    assert "Python-specific" not in prompt


def test_prompt_with_all_context_blocks():
    """All blocks can be combined in one prompt."""
    findings = [AnalyzerFinding(
        rule_id="REGEX/EVAL", severity="high", category="Security",
        title="eval() usage", explanation="bad",
        file_path="test.py", line_number=1, analyzer_name="regex",
    )]
    prompt = build_review_prompt(
        "test.py", "+pass\n",
        full_file_context="x = 1\n",
        pr_intent="Refactor auth module",
        related_changes=["other.py:5  def foo():"],
        analyzer_findings=findings,
        language_rules="Python-specific rules:\n- Check eval()\n",
    )
    assert "Full file content" in prompt
    assert "PR Intent" in prompt
    assert "Other files changed" in prompt
    assert "Deterministic analyzer" in prompt
    assert "Python-specific rules" in prompt


def test_prompt_version_is_v4():
    """bumps the prompt version to v4 for cache invalidation."""
    assert PROMPT_VERSION == "2026-06-28"


def test_phase2_context_changes_cache_key():
    """Adding file context must produce a DIFFERENT prompt (different cache key)."""
    prompt_no_ctx = build_review_prompt("test.py", "+pass\n")
    prompt_with_ctx = build_review_prompt(
        "test.py", "+pass\n", full_file_context="x = 1\n",
    )
    assert prompt_no_ctx != prompt_with_ctx, \
        "context must change the prompt text (so cache keys differ)"



def test_language_rules_python():
    from inspectra.utils.language_rules import get_language_rules
    rules = get_language_rules("foo.py")
    assert "Python-specific" in rules
    assert "eval" in rules.lower()


def test_language_rules_javascript():
    from inspectra.utils.language_rules import get_language_rules
    rules = get_language_rules("foo.js")
    assert "JavaScript-specific" in rules
    assert "dangerouslySetInnerHTML" in rules


def test_language_rules_typescript():
    from inspectra.utils.language_rules import get_language_rules
    rules = get_language_rules("foo.ts")
    assert "TypeScript-specific" in rules
    assert "@ts-ignore" in rules


def test_language_rules_go():
    from inspectra.utils.language_rules import get_language_rules
    rules = get_language_rules("foo.go")
    assert "Go-specific" in rules
    assert "defer" in rules.lower()


def test_language_rules_unknown_returns_empty():
    from inspectra.utils.language_rules import get_language_rules
    rules = get_language_rules("foo.xyz")
    assert rules == ""


def test_language_rules_get_supported():
    from inspectra.utils.language_rules import get_supported_languages
    langs = get_supported_languages()
    assert "python" in langs
    assert "javascript" in langs
    assert "go" in langs
    assert len(langs) >= 8  # we have at least 8 languages

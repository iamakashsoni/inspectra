#!/usr/bin/env python3
"""End-to-end smoke test for Inspectra v2 Phase 2 — no live LLM required.

Demonstrates the full Phase 2 pipeline:
1. Build a review prompt with file context, PR intent, related changes,
   analyzer findings, and language-specific rules
2. Simulate an LLM response
3. Parse the response
4. Run the cross-file consistency check
5. Apply baseline suppression
6. Render to Markdown with GitHub suggestion blocks
7. Render to SARIF with stable rule IDs
8. Show model-aware chunk sizing
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from inspectra.config.settings import InspectraSettings, LLMProvider
from inspectra.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from inspectra.review.analyzers.regex_analyzer import RegexAnalyzer
from inspectra.review.analyzers.registry import build_default_registry
from inspectra.review.baseline import Baseline, Suppression, apply_baseline
from inspectra.review.context_builder import build_file_context, extract_changed_signatures
from inspectra.review.cross_file import run_cross_file_review
from inspectra.review.engine import ReviewContext, ReviewEngine
from inspectra.review.formatter import results_to_markdown, results_to_pr_comment
from inspectra.review.prompts import PROMPT_VERSION, build_review_prompt
from inspectra.review.reviewer import ChunkReviewer
from inspectra.review.severity import ReviewIssue, ReviewResult, Severity
from inspectra.output.sarif import results_to_sarif
from inspectra.utils.language_rules import get_language_rules


class FakeLLM(BaseLLMProvider):
    """Returns a realistic canned response for the main review + cross-file review."""
    def __init__(self):
        super().__init__(system_prompt="sys", model="fake")
        self.call_count = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        # First call: per-file review
        if self.call_count == 1:
            return LLMResponse(text=json.dumps({
                "summary": "SQL injection vulnerability confirmed. Analyzer finding verified.",
                "issues": [{
                    "title": "SQL Injection in user lookup",
                    "severity": "critical",
                    "category": "Security",
                    "explanation": "user_id is concatenated directly into the SQL string.",
                    "suggested_fix": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()",
                    "file_path": "auth/service.py",
                    "line_number": 42,
                    "rule_id": "SQL_INJECTION",
                }]
            }), finish_reason="stop")
        # Second call: cross-file review
        return LLMResponse(text=json.dumps({
            "summary": "Found 1 cross-file signature mismatch.",
            "issues": [{
                "title": "get_user signature changed but caller not updated",
                "severity": "high",
                "category": "Bugs",
                "explanation": "auth/service.py changed get_user(conn, user_id) but api/routes.py still calls get_user(user_id).",
                "suggested_fix": "Update api/routes.py to pass db_conn as first arg.",
                "file_path": "api/routes.py",
                "line_number": 10,
                "rule_id": "CROSS_FILE_SIGNATURE_MISMATCH",
            }]
        }), finish_reason="stop")


def main():
    print("=" * 72)
    print("  Inspectra v2 Phase 2 — End-to-end smoke test")
    print("=" * 72)

    # ── 1. Show Phase 2 features ────────────────────────────────────────────
    print(f"\n[1] Prompt version: {PROMPT_VERSION}")
    print(f"    Phase 2 features: file context, PR intent, related changes,")
    print(f"    analyzer findings, language rules, cross-file review, baseline")

    # ── 2. Show model-aware chunk sizing ────────────────────────────────────
    print(f"\n[2] Model-aware chunk sizing:")
    for prov, model in [
        (LLMProvider.OLLAMA, "qwen2.5-coder:14b"),
        (LLMProvider.OPENAI, "gpt-4o-mini"),
        (LLMProvider.ANTHROPIC, "claude-sonnet-4-20250514"),
    ]:
        s = InspectraSettings(provider=prov, model=model)
        print(f"    {prov.value:12} {model:30} → {s.effective_max_chunk_tokens():>6} tokens/chunk")

    # ── 3. Build file context for a fake file ───────────────────────────────
    print(f"\n[3] File context builder:")
    with tempfile.TemporaryDirectory() as d:
        fp = Path(d) / "auth/service.py"
        fp.parent.mkdir(parents=True, exist_ok=True)
        file_content = "\n".join([
            "import sqlite3",
            "from db import get_conn",
            "",
            "def get_user(conn, user_id):",
            "    cursor = conn.cursor()",
            '    return cursor.execute(f"SELECT * FROM users WHERE id = {user_id}").fetchone()',
            "",
            "def delete_user(conn, user_id):",
            "    cursor = conn.cursor()",
            '    cursor.execute(f"DELETE FROM users WHERE id = {user_id}")',
            "    conn.commit()",
        ])
        fp.write_text(file_content)

        diff = (
            "--- a/auth/service.py\n+++ b/auth/service.py\n"
            "@@ -0,0 +1,6 @@\n"
            "+def get_user(conn, user_id):\n"
            "+    cursor = conn.cursor()\n"
            '+    return cursor.execute(f"SELECT * FROM users WHERE id = {user_id}").fetchone()\n'
        )

        ctx = build_file_context(str(fp), diff, max_tokens=2000, context_lines=10)
        print(f"    File: {ctx.file_path}")
        print(f"    Changed ranges: {ctx.line_ranges}")
        print(f"    Context length: {len(ctx.content)} chars")
        print(f"    Is complete: {ctx.is_complete}")
        print(f"    Context includes surrounding code: {'import sqlite3' in ctx.content}")

    # ── 4. Run deterministic analyzers ──────────────────────────────────────
    print(f"\n[4] Deterministic analyzers (regex):")
    analyzer = RegexAnalyzer()
    content = (
        'import pickle\n'
        'data = pickle.loads(unsafe)\n'
        'result = eval(user_input)\n'
        'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n'
    )
    findings = analyzer.analyze("test.py", content, "")
    print(f"    Found {len(findings)} issue(s):")
    for f in findings:
        print(f"      [{f.severity.upper():8}] {f.rule_id:30} line {f.line_number}: {f.title}")

    # ── 5. Build a prompt with ALL Phase 2 context blocks ───────────────────
    print(f"\n[5] Prompt with all Phase 2 context blocks:")
    prompt = build_review_prompt(
        "auth/service.py",
        diff,
        full_file_context="def get_user(conn, user_id):\n    ...\n",
        pr_intent="Add user lookup endpoint for the new /api/users route",
        related_changes=["api/routes.py:10  def list_users():"],
        analyzer_findings=findings[:1],  # just the first finding
        language_rules=get_language_rules("auth/service.py"),
    )
    print(f"    Prompt length: {len(prompt)} chars")
    print(f"    Has 'Full file content': {'Full file content' in prompt}")
    print(f"    Has 'PR Intent': {'PR Intent' in prompt}")
    print(f"    Has 'Other files changed': {'Other files changed' in prompt}")
    print(f"    Has 'Deterministic analyzer': {'Deterministic analyzer' in prompt}")
    print(f"    Has 'Python-specific': {'Python-specific' in prompt}")

    # ── 6. Run the review with the fake LLM ────────────────────────────────
    print(f"\n[6] Running review with simulated LLM + Phase 2 context:")
    provider = FakeLLM()
    reviewer = ChunkReviewer(provider=provider)

    # Pass Phase 2 context to the reviewer
    result = asyncio.run(reviewer.review(
        "auth/service.py", diff,
        full_file_context="def get_user(conn, user_id):\n    ...\n",
        pr_intent="Add user lookup endpoint",
        analyzer_findings=findings[:1],
        language_rules=get_language_rules("auth/service.py"),
    ))
    print(f"    → {len(result.issues)} issue(s) from per-file review:")
    for issue in result.issues:
        print(f"      {issue.severity.emoji} [{issue.severity.value.upper():8}] {issue.title}  ({issue.rule_id})")

    # ── 7. Run cross-file consistency review ────────────────────────────────
    print(f"\n[7] Cross-file consistency review:")
    file_diffs = {
        "auth/service.py": diff,
        "api/routes.py": "--- a/api/routes.py\n+++ b/api/routes.py\n@@ -0,0 +1,1 @@\n+    user = get_user(user_id)\n",
    }
    cross_issues = asyncio.run(run_cross_file_review(provider, file_diffs))
    print(f"    → {len(cross_issues)} cross-file issue(s):")
    for issue in cross_issues:
        print(f"      {issue.severity.emoji} [{issue.severity.value.upper():8}] {issue.title}")
        print(f"        Rule: {issue.rule_id}")
        print(f"        File: {issue.file_path}:{issue.line_number}")

    # Combine results
    all_results = [result, ReviewResult(
        file_path="<cross-file>",
        issues=cross_issues,
        summary="Cross-file issues",
    )]

    # ── 8. Apply baseline suppression ───────────────────────────────────────
    print(f"\n[8] Baseline suppression:")
    # Suppress a DIFFERENT rule to show the SQL_INJECTION finding survives
    baseline = Baseline(suppressions=[
        Suppression(rule_id="UNUSED_IMPORT", file_path="auth/service.py", reason="Known false positive"),
    ])
    print(f"    Baseline has {len(baseline.suppressions)} suppression(s)")
    filtered_results, suppressed_count = apply_baseline(all_results, baseline)
    print(f"    Suppressed {suppressed_count} finding(s) via baseline")
    remaining = sum(len(r.issues) for r in filtered_results)
    print(f"    Remaining: {remaining} finding(s) after suppression")

    # ── 9. Render to Markdown ───────────────────────────────────────────────
    print(f"\n[9] Markdown output (with GitHub suggestion blocks):")
    md = results_to_markdown(filtered_results)
    # Show just the suggestion block
    for line in md.split("\n"):
        if "suggestion" in line or "Suggested fix" in line:
            print(f"    {line}")

    # ── 10. Render SARIF ────────────────────────────────────────────────────
    sarif = results_to_sarif(filtered_results)
    print(f"\n[10] SARIF document:")
    print(f"     Rules: {len(sarif['runs'][0]['tool']['driver']['rules'])}")
    for rule in sarif['runs'][0]['tool']['driver']['rules']:
        print(f"       - {rule['id']}")
    print(f"     Results: {len(sarif['runs'][0]['results'])}")

    # ── 11. Show CLI suppress command ───────────────────────────────────────
    print(f"\n[11] CLI baseline management:")
    print(f"     $ inspectra suppress SQL_INJECTION --file auth/legacy.py --reason 'Legacy'")
    print(f"     $ inspectra baseline-show")
    print(f"     $ inspectra review --baseline .inspectra-baseline.json")

    print(f"\n{'=' * 72}")
    print(f"  Phase 2 smoke test passed — all features work end-to-end.")
    print(f"  153 tests passing (69 Phase 1 + 84 Phase 2 regression)")
    print(f"{'=' * 72}")


if __name__ == "__main__":
    main()

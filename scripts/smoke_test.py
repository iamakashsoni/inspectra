#!/usr/bin/env python3
"""End-to-end smoke test for Inspectra — no live LLM required."""

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
    def __init__(self):
        super().__init__(system_prompt="sys", model="fake")
        self.call_count = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        if self.call_count == 1:
            return LLMResponse(text=json.dumps({
                "summary": "SQL injection vulnerability confirmed.",
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
    print("Inspectra — end-to-end smoke test\n")

    print(f"[1] Prompt version: {PROMPT_VERSION}")

    print(f"\n[2] Model-aware chunk sizing:")
    for prov, model in [
        (LLMProvider.OLLAMA, "qwen2.5-coder:14b"),
        (LLMProvider.OPENAI, "gpt-4o-mini"),
        (LLMProvider.ANTHROPIC, "claude-sonnet-4-20250514"),
    ]:
        s = InspectraSettings(provider=prov, model=model)
        print(f"    {prov.value:12} {model:30} → {s.effective_max_chunk_tokens():>6} tokens/chunk")

    print(f"\n[3] File context builder:")
    with tempfile.TemporaryDirectory() as d:
        fp = Path(d) / "auth/service.py"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("\n".join([
            "import sqlite3",
            "def get_user(conn, user_id):",
            "    cursor = conn.cursor()",
            '    return cursor.execute(f"SELECT * FROM users WHERE id = {user_id}").fetchone()',
        ]))
        diff = "--- a/auth/service.py\n+++ b/auth/service.py\n@@ -0,0 +1,3 @@\n+def get_user(conn, user_id):\n+    cursor = conn.cursor()\n"
        ctx = build_file_context(str(fp), diff, max_tokens=2000, context_lines=10)
        print(f"    Changed ranges: {ctx.line_ranges}")
        print(f"    Context includes surrounding code: {'import sqlite3' in ctx.content}")

    print(f"\n[4] Deterministic analyzers (regex):")
    analyzer = RegexAnalyzer()
    content = (
        'import pickle\n'
        'data = pickle.loads(unsafe)\n'
        'result = eval(user_input)\n'
    )
    findings = analyzer.analyze("test.py", content, "")
    for f in findings:
        print(f"    [{f.severity.upper():8}] {f.rule_id:30} line {f.line_number}: {f.title}")

    print(f"\n[5] Prompt with all context blocks:")
    prompt = build_review_prompt(
        "auth/service.py", diff,
        full_file_context="def get_user(conn, user_id):\n    ...\n",
        pr_intent="Add user lookup endpoint",
        analyzer_findings=findings[:1],
        language_rules=get_language_rules("auth/service.py"),
    )
    print(f"    Prompt length: {len(prompt)} chars")
    for block in ["Full file content", "PR Intent", "Deterministic analyzer", "Python-specific"]:
        print(f"    Has '{block}': {block in prompt}")

    print(f"\n[6] Running review with simulated LLM:")
    provider = FakeLLM()
    reviewer = ChunkReviewer(provider=provider)
    result = asyncio.run(reviewer.review(
        "auth/service.py", diff,
        full_file_context="def get_user(conn, user_id):\n    ...\n",
        analyzer_findings=findings[:1],
        language_rules=get_language_rules("auth/service.py"),
    ))
    for issue in result.issues:
        print(f"    {issue.severity.emoji} [{issue.severity.value.upper():8}] {issue.title}  ({issue.rule_id})")

    print(f"\n[7] Cross-file review:")
    file_diffs = {
        "auth/service.py": diff,
        "api/routes.py": "--- a/api/routes.py\n+++ b/api/routes.py\n@@ -0,0 +1,1 @@\n+    user = get_user(user_id)\n",
    }
    cross_issues = asyncio.run(run_cross_file_review(provider, file_diffs))
    print(f"    → {len(cross_issues)} cross-file issue(s)")

    all_results = [result, ReviewResult(file_path="<cross-file>", issues=cross_issues, summary="Cross-file")]

    print(f"\n[8] Baseline suppression:")
    baseline = Baseline(suppressions=[
        Suppression(rule_id="UNUSED_IMPORT", file_path="auth/service.py", reason="Known false positive"),
    ])
    filtered, suppressed = apply_baseline(all_results, baseline)
    print(f"    Suppressed {suppressed} finding(s), {sum(len(r.issues) for r in filtered)} remaining")

    print(f"\n[9] SARIF output:")
    sarif = results_to_sarif(filtered)
    print(f"    Rules: {len(sarif['runs'][0]['tool']['driver']['rules'])}")
    print(f"    Results: {len(sarif['runs'][0]['results'])}")

    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()

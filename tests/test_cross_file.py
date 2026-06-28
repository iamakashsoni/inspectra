# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Tests for the cross-file consistency review (#25)."""

import asyncio
import json

from inspectra.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from inspectra.review.cross_file import run_cross_file_review, _parse_cross_file_response


class FakeProvider(BaseLLMProvider):
    """Returns a canned cross-file review response."""
    def __init__(self, response_text: str):
        super().__init__(system_prompt="sys", model="fake")
        self.response_text = response_text
        self.calls = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        return LLMResponse(text=self.response_text, finish_reason="stop")


VALID_CROSS_FILE_RESPONSE = json.dumps({
    "summary": "Found 1 cross-file signature mismatch.",
    "issues": [
        {
            "title": "get_user signature changed but caller not updated",
            "severity": "high",
            "category": "Bugs",
            "explanation": "auth/service.py changed get_user to accept `conn` as first arg, but api/routes.py still calls get_user(user_id) without conn.",
            "suggested_fix": "Update api/routes.py:10 to call get_user(db_conn, user_id)",
            "file_path": "api/routes.py",
            "line_number": 10,
            "rule_id": "CROSS_FILE_SIGNATURE_MISMATCH",
        }
    ]
})


def test_cross_file_review_returns_issues():
    provider = FakeProvider(VALID_CROSS_FILE_RESPONSE)
    file_diffs = {
        "auth/service.py": "--- a/auth/service.py\n+++ b/auth/service.py\n@@ -0,0 +1,1 @@\n+def get_user(conn, user_id):\n",
        "api/routes.py": "--- a/api/routes.py\n+++ b/api/routes.py\n@@ -0,0 +1,1 @@\n+    user = get_user(user_id)\n",
    }
    issues = asyncio.run(run_cross_file_review(provider, file_diffs))
    assert len(issues) == 1
    assert issues[0].title == "get_user signature changed but caller not updated"
    assert issues[0].severity.value == "high"
    assert issues[0].rule_id == "CROSS_FILE_SIGNATURE_MISMATCH"


def test_cross_file_review_skips_single_file():
    """With only 1 file changed, cross-file review is skipped (no cross-file issues possible)."""
    provider = FakeProvider('{"summary":"ok","issues":[]}')
    file_diffs = {"single.py": "+pass\n"}
    issues = asyncio.run(run_cross_file_review(provider, file_diffs))
    assert issues == []
    assert provider.calls == 0  # provider not called at all


def test_cross_file_review_handles_invalid_json():
    provider = FakeProvider("this is not json")
    file_diffs = {
        "a.py": "+def foo():\n    pass\n",
        "b.py": "+def bar():\n    pass\n",
    }
    issues = asyncio.run(run_cross_file_review(provider, file_diffs))
    assert issues == []  # invalid JSON → empty list, no crash


def test_cross_file_review_handles_provider_error():
    class ErrorProvider(BaseLLMProvider):
        async def complete(self, request):
            raise RuntimeError("API down")
    provider = ErrorProvider(system_prompt="sys", model="fake")
    file_diffs = {
        "a.py": "+def foo():\n    pass\n",
        "b.py": "+def bar():\n    pass\n",
    }
    issues = asyncio.run(run_cross_file_review(provider, file_diffs))
    assert issues == []  # provider error → empty list, no crash


def test_cross_file_review_no_signatures_skips():
    """If no def/class signatures are in the diffs, skip the cross-file call."""
    provider = FakeProvider('{"summary":"ok","issues":[]}')
    file_diffs = {
        "a.py": "+x = 1\n",
        "b.py": "+y = 2\n",
    }
    issues = asyncio.run(run_cross_file_review(provider, file_diffs))
    assert issues == []
    assert provider.calls == 0  # no signatures → no LLM call


def test_parse_cross_file_response_empty_issues():
    issues = _parse_cross_file_response('{"summary":"ok","issues":[]}')
    assert issues == []


def test_parse_cross_file_response_strips_fences():
    fenced = '```json\n{"summary":"ok","issues":[]}\n```'
    issues = _parse_cross_file_response(fenced)
    assert issues == []

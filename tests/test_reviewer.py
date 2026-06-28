# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Tests for the ChunkReviewer — uses a fake provider that returns canned JSON,
verifies the retry loop kicks in on parse failure, and verifies the new
rule_id field is parsed.
"""

import asyncio
import json
from typing import List

from inspectra.config.settings import ReviewCategories
from inspectra.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from inspectra.review.reviewer import ChunkReviewer
from inspectra.review.severity import Severity


class FakeProvider(BaseLLMProvider):
    """Returns canned responses in sequence — for testing the retry loop."""

    def __init__(self, responses: List[str]):
        super().__init__(system_prompt="test", model="fake")
        self.responses = responses
        self.calls = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        resp = self.responses[self.calls]
        self.calls += 1
        return LLMResponse(text=resp, finish_reason="stop")


VALID_RESPONSE = json.dumps({
    "summary": "Adds a SQL query with a vulnerability.",
    "issues": [
        {
            "title": "SQL Injection",
            "severity": "critical",
            "category": "Security",
            "explanation": "Direct string interpolation into SQL.",
            "suggested_fix": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
            "file_path": "auth/service.py",
            "line_number": 42,
            "rule_id": "SQL_INJECTION",
        }
    ]
})


def test_review_parses_valid_response():
    provider = FakeProvider([VALID_RESPONSE])
    reviewer = ChunkReviewer(provider=provider, categories=ReviewCategories())
    result = asyncio.run(reviewer.review("auth/service.py", "+def get_user(conn, user_id): ..."))
    assert result.file_path == "auth/service.py"
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.title == "SQL Injection"
    assert issue.severity == Severity.CRITICAL
    assert issue.rule_id == "SQL_INJECTION"
    assert issue.line_number == 42


def test_review_retries_on_invalid_json():
    """First call returns garbage, second returns valid JSON — should succeed."""
    provider = FakeProvider(["this is not json", VALID_RESPONSE])
    reviewer = ChunkReviewer(provider=provider, categories=ReviewCategories(), max_retries=3)
    result = asyncio.run(reviewer.review("auth/service.py", "+pass"))
    assert len(result.issues) == 1
    assert provider.calls == 2  # First call failed, second succeeded


def test_review_exhausts_retries():
    """All calls return invalid JSON — should return a failure ReviewResult."""
    provider = FakeProvider(["bad", "worse", "still bad"])
    reviewer = ChunkReviewer(provider=provider, categories=ReviewCategories(), max_retries=3)
    result = asyncio.run(reviewer.review("foo.py", "+pass"))
    assert result.has_issues is False
    assert "Failed to review" in result.summary
    assert provider.calls == 3


def test_review_handles_empty_issues():
    """LLM returns no issues — should produce a clean result with empty issues list."""
    empty = json.dumps({"summary": "Looks good.", "issues": []})
    provider = FakeProvider([empty])
    reviewer = ChunkReviewer(provider=provider, categories=ReviewCategories())
    result = asyncio.run(reviewer.review("foo.py", "+pass"))
    assert result.issues == []
    assert result.summary == "Looks good."


def test_review_falls_back_on_missing_rule_id():
    """Issues without rule_id get an empty string (not a crash)."""
    response = json.dumps({
        "summary": "ok",
        "issues": [{
            "title": "Bad", "severity": "low", "category": "General",
            "explanation": "vague", "suggested_fix": "",
            "file_path": "foo.py", "line_number": 1,
            # rule_id intentionally omitted
        }]
    })
    provider = FakeProvider([response])
    reviewer = ChunkReviewer(provider=provider, categories=ReviewCategories())
    result = asyncio.run(reviewer.review("foo.py", "+pass"))
    assert len(result.issues) == 1
    assert result.issues[0].rule_id == ""

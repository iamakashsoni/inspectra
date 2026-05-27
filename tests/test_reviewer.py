"""Tests for the chunk reviewer and response parser."""

import json
import pytest

from inspectra.llm.base import BaseLLMProvider
from inspectra.review.reviewer import ChunkReviewer, _strip_fences
from inspectra.review.severity import Severity


class MockProvider(BaseLLMProvider):
    def __init__(self, response: str):
        self._response = response

    async def review_code(self, prompt: str) -> str:
        return self._response


VALID_RESPONSE = json.dumps({
    "summary": "The code has a SQL injection vulnerability.",
    "issues": [
        {
            "title": "SQL Injection",
            "severity": "critical",
            "category": "Security",
            "explanation": "User input directly concatenated into SQL query.",
            "suggested_fix": "Use parameterized queries.",
            "file_path": "auth/service.py",
            "line_number": 42,
        }
    ],
})


@pytest.mark.asyncio
async def test_reviewer_parses_valid_json():
    provider = MockProvider(VALID_RESPONSE)
    reviewer = ChunkReviewer(provider)
    result = await reviewer.review("auth/service.py", "some diff")

    assert result.file_path == "auth/service.py"
    assert len(result.issues) == 1
    assert result.issues[0].severity == Severity.CRITICAL
    assert result.issues[0].title == "SQL Injection"


@pytest.mark.asyncio
async def test_reviewer_handles_invalid_json():
    provider = MockProvider("This is not JSON at all.")
    reviewer = ChunkReviewer(provider)
    result = await reviewer.review("foo.py", "diff")

    assert result.file_path == "foo.py"
    assert result.issues == []


@pytest.mark.asyncio
async def test_reviewer_handles_fenced_json():
    fenced = f"```json\n{VALID_RESPONSE}\n```"
    provider = MockProvider(fenced)
    reviewer = ChunkReviewer(provider)
    result = await reviewer.review("auth/service.py", "diff")

    assert len(result.issues) == 1


def test_strip_fences():
    assert _strip_fences("```json\n{}\n```") == "{}"
    assert _strip_fences("```\n{}\n```") == "{}"
    assert _strip_fences("{}") == "{}"


@pytest.mark.asyncio
async def test_reviewer_handles_provider_exception():
    class FailingProvider(BaseLLMProvider):
        async def review_code(self, prompt: str) -> str:
            raise RuntimeError("LLM is down")

    reviewer = ChunkReviewer(FailingProvider())
    result = await reviewer.review("crash.py", "diff")

    assert "Review failed" in result.summary
    assert result.issues == []

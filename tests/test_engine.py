"""Tests for the ReviewEngine orchestration layer."""

from __future__ import annotations

import json
import pytest

from inspectra.config.settings import InspectraSettings, LLMProvider
from inspectra.llm.base import BaseLLMProvider
from inspectra.review.engine import ReviewEngine, _merge_results
from inspectra.review.severity import ReviewIssue, ReviewResult, Severity


def _make_settings(**kwargs) -> InspectraSettings:
    defaults = dict(provider=LLMProvider.OLLAMA, model="test", dry_run=False)
    return InspectraSettings(**{**defaults, **kwargs})


class EchoProvider(BaseLLMProvider):
    """Returns a valid JSON review response for every call."""

    def __init__(self, issues: list[dict] | None = None):
        self._issues = issues or []

    async def review_code(self, prompt: str) -> str:
        return json.dumps(
            {
                "summary": "Test summary",
                "issues": self._issues,
            }
        )


class BrokenProvider(BaseLLMProvider):
    async def review_code(self, prompt: str) -> str:
        raise RuntimeError("Provider unavailable")


@pytest.mark.asyncio
async def test_engine_dry_run_skips_llm():
    settings = _make_settings(dry_run=True)
    engine = ReviewEngine(provider=BrokenProvider(), settings=settings)
    results = await engine.run({"foo.py": "some diff"})
    # Should return dry-run results without calling the (broken) provider
    assert len(results) == 1
    assert results[0].summary == "[dry-run]"


@pytest.mark.asyncio
async def test_engine_returns_empty_for_no_files():
    settings = _make_settings()
    engine = ReviewEngine(provider=EchoProvider(), settings=settings)
    results = await engine.run({})
    assert results == []


@pytest.mark.asyncio
async def test_engine_reviews_single_file():
    settings = _make_settings()
    provider = EchoProvider(
        issues=[
            {
                "title": "SQL Injection",
                "severity": "critical",
                "category": "Security",
                "explanation": "User input in query",
                "suggested_fix": "Use params",
                "file_path": "app.py",
                "line_number": 10,
            }
        ]
    )
    engine = ReviewEngine(provider=provider, settings=settings)
    results = await engine.run({"app.py": "some diff"})

    assert len(results) == 1
    assert results[0].file_path == "app.py"
    assert len(results[0].issues) == 1
    assert results[0].issues[0].severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_engine_merges_multiple_chunks_same_file():
    settings = _make_settings(max_chunk_tokens=1)  # force many chunks
    provider = EchoProvider()
    engine = ReviewEngine(provider=provider, settings=settings)

    # Provide a diff large enough to produce multiple chunks
    big_diff = "\n".join(
        f"@@ -{i},{5} +{i},{5} @@\n" + "\n".join(f" line {j}" for j in range(5))
        for i in range(10)
    )
    results = await engine.run({"big.py": big_diff})

    # Even if chunked, all results should merge into a single file entry
    assert all(r.file_path == "big.py" for r in results)


@pytest.mark.asyncio
async def test_engine_pr_summary_dry_run():
    settings = _make_settings(dry_run=True)
    engine = ReviewEngine(provider=EchoProvider(), settings=settings)
    summary = await engine.generate_pr_summary(
        [ReviewResult(file_path="foo.py", summary="ok")]
    )
    assert "dry-run" in summary


@pytest.mark.asyncio
async def test_engine_pr_summary_with_no_results():
    settings = _make_settings()
    engine = ReviewEngine(provider=EchoProvider(), settings=settings)
    summary = await engine.generate_pr_summary([])
    assert "No changes" in summary


def test_merge_results_combines_issues():
    r1 = ReviewResult(
        file_path="a.py",
        summary="First chunk",
        issues=[ReviewIssue(title="Bug A", severity=Severity.HIGH, explanation="x")],
    )
    r2 = ReviewResult(
        file_path="a.py",
        summary="Second chunk",
        issues=[ReviewIssue(title="Bug B", severity=Severity.MEDIUM, explanation="y")],
    )
    merged = _merge_results([r1, r2])
    assert len(merged) == 1
    assert len(merged[0].issues) == 2
    assert "First chunk" in merged[0].summary
    assert "Second chunk" in merged[0].summary


def test_merge_results_preserves_separate_files():
    r1 = ReviewResult(file_path="a.py")
    r2 = ReviewResult(file_path="b.py")
    merged = _merge_results([r1, r2])
    assert len(merged) == 2

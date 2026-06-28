# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Tests for model-aware chunk tokens (#28) and ReviewContext wiring."""

import asyncio
import json

from inspectra.config.settings import InspectraSettings, LLMProvider
from inspectra.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from inspectra.review.engine import ReviewContext, ReviewEngine
from inspectra.review.severity import ReviewResult


def test_effective_max_chunk_tokens_uses_model_context_window():
    """gpt-4o-mini has 128k context → should use up to 16k per chunk."""
    s = InspectraSettings(provider=LLMProvider.OPENAI, model="gpt-4o-mini")
    chunk = s.effective_max_chunk_tokens()
    assert chunk == 16_000  # capped at 16k


def test_effective_max_chunk_tokens_caps_at_16k():
    """Claude has 200k context, but we cap at 16k for safety."""
    s = InspectraSettings(provider=LLMProvider.ANTHROPIC, model="claude-sonnet-4-20250514")
    chunk = s.effective_max_chunk_tokens()
    assert chunk == 16_000


def test_effective_max_chunk_tokens_ollama_14b():
    """qwen2.5-coder:14b has 32k context → 16k per chunk."""
    s = InspectraSettings(provider=LLMProvider.OLLAMA, model="qwen2.5-coder:14b")
    chunk = s.effective_max_chunk_tokens()
    assert chunk == 16_000


def test_effective_max_chunk_tokens_ollama_7b():
    """qwen2.5-coder:7b has 32k context → 16k per chunk."""
    s = InspectraSettings(provider=LLMProvider.OLLAMA, model="qwen2.5-coder:7b")
    chunk = s.effective_max_chunk_tokens()
    assert chunk == 16_000


def test_effective_max_chunk_tokens_unknown_model_falls_back():
    """Unknown model → fall back to max_chunk_tokens setting."""
    s = InspectraSettings(provider=LLMProvider.OPENAI, model="some-unknown-model-xyz")
    s.max_chunk_tokens = 5000
    chunk = s.effective_max_chunk_tokens()
    assert chunk == 5000


def test_effective_max_chunk_tokens_bigger_than_default():
    """Model-aware chunking should produce LARGER chunks than the 3k default."""
    s = InspectraSettings(provider=LLMProvider.OPENAI, model="gpt-4o-mini")
    assert s.effective_max_chunk_tokens() > s.max_chunk_tokens  # 16000 > 3000



class FakeProvider(BaseLLMProvider):
    """Returns a canned valid JSON response."""
    def __init__(self):
        super().__init__(system_prompt="sys", model="fake")
        self.calls = 0
        self.last_request = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        self.last_request = request
        return LLMResponse(
            text=json.dumps({"summary": "ok", "issues": []}),
            finish_reason="stop",
        )


def test_engine_with_empty_context_behaves_like_phase1():
    """When ReviewContext is empty (all defaults), the engine runs behavior
    but with features enabled by default (file context, analyzers, etc).
    Passing None should still work."""
    provider = FakeProvider()
    settings = InspectraSettings(provider=LLMProvider.OLLAMA, dry_run=True)
    engine = ReviewEngine(provider=provider, settings=settings)
    results = asyncio.run(engine.run({"test.py": "+pass\n"}, context=None))
    assert len(results) == 1
    assert results[0].summary == "[dry-run]"


def test_engine_disabling_file_context():
    """With enable_file_context=False, the prompt should NOT include 'Full file content'."""
    provider = FakeProvider()
    settings = InspectraSettings(provider=LLMProvider.OLLAMA, dry_run=True)
    engine = ReviewEngine(provider=provider, settings=settings)
    ctx = ReviewContext(enable_file_context=False, enable_analyzers=False,
                        enable_cross_file=False, enable_language_rules=False)
    # dry_run skips LLM calls, so we can't inspect the prompt directly.
    # But we can verify the engine doesn't crash with the context.
    results = asyncio.run(engine.run({"test.py": "+pass\n"}, ctx))
    assert len(results) == 1


def test_engine_disabling_all_phase2_features():
    """When all features are disabled, behavior matches exactly."""
    provider = FakeProvider()
    settings = InspectraSettings(provider=LLMProvider.OLLAMA, dry_run=True)
    engine = ReviewEngine(provider=provider, settings=settings)
    ctx = ReviewContext(
        enable_file_context=False,
        enable_analyzers=False,
        enable_cross_file=False,
        enable_language_rules=False,
        pr_intent=None,
        baseline=None,
    )
    results = asyncio.run(engine.run({"test.py": "+pass\n"}, ctx))
    assert len(results) == 1
    assert results[0].summary == "[dry-run]"


def test_review_context_defaults_enable_phase2():
    """By default, ReviewContext should enable all features."""
    ctx = ReviewContext()
    assert ctx.enable_file_context is True
    assert ctx.enable_analyzers is True
    assert ctx.enable_cross_file is True
    assert ctx.enable_language_rules is True
    assert ctx.pr_intent is None
    assert ctx.baseline is None

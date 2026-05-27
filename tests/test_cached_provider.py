"""Tests for the CachedProvider LLM wrapper."""

from __future__ import annotations

import pytest

from inspectra.llm.base import BaseLLMProvider
from inspectra.llm.cached_provider import CachedProvider
from inspectra.utils.cache import ReviewCache


class CountingProvider(BaseLLMProvider):
    """Records how many times review_code is called."""

    def __init__(self, response: str = "ok") -> None:
        self._response = response
        self.call_count = 0

    async def review_code(self, prompt: str) -> str:
        self.call_count += 1
        return self._response


@pytest.fixture
def inner():
    return CountingProvider(response='{"summary":"good","issues":[]}')


@pytest.fixture
def cache(tmp_path):
    return ReviewCache(cache_dir=tmp_path / "cache")


@pytest.mark.asyncio
async def test_first_call_hits_provider(inner, cache):
    provider = CachedProvider(inner, cache)
    result = await provider.review_code("prompt A")
    assert inner.call_count == 1
    assert result == inner._response


@pytest.mark.asyncio
async def test_second_call_uses_cache(inner, cache):
    provider = CachedProvider(inner, cache)
    await provider.review_code("same prompt")
    await provider.review_code("same prompt")
    assert inner.call_count == 1  # second call was cached


@pytest.mark.asyncio
async def test_different_prompts_both_call_provider(inner, cache):
    provider = CachedProvider(inner, cache)
    await provider.review_code("prompt A")
    await provider.review_code("prompt B")
    assert inner.call_count == 2


@pytest.mark.asyncio
async def test_cache_stats_reflect_hits(inner, cache):
    provider = CachedProvider(inner, cache)
    await provider.review_code("p")
    await provider.review_code("p")
    stats = provider.cache_stats
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_name_includes_inner_name(inner, cache):
    provider = CachedProvider(inner, cache)
    assert "Cached" in provider.name
    assert "CountingProvider" in provider.name

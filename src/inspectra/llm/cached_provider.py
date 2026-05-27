"""Caching wrapper for any LLM provider."""

from __future__ import annotations

from inspectra.llm.base import BaseLLMProvider
from inspectra.utils.cache import ReviewCache
from inspectra.utils.logger import logger


class CachedProvider(BaseLLMProvider):
    """
    Decorator that adds disk-based caching to any BaseLLMProvider.

    Cache key is derived from the prompt, so identical prompts
    (same diff + same file path) skip the LLM call entirely.
    """

    def __init__(self, inner: BaseLLMProvider, cache: ReviewCache) -> None:
        self._inner = inner
        self._cache = cache

    @property
    def name(self) -> str:
        return f"Cached({self._inner.name})"

    async def review_code(self, prompt: str) -> str:
        key = ReviewCache.make_key("prompt", prompt)
        cached = self._cache.get(key)

        if cached is not None:
            return cached

        response = await self._inner.review_code(prompt)
        self._cache.set(key, response)
        logger.debug("Cached response for key %s", key[:8])
        return response

    @property
    def cache_stats(self) -> dict[str, int]:
        return self._cache.stats

# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Caching wrapper for any LLM provider.

Cache key includes all request fields that affect output (user_prompt,
system_prompt, temperature, max_tokens, schema presence, model) so changing
any of them correctly invalidates the cache.
"""

from __future__ import annotations

import asyncio
import json

from inspectra.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from inspectra.utils.cache import ReviewCache
from inspectra.utils.logger import logger


class CachedProvider(BaseLLMProvider):
    """Decorator that adds disk-based caching to any BaseLLMProvider."""

    def __init__(self, inner: BaseLLMProvider, cache: ReviewCache) -> None:
        super().__init__(system_prompt=inner.system_prompt, model=inner.model)
        self._inner = inner
        self._cache = cache

    @property
    def name(self) -> str:
        return f"Cached({self._inner.name})"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        schema_sig = "schema" if request.json_schema else "no-schema"
        cache_payload = json.dumps({
            "user_prompt": request.user_prompt,
            "system_prompt": request.system_prompt or self.system_prompt,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "schema": schema_sig,
            "model": self.model,
        }, sort_keys=True, ensure_ascii=False)

        key = ReviewCache.make_key("prompt", cache_payload)

        cached = await asyncio.to_thread(self._cache.get, key)
        if cached is not None:
            logger.debug("Cache hit for key %s", key[:8])
            return LLMResponse(text=cached, finish_reason="stop", model=self.model)

        response = await self._inner.complete(request)
        if response.text:
            await asyncio.to_thread(self._cache.set, key, response.text)
        return response

    @property
    def cache_stats(self) -> dict[str, int]:
        return self._cache.stats

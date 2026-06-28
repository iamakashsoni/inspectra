# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Factory that instantiates the correct LLM provider from settings.

Phase 1: now supports 5 providers (added Nvidia + OpenRouter). All
OpenAI-compatible providers share the same code path, just different defaults.
"""

from __future__ import annotations

from pathlib import Path

from inspectra.config.settings import InspectraSettings, LLMProvider
from inspectra.llm.base import BaseLLMProvider
from inspectra.review.prompts import SYSTEM_PROMPT


def build_provider(
    settings: InspectraSettings,
    use_cache: bool = False,
    cache_dir: Path | str | None = None,
) -> BaseLLMProvider:
    """Instantiate and return the configured LLM provider."""
    model = settings.model_for_provider()

    match settings.provider:
        case LLMProvider.OLLAMA:
            from inspectra.llm.ollama_provider import OllamaProvider
            provider: BaseLLMProvider = OllamaProvider(
                model=model,
                host=settings.ollama.host,
                timeout=settings.ollama.timeout,
                system_prompt=SYSTEM_PROMPT,
            )

        case LLMProvider.OPENAI:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not set.")
            from inspectra.llm.openai_provider import OpenAIProvider
            provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model=model,
                base_url=settings.openai_base_url,
                system_prompt=SYSTEM_PROMPT,
            )

        case LLMProvider.ANTHROPIC:
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is not set.")
            from inspectra.llm.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=model,
                base_url=settings.anthropic_base_url,
                system_prompt=SYSTEM_PROMPT,
            )

        case LLMProvider.NVIDIA:
            if not settings.nvidia_api_key:
                raise ValueError("NVIDIA_API_KEY is not set.")
            from inspectra.llm.nvidia_provider import NvidiaProvider
            provider = NvidiaProvider(
                api_key=settings.nvidia_api_key,
                model=model,
                base_url=settings.nvidia_base_url,
                system_prompt=SYSTEM_PROMPT,
            )

        case LLMProvider.OPENROUTER:
            if not settings.openrouter_api_key:
                raise ValueError("OPENROUTER_API_KEY is not set.")
            from inspectra.llm.openrouter_provider import OpenRouterProvider
            provider = OpenRouterProvider(
                api_key=settings.openrouter_api_key,
                model=model,
                base_url=settings.openrouter_base_url,
                system_prompt=SYSTEM_PROMPT,
            )

        case _:
            raise ValueError(f"Unknown provider: {settings.provider!r}")

    if use_cache:
        from inspectra.llm.cached_provider import CachedProvider
        from inspectra.utils.cache import ReviewCache
        _cache_dir = Path(cache_dir) if cache_dir else Path(".inspectra_cache")
        provider = CachedProvider(provider, ReviewCache(cache_dir=_cache_dir))

    return provider

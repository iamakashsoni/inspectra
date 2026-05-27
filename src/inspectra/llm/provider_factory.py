"""Factory that instantiates the correct LLM provider from settings."""

from __future__ import annotations

from pathlib import Path

from inspectra.config.settings import InspectraSettings, LLMProvider
from inspectra.llm.base import BaseLLMProvider


def build_provider(
    settings: InspectraSettings,
    use_cache: bool = False,
    cache_dir: Path | str | None = None,
) -> BaseLLMProvider:
    """
    Instantiate and return the configured LLM provider.

    Args:
        settings:   Resolved InspectraSettings.
        use_cache:  If True, wrap the provider in a CachedProvider.
        cache_dir:  Override the default cache directory.

    Raises:
        ValueError: If the required API key is missing or provider is unknown.
    """
    model = settings.model_for_provider()

    match settings.provider:
        case LLMProvider.OLLAMA:
            from inspectra.llm.ollama_provider import OllamaProvider
            provider: BaseLLMProvider = OllamaProvider(
                model=model,
                host=settings.ollama.host,
                timeout=settings.ollama.timeout,
            )

        case LLMProvider.OPENAI:
            if not settings.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY is not set. "
                    "Export it or add it to your .env file."
                )
            from inspectra.llm.openai_provider import OpenAIProvider
            provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model=model,
                temperature=settings.temperature,
            )

        case LLMProvider.ANTHROPIC:
            if not settings.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is not set. "
                    "Export it or add it to your .env file."
                )
            from inspectra.llm.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=model,
                temperature=settings.temperature,
            )

        case _:
            raise ValueError(f"Unknown provider: {settings.provider!r}")

    if use_cache:
        from inspectra.llm.cached_provider import CachedProvider
        from inspectra.utils.cache import ReviewCache
        _cache_dir = Path(cache_dir) if cache_dir else Path(".inspectra_cache")
        provider = CachedProvider(provider, ReviewCache(cache_dir=_cache_dir))

    return provider

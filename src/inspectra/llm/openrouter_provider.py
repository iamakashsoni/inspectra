"""OpenRouter provider.

OpenRouter (openrouter.ai) is an aggregator: one API key, access to dozens of
model providers (Anthropic, OpenAI, Meta, Mistral, etc.). It's OpenAI-compatible
at the wire level.

Two useful extras OpenRouter supports:
- `HTTP-Referer` and `X-Title` headers (for app attribution in their dashboard)
- Model strings like `anthropic/claude-3.5-sonnet` or `openai/gpt-4o`

Default model: `anthropic/claude-3.5-sonnet` (a strong, cheap default that
many OpenRouter users start with).
"""

from __future__ import annotations

from inspectra.llm.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter (openrouter.ai) — aggregator over many model providers."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        base_url: str = "https://openrouter.ai/api/v1",
        system_prompt: str = "",
        timeout: int = 300,
        app_name: str = "inspectra",
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            system_prompt=system_prompt,
            timeout=timeout,
        )
        # OpenRouter-friendly attribution headers (optional but appreciated)
        self.extra_headers["HTTP-Referer"] = "https://github.com/iamakashsoni/inspectra"
        self.extra_headers["X-Title"] = app_name

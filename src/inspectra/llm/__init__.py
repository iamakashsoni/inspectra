"""LLM provider abstraction layer.

Design principles (Phase 1):
- One unified `BaseLLMProvider` interface with a richer `LLMRequest`/`LLMResponse`
- `OpenAICompatibleProvider` base class shared by OpenAI, Nvidia NIM, OpenRouter
- Structured JSON output via schema (works on all 5 providers)
- Single canonical SYSTEM_PROMPT, shared across providers (no duplication)
- `CachedProvider` keys on `(prompt_version, file_path, diff_text)` so prompt
  tweaks invalidate cleanly instead of nuking the whole cache
"""

from inspectra.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from inspectra.llm.provider_factory import build_provider

__all__ = [
    "BaseLLMProvider",
    "LLMRequest",
    "LLMResponse",
    "build_provider",
]

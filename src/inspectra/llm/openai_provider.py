"""OpenAI Chat Completions provider — thin specialization of OpenAICompatibleProvider."""

from __future__ import annotations

from inspectra.llm.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI (api.openai.com)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        system_prompt: str = "",
        timeout: int = 300,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            system_prompt=system_prompt,
            timeout=timeout,
        )

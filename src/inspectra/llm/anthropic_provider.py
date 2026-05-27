"""Anthropic Claude LLM provider."""

from __future__ import annotations

import anthropic

from inspectra.llm.base import BaseLLMProvider
from inspectra.utils.logger import logger


class AnthropicProvider(BaseLLMProvider):
    """Uses the Anthropic Messages API."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def review_code(self, prompt: str) -> str:
        logger.debug("Sending prompt to Anthropic model=%s", self.model)

        message = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=(
                "You are Inspectra, a senior software engineer performing a thorough code review. "
                "Be precise, constructive, and focus on correctness, security, and maintainability."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

        result = message.content[0].text if message.content else ""
        logger.debug("Anthropic responded with %d chars", len(result))
        return result

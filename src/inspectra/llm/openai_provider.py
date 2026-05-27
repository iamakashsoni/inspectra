"""OpenAI LLM provider."""

from __future__ import annotations

from openai import AsyncOpenAI

from inspectra.llm.base import BaseLLMProvider
from inspectra.utils.logger import logger


class OpenAIProvider(BaseLLMProvider):
    """Uses the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = AsyncOpenAI(api_key=api_key)

    async def review_code(self, prompt: str) -> str:
        logger.debug("Sending prompt to OpenAI model=%s", self.model)

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Inspectra, a senior software engineer "
                        "performing a thorough code review. Be precise, "
                        "constructive, and focus on correctness, security, "
                        "and maintainability."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        result = response.choices[0].message.content or ""
        logger.debug("OpenAI responded with %d chars", len(result))
        return result

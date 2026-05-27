"""Ollama local LLM provider."""

from __future__ import annotations

import httpx

from inspectra.llm.base import BaseLLMProvider
from inspectra.utils.logger import logger


class OllamaProvider(BaseLLMProvider):
    """
    Calls a locally running Ollama server.

    Recommended for:
    - Air-gapped / enterprise deployments
    - Keeping repository code private
    - Avoiding cloud API costs
    """

    def __init__(
        self,
        model: str = "qwen2.5-coder:14b",
        host: str = "http://localhost:11434",
        timeout: int = 300,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    async def review_code(self, prompt: str) -> str:
        logger.debug("Sending prompt to Ollama model=%s host=%s", self.model, self.host)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()

        result: str = data.get("response", "")
        logger.debug("Ollama responded with %d chars", len(result))
        return result

    async def list_models(self) -> list[str]:
        """Return available models from local Ollama instance."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            data = response.json()
        return [m["name"] for m in data.get("models", [])]

    async def health_check(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(self.host)
                return r.status_code < 500
        except Exception:
            return False

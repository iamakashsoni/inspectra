# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Ollama local LLM provider."""

from __future__ import annotations

from typing import Any

import httpx

from inspectra.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from inspectra.llm.openai_compatible import _normalize_finish_reason
from inspectra.utils.logger import logger


class OllamaProvider(BaseLLMProvider):
    """Calls a locally (or remotely) running Ollama server."""

    def __init__(
        self,
        *,
        model: str = "qwen2.5-coder:14b",
        host: str = "http://localhost:11434",
        timeout: int = 300,
        system_prompt: str = "",
    ) -> None:
        super().__init__(system_prompt=system_prompt, model=model)
        self.host = host.rstrip("/")
        self.timeout = timeout
        #  lazily-created, reused client
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=30,
                ),
            )
        return self._client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        url = f"{self.host}/api/chat"
        system = request.system_prompt or self.system_prompt

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "options": {"temperature": request.temperature},
        }

        # Ollama supports `format` as a JSON schema for guaranteed-valid JSON
        if request.json_schema:
            payload["format"] = request.json_schema

        logger.debug("POST %s model=%s", url, self.model)

        client = self._get_client()
        resp = await client.post(url, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(
                f"{self.name} returned {resp.status_code}: {resp.text[:500]}"
            )

        resp.raise_for_status()
        data = resp.json()
        message = data.get("message", {})

        #  normalize Ollama's done_reason to canonical finish_reason
        done_reason = data.get("done_reason", "stop")
        finish_reason = _normalize_finish_reason(done_reason)

        return LLMResponse(
            text=message.get("content", ""),
            finish_reason=finish_reason,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            model=data.get("model", self.model),
            raw=data,
        )

    async def list_models(self) -> list[str]:
        """Return available models from the Ollama instance."""
        # Use a separate short-timeout client for this one-shot metadata call
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.host}/api/tags")
            resp.raise_for_status()
            data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    async def health_check(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(self.host)
                return r.status_code < 500
        except Exception:
            return False

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Base class for any provider that speaks the OpenAI Chat Completions API.

This single class is the entire implementation for three providers:
- OpenAI        (api.openai.com/v1)
- Nvidia NIM    (integrate.api.nvidia.com/v1)  — same API, different default model
- OpenRouter    (openrouter.ai/api/v1)         — same API, different default model

That's the whole point: the user said "avoid over-complication." Three providers
become ~30 lines of config each instead of 3× duplicated HTTP code.

Audit fix (H1): a single httpx.AsyncClient is now created lazily per provider
instance and reused across all complete() calls, enabling HTTP connection
pooling. For a 30-file PR with concurrency=10, this eliminates ~27 redundant
TCP+TLS handshakes.
"""

from __future__ import annotations

from typing import Any

import httpx

from inspectra.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from inspectra.utils.logger import logger


class OpenAICompatibleProvider(BaseLLMProvider):
    """Speaks the OpenAI Chat Completions API over a configurable base URL."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        system_prompt: str = "",
        timeout: int = 300,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(system_prompt=system_prompt, model=model)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.extra_headers = extra_headers or {}
        # H1 fix: lazily-created, reused client for connection pooling
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Return the shared AsyncClient, creating it on first use."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                # Connection pooling: reuse connections across requests
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=30,
                ),
            )
        return self._client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }

        messages = []
        if request.system_prompt or self.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt or self.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        # Structured output: prefer json_schema (OpenAI/Nvidia), fall back to json_object
        if request.json_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "inspectra_review",
                    "schema": request.json_schema,
                    "strict": False,
                },
            }

        logger.debug("POST %s model=%s", url, self.model)

        client = self._get_client()
        resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code != 200:
            # Include status code in the error message so the retry layer
            # can detect transient codes (429, 503, etc.)
            raise RuntimeError(
                f"{self.name} returned {resp.status_code}: {resp.text[:500]}"
            )

        # Raise on HTTP errors so the retry layer catches them
        resp.raise_for_status()

        data = resp.json()
        choice = data["choices"][0]
        return LLMResponse(
            text=choice["message"]["content"] or "",
            finish_reason=_normalize_finish_reason(choice.get("finish_reason", "stop")),
            prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
            completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
            model=data.get("model", self.model),
            raw=data,
        )

    async def close(self) -> None:
        """Close the shared HTTP client. Call this when done with the provider."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


def _normalize_finish_reason(reason: str) -> str:
    """Normalize provider-specific finish_reason values to a canonical set.

    H5 fix: different providers use different names for the same concept.
    We normalize to: stop | length | tool_call | content_filter | error
    """
    mapping = {
        "stop": "stop",
        "length": "length",
        "max_tokens": "length",           # Anthropic
        "tool_calls": "tool_call",
        "tool_use": "tool_call",           # Anthropic
        "function_call": "tool_call",
        "content_filter": "content_filter",
        "end_turn": "stop",               # Anthropic
        "end_sequence": "stop",
    }
    return mapping.get(reason, reason if reason else "stop")

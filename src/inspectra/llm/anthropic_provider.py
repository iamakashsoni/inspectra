# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Anthropic Claude provider.

Uses the Messages API with tool-calling forced to `submit_review` so we get
guaranteed-valid structured output (no fence-stripping, no truncation loss).

Audit fixes:
- H1: Shared httpx.AsyncClient for connection pooling (was: new client per request)
- H5: finish_reason normalized via _normalize_finish_reason (was: raw Anthropic
  stop_reason values like 'end_turn', 'max_tokens' which didn't match the
  reviewer's 'length' check)
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from inspectra.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from inspectra.llm.openai_compatible import _normalize_finish_reason
from inspectra.utils.logger import logger


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Messages API with forced tool-call for structured output."""

    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: str | None = None,
        system_prompt: str = "",
        timeout: int = 300,
    ) -> None:
        super().__init__(system_prompt=system_prompt, model=model)
        self.api_key = api_key
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        # H1 fix: lazily-created, reused client
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
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json",
        }

        system = request.system_prompt or self.system_prompt
        messages = [{"role": "user", "content": request.user_prompt}]

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "system": system,
            "messages": messages,
        }

        # Force structured output via tool_use when a schema is provided
        if request.json_schema:
            payload["tools"] = [{
                "name": "submit_review",
                "description": "Submit the structured code review findings.",
                "input_schema": request.json_schema,
            }]
            payload["tool_choice"] = {"type": "tool", "name": "submit_review"}

        logger.debug("POST %s model=%s", url, self.model)

        client = self._get_client()
        resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(
                f"{self.name} returned {resp.status_code}: {resp.text[:500]}"
            )

        resp.raise_for_status()
        data = resp.json()

        # Extract text or tool_use input
        text = ""
        raw_stop_reason = data.get("stop_reason", "stop")
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
            elif block.get("type") == "tool_use" and block.get("name") == "submit_review":
                # Serialize the tool input back to JSON for our parser
                text = json.dumps(block.get("input", {}))

        # H5 fix: normalize Anthropic's stop_reason to canonical finish_reason
        finish_reason = _normalize_finish_reason(raw_stop_reason)

        usage = data.get("usage", {})
        return LLMResponse(
            text=text,
            finish_reason=finish_reason,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            model=data.get("model", self.model),
            raw=data,
        )

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

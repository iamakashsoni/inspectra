# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Tests for all five providers' wire-level behavior.

Uses httpx.MockTransport to intercept HTTP calls so we don't need real
API keys or network access. Verifies each provider:
- Posts to the correct URL
- Sends the right headers (auth, content-type)
- Includes the JSON schema in the request when one is provided
- Parses the response into an LLMResponse correctly
"""

import asyncio
import json
from typing import Callable

import httpx

from inspectra.llm.base import LLMRequest
from inspectra.llm.nvidia_provider import NvidiaProvider
from inspectra.llm.openai_provider import OpenAIProvider
from inspectra.llm.openrouter_provider import OpenRouterProvider
from inspectra.review.prompts import REVIEW_JSON_SCHEMA, SYSTEM_PROMPT


def _make_mock_transport(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def _openai_style_response(content: str, model: str = "test-model") -> bytes:
    return json.dumps({
        "model": model,
        "choices": [{
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }).encode()


def test_openai_provider_sends_correct_request():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["headers"] = dict(req.headers)
        captured["body"] = json.loads(req.content)
        return httpx.Response(200, content=_openai_style_response('{"summary":"ok","issues":[]}'))

    # Monkey-patch httpx.AsyncClient to use our transport
    original_init = httpx.AsyncClient.__init__
    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = _make_mock_transport(handler)
        original_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = patched_init
    try:
        provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini", system_prompt=SYSTEM_PROMPT)
        resp = asyncio.run(provider.complete(LLMRequest(
            user_prompt="review this", json_schema=REVIEW_JSON_SCHEMA
        )))
    finally:
        httpx.AsyncClient.__init__ = original_init

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer sk-test"
    assert captured["body"]["model"] == "gpt-4o-mini"
    assert captured["body"]["response_format"]["type"] == "json_schema"
    assert captured["body"]["messages"][0]["role"] == "system"
    assert captured["body"]["messages"][1]["role"] == "user"
    assert resp.text == '{"summary":"ok","issues":[]}'
    assert resp.prompt_tokens == 10


def test_nvidia_provider_uses_nvidia_url():
    captured: dict = {}
    def handler(req):
        captured["url"] = str(req.url)
        return httpx.Response(200, content=_openai_style_response('{}', "meta/llama-3.3-70b-instruct"))
    original_init = httpx.AsyncClient.__init__
    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = _make_mock_transport(handler)
        original_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = patched_init
    try:
        provider = NvidiaProvider(api_key="nvapi-test")
        asyncio.run(provider.complete(LLMRequest(user_prompt="x")))
    finally:
        httpx.AsyncClient.__init__ = original_init
    assert captured["url"] == "https://integrate.api.nvidia.com/v1/chat/completions"


def test_openrouter_provider_adds_attribution_headers():
    captured: dict = {}
    def handler(req):
        captured["headers"] = dict(req.headers)
        return httpx.Response(200, content=_openai_style_response('{}'))
    original_init = httpx.AsyncClient.__init__
    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = _make_mock_transport(handler)
        original_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = patched_init
    try:
        provider = OpenRouterProvider(api_key="sk-or-test")
        asyncio.run(provider.complete(LLMRequest(user_prompt="x")))
    finally:
        httpx.AsyncClient.__init__ = original_init
    assert captured["headers"]["x-title"] == "inspectra"
    assert "http-referer" in {k.lower() for k in captured["headers"]}


def test_self_hosted_nim_url_override():
    """User can point NvidiaProvider at a self-hosted NIM container."""
    captured: dict = {}
    def handler(req):
        captured["url"] = str(req.url)
        return httpx.Response(200, content=_openai_style_response('{}'))
    original_init = httpx.AsyncClient.__init__
    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = _make_mock_transport(handler)
        original_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = patched_init
    try:
        provider = NvidiaProvider(
            api_key="dummy",
            base_url="http://localhost:8000/v1",  # self-hosted NIM
        )
        asyncio.run(provider.complete(LLMRequest(user_prompt="x")))
    finally:
        httpx.AsyncClient.__init__ = original_init
    assert captured["url"] == "http://localhost:8000/v1/chat/completions"

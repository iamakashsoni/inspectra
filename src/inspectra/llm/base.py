# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Abstract base class and request/response models for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMRequest:
    """A single completion request, provider-agnostic."""

    user_prompt: str
    system_prompt: str = ""
    json_schema: dict | None = None      # If set, provider must return valid JSON matching this schema
    temperature: float = 0.2
    max_tokens: int = 4096
    # Provider-specific passthrough (e.g. OpenAI "organization" header)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """A single completion response, provider-agnostic."""

    text: str
    finish_reason: str = "stop"          # "stop" | "length" | "tool_call" | "error"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""                      # Echo back which model actually answered
    raw: Any = None                      # Original SDK response, for debugging


class BaseLLMProvider(ABC):
    """All LLM providers (Ollama, OpenAI, Anthropic, Nvidia, OpenRouter) implement this."""

    def __init__(self, *, system_prompt: str = "", model: str = "") -> None:
        self.system_prompt = system_prompt
        self.model = model

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a request and return a response."""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__

# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Nvidia NIM provider.

Nvidia's integrate.api.nvidia.com endpoint is fully OpenAI-compatible —
same /chat/completions route, same request/response shape, same `response_format`
support for JSON schema. So this class is ~10 lines: just set the right base_url
and a sane default model.

The user can override the URL to point at a self-hosted NIM container
(e.g. http://localhost:8000/v1) for fully air-gapped reviews.

Default model: meta/llama-3.3-70b-instruct (a strong general-purpose model
hosted on build.nvidia.com).
"""

from __future__ import annotations

from inspectra.llm.openai_compatible import OpenAICompatibleProvider


class NvidiaProvider(OpenAICompatibleProvider):
    """Nvidia NIM (integrate.api.nvidia.com or self-hosted NIM container)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "meta/llama-3.3-70b-instruct",
        base_url: str = "https://integrate.api.nvidia.com/v1",
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
        # Nvidia accepts extra headers for tracing; harmless if absent.
        self.extra_headers["Accept"] = "application/json"

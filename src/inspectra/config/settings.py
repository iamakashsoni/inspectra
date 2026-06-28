# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Settings and configuration models for Inspectra v2.

Phase 1 changes:
- Added Nvidia + OpenRouter providers to the enum
- Added per-provider base_url overrides (so users can point at self-hosted NIM, etc.)
- Added review_concurrency setting (0 = auto, picks sensible default per provider)
- Added inline_comments setting (whether to post inline comments on PRs)
- All API keys accept env var aliases
"""

from enum import StrEnum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class LLMProvider(StrEnum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NVIDIA = "nvidia"
    OPENROUTER = "openrouter"


class ReviewCategories(BaseSettings):
    security: bool = True
    bugs: bool = True
    performance: bool = True
    maintainability: bool = True
    architecture: bool = True
    concurrency: bool = True
    scalability: bool = True


class OllamaConfig(BaseSettings):
    host: str = "http://localhost:11434"
    timeout: int = 300


# Approximate context windows for chunk-size auto-tuning (Phase 2 hook).
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "claude-sonnet-4-20250514": 200_000,
    "claude-haiku-4-5-20251001": 200_000,
    "qwen2.5-coder:7b": 32_000,
    "qwen2.5-coder:14b": 32_000,
    "qwen2.5-coder:32b": 32_000,
    "meta/llama-3.3-70b-instruct": 128_000,
}


class InspectraSettings(BaseSettings):
    # LLM
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "qwen2.5-coder:14b"

    # API Keys (from env)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")

    # Per-provider base URL overrides (for self-hosted NIM, on-prem OpenAI proxy, etc.)
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # GitHub
    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    github_repository: str = Field(default="", alias="GITHUB_REPOSITORY")
    github_pr_number: int = Field(default=0, alias="PR_NUMBER")

    # Ollama
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)

    # Review config
    review: ReviewCategories = Field(default_factory=ReviewCategories)

    # Files to exclude
    exclude: list[str] = Field(
        default=[
            "*.lock", "*.min.js", "*.min.css", "dist/*", "build/*", "vendor/*",
            "*.generated.*", "package-lock.json", "yarn.lock", "poetry.lock",
            "*.pb.go", "*.pb.py",
        ]
    )

    # Token management
    max_tokens: int = 12000
    max_chunk_tokens: int = 3000
    temperature: float = 0.2

    # Concurrency — 0 means "auto-pick based on provider"
    review_concurrency: int = 0

    # Whether to post inline PR comments (in addition to the summary comment)
    inline_comments: bool = True

    # Behavior
    verbose: bool = False
    dry_run: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v

    # Sentinel: empty string means "user hasn't picked a model — pick per-provider default"
    # We can't just check truthiness because model has a class-level default of "qwen2.5-coder:14b".
    # So model_for_provider() below checks whether the model matches the Ollama default AND
    # the provider isn't Ollama — if so, swap in the provider-specific default.

    def model_for_provider(self) -> str:
        """Return sensible default model per provider if not explicitly set.

        Behavior: if `self.model` is the Ollama default ("qwen2.5-coder:14b") AND
        the provider is NOT Ollama, treat it as "unset" and use the provider's
        own default. Otherwise return self.model as-is.
        """
        defaults: dict[LLMProvider, str] = {
            LLMProvider.OPENAI: "gpt-4o-mini",
            LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
            LLMProvider.OLLAMA: "qwen2.5-coder:14b",
            LLMProvider.NVIDIA: "meta/llama-3.3-70b-instruct",
            LLMProvider.OPENROUTER: "anthropic/claude-3.5-sonnet",
        }
        # If user is using a non-Ollama provider but never changed the model from
        # the Ollama default, they almost certainly want the provider's real default.
        if self.provider != LLMProvider.OLLAMA and self.model == defaults[LLMProvider.OLLAMA]:
            return defaults[self.provider]
        return self.model

    def effective_concurrency(self) -> int:
        """Pick concurrency: explicit setting wins, otherwise per-provider default."""
        if self.review_concurrency > 0:
            return self.review_concurrency
        # Conservative defaults — cloud providers can do more, Ollama is hardware-bound
        if self.provider == LLMProvider.OLLAMA:
            return 2 if "32b" in self.model else 3
        if self.provider == LLMProvider.OPENAI:
            return 10
        if self.provider == LLMProvider.ANTHROPIC:
            return 8
        if self.provider == LLMProvider.NVIDIA:
            return 5
        if self.provider == LLMProvider.OPENROUTER:
            return 5
        return 3

    def effective_max_chunk_tokens(self) -> int:
        """Phase 2: model-aware chunk size.

        Looks up the configured model's context window and uses up to half of it
        (leaving room for the prompt + response). Falls back to max_chunk_tokens
        setting if the model is unknown.

        This means a 30-file PR on gpt-4o-mini (128k context) can send ~16k-token
        chunks instead of the 3k default — 5× fewer LLM calls, 5× less latency.
        """
        ctx = MODEL_CONTEXT_WINDOWS.get(self.model, 0)
        if ctx > 0:
            # Use half the context window, capped at 16k for safety
            return min(ctx // 2, 16_000)
        return self.max_chunk_tokens

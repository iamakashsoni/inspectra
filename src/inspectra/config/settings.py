"""Settings and configuration models for Inspectra."""

from enum import Enum
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


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


class InspectraSettings(BaseSettings):
    # LLM
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "qwen2.5-coder:14b"

    # API Keys (from env)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

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
            "*.lock",
            "*.min.js",
            "*.min.css",
            "dist/*",
            "build/*",
            "vendor/*",
            "*.generated.*",
            "package-lock.json",
            "yarn.lock",
            "poetry.lock",
            "*.pb.go",
            "*.pb.py",
        ]
    )

    # Token management
    max_tokens: int = 12000
    max_chunk_tokens: int = 3000
    temperature: float = 0.2

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

    def model_for_provider(self) -> str:
        """Return sensible default model per provider if not explicitly set."""
        defaults: dict[LLMProvider, str] = {
            LLMProvider.OPENAI: "gpt-4o-mini",
            LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
            LLMProvider.OLLAMA: "qwen2.5-coder:14b",
        }
        if self.model:
            return self.model
        return defaults[self.provider]

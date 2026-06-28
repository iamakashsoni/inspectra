"""Tests for the language detector and the configurable concurrency logic."""

from inspectra.config.settings import InspectraSettings, LLMProvider
from inspectra.utils.language import detect_language


def test_detect_language_python():
    assert detect_language("foo.py") == "python"
    assert detect_language("foo.pyi") == "python"


def test_detect_language_typescript():
    assert detect_language("foo.ts") == "typescript"
    assert detect_language("foo.tsx") == "typescript"


def test_detect_language_dockerfile_by_basename():
    assert detect_language("Dockerfile") == "dockerfile"
    assert detect_language("containers/Dockerfile") == "dockerfile"
    # .prod suffix variant — basename no longer matches exactly, returns None
    # (acceptable: not all Dockerfile.* variants are common enough to special-case)
    assert detect_language("containers/Dockerfile.prod") is None


def test_detect_language_unknown():
    assert detect_language("foo.xyz") is None
    assert detect_language("README") is None


def test_effective_concurrency_respects_explicit_value():
    s = InspectraSettings(provider=LLMProvider.OPENAI, review_concurrency=7)
    assert s.effective_concurrency() == 7


def test_effective_concurrency_auto_picks_per_provider():
    assert InspectraSettings(provider=LLMProvider.OPENAI).effective_concurrency() == 10
    assert InspectraSettings(provider=LLMProvider.OLLAMA).effective_concurrency() == 3
    assert InspectraSettings(provider=LLMProvider.OLLAMA, model="qwen2.5-coder:32b").effective_concurrency() == 2
    assert InspectraSettings(provider=LLMProvider.ANTHROPIC).effective_concurrency() == 8
    assert InspectraSettings(provider=LLMProvider.NVIDIA).effective_concurrency() == 5
    assert InspectraSettings(provider=LLMProvider.OPENROUTER).effective_concurrency() == 5


def test_settings_default_provider_is_ollama():
    """Self-hosted-first: default provider must be Ollama."""
    s = InspectraSettings()
    assert s.provider == LLMProvider.OLLAMA


def test_settings_supports_all_five_providers():
    """The enum must include all five providers the user asked for."""
    providers = {p.value for p in LLMProvider}
    assert providers == {"ollama", "openai", "anthropic", "nvidia", "openrouter"}

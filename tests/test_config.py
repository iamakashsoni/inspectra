"""Tests for configuration loading and validation."""

import pytest
from pathlib import Path

from inspectra.config.loader import load_settings, _find_config_file
from inspectra.config.settings import InspectraSettings, LLMProvider


def test_default_settings():
    settings = InspectraSettings()
    assert settings.provider == LLMProvider.OLLAMA
    assert settings.model == "qwen2.5-coder:14b"
    assert settings.temperature == 0.2
    assert settings.max_tokens == 12000
    assert settings.dry_run is False


def test_load_settings_with_overrides():
    settings = load_settings(provider="openai", model="gpt-4o")
    assert settings.provider == LLMProvider.OPENAI
    assert settings.model == "gpt-4o"


def test_load_settings_from_yaml(tmp_path: Path):
    config_file = tmp_path / ".inspectra.yml"
    config_file.write_text(
        "provider: anthropic\nmodel: claude-opus-4\ntemperature: 0.1\n"
    )
    settings = load_settings(config_path=config_file)
    assert settings.provider == LLMProvider.ANTHROPIC
    assert settings.model == "claude-opus-4"
    assert settings.temperature == 0.1


def test_load_settings_override_wins_over_file(tmp_path: Path):
    config_file = tmp_path / ".inspectra.yml"
    config_file.write_text("provider: anthropic\nmodel: claude-opus-4\n")
    settings = load_settings(config_path=config_file, provider="openai")
    assert settings.provider == LLMProvider.OPENAI


def test_load_settings_empty_yaml(tmp_path: Path):
    config_file = tmp_path / ".inspectra.yml"
    config_file.write_text("")
    # Should not raise, should use defaults
    settings = load_settings(config_path=config_file)
    assert settings.provider == LLMProvider.OLLAMA


def test_temperature_validation():
    with pytest.raises(Exception):
        InspectraSettings(temperature=3.0)


def test_model_for_provider_defaults():
    settings = InspectraSettings(provider=LLMProvider.OPENAI, model="")
    assert settings.model_for_provider() == "gpt-4o-mini"


def test_model_for_provider_explicit():
    settings = InspectraSettings(provider=LLMProvider.OPENAI, model="gpt-4o")
    assert settings.model_for_provider() == "gpt-4o"


def test_find_config_file_returns_none_when_missing(tmp_path: Path):
    result = _find_config_file(start=tmp_path)
    assert result is None


def test_find_config_file_finds_file(tmp_path: Path):
    config_file = tmp_path / ".inspectra.yml"
    config_file.write_text("provider: ollama\n")
    result = _find_config_file(start=tmp_path)
    assert result == config_file

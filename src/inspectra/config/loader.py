# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Load and merge .inspectra.yml config with environment + CLI overrides."""

from pathlib import Path
from typing import Any

import yaml

from inspectra.config.settings import InspectraSettings, OllamaConfig, ReviewCategories

_CONFIG_FILENAME = ".inspectra.yml"


def _find_config_file(start: Path | None = None) -> Path | None:
    """Walk up directory tree looking for .inspectra.yml."""
    current = start or Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / _CONFIG_FILENAME
        if candidate.exists():
            return candidate
    return None


def load_settings(config_path: Path | None = None, **overrides: Any) -> InspectraSettings:
    """Merge defaults ← YAML ← env ← CLI overrides."""
    file_data: dict[str, Any] = {}

    resolved = config_path or _find_config_file()
    if resolved and resolved.exists():
        with resolved.open() as f:
            raw = yaml.safe_load(f) or {}
        file_data = _normalize_yaml(raw)

    merged = {**file_data, **{k: v for k, v in overrides.items() if v is not None}}
    return InspectraSettings(**merged)


def _normalize_yaml(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested YAML keys into a form InspectraSettings understands."""
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key == "ollama" and isinstance(value, dict):
            out["ollama"] = OllamaConfig(**value)
        elif key == "review" and isinstance(value, dict):
            out["review"] = ReviewCategories(**value)
        else:
            out[key] = value
    return out

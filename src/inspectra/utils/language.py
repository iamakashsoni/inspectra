# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Language detection from file path — used by future analyzer routing
and language-specific prompt sections.

Phase 1 ships just the detection table; the per-language prompt logic
comes in Phase 2.
"""

from __future__ import annotations

from pathlib import Path

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp", ".cxx": "cpp",
    ".swift": "swift",
    ".scala": "scala", ".sc": "scala",
    ".clj": "clojure",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".sql": "sql",
    ".yml": "yaml", ".yaml": "yaml",
    ".json": "json",
    ".tf": "terraform", ".tfvars": "terraform",
    ".dockerfile": "dockerfile",
}

# Files whose name (not extension) indicates a language
BASENAME_TO_LANGUAGE: dict[str, str] = {
    "Dockerfile": "dockerfile",
    "Makefile": "makefile",
    "go.mod": "go",
}


def detect_language(file_path: str) -> str | None:
    """Return the language string for a file path, or None if unknown."""
    p = Path(file_path)
    name = p.name
    if name in BASENAME_TO_LANGUAGE:
        return BASENAME_TO_LANGUAGE[name]
    return EXTENSION_TO_LANGUAGE.get(p.suffix.lower())

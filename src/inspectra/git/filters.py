# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Filter files that should be skipped during code review (unchanged from v1)."""

from __future__ import annotations

import fnmatch
from pathlib import Path

_ALWAYS_IGNORE: list[str] = [
    "*.lock", "package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock",
    "Gemfile.lock", "composer.lock",
    "*.min.js", "*.min.css", "*.map",
    "dist/*", "build/*", "out/*", ".next/*", "__pycache__/*", "*.pyc", "*.pyo",
    "vendor/*", "node_modules/*",
    "*.pb.go", "*.pb.py", "*_pb2.py", "*_pb2_grpc.py",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg",
    "*.woff", "*.woff2", "*.ttf", "*.eot", "*.pdf",
    "*.zip", "*.tar.gz", "*.jar", "*.war", "*.class", "*.exe", "*.dll", "*.so",
]

_MAX_DIFF_LINES = 2000


def should_skip(file_path: str, extra_patterns: list[str] | None = None) -> bool:
    patterns = _ALWAYS_IGNORE + (extra_patterns or [])
    name = Path(file_path).name
    for pattern in patterns:
        if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(name, pattern):
            return True
    return False


def filter_files(
    file_diffs: dict[str, str],
    extra_patterns: list[str] | None = None,
) -> dict[str, str]:
    return {
        path: diff
        for path, diff in file_diffs.items()
        if not should_skip(path, extra_patterns) and not _too_large(diff)
    }


def _too_large(diff_text: str) -> bool:
    return diff_text.count("\n") > _MAX_DIFF_LINES

"""Filter files that should be skipped during code review."""

from __future__ import annotations

import fnmatch
from pathlib import Path

# Hard-coded patterns that are always ignored regardless of user config
_ALWAYS_IGNORE: list[str] = [
    # Lock files
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    "Gemfile.lock",
    "composer.lock",
    # Minified / compiled
    "*.min.js",
    "*.min.css",
    "*.map",
    # Build artefacts
    "dist/*",
    "build/*",
    "out/*",
    ".next/*",
    "__pycache__/*",
    "*.pyc",
    "*.pyo",
    # Vendor
    "vendor/*",
    "node_modules/*",
    # Generated proto / gRPC
    "*.pb.go",
    "*.pb.py",
    "*_pb2.py",
    "*_pb2_grpc.py",
    # Binary / media
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.svg",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
    "*.pdf",
    "*.zip",
    "*.tar.gz",
    "*.jar",
    "*.war",
    "*.class",
    "*.exe",
    "*.dll",
    "*.so",
]

# Max diff size (lines) before a file is skipped entirely
_MAX_DIFF_LINES = 2000


def should_skip(file_path: str, extra_patterns: list[str] | None = None) -> bool:
    """Return True if the file should be excluded from review."""
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
    """
    Remove files that should be skipped.
    Returns filtered dict of {file_path: diff_text}.
    """
    return {
        path: diff
        for path, diff in file_diffs.items()
        if not should_skip(path, extra_patterns) and not _too_large(diff)
    }


def _too_large(diff_text: str) -> bool:
    return diff_text.count("\n") > _MAX_DIFF_LINES

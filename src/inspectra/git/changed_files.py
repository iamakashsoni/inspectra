# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""High-level interface to get reviewable changed files from a diff."""

from __future__ import annotations

from pathlib import Path

from inspectra.git.diff_parser import get_local_diff, parse_diff
from inspectra.git.filters import filter_files
from inspectra.utils.logger import logger


def get_reviewable_files(
    raw_diff: str | None = None,
    repo_path: Path | None = None,
    staged_only: bool = False,
    exclude_patterns: list[str] | None = None,
) -> dict[str, str]:
    """Return a filtered dict of {file_path: diff_text} ready for review."""
    if raw_diff is None:
        raw_diff = get_local_diff(repo_path=repo_path, staged_only=staged_only)
    if not raw_diff.strip():
        logger.info("No diff found — nothing to review.")
        return {}
    parsed = parse_diff(raw_diff)
    logger.debug("Parsed %d changed files", len(parsed))
    filtered = filter_files(parsed, extra_patterns=exclude_patterns)
    skipped = len(parsed) - len(filtered)
    if skipped:
        logger.debug("Skipped %d file(s) (generated / binary / excluded)", skipped)
    return filtered

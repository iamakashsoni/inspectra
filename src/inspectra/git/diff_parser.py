# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Parse git diffs and extract per-file changed hunks (unchanged from v1)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from inspectra.utils.logger import logger


def get_local_diff(repo_path: Path | None = None, staged_only: bool = False) -> str:
    """Run `git diff` and return the raw diff string."""
    cwd = repo_path or Path.cwd()
    cmd = ["git", "diff"]
    if staged_only:
        cmd.append("--cached")
    cmd += ["HEAD"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        logger.warning("git diff returned non-zero: %s", result.stderr)
    return result.stdout


def parse_diff(raw_diff: str) -> dict[str, str]:
    """Parse a raw unified diff into a dict of {file_path: diff_text}."""
    if not raw_diff.strip():
        return {}
    try:
        from unidiff import PatchSet
        patch = PatchSet(raw_diff)
    except Exception as exc:
        logger.error("Failed to parse diff: %s", exc)
        return {}

    result: dict[str, str] = {}
    for patched_file in patch:
        if patched_file.is_removed_file:
            continue
        path = patched_file.path
        hunks: list[str] = []
        for hunk in patched_file:
            hunk_lines: list[str] = [str(hunk.section_header) + "\n"]
            for line in hunk:
                hunk_lines.append(str(line))
            hunks.append("".join(hunk_lines))
        if hunks:
            header = f"--- {patched_file.source_file}\n+++ {patched_file.target_file}\n"
            result[path] = header + "\n".join(hunks)
    return result

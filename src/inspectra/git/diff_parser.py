"""Parse git diffs and extract per-file changed hunks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from unidiff import PatchSet

from inspectra.utils.logger import logger


def get_local_diff(repo_path: Path | None = None, staged_only: bool = False) -> str:
    """
    Run `git diff` and return the raw diff string.

    Args:
        repo_path: Path to the git repository root (defaults to cwd).
        staged_only: If True, use `git diff --cached` (staged changes only).
    """
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
    """
    Parse a raw unified diff into a dict of {file_path: diff_text}.

    Only includes added/modified files. Deleted files are excluded
    because there's nothing to review in removed code.
    """
    if not raw_diff.strip():
        return {}

    try:
        patch = PatchSet(raw_diff)
    except Exception as exc:
        logger.error("Failed to parse diff: %s", exc)
        return {}

    result: dict[str, str] = {}

    for patched_file in patch:
        # Skip pure deletions
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


def extract_changed_lines(raw_diff: str) -> dict[str, list[int]]:
    """
    Return a mapping of {file_path: [line_numbers]} for all added lines.
    Useful for posting inline PR comments at the right position.
    """
    if not raw_diff.strip():
        return {}

    try:
        patch = PatchSet(raw_diff)
    except Exception:
        return {}

    result: dict[str, list[int]] = {}

    for patched_file in patch:
        if patched_file.is_removed_file:
            continue
        added_lines: list[int] = []
        for hunk in patched_file:
            for line in hunk:
                if line.is_added and line.target_line_no is not None:
                    added_lines.append(line.target_line_no)
        if added_lines:
            result[patched_file.path] = added_lines

    return result

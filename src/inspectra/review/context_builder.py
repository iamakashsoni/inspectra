# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Build rich context for a review prompt.

Phase 2 introduces the single biggest quality win: giving the LLM the FULL
file content around the changed lines, not just the diff. A diff alone tells
you what changed but not what the surrounding code does — the LLM has to guess.

This module:
- Reads the working-tree version of a changed file
- Identifies which line ranges were changed (from the diff, via unidiff)
- Extracts a window of context around each changed range (default ±20 lines)
- Truncates to a token budget, preserving the most relevant context
- Falls back gracefully when the file can't be read (deleted, binary, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from unidiff import PatchSet

from inspectra.utils.tokenizer import count_tokens, fits_in_budget


@dataclass
class FileContext:
    """Context extracted from a file's full content for a review prompt."""
    file_path: str
    content: str          # The truncated context (may be partial)
    is_complete: bool     # True if the full file fit in the budget
    line_ranges: list[tuple[int, int]]  # The changed line ranges (1-indexed, inclusive)


def build_file_context(
    file_path: str,
    raw_diff: str,
    max_tokens: int = 2000,
    context_lines: int = 20,
) -> FileContext | None:
    """Build context for a single file from its diff.

    Args:
        file_path: Path to the file (relative to repo root).
        raw_diff: The unified diff for this file (used to find changed line ranges).
        max_tokens: Token budget for the context block.
        context_lines: Number of lines of context to include around each change.

    Returns:
        FileContext if the file could be read, None otherwise.
    """
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return None

    try:
        full_content = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    # Find changed line ranges from the diff (in terms of the NEW file's line numbers)
    changed_ranges = _extract_changed_ranges(raw_diff, file_path)
    if not changed_ranges:
        # No changed lines found in diff — give the whole file if it fits
        if fits_in_budget(full_content, max_tokens):
            return FileContext(
                file_path=file_path,
                content=full_content,
                is_complete=True,
                line_ranges=[],
            )
        truncated = _truncate_to_tokens(full_content, max_tokens)
        return FileContext(
            file_path=file_path,
            content=truncated,
            is_complete=False,
            line_ranges=[],
        )

    # Build context windows around each changed range
    lines = full_content.splitlines(keepends=True)
    total_lines = len(lines)

    # Merge overlapping/adjacent windows to avoid duplication
    windows: list[tuple[int, int]] = []
    for start, end in changed_ranges:
        win_start = max(1, start - context_lines)
        win_end = min(total_lines, end + context_lines)
        if windows and win_start <= windows[-1][1] + 1:
            windows[-1] = (windows[-1][0], max(windows[-1][1], win_end))
        else:
            windows.append((win_start, win_end))

    # Extract the windowed content, with clear truncation markers between windows
    parts: list[str] = []
    last_end = 0
    for win_start, win_end in windows:
        if win_start > last_end + 1 and last_end > 0:
            parts.append(f"\n... [{last_end + 1}-{win_start - 1} lines omitted] ...\n")
        segment = "".join(lines[win_start - 1:win_end])
        parts.append(segment)
        last_end = win_end

    content = "".join(parts)

    if not fits_in_budget(content, max_tokens):
        content = _truncate_to_tokens(content, max_tokens)

    is_complete = (
        len(windows) == 1
        and windows[0] == (1, total_lines)
        and fits_in_budget(full_content, max_tokens)
    )

    return FileContext(
        file_path=file_path,
        content=content,
        is_complete=is_complete,
        line_ranges=changed_ranges,
    )


def _extract_changed_ranges(raw_diff: str, file_path: str) -> list[tuple[int, int]]:
    """Extract (start_line, end_line) ranges of CHANGED lines from a unified diff,
    in terms of the NEW file's line numbers.

    Uses unidiff (already a dependency) for robust parsing.
    Matches the file by comparing basenames when full paths don't match
    (diffs often use relative paths like a/src/foo.py while file_path may be absolute).
    Returns a list of (start, end) tuples, 1-indexed, inclusive.
    """
    if not raw_diff.strip():
        return []

    try:
        patch = PatchSet(raw_diff)
    except Exception:
        return []

    from pathlib import Path as _Path
    target_basename = _Path(file_path).name

    ranges: list[tuple[int, int]] = []
    for patched_file in patch:
        # Match by full path, stripped path, or basename
        diff_path = patched_file.path
        diff_target = patched_file.target_file
        diff_basename = _Path(diff_target.lstrip("b/")).name

        if (file_path != diff_path
                and file_path != diff_target
                and file_path != diff_target.lstrip("b/")
                and target_basename != diff_basename):
            continue

        for hunk in patched_file:
            # Find the range of ADDED lines in this hunk (target line numbers)
            added_lines = [
                line.target_line_no
                for line in hunk
                if line.is_added and line.target_line_no is not None
            ]
            if not added_lines:
                continue
            ranges.append((min(added_lines), max(added_lines)))

    return _merge_ranges(ranges, gap_threshold=3)


def _merge_ranges(
    ranges: list[tuple[int, int]], gap_threshold: int = 3
) -> list[tuple[int, int]]:
    """Merge ranges that are within `gap_threshold` lines of each other."""
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if start - last_end <= gap_threshold:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget, preserving line boundaries."""
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    for line in lines:
        candidate = "".join(result + [line])
        if not fits_in_budget(candidate, max_tokens):
            break
        result.append(line)
    return "".join(result) + f"\n... [truncated — full file exceeded {max_tokens} token budget]"


def extract_changed_signatures(
    file_path: str,
    raw_diff: str,
    max_signatures: int = 10,
) -> list[str]:
    """Extract signature lines (def/class/func/fn declarations) from the diff.

    Used to build the 'related changes' block — gives the LLM awareness of
    what symbols changed in other files without sending the full content.

    Returns a list of signature strings like:
        ["auth/service.py:42  def get_user(conn, user_id):", ...]
    """
    try:
        patch = PatchSet(raw_diff)
    except Exception:
        return []

    signatures: list[str] = []
    sig_keywords = ("def ", "class ", "func ", "fn ", "public ", "private ",
                    "protected ", "async def ", "export function", "export const")

    for patched_file in patch:
        for hunk in patched_file:
            for line in hunk:
                if not line.is_added:
                    continue
                content = line.value.strip() if hasattr(line, "value") else str(line).strip()
                if content.startswith("+"):
                    content = content[1:].strip()
                if any(content.startswith(kw) for kw in sig_keywords):
                    signatures.append(f"{file_path}:{line.target_line_no}  {content}")
                    if len(signatures) >= max_signatures:
                        return signatures
    return signatures

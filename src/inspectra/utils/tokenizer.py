# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Token counting utilities — Phase 1: memoized via lru_cache."""

from __future__ import annotations

from functools import lru_cache

try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")

    @lru_cache(maxsize=4096)
    def count_tokens(text: str) -> int:
        """Token count, memoized per-process. Safe to call repeatedly on same text."""
        return len(_ENCODER.encode(text))

except Exception:
    @lru_cache(maxsize=4096)
    def count_tokens(text: str) -> int:  # type: ignore[misc]
        return max(1, len(text) // 4)


def fits_in_budget(text: str, budget: int) -> bool:
    return count_tokens(text) <= budget


def truncate_to_budget(text: str, budget: int) -> str:
    """Truncate text so it fits within the token budget."""
    if fits_in_budget(text, budget):
        return text
    lines = text.splitlines(keepends=True)
    lo, hi = 0, len(lines)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = "".join(lines[:mid])
        if fits_in_budget(candidate, budget):
            lo = mid
        else:
            hi = mid - 1
    return "".join(lines[:lo]) + f"\n\n... [truncated — exceeded {budget} token budget]"

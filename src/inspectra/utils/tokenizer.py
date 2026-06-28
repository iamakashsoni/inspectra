# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Token counting utilities."""

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

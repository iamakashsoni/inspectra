"""Token counting utilities for prompt size management."""

from __future__ import annotations

try:
    import tiktoken

    _ENCODER = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_ENCODER.encode(text))

except Exception:
    # Fallback: rough character-based estimate (1 token ≈ 4 chars)
    def count_tokens(text: str) -> int:  # type: ignore[misc]
        return max(1, len(text) // 4)


def fits_in_budget(text: str, budget: int) -> bool:
    return count_tokens(text) <= budget


def truncate_to_budget(text: str, budget: int) -> str:
    """Truncate text so it fits within the token budget."""
    if fits_in_budget(text, budget):
        return text

    # Binary search for the right split point
    lines = text.splitlines(keepends=True)
    lo, hi = 0, len(lines)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = "".join(lines[:mid])
        if fits_in_budget(candidate, budget):
            lo = mid
        else:
            hi = mid - 1

    truncated = "".join(lines[:lo])
    return truncated + f"\n\n... [truncated — exceeded {budget} token budget]"

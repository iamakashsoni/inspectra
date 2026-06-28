"""Disk-backed cache for LLM review responses.

Phase 1: cache key signature unchanged on the surface — the prompt builder
stamps PROMPT_VERSION into the prompt text, so a prompt bump invalidates
all entries automatically without changing this module.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from inspectra.utils.logger import logger

_DEFAULT_CACHE_DIR = Path(".inspectra_cache")
_CACHE_VERSION = 2                          # Bumped for v2 (new key semantics)
_DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 7     # 7 days


class ReviewCache:
    """Disk-backed key/value store for LLM review responses."""

    def __init__(
        self,
        cache_dir: Path | str = _DEFAULT_CACHE_DIR,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    def _ensure_dir(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        gitignore = self.cache_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n")

    def _key_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    @staticmethod
    def make_key(kind: str, payload: str) -> str:
        """Derive a stable cache key from a kind tag + payload string."""
        data = f"{kind}::{payload}"
        return hashlib.sha256(data.encode()).hexdigest()

    def get(self, key: str) -> str | None:
        path = self._key_path(key)
        if not path.exists():
            self._misses += 1
            return None
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            self._misses += 1
            return None
        if data.get("version") != _CACHE_VERSION:
            self._misses += 1
            return None
        age = time.time() - data.get("timestamp", 0)
        if age > self.ttl_seconds:
            path.unlink(missing_ok=True)
            self._misses += 1
            logger.debug("Cache expired for key %s", key[:8])
            return None
        self._hits += 1
        return data.get("response")

    def set(self, key: str, response: str) -> None:
        """Store a response in the cache.

        H2 fix: writes to a temp file first, then atomically renames. A crash
        mid-write no longer leaves a corrupted cache entry that would cause
        a permanent cache miss for that key.
        """
        self._ensure_dir()
        path = self._key_path(key)
        data = {
            "version": _CACHE_VERSION,
            "timestamp": time.time(),
            "response": response,
        }
        # H2 fix: atomic write via temp file + rename
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(data), encoding="utf-8")
        # os.rename is atomic on POSIX (same filesystem). On Windows, need to
        # handle existing target — os.replace does that cross-platform.
        import os
        os.replace(tmp_path, path)

    def clear(self) -> int:
        if not self.cache_dir.exists():
            return 0
        removed = 0
        for entry in self.cache_dir.glob("*.json"):
            entry.unlink(missing_ok=True)
            removed += 1
        logger.info("Cleared %d cache entries from %s", removed, self.cache_dir)
        return removed

    @property
    def stats(self) -> dict[str, int]:
        return {"hits": self._hits, "misses": self._misses}

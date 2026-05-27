"""
Simple file-based cache for LLM review responses.

When the same diff hunk is seen again (same sha256 hash), the cached
response is returned without calling the LLM. Useful for incremental
reviews where most files haven't changed.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from inspectra.utils.logger import logger

_DEFAULT_CACHE_DIR = Path(".inspectra_cache")
_CACHE_VERSION = 1
_DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


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
    def make_key(file_path: str, diff_text: str) -> str:
        """Derive a stable cache key from the file path and diff content."""
        payload = f"{file_path}::{diff_text}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, key: str) -> str | None:
        """Return cached response or None if missing / expired."""
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
        logger.debug("Cache hit for key %s", key[:8])
        return data.get("response")

    def set(self, key: str, response: str) -> None:
        """Store a response in the cache."""
        self._ensure_dir()
        path = self._key_path(key)
        data = {
            "version": _CACHE_VERSION,
            "timestamp": time.time(),
            "response": response,
        }
        path.write_text(json.dumps(data))

    def clear(self) -> int:
        """Delete all cache entries. Returns number of files removed."""
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

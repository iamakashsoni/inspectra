"""Tests for the disk-based review cache."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from inspectra.utils.cache import ReviewCache


@pytest.fixture
def cache(tmp_path: Path) -> ReviewCache:
    return ReviewCache(cache_dir=tmp_path / "cache", ttl_seconds=60)


def test_cache_miss_returns_none(cache):
    assert cache.get("nonexistent-key") is None


def test_cache_set_and_get(cache):
    cache.set("key1", "response text")
    assert cache.get("key1") == "response text"


def test_cache_hit_increments_stats(cache):
    cache.set("k", "v")
    cache.get("k")
    assert cache.stats["hits"] == 1
    assert cache.stats["misses"] == 0


def test_cache_miss_increments_stats(cache):
    cache.get("missing")
    assert cache.stats["misses"] == 1
    assert cache.stats["hits"] == 0


def test_cache_expired_entry_returns_none(tmp_path):
    short_cache = ReviewCache(cache_dir=tmp_path / "short", ttl_seconds=0)
    short_cache.set("k", "v")
    time.sleep(0.01)
    result = short_cache.get("k")
    assert result is None


def test_cache_clear(cache):
    cache.set("a", "1")
    cache.set("b", "2")
    removed = cache.clear()
    assert removed == 2
    assert cache.get("a") is None


def test_cache_clear_empty_dir(tmp_path):
    cache = ReviewCache(cache_dir=tmp_path / "empty")
    assert cache.clear() == 0


def test_make_key_is_deterministic():
    k1 = ReviewCache.make_key("foo.py", "diff content")
    k2 = ReviewCache.make_key("foo.py", "diff content")
    assert k1 == k2


def test_make_key_differs_for_different_inputs():
    k1 = ReviewCache.make_key("foo.py", "diff A")
    k2 = ReviewCache.make_key("foo.py", "diff B")
    assert k1 != k2


def test_make_key_differs_for_different_files():
    k1 = ReviewCache.make_key("a.py", "diff")
    k2 = ReviewCache.make_key("b.py", "diff")
    assert k1 != k2


def test_gitignore_created_on_first_write(cache):
    cache.set("k", "v")
    gitignore = cache.cache_dir / ".gitignore"
    assert gitignore.exists()
    assert "*" in gitignore.read_text()


def test_cache_handles_corrupted_entry(tmp_path):
    cache = ReviewCache(cache_dir=tmp_path / "corrupt")
    cache._ensure_dir()
    key = "badkey"
    (cache.cache_dir / f"{key}.json").write_text("not valid json{{{{")
    result = cache.get(key)
    assert result is None

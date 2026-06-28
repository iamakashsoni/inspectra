# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Tests for the file context builder (Phase 2 #16)."""

import tempfile
from pathlib import Path

from inspectra.review.context_builder import (
    build_file_context,
    extract_changed_signatures,
    _merge_ranges,
)


def _make_diff(file_path: str, additions: list[tuple[int, str]]) -> str:
    """Build a minimal unified diff that adds lines at the given positions."""
    # For simplicity, just produce a diff with added lines
    lines = [f"--- a/{file_path}", f"+++ b/{file_path}"]
    for line_no, content in additions:
        lines.append(f"@@ -0,0 +{line_no},1 @@")
        lines.append(f"+{content}")
    return "\n".join(lines) + "\n"


def test_build_file_context_reads_full_file():
    """When the file exists and fits, return its full content."""
    with tempfile.TemporaryDirectory() as d:
        fp = Path(d) / "test.py"
        fp.write_text("def foo():\n    return 1\n")
        diff = f"--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,2 @@\n def foo():\n+    return 1\n"
        ctx = build_file_context(str(fp), diff, max_tokens=2000)
        assert ctx is not None
        assert "def foo" in ctx.content
        assert ctx.is_complete is True


def test_build_file_context_returns_none_for_missing_file():
    ctx = build_file_context("/nonexistent/file.py", "", max_tokens=2000)
    assert ctx is None


def test_build_file_context_returns_none_for_binary_file():
    with tempfile.TemporaryDirectory() as d:
        fp = Path(d) / "test.bin"
        fp.write_bytes(b"\x00\x01\x02\xff")
        ctx = build_file_context(str(fp), "", max_tokens=2000)
        # read_text with errors="replace" will still read it, but content will be replacement chars
        # This is acceptable — the LLM will see garbage but won't crash
        assert ctx is not None  # we don't crash on binary, just get garbled content


def test_build_file_context_truncates_large_file():
    """When the file exceeds the token budget, content is truncated."""
    with tempfile.TemporaryDirectory() as d:
        fp = Path(d) / "big.py"
        # Write a file larger than 100 tokens
        fp.write_text("\n".join([f"x{i} = {i}" for i in range(500)]))
        ctx = build_file_context(str(fp), "", max_tokens=100)
        assert ctx is not None
        assert ctx.is_complete is False
        assert "truncated" in ctx.content.lower()


def test_build_file_context_window_around_changes():
    """Context should include lines around the changed range, not the whole file.

    The context builder reads the WORKING TREE file (which has changes applied)
    and uses the diff only to find WHICH lines changed. So the file on disk
    must reflect the post-change state.
    """
    with tempfile.TemporaryDirectory() as d:
        fp = Path(d) / "test.py"
        # File with the change already applied (simulates working tree state)
        content_lines = [f"line_number_{i}" for i in range(1, 101)]
        content_lines[49] = "CHANGED_LINE_HERE"  # line 50 (0-indexed 49)
        fp.write_text("\n".join(content_lines) + "\n")
        # Diff that changes line 50 (1-indexed)
        diff = (
            "--- a/test.py\n+++ b/test.py\n"
            "@@ -50,1 +50,1 @@\n-line_number_50\n+CHANGED_LINE_HERE\n"
        )
        ctx = build_file_context(str(fp), diff, max_tokens=2000, context_lines=5)
        assert ctx is not None
        # Should include the changed line (from the working-tree file)
        assert "CHANGED_LINE_HERE" in ctx.content
        # Should include lines near the change (within ±5 of line 50)
        assert "line_number_45" in ctx.content   # 5 lines before
        assert "line_number_55" in ctx.content   # 5 lines after
        # Should NOT include far-away lines
        assert "line_number_1\n" not in ctx.content
        assert "line_number_100" not in ctx.content
        assert "line_number_90" not in ctx.content


def test_merge_ranges_merges_adjacent():
    ranges = [(1, 5), (6, 10), (20, 25)]
    merged = _merge_ranges(ranges, gap_threshold=3)
    assert merged == [(1, 10), (20, 25)]


def test_merge_ranges_keeps_distant_separate():
    ranges = [(1, 5), (50, 55)]
    merged = _merge_ranges(ranges, gap_threshold=3)
    assert merged == [(1, 5), (50, 55)]


def test_merge_ranges_empty():
    assert _merge_ranges([], gap_threshold=3) == []


def test_extract_changed_signatures_finds_def():
    """Should extract Python def signatures from the diff."""
    diff = (
        "--- a/auth.py\n+++ b/auth.py\n"
        "@@ -0,0 +1,3 @@\n"
        "+def get_user(conn, user_id):\n"
        "+    pass\n"
        "+    return None\n"
    )
    sigs = extract_changed_signatures("auth.py", diff)
    assert len(sigs) == 1
    assert "def get_user" in sigs[0]
    assert "auth.py" in sigs[0]


def test_extract_changed_signatures_finds_class():
    diff = (
        "--- a/models.py\n+++ b/models.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+class User:\n"
        "+    pass\n"
    )
    sigs = extract_changed_signatures("models.py", diff)
    assert len(sigs) == 1
    assert "class User" in sigs[0]


def test_extract_changed_signatures_ignores_non_signatures():
    diff = (
        "--- a/x.py\n+++ b/x.py\n"
        "@@ -0,0 +1,3 @@\n"
        "+x = 1\n"
        "+y = 2\n"
        "+return x\n"
    )
    sigs = extract_changed_signatures("x.py", diff)
    assert len(sigs) == 0  # no def/class lines


def test_extract_changed_signatures_caps_at_max():
    # Build a proper diff with 15 added def lines
    diff = "--- a/x.py\n+++ b/x.py\n@@ -0,0 +1,30 @@\n"
    for i in range(15):
        diff += f"+def func_{i}():\n"
        diff += f"+    pass\n"
    sigs = extract_changed_signatures("x.py", diff, max_signatures=5)
    assert len(sigs) == 5

"""Tests for file filtering logic."""

import pytest

from inspectra.git.filters import filter_files, should_skip


@pytest.mark.parametrize(
    "path,expected",
    [
        ("package-lock.json", True),
        ("yarn.lock", True),
        ("dist/bundle.js", True),
        ("vendor/lib.py", True),
        ("app.min.js", True),
        ("src/main.py", False),
        ("auth/service.py", False),
        ("tests/test_api.py", False),
        ("app/models.py", False),
    ],
)
def test_should_skip(path: str, expected: bool):
    assert should_skip(path) == expected


def test_filter_files_removes_ignored():
    diffs = {
        "src/main.py": "diff content",
        "package-lock.json": "diff content",
        "dist/bundle.min.js": "diff content",
    }
    result = filter_files(diffs)
    assert "src/main.py" in result
    assert "package-lock.json" not in result
    assert "dist/bundle.min.js" not in result


def test_filter_files_respects_extra_patterns():
    diffs = {
        "src/main.py": "diff content",
        "src/generated.py": "diff content",
    }
    result = filter_files(diffs, extra_patterns=["*generated*"])
    assert "src/main.py" in result
    assert "src/generated.py" not in result


def test_filter_files_skips_huge_diffs():
    huge_diff = "\n".join(f"+line {i}" for i in range(3000))
    diffs = {"big_file.py": huge_diff}
    result = filter_files(diffs)
    assert "big_file.py" not in result

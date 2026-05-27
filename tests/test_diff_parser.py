"""Tests for the git diff parser."""

import pytest

from inspectra.git.diff_parser import extract_changed_lines, parse_diff


# A self-consistent unified diff:
# hunk @@ -1,4 +1,6 @@ => 4 lines in old, 6 lines in new
# old: 4 context/removed lines  new: 4 context + 2 added = 6
SAMPLE_DIFF = """\
diff --git a/api/client.py b/api/client.py
--- a/api/client.py
+++ b/api/client.py
@@ -1,4 +1,6 @@
 class APIClient:
     def fetch(self, url: str):
+        try:
+            return requests.get(url, timeout=10)
         pass
     done = True
diff --git a/README.md b/README.md
deleted file mode 100644
--- a/README.md
+++ /dev/null
@@ -1,3 +0,0 @@
-# Old README
-## Intro
-Deprecated.
"""


def test_parse_diff_returns_dict():
    result = parse_diff(SAMPLE_DIFF)
    assert isinstance(result, dict)


def test_parse_diff_excludes_deleted_files():
    result = parse_diff(SAMPLE_DIFF)
    assert "README.md" not in result


def test_parse_diff_includes_modified_files():
    result = parse_diff(SAMPLE_DIFF)
    assert "api/client.py" in result


def test_parse_diff_empty_string():
    assert parse_diff("") == {}


def test_parse_diff_invalid_input():
    assert parse_diff("this is not a diff") == {}


def test_extract_changed_lines():
    lines = extract_changed_lines(SAMPLE_DIFF)
    assert "api/client.py" in lines
    assert isinstance(lines["api/client.py"], list)
    assert len(lines["api/client.py"]) > 0

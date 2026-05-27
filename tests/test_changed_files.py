"""Tests for the changed-files pipeline (diff → filter → reviewable dict)."""

from __future__ import annotations

from inspectra.git.changed_files import get_reviewable_files

VALID_DIFF = """\
diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,4 @@
 def main():
+    print("hello")
     pass
 done = True
diff --git a/package-lock.json b/package-lock.json
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,3 +1,3 @@
 {
-  "version": "1"
+  "version": "2"
 }
"""


def test_reviewable_files_filters_lock_files():
    result = get_reviewable_files(raw_diff=VALID_DIFF)
    assert "src/app.py" in result
    assert "package-lock.json" not in result


def test_reviewable_files_empty_diff():
    result = get_reviewable_files(raw_diff="")
    assert result == {}


def test_reviewable_files_respects_extra_exclude():
    result = get_reviewable_files(
        raw_diff=VALID_DIFF,
        exclude_patterns=["src/*"],
    )
    assert "src/app.py" not in result


def test_reviewable_files_diff_text_included():
    result = get_reviewable_files(raw_diff=VALID_DIFF)
    assert "src/app.py" in result
    diff_text = result["src/app.py"]
    assert "+" in diff_text  # contains added lines
    assert isinstance(diff_text, str)


def test_reviewable_files_only_added_content():
    """Deleted-only files should not appear."""
    deleted_diff = """\
diff --git a/old.py b/old.py
deleted file mode 100644
--- a/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-class Old:
-    pass
-done = True
"""
    result = get_reviewable_files(raw_diff=deleted_diff)
    assert "old.py" not in result

"""Tests for diff chunking logic."""


from inspectra.utils.chunking import chunk_diff_by_file

SMALL_DIFF = """\
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,4 @@
 def hello():
+    print("world")
     pass
"""


def test_small_diff_single_chunk():
    diffs = {"foo.py": SMALL_DIFF}
    chunks = chunk_diff_by_file(diffs, max_chunk_tokens=3000)
    assert len(chunks) == 1
    assert chunks[0].file_path == "foo.py"
    assert isinstance(chunks[0].token_count, int)


def test_multiple_files_produce_multiple_chunks():
    diffs = {
        "a.py": SMALL_DIFF,
        "b.py": SMALL_DIFF,
    }
    chunks = chunk_diff_by_file(diffs, max_chunk_tokens=3000)
    assert len(chunks) == 2
    paths = {c.file_path for c in chunks}
    assert paths == {"a.py", "b.py"}


def test_large_diff_split_by_hunks():
    # Build a diff with many hunks to exceed a tiny budget
    hunks = []
    for i in range(20):
        hunks.append(
            f"@@ -{i * 10 + 1},{10} +{i * 10 + 1},{11} @@\n"
            + "".join(f" line {j}\n" for j in range(9))
            + f"+new line {i}\n"
        )
    big_diff = "--- a/big.py\n+++ b/big.py\n" + "".join(hunks)
    diffs = {"big.py": big_diff}
    chunks = chunk_diff_by_file(diffs, max_chunk_tokens=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.file_path == "big.py"


def test_empty_diffs():
    chunks = chunk_diff_by_file({})
    assert chunks == []

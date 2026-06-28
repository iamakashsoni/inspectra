#!/usr/bin/env python3
"""Add copyright headers to all Python source files."""
import os
import sys
from pathlib import Path

HEADER = '''\
# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

'''

EXCLUDE_DIRS = {'.venv', '.pytest_cache', '__pycache__', '.git', '.mypy_cache', '.ruff_cache'}
EXCLUDE_FILES = {'__init__.py'}  # these stay minimal


def needs_header(path: Path, content: str) -> bool:
    """Return True if the file needs a copyright header added."""
    if path.name in EXCLUDE_FILES:
        return False
    # Already has a copyright header
    if 'Copyright (c)' in content[:200]:
        return False
    return True


def add_headers(root: str) -> int:
    """Add copyright headers to all .py files under root."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if not fname.endswith('.py'):
                continue
            fpath = Path(dirpath) / fname
            content = fpath.read_text(encoding='utf-8')
            if not needs_header(fpath, content):
                continue
            # Handle files with shebang or encoding declarations
            lines = content.split('\n')
            insert_at = 0
            # Skip shebang
            if lines and lines[0].startswith('#!'):
                insert_at = 1
            # Skip coding declaration
            if insert_at < len(lines) and ('coding' in lines[insert_at] or 'encoding' in lines[insert_at]):
                insert_at += 1
            # Skip module docstring start
            new_lines = lines[:insert_at]
            rest = '\n'.join(lines[insert_at:])
            new_content = '\n'.join(new_lines) + ('\n' if new_lines else '') + HEADER + rest
            fpath.write_text(new_content, encoding='utf-8')
            count += 1
            print(f'  + {fpath}')
    return count


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'src'
    print(f'Adding copyright headers to .py files under {root}/...')
    n = add_headers(root)
    print(f'Done. {n} files updated.')

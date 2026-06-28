# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""GitHub authentication utilities."""

from __future__ import annotations

from github import Github, GithubException


def get_github_client(token: str) -> Github:
    if not token:
        raise ValueError("GITHUB_TOKEN is not set. Cannot interact with GitHub API.")
    return Github(token)

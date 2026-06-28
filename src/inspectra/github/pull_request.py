# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Fetch pull request data from GitHub.

Phase 1 change: `get_pr_metadata` now returns `head_sha`, which is required by
the inline-comment posting API (GitHub needs to know which commit the comment
anchors to).
"""

from __future__ import annotations

import httpx
from github import Github
from github.PullRequest import PullRequest

from inspectra.utils.logger import logger


def get_pull_request(token: str, repo_name: str, pr_number: int) -> PullRequest:
    g = Github(token)
    repo = g.get_repo(repo_name)
    return repo.get_pull(pr_number)


def get_pr_diff(token: str, repo_name: str, pr_number: int) -> str:
    """Return the unified diff string for a GitHub PR (via REST API)."""
    api_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"
    logger.debug("Fetching PR diff from GitHub API: %s", api_url)

    response = httpx.get(
        api_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.diff",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        follow_redirects=True,
        timeout=30,
    )

    if response.status_code == 401:
        raise PermissionError("GitHub token is invalid or expired.")
    if response.status_code == 403:
        raise PermissionError("GitHub token does not have permission to read this repository.")
    if response.status_code == 404:
        raise ValueError(f"PR #{pr_number} not found in {repo_name}.")

    response.raise_for_status()
    return response.text


def get_pr_metadata(token: str, repo_name: str, pr_number: int) -> dict[str, str]:
    """Return basic PR metadata including the head SHA (needed for inline comments)."""
    pr = get_pull_request(token, repo_name, pr_number)
    return {
        "title": pr.title,
        "author": pr.user.login,
        "base": pr.base.ref,
        "head": pr.head.ref,
        "head_sha": pr.head.sha,           # NEW in v2
        "url": pr.html_url,
    }

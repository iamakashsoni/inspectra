"""Fetch pull request data from GitHub."""

from __future__ import annotations

import httpx
from github import Github
from github.PullRequest import PullRequest

from inspectra.utils.logger import logger


def get_pull_request(token: str, repo_name: str, pr_number: int) -> PullRequest:
    """Fetch a PullRequest object from GitHub."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    return repo.get_pull(pr_number)


def get_pr_diff(token: str, repo_name: str, pr_number: int) -> str:
    """
    Return the unified diff string for a GitHub Pull Request.

    Uses the GitHub REST API directly (not the web diff_url) so it works
    correctly for both private and public repositories.
    """
    # Use the API endpoint — works for private repos with a valid token
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
        raise PermissionError(
            "GitHub token is invalid or expired. "
            "Check that GITHUB_TOKEN is set correctly."
        )
    if response.status_code == 403:
        raise PermissionError(
            "GitHub token does not have permission to read this repository. "
            "Ensure the workflow has 'contents: read' permission."
        )
    if response.status_code == 404:
        raise ValueError(
            f"PR #{pr_number} not found in {repo_name}. "
            "Check that GITHUB_REPOSITORY is set to 'owner/repo' format "
            "and the PR number is correct."
        )

    response.raise_for_status()
    return response.text


def get_pr_metadata(token: str, repo_name: str, pr_number: int) -> dict[str, str]:
    """Return basic PR metadata (title, author, branch, etc.)."""
    pr = get_pull_request(token, repo_name, pr_number)
    return {
        "title": pr.title,
        "author": pr.user.login,
        "base": pr.base.ref,
        "head": pr.head.ref,
        "url": pr.html_url,
    }

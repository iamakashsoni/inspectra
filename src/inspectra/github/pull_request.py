"""Fetch pull request data from GitHub."""

from __future__ import annotations

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

    Uses PyGithub to fetch the PR diff via the GitHub API.
    """
    import httpx

    pr = get_pull_request(token, repo_name, pr_number)
    diff_url = pr.diff_url

    logger.debug("Fetching PR diff from %s", diff_url)

    response = httpx.get(
        diff_url,
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.diff"},
        follow_redirects=True,
        timeout=30,
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

"""GitHub authentication utilities (unchanged from v1)."""

from __future__ import annotations

from github import Github, GithubException


def get_github_client(token: str) -> Github:
    if not token:
        raise ValueError("GITHUB_TOKEN is not set. Cannot interact with GitHub API.")
    return Github(token)


def validate_token(token: str) -> bool:
    try:
        g = get_github_client(token)
        _ = g.get_user().login
        return True
    except GithubException:
        return False

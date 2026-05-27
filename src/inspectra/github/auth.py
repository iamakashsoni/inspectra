"""GitHub authentication utilities."""

from __future__ import annotations

from github import Github, GithubException


def get_github_client(token: str) -> Github:
    """Return an authenticated PyGithub client."""
    if not token:
        raise ValueError(
            "GITHUB_TOKEN is not set. Cannot interact with GitHub API."
        )
    return Github(token)


def validate_token(token: str) -> bool:
    """Return True if the token is valid and has the required permissions."""
    try:
        g = get_github_client(token)
        g.get_user().login
        return True
    except GithubException:
        return False

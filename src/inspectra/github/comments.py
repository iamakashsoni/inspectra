"""Post review comments to a GitHub Pull Request."""

from __future__ import annotations

from github import Github, GithubException

from inspectra.utils.logger import logger


def post_pr_comment(
    token: str,
    repo_name: str,
    pr_number: int,
    body: str,
) -> str:
    """
    Post a markdown comment to a GitHub PR.

    Returns the URL of the created comment.
    """
    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    comment = pr.create_issue_comment(body)
    logger.info("Posted review comment: %s", comment.html_url)
    return comment.html_url


def delete_previous_inspectra_comments(
    token: str,
    repo_name: str,
    pr_number: int,
    marker: str = "🔍 Inspectra Review",
) -> int:
    """
    Delete all previous Inspectra review comments on a PR.

    Returns the number of comments deleted.
    """
    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    deleted = 0
    for comment in pr.get_issue_comments():
        if marker in (comment.body or ""):
            try:
                comment.delete()
                deleted += 1
                logger.debug("Deleted old comment #%s", comment.id)
            except GithubException as exc:
                logger.warning("Could not delete comment #%s: %s", comment.id, exc)

    if deleted:
        logger.info("Removed %d old Inspectra comment(s)", deleted)
    return deleted

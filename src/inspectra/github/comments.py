"""Post review comments to a GitHub Pull Request.

Phase 1 change: `delete_previous_inspectra_comments` now ALSO deletes inline
review comments (not just issue-level comments), preventing duplicates on
re-runs after a force-push.
"""

from __future__ import annotations

from github import Github, GithubException

from inspectra.utils.logger import logger

# Marker stamped on every Inspectra-created comment so we can find them later
SUMMARY_MARKER = "<!-- inspectra:summary -->"
INLINE_MARKER = "<!-- inspectra:inline -->"


def post_pr_comment(token: str, repo_name: str, pr_number: int, body: str) -> str:
    """Post a markdown comment to a GitHub PR. Returns the comment URL."""
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
) -> int:
    """Delete all previous Inspectra comments on a PR — both issue-level and inline."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    deleted = 0

    # Issue-level (summary) comments
    for comment in pr.get_issue_comments():
        if SUMMARY_MARKER in (comment.body or ""):
            try:
                comment.delete()
                deleted += 1
                logger.debug("Deleted old summary comment #%s", comment.id)
            except GithubException as exc:
                logger.warning("Could not delete comment #%s: %s", comment.id, exc)

    # Inline review comments (the ones posted at specific lines)
    try:
        for rc in pr.get_review_comments():
            if INLINE_MARKER in (rc.body or ""):
                try:
                    rc.delete()
                    deleted += 1
                    logger.debug("Deleted old inline comment %s", rc.id)
                except GithubException as exc:
                    logger.warning("Could not delete inline comment %s: %s", rc.id, exc)
    except GithubException as exc:
        # Some PRs may not expose review comments depending on permissions
        logger.debug("Could not list review comments: %s", exc)

    if deleted:
        logger.info("Removed %d old Inspectra comment(s)", deleted)
    return deleted

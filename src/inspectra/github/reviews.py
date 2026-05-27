"""Submit formal GitHub Pull Request reviews (approve / request-changes / comment)."""

from __future__ import annotations

from enum import StrEnum

from github import Github

from inspectra.review.severity import ReviewResult, Severity
from inspectra.utils.logger import logger


class ReviewEvent(StrEnum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


def decide_review_event(results: list[ReviewResult]) -> ReviewEvent:
    """
    Choose the appropriate review event based on severity of findings.

    - Any CRITICAL issue   → REQUEST_CHANGES
    - Any HIGH issue       → REQUEST_CHANGES
    - MEDIUM / LOW only    → COMMENT
    - No issues            → APPROVE
    """
    critical = sum(r.critical_count for r in results)
    high = sum(r.high_count for r in results)
    total = sum(len(r.issues) for r in results)

    if critical > 0 or high > 0:
        return ReviewEvent.REQUEST_CHANGES
    if total > 0:
        return ReviewEvent.COMMENT
    return ReviewEvent.APPROVE


def submit_pr_review(
    token: str,
    repo_name: str,
    pr_number: int,
    body: str,
    results: list[ReviewResult],
    event: ReviewEvent | None = None,
) -> str:
    """
    Submit a formal GitHub PR review with a body comment and an event decision.

    Returns the HTML URL of the submitted review.
    """
    if event is None:
        event = decide_review_event(results)

    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    review = pr.create_review(body=body, event=event.value)
    logger.info(
        "Submitted %s review for PR #%d: %s",
        event.value,
        pr_number,
        review.html_url,
    )
    return review.html_url


def post_inline_comments(
    token: str,
    repo_name: str,
    pr_number: int,
    results: list[ReviewResult],
    commit_sha: str,
    min_severity: Severity = Severity.MEDIUM,
) -> int:
    """
    Post inline review comments on changed lines for issues that have a line number.

    Only issues at or above `min_severity` are posted inline.
    Returns the number of comments posted.

    Args:
        commit_sha: The HEAD commit SHA of the PR (required by GitHub API for inline comments).
    """
    _severity_rank = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 4,
    }
    min_rank = _severity_rank[min_severity]

    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    posted = 0
    for result in results:
        for issue in result.issues:
            if _severity_rank[issue.severity] > min_rank:
                continue
            if not issue.line_number:
                continue

            comment_body = (
                f"**{issue.severity.emoji} [{issue.severity.value.upper()}] {issue.title}**\n\n"
                f"{issue.explanation}"
                + (f"\n\n**Suggested fix:** {issue.suggested_fix}" if issue.suggested_fix else "")
            )

            try:
                pr.create_review_comment(
                    body=comment_body,
                    commit=repo.get_commit(commit_sha),
                    path=issue.file_path or result.file_path,
                    line=issue.line_number,
                )
                posted += 1
                logger.debug(
                    "Inline comment posted on %s:%d",
                    issue.file_path,
                    issue.line_number,
                )
            except Exception as exc:
                logger.warning(
                    "Could not post inline comment on %s:%d — %s",
                    issue.file_path,
                    issue.line_number,
                    exc,
                )

    logger.info("Posted %d inline review comment(s)", posted)
    return posted

# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Submit formal GitHub PR reviews and post inline review comments.

Inline comments are stamped with ``<!-- inspectra:inline -->`` so
``delete_previous_inspectra_comments()`` can find and remove them on re-runs.
The commit object is fetched once and reused across all inline comments
(no N+1 API calls).
"""

from __future__ import annotations

from enum import StrEnum

from github import Github

from inspectra.github.comments import INLINE_MARKER
from inspectra.review.severity import ReviewResult, Severity
from inspectra.utils.logger import logger


class ReviewEvent(StrEnum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


def decide_review_event(results: list[ReviewResult]) -> ReviewEvent:
    """Choose the appropriate review event based on severity of findings."""
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
    """Submit a formal GitHub PR review with a body comment and an event decision."""
    if event is None:
        event = decide_review_event(results)

    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    review = pr.create_review(body=body, event=event.value)
    logger.info("Submitted %s review for PR #%d: %s", event.value, pr_number, review.html_url)
    return review.html_url


def post_inline_comments(
    token: str,
    repo_name: str,
    pr_number: int,
    results: list[ReviewResult],
    commit_sha: str,
    min_severity: Severity = Severity.MEDIUM,
) -> int:
    """Post inline review comments on changed lines for issues that have a line number.

    Returns the number of comments successfully posted.
    """
    _severity_rank = {
        Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2,
        Severity.LOW: 3, Severity.INFO: 4,
    }
    min_rank = _severity_rank[min_severity]

    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Fetch the commit ONCE and reuse for all inline comments
    try:
        commit = repo.get_commit(commit_sha)
    except Exception as exc:
        logger.error(
            "Could not fetch commit %s for inline comments — skipping: %s",
            commit_sha[:8], exc,
        )
        return 0

    # Pre-filter qualifying issues
    candidates: list[tuple[ReviewResult, ReviewIssue]] = []
    for result in results:
        for issue in result.issues:
            if _severity_rank[issue.severity] > min_rank:
                continue
            if not issue.line_number:
                continue
            candidates.append((result, issue))

    if not candidates:
        logger.info("No issues qualify for inline comments")
        return 0

    logger.info("Posting %d inline comment(s)…", len(candidates))

    posted = 0
    for result, issue in candidates:
        body = (
            f"{INLINE_MARKER}\n"
            f"**{issue.severity.emoji} [{issue.severity.value.upper()}] {issue.title}**\n\n"
            f"{issue.explanation}"
            + (f"\n\n**Suggested fix:**\n\n```suggestion\n{issue.suggested_fix}\n```"
               if issue.suggested_fix and "\n" in issue.suggested_fix else
               (f"\n\n**Suggested fix:** {issue.suggested_fix}" if issue.suggested_fix else ""))
        )

        try:
            pr.create_review_comment(
                body=body,
                commit=commit,
                path=issue.file_path or result.file_path,
                line=issue.line_number,
            )
            posted += 1
            logger.debug("Inline comment posted on %s:%d", issue.file_path, issue.line_number)
        except Exception as exc:
            logger.warning(
                "Could not post inline comment on %s:%d — %s",
                issue.file_path, issue.line_number, exc,
            )

    logger.info("Posted %d/%d inline review comment(s)", posted, len(candidates))
    return posted

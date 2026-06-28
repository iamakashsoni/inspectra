"""Baseline suppression — false-positive management.

Phase 2 #30: lets users record "this finding is a false positive, don't
report it again" in a `.inspectra-baseline.json` file. Findings matching
the baseline are filtered out before output.

This is essential for production use — without it, every Inspectra run
re-reports the same false positives, and developers start ignoring all
findings (alert fatigue).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from inspectra.review.severity import ReviewIssue, ReviewResult
from inspectra.utils.logger import logger


@dataclass
class Suppression:
    """A single suppression rule in the baseline file."""
    rule_id: str                    # e.g. "SQL_INJECTION" or "BANDIT/B608"
    file_path: str | None = None    # If set, only suppress in this file
    line_number: int | None = None  # If set, only suppress at this line
    reason: str = ""                # Why this is suppressed (for humans)
    expires: str | None = None      # ISO date string; suppression ignored after this
    created_at: str = ""            # ISO date string


@dataclass
class Baseline:
    """A loaded baseline file."""
    version: int = 1
    suppressions: list[Suppression] = field(default_factory=list)

    def matches(self, issue: ReviewIssue, file_path: str) -> bool:
        """Return True if any suppression in the baseline matches this issue."""
        for supp in self.suppressions:
            # Check expiry
            if supp.expires:
                from datetime import date
                try:
                    expiry = date.fromisoformat(supp.expires)
                    if date.today() > expiry:
                        continue  # Suppression expired
                except ValueError:
                    pass  # Bad date format — ignore expiry, keep suppressing

            # Rule ID must match (case-insensitive)
            if supp.rule_id.upper() != (issue.rule_id or "").upper():
                continue

            # If suppression specifies a file, it must match
            if supp.file_path and supp.file_path != file_path:
                continue

            # If suppression specifies a line, it must match
            if supp.line_number and supp.line_number != issue.line_number:
                continue

            return True  # All matching criteria met
        return False


def load_baseline(path: Path | str | None) -> Baseline:
    """Load a baseline file. Returns an empty Baseline if path is None or missing."""
    if path is None:
        return Baseline()

    p = Path(path)
    if not p.exists():
        return Baseline()

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load baseline %s: %s", p, exc)
        return Baseline()

    suppressions: list[Suppression] = []
    for item in data.get("suppressions", []):
        try:
            suppressions.append(Suppression(
                rule_id=item.get("rule_id", ""),
                file_path=item.get("file_path"),
                line_number=item.get("line_number"),
                reason=item.get("reason", ""),
                expires=item.get("expires"),
                created_at=item.get("created_at", ""),
            ))
        except Exception as exc:
            logger.debug("Skipping malformed suppression: %s — %s", item, exc)

    return Baseline(version=data.get("version", 1), suppressions=suppressions)


def apply_baseline(
    results: list[ReviewResult],
    baseline: Baseline,
) -> tuple[list[ReviewResult], int]:
    """Filter out findings that match the baseline.

    Returns:
        (filtered_results, suppressed_count)
    """
    suppressed_count = 0

    for result in results:
        kept_issues: list[ReviewIssue] = []
        for issue in result.issues:
            if baseline.matches(issue, result.file_path):
                suppressed_count += 1
                logger.debug(
                    "Suppressed %s at %s:%s (matched baseline)",
                    issue.rule_id, result.file_path, issue.line_number,
                )
            else:
                kept_issues.append(issue)
        result.issues = kept_issues

    return results, suppressed_count


def save_baseline(baseline: Baseline, path: Path | str) -> None:
    """Save a baseline to a file."""
    p = Path(path)
    data = {
        "version": baseline.version,
        "suppressions": [
            {
                "rule_id": s.rule_id,
                "file_path": s.file_path,
                "line_number": s.line_number,
                "reason": s.reason,
                "expires": s.expires,
                "created_at": s.created_at,
            }
            for s in baseline.suppressions
        ],
    }
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_suppression(
    path: Path | str,
    rule_id: str,
    file_path: str | None = None,
    line_number: int | None = None,
    reason: str = "",
    expires: str | None = None,
) -> None:
    """Add a single suppression to a baseline file (creating it if needed)."""
    baseline = load_baseline(path)
    from datetime import date
    baseline.suppressions.append(Suppression(
        rule_id=rule_id,
        file_path=file_path,
        line_number=line_number,
        reason=reason,
        expires=expires,
        created_at=date.today().isoformat(),
    ))
    save_baseline(baseline, path)

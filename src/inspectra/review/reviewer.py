"""Core reviewer: sends a diff chunk to the LLM and parses the response."""

from __future__ import annotations

import json
import re

from inspectra.config.settings import ReviewCategories
from inspectra.llm.base import BaseLLMProvider
from inspectra.review.prompts import build_review_prompt
from inspectra.review.severity import ReviewIssue, ReviewResult, Severity
from inspectra.utils.logger import logger


class ChunkReviewer:
    """Reviews a single diff chunk using an LLM provider."""

    def __init__(
        self, provider: BaseLLMProvider, categories: ReviewCategories | None = None
    ) -> None:
        self.provider = provider
        self.categories = categories

    async def review(self, file_path: str, diff_text: str) -> ReviewResult:
        """Run a review and return structured results."""
        prompt = build_review_prompt(file_path, diff_text, self.categories)

        try:
            raw_response = await self.provider.review_code(prompt)
        except Exception as exc:
            logger.error("LLM call failed for %s: %s", file_path, exc)
            return ReviewResult(file_path=file_path, summary=f"Review failed: {exc}")

        return self._parse_response(file_path, raw_response)

    def _parse_response(self, file_path: str, raw: str) -> ReviewResult:
        """Parse JSON response from LLM into ReviewResult."""
        cleaned = _strip_fences(raw)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON from LLM response for %s", file_path)
            logger.debug("Raw response: %s", raw[:500])
            return ReviewResult(
                file_path=file_path,
                summary=raw[:500],
                issues=[],
            )

        issues: list[ReviewIssue] = []
        for item in data.get("issues", []):
            try:
                issue = ReviewIssue(
                    title=item.get("title", "Unknown Issue"),
                    severity=Severity.from_string(item.get("severity", "info")),
                    category=item.get("category", "General"),
                    explanation=item.get("explanation", ""),
                    suggested_fix=item.get("suggested_fix", ""),
                    file_path=item.get("file_path", file_path),
                    line_number=item.get("line_number"),
                )
                issues.append(issue)
            except Exception as exc:
                logger.debug("Skipping malformed issue: %s — %s", item, exc)

        return ReviewResult(
            file_path=file_path,
            summary=data.get("summary", ""),
            issues=issues,
        )


def _strip_fences(text: str) -> str:
    """Remove markdown code fences wrapping JSON."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

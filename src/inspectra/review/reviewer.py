"""Core reviewer: sends a diff chunk to the LLM and parses the response.

- Uses LLMRequest/LLMResponse interface with structured JSON output (schema-enforced)
- Retries on JSON parse failure (with corrective prompt) and transient network
  errors (timeouts, 429, 503) with exponential backoff
- Detects response truncation via finish_reason
- Phase 2: accepts file context, PR intent, related changes, analyzer findings,
  and language rules to enrich the prompt
"""

from __future__ import annotations

import asyncio
import json
import re

from inspectra.config.settings import ReviewCategories
from inspectra.llm.base import BaseLLMProvider, LLMRequest
from inspectra.review.prompts import (
    REVIEW_JSON_SCHEMA,
    build_corrective_prompt,
    build_review_prompt,
)
from inspectra.review.severity import ReviewIssue, ReviewResult, Severity
from inspectra.utils.logger import logger


class JSONParseError(Exception):
    """Raised when the LLM response cannot be parsed as JSON."""


class TransientLLMError(Exception):
    """Raised for transient LLM failures (timeouts, 429, 503) that warrant retry."""


_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class ChunkReviewer:
    """Reviews a single diff chunk using an LLM provider."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        categories: ReviewCategories | None = None,
        max_retries: int = 3,
        network_retries: int = 2,
    ) -> None:
        self.provider = provider
        self.categories = categories
        self.max_retries = max_retries
        self.network_retries = network_retries

    async def review(
        self,
        file_path: str,
        diff_text: str,
        *,
        full_file_context: str | None = None,
        pr_intent: str | None = None,
        related_changes: list[str] | None = None,
        analyzer_findings: list | None = None,
        language_rules: str | None = None,
    ) -> ReviewResult:
        """Run a review and return structured results, with retry on failure."""
        prompt = build_review_prompt(
            file_path, diff_text, self.categories,
            full_file_context=full_file_context,
            pr_intent=pr_intent,
            related_changes=related_changes,
            analyzer_findings=analyzer_findings,
            language_rules=language_rules,
        )

        last_error: Exception | None = None
        response = None

        for attempt in range(1, self.max_retries + 1):
            try:
                request = LLMRequest(
                    user_prompt=prompt,
                    system_prompt=self.provider.system_prompt,
                    json_schema=REVIEW_JSON_SCHEMA,
                    temperature=0.2,
                    max_tokens=4096,
                )
                response = await self._call_with_network_retry(request, file_path)

                if response.finish_reason == "length":
                    logger.warning(
                        "Response truncated for %s (attempt %d) — chunk may be too large",
                        file_path, attempt,
                    )

                return self._parse_response(file_path, response.text)

            except JSONParseError as exc:
                last_error = exc
                logger.warning(
                    "JSON parse failed for %s (attempt %d/%d): %s",
                    file_path, attempt, self.max_retries, exc,
                )
                if attempt < self.max_retries:
                    bad_text = response.text if response is not None else ""
                    prompt = build_corrective_prompt(prompt, str(exc), bad_text)
                    await asyncio.sleep(0.5 * attempt)
                continue

            except TransientLLMError as exc:
                last_error = exc
                logger.warning(
                    "Transient LLM error for %s (attempt %d/%d): %s",
                    file_path, attempt, self.max_retries, exc,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0 * attempt)
                continue

            except Exception as exc:
                logger.error("LLM call failed for %s: %s", file_path, exc)
                return ReviewResult(file_path=file_path, summary=f"Review failed: {exc}")

        return ReviewResult(
            file_path=file_path,
            summary=f"Failed to review after {self.max_retries} attempts: {last_error}",
        )

    async def _call_with_network_retry(
        self, request: LLMRequest, file_path: str
    ) -> "LLMResponse":
        """Call provider.complete() with retry on transient network errors.

        Network retries are separate from parse retries so a network blip
        doesn't waste a parse-retry slot.
        """
        import httpx

        last_exc: Exception | None = None
        for net_attempt in range(1, self.network_retries + 1):
            try:
                return await self.provider.complete(request)
            except httpx.TimeoutException as exc:
                last_exc = TransientLLMError(f"Timeout: {exc}")
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response else 0
                if status in _TRANSIENT_STATUS_CODES:
                    last_exc = TransientLLMError(f"HTTP {status}")
                else:
                    raise
            except RuntimeError as exc:
                msg = str(exc)
                if any(f"returned {code}" in msg for code in _TRANSIENT_STATUS_CODES):
                    last_exc = TransientLLMError(msg)
                else:
                    raise
            except (ConnectionError, OSError) as exc:
                last_exc = TransientLLMError(f"Connection error: {exc}")

            if net_attempt < self.network_retries:
                await asyncio.sleep(0.5 * net_attempt)

        raise last_exc or TransientLLMError("Unknown transient error")

    def _parse_response(self, file_path: str, raw: str) -> ReviewResult:
        """Parse JSON response from LLM into ReviewResult."""
        cleaned = _strip_fences(raw)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise JSONParseError(f"{exc}. First 200 chars: {cleaned[:200]!r}") from exc

        issues: list[ReviewIssue] = []
        for item in data.get("issues", []):
            try:
                issue = ReviewIssue(
                    title=item.get("title", "Unknown Issue"),
                    severity=Severity.from_string(item.get("severity", "info")),
                    category=item.get("category", "General"),
                    explanation=item.get("explanation", ""),
                    suggested_fix=item.get("suggested_fix", ""),
                    file_path=item.get("file_path") or file_path,
                    line_number=item.get("line_number"),
                    rule_id=item.get("rule_id", ""),
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
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

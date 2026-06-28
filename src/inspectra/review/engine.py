# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Review engine — orchestrates chunking, reviewing, and aggregating results.

Phase 1: configurable concurrency (was hardcoded at 3).
Phase 2: supports file context, PR intent, related changes, analyzer findings,
         language rules, cross-file second pass, and baseline suppression.

All Phase 2 features are opt-in via the ReviewContext dataclass — when it's
empty (the default), the engine behaves identically to Phase 1.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from inspectra.config.settings import InspectraSettings
from inspectra.llm.base import BaseLLMProvider
from inspectra.review.baseline import Baseline, apply_baseline
from inspectra.review.context_builder import build_file_context, extract_changed_signatures
from inspectra.review.cross_file import run_cross_file_review
from inspectra.review.prompts import build_pr_summary_prompt
from inspectra.review.reviewer import ChunkReviewer
from inspectra.review.severity import ReviewIssue, ReviewResult
from inspectra.utils.chunking import chunk_diff_by_file
from inspectra.utils.language_rules import get_language_rules
from inspectra.utils.logger import logger


@dataclass
class ReviewContext:
    """Optional context for a review run (Phase 2).

    When all fields are empty/None, the engine behaves identically to Phase 1.
    """
    pr_intent: str | None = None                  # PR title + body
    enable_file_context: bool = True              # Read full file content around changes
    enable_analyzers: bool = True                 # Run deterministic analyzers
    enable_cross_file: bool = True                # Run second-pass cross-file review
    enable_language_rules: bool = True            # Add language-specific prompt rules
    baseline: Baseline | None = None              # Suppression baseline
    analyzer_registry: object | None = None       # AnalyzerRegistry (injected for testing)
    file_context_tokens: int = 2000               # Token budget per file's context block


class ReviewEngine:
    """Coordinates the end-to-end review pipeline."""

    def __init__(self, provider: BaseLLMProvider, settings: InspectraSettings) -> None:
        self.provider = provider
        self.settings = settings
        self._reviewer = ChunkReviewer(provider=provider, categories=settings.review)

    async def run(
        self,
        file_diffs: dict[str, str],
        context: ReviewContext | None = None,
    ) -> list[ReviewResult]:
        """Review all provided file diffs and return aggregated results.

        Phase 2: if `context` is provided, enables file context, analyzers,
        cross-file review, and baseline suppression as configured.
        """
        if not file_diffs:
            logger.info("No files to review.")
            return []

        ctx = context or ReviewContext()

        # Pre-compute related-changes signatures for all files (for cross-file awareness)
        all_signatures: dict[str, list[str]] = {}
        if ctx.enable_cross_file or ctx.enable_file_context:
            for fp, diff in file_diffs.items():
                sigs = extract_changed_signatures(fp, diff, max_signatures=10)
                if sigs:
                    all_signatures[fp] = sigs

        # Build analyzer registry if enabled
        analyzer_registry = ctx.analyzer_registry
        if ctx.enable_analyzers and analyzer_registry is None:
            try:
                from inspectra.review.analyzers.registry import build_default_registry
                analyzer_registry = build_default_registry()
            except Exception as exc:
                logger.warning("Could not build analyzer registry: %s", exc)
                analyzer_registry = None

        chunks = chunk_diff_by_file(
            file_diffs, max_chunk_tokens=self.settings.effective_max_chunk_tokens()
        )

        concurrency = self.settings.effective_concurrency()
        logger.info(
            "Reviewing %d chunk(s) across %d file(s) via %s (concurrency=%d)",
            len(chunks), len(file_diffs), self.settings.provider.value, concurrency,
        )

        if self.settings.dry_run:
            logger.info("Dry-run mode — skipping LLM calls.")
            return [ReviewResult(file_path=c.file_path, summary="[dry-run]") for c in chunks]

        semaphore = asyncio.Semaphore(concurrency)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Reviewing...", total=len(chunks))

            async def review_chunk(chunk):
                async with semaphore:
                    try:
                        # Build per-chunk context (Phase 2)
                        kwargs: dict = {}

                        # File context: read the full file around changed lines
                        if ctx.enable_file_context:
                            file_ctx = build_file_context(
                                chunk.file_path, chunk.content,
                                max_tokens=ctx.file_context_tokens,
                            )
                            if file_ctx:
                                kwargs["full_file_context"] = file_ctx.content

                        # PR intent
                        if ctx.pr_intent:
                            kwargs["pr_intent"] = ctx.pr_intent

                        # Related changes: signatures from OTHER files
                        if all_signatures and len(file_diffs) > 1:
                            related: list[str] = []
                            for fp, sigs in all_signatures.items():
                                if fp != chunk.file_path:
                                    related.extend(sigs)
                            if related:
                                kwargs["related_changes"] = related[:20]  # cap at 20

                        # Analyzer findings for this file
                        if ctx.enable_analyzers and analyzer_registry is not None:
                            try:
                                full_content = Path(chunk.file_path).read_text(
                                    encoding="utf-8", errors="replace"
                                ) if Path(chunk.file_path).exists() else ""
                                if full_content:
                                    findings = analyzer_registry.analyze_file(
                                        chunk.file_path, full_content, chunk.content
                                    )
                                    if findings:
                                        kwargs["analyzer_findings"] = findings
                            except Exception as exc:
                                logger.debug("Analyzer failed for %s: %s", chunk.file_path, exc)

                        # Language-specific rules
                        if ctx.enable_language_rules:
                            rules = get_language_rules(chunk.file_path)
                            if rules:
                                kwargs["language_rules"] = rules

                        result = await self._reviewer.review(
                            chunk.file_path, chunk.content, **kwargs
                        )
                        progress.advance(task)
                        return result
                    except Exception as exc:
                        logger.error(
                            "Unexpected error reviewing %s: %s — continuing with other chunks",
                            chunk.file_path, exc,
                        )
                        progress.advance(task)
                        return ReviewResult(
                            file_path=chunk.file_path,
                            summary=f"Review failed unexpectedly: {exc}",
                        )

            gathered = await asyncio.gather(
                *[review_chunk(c) for c in chunks],
                return_exceptions=True,
            )

            raw_results: list[ReviewResult] = []
            for item in gathered:
                if isinstance(item, Exception):
                    logger.error("Chunk review raised unexpectedly: %s", item)
                    raw_results.append(ReviewResult(
                        file_path="<unknown>",
                        summary=f"Chunk failed: {item}",
                    ))
                else:
                    raw_results.append(item)

        merged = _merge_results(raw_results)

        # Phase 2: cross-file second pass
        if ctx.enable_cross_file and len(file_diffs) > 1 and not self.settings.dry_run:
            logger.info("Running cross-file consistency review…")
            try:
                cross_issues = await run_cross_file_review(self.provider, file_diffs)
                if cross_issues:
                    # Attach cross-file issues to a synthetic result entry
                    cross_result = ReviewResult(
                        file_path="<cross-file>",
                        issues=cross_issues,
                        summary="Cross-file consistency issues found.",
                    )
                    merged.append(cross_result)
                    logger.info("Cross-file review found %d issue(s)", len(cross_issues))
            except Exception as exc:
                logger.warning("Cross-file review failed: %s", exc)

        # Phase 2: apply baseline suppression
        if ctx.baseline is not None:
            merged, suppressed = apply_baseline(merged, ctx.baseline)
            if suppressed > 0:
                logger.info("Suppressed %d finding(s) via baseline", suppressed)

        return merged

    async def generate_pr_summary(self, results: list[ReviewResult]) -> str:
        """Generate a high-level PR summary by asking the LLM to synthesise file results."""
        if not results:
            return "No changes were reviewed."
        if self.settings.dry_run:
            return "[dry-run] PR summary skipped."

        parts: list[str] = []
        for r in results:
            issue_lines = "\n".join(
                f"  - [{i.severity.value.upper()}] {i.title}: {i.explanation[:120]}"
                for i in r.issues
            )
            parts.append(
                f"File: {r.file_path}\n"
                f"Summary: {r.summary or 'No issues found.'}\n"
                + (f"Issues:\n{issue_lines}" if issue_lines else "")
            )

        combined = "\n\n".join(parts)
        prompt = build_pr_summary_prompt(combined)

        try:
            from inspectra.llm.base import LLMRequest
            resp = await self.provider.complete(LLMRequest(user_prompt=prompt, temperature=0.3))
            return resp.text
        except Exception as exc:
            logger.warning("PR summary generation failed: %s", exc)
            return ""

    def run_sync(
        self,
        file_diffs: dict[str, str],
        context: ReviewContext | None = None,
    ) -> list[ReviewResult]:
        """Synchronous wrapper around `run`."""
        return asyncio.run(self.run(file_diffs, context))

    def generate_pr_summary_sync(self, results: list[ReviewResult]) -> str:
        """Synchronous wrapper around `generate_pr_summary`."""
        return asyncio.run(self.generate_pr_summary(results))

    async def run_and_summarize(
        self,
        file_diffs: dict[str, str],
        context: ReviewContext | None = None,
    ) -> tuple[list[ReviewResult], str]:
        """Run review + generate summary in a SINGLE event loop."""
        results = await self.run(file_diffs, context)
        summary = await self.generate_pr_summary(results)
        await self._close_provider()
        return results, summary

    def run_and_summarize_sync(
        self,
        file_diffs: dict[str, str],
        context: ReviewContext | None = None,
    ) -> tuple[list[ReviewResult], str]:
        """Sync wrapper for run_and_summarize — single event loop for everything."""
        return asyncio.run(self.run_and_summarize(file_diffs, context))

    async def _close_provider(self) -> None:
        """Close the provider's HTTP client if it has one (releases pooled connections)."""
        close = getattr(self.provider, "close", None)
        if close and callable(close):
            try:
                await close()
            except Exception as exc:
                logger.debug("Provider close failed: %s", exc)


def _merge_results(results: list[ReviewResult]) -> list[ReviewResult]:
    """Merge multiple chunk results for the same file into one ReviewResult."""
    merged: dict[str, ReviewResult] = {}
    for result in results:
        if result.file_path not in merged:
            merged[result.file_path] = result
        else:
            existing = merged[result.file_path]
            existing.issues.extend(result.issues)
            if result.summary and result.summary not in ("[dry-run]", ""):
                separator = " " if existing.summary else ""
                existing.summary += separator + result.summary
    return list(merged.values())

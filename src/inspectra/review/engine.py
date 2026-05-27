"""Review engine: orchestrates chunking, reviewing, and aggregating results."""

from __future__ import annotations

import asyncio

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from inspectra.config.settings import InspectraSettings
from inspectra.llm.base import BaseLLMProvider
from inspectra.review.prompts import build_pr_summary_prompt
from inspectra.review.reviewer import ChunkReviewer
from inspectra.review.severity import ReviewResult
from inspectra.utils.chunking import chunk_diff_by_file
from inspectra.utils.logger import logger


class ReviewEngine:
    """
    Coordinates the end-to-end review pipeline:
      1. Chunk diffs into token-safe pieces
      2. Send each chunk to the LLM reviewer
      3. Aggregate and merge results per file
      4. Optionally generate a PR-level summary
    """

    def __init__(self, provider: BaseLLMProvider, settings: InspectraSettings) -> None:
        self.provider = provider
        self.settings = settings
        self._reviewer = ChunkReviewer(provider=provider, categories=settings.review)

    # ── Main entry point ──────────────────────────────────────────────────────

    async def run(self, file_diffs: dict[str, str]) -> list[ReviewResult]:
        """
        Review all provided file diffs and return aggregated results.

        Args:
            file_diffs: {file_path: diff_text} — already filtered.

        Returns:
            List of ReviewResult, one per file.
        """
        if not file_diffs:
            logger.info("No files to review.")
            return []

        chunks = chunk_diff_by_file(
            file_diffs, max_chunk_tokens=self.settings.max_chunk_tokens
        )

        logger.info(
            "Reviewing %d chunk(s) across %d file(s) via [bold]%s[/bold]",
            len(chunks),
            len(file_diffs),
            self.settings.provider.value,
        )

        if self.settings.dry_run:
            logger.info("[yellow]Dry-run mode — skipping LLM calls.[/yellow]")
            return [ReviewResult(file_path=c.file_path, summary="[dry-run]") for c in chunks]

        # Run reviews with limited concurrency (avoid overwhelming Ollama)
        semaphore = asyncio.Semaphore(3)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Reviewing...", total=len(chunks))

            async def review_chunk(chunk):  # type: ignore[no-untyped-def]
                async with semaphore:
                    result = await self._reviewer.review(chunk.file_path, chunk.content)
                    progress.advance(task)
                    return result

            raw_results: list[ReviewResult] = list(
                await asyncio.gather(*[review_chunk(c) for c in chunks])
            )

        return _merge_results(raw_results)

    async def generate_pr_summary(self, results: list[ReviewResult]) -> str:
        """
        Generate a high-level PR summary by asking the LLM to synthesise
        the individual file results.
        """
        if not results:
            return "No changes were reviewed."

        if self.settings.dry_run:
            return "[dry-run] PR summary skipped."

        # Build a compact text representation of what we found
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
            return await self.provider.review_code(prompt)
        except Exception as exc:
            logger.warning("PR summary generation failed: %s", exc)
            return ""

    # ── Sync convenience wrappers ──────────────────────────────────────────────

    def run_sync(self, file_diffs: dict[str, str]) -> list[ReviewResult]:
        """Synchronous wrapper around `run` for CLI use."""
        return asyncio.run(self.run(file_diffs))

    def generate_pr_summary_sync(self, results: list[ReviewResult]) -> str:
        """Synchronous wrapper around `generate_pr_summary` for CLI use."""
        return asyncio.run(self.generate_pr_summary(results))


# ── helpers ───────────────────────────────────────────────────────────────────


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

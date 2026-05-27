"""Inspectra CLI — AI-powered code review."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="inspectra",
    help="🔍 AI-powered code review engine",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


# ──────────────────────────────────────────────────────────────────────────────
# review
# ──────────────────────────────────────────────────────────────────────────────

@app.command()
def review(
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p",
        help="LLM provider: ollama | openai | anthropic",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m",
        help="Model name (e.g. qwen2.5-coder:14b, gpt-4o-mini)",
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", "-c",
        help="Path to .inspectra.yml",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Write Markdown report to this file",
    ),
    sarif: Optional[Path] = typer.Option(
        None, "--sarif",
        help="Write SARIF report to this file (for GitHub Code Scanning)",
    ),
    pr_number: Optional[int] = typer.Option(
        None, "--pr",
        help="GitHub PR number (requires GITHUB_TOKEN + GITHUB_REPOSITORY)",
    ),
    post_comment: bool = typer.Option(
        False, "--post-comment",
        help="Post review as a GitHub PR comment",
    ),
    with_pr_summary: bool = typer.Option(
        True, "--pr-summary/--no-pr-summary",
        help="Generate an AI PR-level summary (on by default)",
    ),
    staged: bool = typer.Option(
        False, "--staged",
        help="Review staged (cached) changes only",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Parse diff but skip LLM calls",
    ),
    fail_on_high: bool = typer.Option(
        True, "--fail-on-high/--no-fail-on-high",
        help="Exit with code 1 when critical/high issues are found",
    ),
    cache: bool = typer.Option(
        False, "--cache/--no-cache",
        help="Cache LLM responses to .inspectra_cache/ to skip re-reviewing unchanged hunks",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Review the current git diff (or a GitHub PR) with AI."""

    from inspectra.config.loader import load_settings
    from inspectra.git.changed_files import get_reviewable_files
    from inspectra.llm.provider_factory import build_provider
    from inspectra.output.console import print_results, print_stats
    from inspectra.output.markdown import write_markdown_report
    from inspectra.output.sarif import write_sarif_report
    from inspectra.review.engine import ReviewEngine
    from inspectra.review.formatter import results_to_pr_comment
    from inspectra.utils.logger import get_logger

    log = get_logger(verbose=verbose)

    # ── Settings ──────────────────────────────────────────────────────────────
    overrides: dict = {}
    if provider:
        overrides["provider"] = provider
    if model:
        overrides["model"] = model
    if dry_run:
        overrides["dry_run"] = True
    if verbose:
        overrides["verbose"] = True

    try:
        settings = load_settings(config_path=config, **overrides)
    except Exception as exc:
        err_console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(1)

    # ── Fetch diff ────────────────────────────────────────────────────────────
    raw_diff: str | None = None
    pr_meta: dict | None = None

    num = pr_number or settings.github_pr_number
    if num:
        if not settings.github_token or not settings.github_repository:
            err_console.print(
                "[red]GITHUB_TOKEN and GITHUB_REPOSITORY must be set for PR review.[/red]"
            )
            raise typer.Exit(1)

        from inspectra.github.pull_request import get_pr_diff, get_pr_metadata

        console.print(
            f"Fetching PR [cyan]#{num}[/cyan] "
            f"from [cyan]{settings.github_repository}[/cyan]…"
        )
        raw_diff = get_pr_diff(settings.github_token, settings.github_repository, num)
        pr_meta = get_pr_metadata(settings.github_token, settings.github_repository, num)
        console.print(
            f"  [bold]{pr_meta['title']}[/bold] "
            f"by {pr_meta['author']} "
            f"({pr_meta['head']} → {pr_meta['base']})"
        )

    file_diffs = get_reviewable_files(
        raw_diff=raw_diff,
        staged_only=staged,
        exclude_patterns=settings.exclude,
    )

    if not file_diffs:
        console.print(
            "[yellow]Nothing to review — diff is empty or all files were excluded.[/yellow]"
        )
        raise typer.Exit(0)

    console.print(f"Found [bold]{len(file_diffs)}[/bold] reviewable file(s).")

    # ── Build provider ────────────────────────────────────────────────────────
    try:
        provider_instance = build_provider(settings, use_cache=cache)
    except ValueError as exc:
        err_console.print(f"[red]Provider error:[/red] {exc}")
        raise typer.Exit(1)

    # ── Run review ────────────────────────────────────────────────────────────
    engine = ReviewEngine(provider=provider_instance, settings=settings)
    results = engine.run_sync(file_diffs)

    # ── PR summary ────────────────────────────────────────────────────────────
    pr_summary = ""
    if with_pr_summary and not settings.dry_run:
        console.print("Generating PR summary…")
        pr_summary = engine.generate_pr_summary_sync(results)

    # ── Console output ────────────────────────────────────────────────────────
    print_results(results, pr_summary=pr_summary)
    print_stats(results)

    # ── File reports ──────────────────────────────────────────────────────────
    if output:
        write_markdown_report(results, output_path=output, pr_summary=pr_summary)
        console.print(f"Markdown report → [cyan]{output}[/cyan]")

    if sarif:
        write_sarif_report(results, output_path=sarif)
        console.print(f"SARIF report    → [cyan]{sarif}[/cyan]")

    # ── GitHub PR comment ─────────────────────────────────────────────────────
    if post_comment:
        if not num:
            err_console.print(
                "[red]--post-comment requires a PR number (--pr or PR_NUMBER env).[/red]"
            )
            raise typer.Exit(1)

        from inspectra.github.comments import (
            delete_previous_inspectra_comments,
            post_pr_comment,
        )

        delete_previous_inspectra_comments(
            settings.github_token, settings.github_repository, num
        )
        comment_body = results_to_pr_comment(results, pr_summary=pr_summary)
        url = post_pr_comment(
            settings.github_token, settings.github_repository, num, comment_body
        )
        console.print(f"Review posted → [link={url}]{url}[/link]")

    # ── Exit code ─────────────────────────────────────────────────────────────
    if fail_on_high:
        critical = sum(r.critical_count for r in results)
        high = sum(r.high_count for r in results)
        if critical > 0 or high > 0:
            raise typer.Exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# version
# ──────────────────────────────────────────────────────────────────────────────

@app.command()
def version() -> None:
    """Show Inspectra version."""
    from inspectra import __version__
    console.print(f"inspectra [bold]{__version__}[/bold]")


# ──────────────────────────────────────────────────────────────────────────────
# models
# ──────────────────────────────────────────────────────────────────────────────

@app.command()
def models() -> None:
    """List available models in the local Ollama instance."""
    import asyncio
    from inspectra.llm.ollama_provider import OllamaProvider

    provider_inst = OllamaProvider()

    async def _list() -> None:
        healthy = await provider_inst.health_check()
        if not healthy:
            err_console.print(
                f"[red]Ollama not reachable at {provider_inst.host}[/red]\n"
                "Run: [bold]ollama serve[/bold]"
            )
            raise typer.Exit(1)

        names = await provider_inst.list_models()
        if not names:
            console.print(
                "[yellow]No models pulled yet.[/yellow]\n"
                "Run: [bold]ollama pull qwen2.5-coder:14b[/bold]"
            )
            return

        console.print("[bold]Available Ollama models:[/bold]")
        for name in names:
            console.print(f"  • {name}")

    asyncio.run(_list())


# ──────────────────────────────────────────────────────────────────────────────
# init
# ──────────────────────────────────────────────────────────────────────────────

@app.command()
def init() -> None:
    """Create a default .inspectra.yml in the current directory."""
    target = Path(".inspectra.yml")
    if target.exists():
        console.print("[yellow].inspectra.yml already exists — not overwriting.[/yellow]")
        raise typer.Exit(0)

    default_config = """\
# .inspectra.yml — Inspectra configuration
provider: ollama
model: qwen2.5-coder:14b

ollama:
  host: http://localhost:11434

review:
  security: true
  bugs: true
  performance: true
  maintainability: true
  architecture: true

exclude:
  - "*.lock"
  - "dist/*"
  - "*.min.js"
  - "vendor/*"

max_tokens: 12000
temperature: 0.2
"""
    target.write_text(default_config)
    console.print("[green]✓[/green] Created .inspectra.yml")



# ──────────────────────────────────────────────────────────────────────────────
# cache
# ──────────────────────────────────────────────────────────────────────────────

@app.command(name="cache-clear")
def cache_clear(
    cache_dir: Path = typer.Option(
        Path(".inspectra_cache"),
        "--dir",
        help="Cache directory to clear",
    )
) -> None:
    """Clear the local LLM response cache."""
    from inspectra.utils.cache import ReviewCache
    removed = ReviewCache(cache_dir=cache_dir).clear()
    if removed:
        console.print(f"[green]✓[/green] Removed {removed} cached response(s) from {cache_dir}")
    else:
        console.print(f"[yellow]Cache at {cache_dir} was already empty.[/yellow]")


if __name__ == "__main__":
    app()

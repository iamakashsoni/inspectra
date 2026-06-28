# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Inspectra v2 CLI — self-hosted AI code reviewer.

 vs original:
- `--provider` now accepts: ollama | openai | anthropic | nvidia | openrouter
- `--inline / --no-inline` flag controls whether inline PR comments are posted
  (on by default when --post-comment is used and a PR number is set)
- The PR-comment path now submits a formal review + inline comments (was: only
  an issue-level comment) — uses the previously-dead-code in github/reviews.py
- `--model` accepts any model string per provider (Nvidia: meta/llama-3.3-70b-instruct,
  OpenRouter: anthropic/claude-3.5-sonnet, etc.)
- `--base-url` lets users override any provider's API endpoint (for self-hosted
  NIM, on-prem OpenAI proxy, remote Ollama box, etc.)
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

app = typer(
    name="inspectra",
    help="🔍 AI-powered self-hosted code reviewer",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


@app.command()
def review(
    provider: str | None = typer.Option(  # noqa: B008
        None, "--provider", "-p",
        help="LLM provider: ollama | openai | anthropic | nvidia | openrouter",
    ),
    model: str | None = typer.Option(  # noqa: B008
        None, "--model", "-m",
        help="Model name (provider-specific)",
    ),
    base_url: str | None = typer.Option(  # noqa: B008
        None, "--base-url",
        help="Override the provider's API URL (for self-hosted NIM, on-prem proxies, remote Ollama)",
    ),
    config: Path | None = typer.Option(  # noqa: B008
        None, "--config", "-c",
        help="Path to .inspectra.yml",
    ),
    output: Path | None = typer.Option(  # noqa: B008
        None, "--output", "-o",
        help="Write Markdown report to this file",
    ),
    sarif: Path | None = typer.Option(  # noqa: B008
        None, "--sarif",
        help="Write SARIF report (for GitHub Code Scanning)",
    ),
    pr_number: int | None = typer.Option(  # noqa: B008
        None, "--pr",
        help="GitHub PR number",
    ),
    post_comment: bool = typer.Option(  # noqa: B008
        False, "--post-comment",
        help="Post review as a GitHub PR comment",
    ),
    inline: bool = typer.Option(  # noqa: B008
        True, "--inline/--no-inline",
        help="Post inline comments at issue lines (on by default with --post-comment)",
    ),
    with_pr_summary: bool = typer.Option(  # noqa: B008
        True, "--pr-summary/--no-pr-summary",
        help="Generate an AI PR-level summary",
    ),
    staged: bool = typer.Option(  # noqa: B008
        False, "--staged",
        help="Review staged (cached) changes only",
    ),
    dry_run: bool = typer.Option(  # noqa: B008
        False, "--dry-run",
        help="Parse diff but skip LLM calls",
    ),
    fail_on_high: bool = typer.Option(  # noqa: B008
        True, "--fail-on-high/--no-fail-on-high",
        help="Exit with code 1 when critical/high issues are found",
    ),
    cache: bool = typer.Option(  # noqa: B008
        False, "--cache/--no-cache",
        help="Cache LLM responses to .inspectra_cache/",
    ),
    concurrency: int | None = typer.Option(  # noqa: B008
        None, "--concurrency",
        help="Max concurrent LLM calls (0 = auto, default per-provider)",
    ),
    baseline: Path | None = typer.Option(  # noqa: B008
        None, "--baseline",
        help="Path to .inspectra-baseline.json for false-positive suppression",
    ),
    pr_intent: str | None = typer.Option(  # noqa: B008
        None, "--pr-intent",
        help="PR intent / description (fed to the LLM for context). Auto-extracted from PR if --pr is set.",
    ),
    no_file_context: bool = typer.Option(  # noqa: B008
        False, "--no-file-context",
        help="Disable reading full file content around changed lines ",
    ),
    no_analyzers: bool = typer.Option(  # noqa: B008
        False, "--no-analyzers",
        help="Disable deterministic analyzers (Bandit/Semgrep/regex)",
    ),
    no_cross_file: bool = typer.Option(  # noqa: B008
        False, "--no-cross-file",
        help="Disable the second-pass cross-file consistency review",
    ),
    no_language_rules: bool = typer.Option(  # noqa: B008
        False, "--no-language-rules",
        help="Disable language-specific antipattern hints in the prompt",
    ),
    verbose: bool = typer.Option(  # noqa: B008
        False, "--verbose", "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Review the current git diff (or a GitHub PR) with AI."""

    from inspectra.config.loader import load_settings
    from inspectra.config.settings import LLMProvider, OllamaConfig
    from inspectra.git.changed_files import get_reviewable_files
    from inspectra.llm.provider_factory import build_provider
    from inspectra.output.console import print_results, print_stats
    from inspectra.output.markdown import write_markdown_report
    from inspectra.output.sarif import write_sarif_report
    from inspectra.review.engine import ReviewEngine
    from inspectra.review.formatter import results_to_pr_comment
    from inspectra.review.severity import Severity
    from inspectra.utils.logger import get_logger

    get_logger(verbose=verbose)

    # ── Settings ──────────────────────────────────────────────────────────────
    overrides: dict = {}
    if provider:
        overrides["provider"] = provider
    if model:
        overrides["model"] = model
    if concurrency is not None:
        overrides["review_concurrency"] = concurrency
    if dry_run:
        overrides["dry_run"] = True
    if verbose:
        overrides["verbose"] = True
    if not inline:
        overrides["inline_comments"] = False

    try:
        settings = load_settings(config_path=config, **overrides)
    except Exception as exc:
        err_console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(1) from None

    #  apply --base-url AFTER loading settings so we can MERGE into
    # the existing OllamaConfig rather than replacing it (which would clobber
    # timeout and any other fields the user set in YAML).
    if base_url:
        prov = settings.provider
        if prov == LLMProvider.OPENAI:
            settings.openai_base_url = base_url
        elif prov == LLMProvider.ANTHROPIC:
            settings.anthropic_base_url = base_url
        elif prov == LLMProvider.NVIDIA:
            settings.nvidia_base_url = base_url
        elif prov == LLMProvider.OPENROUTER:
            settings.openrouter_base_url = base_url
        elif prov == LLMProvider.OLLAMA:
            # Merge: keep existing timeout, only override host
            settings.ollama = OllamaConfig(
                host=base_url,
                timeout=settings.ollama.timeout,
            )

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

        console.print(f"Fetching PR [cyan]#{num}[/cyan] from [cyan]{settings.github_repository}[/cyan]…")
        raw_diff = get_pr_diff(settings.github_token, settings.github_repository, num)
        pr_meta = get_pr_metadata(settings.github_token, settings.github_repository, num)
        console.print(
            f"  [bold]{pr_meta['title']}[/bold] by {pr_meta['author']} "
            f"({pr_meta['head']} → {pr_meta['base']})"
        )

    file_diffs = get_reviewable_files(
        raw_diff=raw_diff,
        staged_only=staged,
        exclude_patterns=settings.exclude,
    )

    if not file_diffs:
        console.print("[yellow]Nothing to review — diff is empty or all files were excluded.[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found [bold]{len(file_diffs)}[/bold] reviewable file(s).")

    # ── Build provider ────────────────────────────────────────────────────────
    try:
        provider_instance = build_provider(settings, use_cache=cache)
    except ValueError as exc:
        err_console.print(f"[red]Provider error:[/red] {exc}")
        raise typer.Exit(1) from None

    # ── Build review context ──────────────────────────────────────────
    from inspectra.review.engine import ReviewContext
    from inspectra.review.baseline import load_baseline

    # Auto-extract PR intent from PR title + body if --pr is set and --pr-intent not given
    effective_pr_intent = pr_intent
    if not effective_pr_intent and pr_meta:
        effective_pr_intent = f"Title: {pr_meta.get('title', '')}\nBranch: {pr_meta.get('head', '')} → {pr_meta.get('base', '')}"

    review_context = ReviewContext(
        pr_intent=effective_pr_intent,
        enable_file_context=not no_file_context,
        enable_analyzers=not no_analyzers,
        enable_cross_file=not no_cross_file,
        enable_language_rules=not no_language_rules,
        baseline=load_baseline(baseline) if baseline else None,
    )

    # ── Run review + summary in a single event loop ──────────────────────────
    #  run review and PR summary in ONE event loop so the provider's
    # shared AsyncClient (connection pool) is valid for both calls.
    engine = ReviewEngine(provider=provider_instance, settings=settings)

    if with_pr_summary and not settings.dry_run:
        console.print("Reviewing + generating PR summary…")
        results, pr_summary = engine.run_and_summarize_sync(file_diffs, review_context)
    else:
        results = engine.run_sync(file_diffs, review_context)
        pr_summary = ""

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

    # ── GitHub PR comment + inline comments ───────────────────────────────────
    if post_comment:
        if not num:
            err_console.print("[red]--post-comment requires a PR number.[/red]")
            raise typer.Exit(1)

        from inspectra.github.comments import (
            delete_previous_inspectra_comments,
            post_pr_comment,
        )
        from inspectra.github.reviews import post_inline_comments

        # Clean up old comments (both summary and inline)
        delete_previous_inspectra_comments(
            settings.github_token, settings.github_repository, num
        )

        # Post summary comment (with table header)
        comment_body = results_to_pr_comment(results, pr_summary=pr_summary)
        url = post_pr_comment(
            settings.github_token, settings.github_repository, num, comment_body
        )
        console.print(f"Review posted → [link={url}]{url}[/link]")

        # Post inline comments at issue lines (if enabled and we have the head SHA)
        if settings.inline_comments and pr_meta and pr_meta.get("head_sha"):
            inline_count = post_inline_comments(
                token=settings.github_token,
                repo_name=settings.github_repository,
                pr_number=num,
                results=results,
                commit_sha=pr_meta["head_sha"],
                min_severity=Severity.MEDIUM,
            )
            console.print(f"  [dim]Posted {inline_count} inline comment(s) at issue lines.[/dim]")

    # ── Exit code ─────────────────────────────────────────────────────────────
    if fail_on_high:
        critical = sum(r.critical_count for r in results)
        high = sum(r.high_count for r in results)
        if critical > 0 or high > 0:
            raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show Inspectra version."""
    from inspectra import __version__
    console.print(f"inspectra [bold]{__version__}[/bold]")


@app.command()
def models(
    host: str = typer.Option(  # noqa: B008
        "http://localhost:11434", "--host",
        help="Ollama host URL",
    ),
) -> None:
    """List available models in the local Ollama instance."""
    import asyncio
    from inspectra.llm.ollama_provider import OllamaProvider

    provider_inst = OllamaProvider(host=host)

    async def _list() -> None:
        healthy = await provider_inst.health_check()
        if not healthy:
            err_console.print(
                f"[red]Ollama not reachable at {host}[/red]\nRun: [bold]ollama serve[/bold]"
            )
            raise typer.Exit(1)
        names = await provider_inst.list_models()
        if not names:
            console.print("[yellow]No models pulled yet.[/yellow]\nRun: [bold]ollama pull qwen2.5-coder:14b[/bold]")
            return
        console.print("[bold]Available Ollama models:[/bold]")
        for name in names:
            console.print(f"  • {name}")

    asyncio.run(_list())


@app.command()
def init() -> None:
    """Create a default .inspectra.yml in the current directory."""
    target = Path(".inspectra.yml")
    if target.exists():
        console.print("[yellow].inspectra.yml already exists — not overwriting.[/yellow]")
        raise typer.Exit(0)
    default_config = _default_config()
    target.write_text(default_config)
    console.print("[green]✓[/green] Created .inspectra.yml")


@app.command(name="cache-clear")
def cache_clear(
    cache_dir: Path = typer.Option(  # noqa: B008
        Path(".inspectra_cache"), "--dir",
        help="Cache directory to clear",
    ),
) -> None:
    """Clear the local LLM response cache."""
    from inspectra.utils.cache import ReviewCache
    removed = ReviewCache(cache_dir=cache_dir).clear()
    if removed:
        console.print(f"[green]✓[/green] Removed {removed} cached response(s) from {cache_dir}")
    else:
        console.print(f"[yellow]Cache at {cache_dir} was already empty.[/yellow]")


@app.command()
def suppress(
    rule_id: str = typer.Argument(  # noqa: B008
        ..., help="Rule ID to suppress (e.g. SQL_INJECTION, BANDIT/B608)",
    ),
    file_path: str | None = typer.Option(  # noqa: B008
        None, "--file", help="Only suppress in this file (optional)",
    ),
    line_number: int | None = typer.Option(  # noqa: B008
        None, "--line", help="Only suppress at this line number (optional)",
    ),
    reason: str = typer.Option(  # noqa: B008
        "", "--reason", help="Why this is suppressed (for humans)",
    ),
    expires: str | None = typer.Option(  # noqa: B008
        None, "--expires", help="ISO date when suppression expires (e.g. 2026-12-31)",
    ),
    baseline_file: Path = typer.Option(  # noqa: B008
        Path(".inspectra-baseline.json"), "--baseline", "-b",
        help="Path to the baseline file",
    ),
) -> None:
    """Add a false-positive suppression to the baseline file.

    Examples:
      inspectra suppress SQL_INJECTION --file auth/legacy.py --reason "Legacy code, deprecated Q3"
      inspectra suppress BANDIT/B608 --expires 2026-12-31
    """
    from inspectra.review.baseline import add_suppression, load_baseline

    add_suppression(
        path=baseline_file,
        rule_id=rule_id,
        file_path=file_path,
        line_number=line_number,
        reason=reason,
        expires=expires,
    )

    # Show the current baseline
    baseline = load_baseline(baseline_file)
    console.print(
        f"[green]✓[/green] Added suppression for [cyan]{rule_id}[/cyan] "
        f"to [cyan]{baseline_file}[/cyan]"
    )
    console.print(f"  Total suppressions: {len(baseline.suppressions)}")


@app.command()
def baseline_show(
    baseline_file: Path = typer.Option(  # noqa: B008
        Path(".inspectra-baseline.json"), "--baseline", "-b",
        help="Path to the baseline file",
    ),
) -> None:
    """Show all suppressions in the baseline file."""
    from inspectra.review.baseline import load_baseline

    baseline = load_baseline(baseline_file)
    if not baseline.suppressions:
        console.print(f"[yellow]No suppressions in {baseline_file}[/yellow]")
        return

    console.print(f"[bold]Suppressions in {baseline_file}[/bold] ({len(baseline.suppressions)}):")
    for s in baseline.suppressions:
        loc = s.file_path or "*"
        if s.line_number:
            loc += f":{s.line_number}"
        expires_str = f" (expires {s.expires})" if s.expires else ""
        reason_str = f" — {s.reason}" if s.reason else ""
        console.print(f"  • [cyan]{s.rule_id}[/cyan] at [dim]{loc}[/dim]{expires_str}{reason_str}")


def _default_config() -> str:
    return """\
# .inspectra.yml — Inspectra configuration
# Docs: https://github.com/iamakashsoni/inspectra

# LLM provider: ollama | openai | anthropic | nvidia | openrouter
provider: ollama
model: qwen2.5-coder:14b

# Ollama (only used when provider = ollama)
ollama:
  host: http://localhost:11434
  timeout: 300

# Cloud provider API keys (set via env vars or here — never commit real keys!)
# openai_api_key: sk-...
# anthropic_api_key: sk-ant-...
# nvidia_api_key: nvapi-...
# openrouter_api_key: sk-or-...

# Self-hosted NIM / on-prem proxy overrides (uncomment to use)
# openai_base_url: https://api.openai.com/v1
# anthropic_base_url: https://api.anthropic.com/v1
# nvidia_base_url: https://integrate.api.nvidia.com/v1
# openrouter_base_url: https://openrouter.ai/api/v1

# Review categories (set to false to disable)
review:
  security: true
  bugs: true
  performance: true
  maintainability: true
  architecture: true
  concurrency: true
  scalability: true

# Files/patterns to exclude from review
exclude:
  - "*.lock"
  - "dist/*"
  - "*.min.js"
  - "vendor/*"

# Token limits
max_tokens: 12000
max_chunk_tokens: 3000

# LLM temperature (lower = more deterministic)
temperature: 0.2

# Concurrency: 0 = auto-pick per provider (Ollama=3, OpenAI=10, etc.)
review_concurrency: 0

# Post inline comments at issue lines when reviewing a PR
inline_comments: true
"""


if __name__ == "__main__":
    app()

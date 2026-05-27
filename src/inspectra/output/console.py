"""Console output using Rich tables and panels."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from inspectra.review.severity import ReviewResult, Severity

console = Console()


def print_results(results: list[ReviewResult], pr_summary: str = "") -> None:
    """Print a rich, colorful review summary to the console."""
    if pr_summary:
        console.print(Panel(pr_summary, title="[bold]PR Summary[/bold]", border_style="cyan"))
        console.print()

    total_issues = sum(len(r.issues) for r in results)

    if not total_issues:
        console.print(
            Panel(
                "[bold green]✅ No issues found — the diff looks great![/bold green]",
                border_style="green",
            )
        )
        return

    # Summary table
    table = Table(title="Review Summary", show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Issues", justify="right")
    table.add_column("Critical", justify="right", style="red")
    table.add_column("High", justify="right", style="orange1")

    for result in results:
        table.add_row(
            result.file_path,
            str(len(result.issues)),
            str(result.critical_count),
            str(result.high_count),
        )

    console.print(table)
    console.print()

    # Detail per issue
    for result in results:
        if not result.issues:
            continue

        console.print(Rule(f"[cyan]{result.file_path}[/cyan]"))

        for issue in sorted(result.issues, key=lambda i: _severity_sort_key(i.severity)):
            title_text = Text(f"{issue.severity.emoji} {issue.title}", style=issue.severity.rich_style)
            lines: list[str] = [
                f"[bold]Category:[/bold] {issue.category}",
                f"[bold]Severity:[/bold] {issue.severity.value.upper()}",
            ]
            if issue.line_number:
                lines.append(f"[bold]Line:[/bold] {issue.line_number}")
            lines.append("")
            lines.append(issue.explanation)
            if issue.suggested_fix:
                lines.append(f"\n[bold]Suggested fix:[/bold] {issue.suggested_fix}")

            console.print(Panel("\n".join(lines), title=title_text, border_style="dim"))

        console.print()


def print_stats(results: list[ReviewResult]) -> None:
    """Print a one-line stats summary."""
    total = sum(len(r.issues) for r in results)
    critical = sum(r.critical_count for r in results)
    high = sum(r.high_count for r in results)
    console.print(
        f"[bold]Inspectra:[/bold] {len(results)} file(s) reviewed · "
        f"{total} issue(s) · "
        f"[red]{critical} critical[/red] · "
        f"[orange1]{high} high[/orange1]"
    )


def _severity_sort_key(s: Severity) -> int:
    order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    try:
        return order.index(s)
    except ValueError:
        return 99

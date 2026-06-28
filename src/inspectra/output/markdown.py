# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Write review output to a Markdown file."""

from __future__ import annotations

from pathlib import Path

from inspectra.review.formatter import results_to_markdown
from inspectra.review.severity import ReviewResult
from inspectra.utils.logger import logger


def write_markdown_report(
    results: list[ReviewResult],
    output_path: Path | str = "inspectra-review.md",
    pr_summary: str = "",
) -> Path:
    output_path = Path(output_path)
    content = results_to_markdown(results, pr_summary)
    output_path.write_text(content, encoding="utf-8")
    logger.info("Markdown report written to %s", output_path)
    return output_path

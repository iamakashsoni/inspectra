# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Centralized logging using Rich."""

import logging

from rich.console import Console
from rich.logging import RichHandler

console = Console(stderr=True)


def get_logger(name: str = "inspectra", verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
    )
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger


logger = get_logger()

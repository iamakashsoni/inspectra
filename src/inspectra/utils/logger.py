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


# Module-level default logger (reconfigured when verbose flag is known)
logger = get_logger()

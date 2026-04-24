"""Logging configuration utilities for the CLI."""

from __future__ import annotations

import logging
import sys


LOG_LEVEL_CHOICES = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def configure_logging(level_name: str = "INFO") -> None:
    """Configure root logging with a stable console format."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root_logger.addHandler(handler)

    root_logger.setLevel(level)

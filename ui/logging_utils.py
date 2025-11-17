"""Logging helpers for the Universal Manga Downloader UI."""

from __future__ import annotations

import logging


def configure_logging(level: int | str | None = None) -> None:
    """Configure a sensible default logger for the application."""

    root_logger = logging.getLogger()

    resolved_level: int | None
    if isinstance(level, str):
        resolved_level = logging.getLevelName(level.upper())
        if not isinstance(resolved_level, int):
            resolved_level = logging.INFO
    else:
        resolved_level = level

    if not root_logger.handlers:
        logging.basicConfig(
            level=resolved_level or logging.INFO,
            format="%(levelname)s:%(name)s:%(message)s",
        )
    elif resolved_level is not None:
        root_logger.setLevel(resolved_level)
        for handler in root_logger.handlers:
            handler.setLevel(resolved_level)


__all__ = ["configure_logging"]

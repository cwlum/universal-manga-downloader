"""Parser package that automatically registers available site handlers."""

from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path

from .base_parser import BaseParser

logger = logging.getLogger(__name__)


def discover_parsers() -> list[type[BaseParser]]:
    """Import parser modules dynamically and collect their parser classes."""

    parser_classes: list[type[BaseParser]] = []
    current_dir = Path(__file__).parent

    for module_path in current_dir.glob("*.py"):
        if module_path.name in {"__init__.py", "base_parser.py"}:
            continue

        module_name = f"{__name__}.{module_path.stem}"
        module = importlib.import_module(module_name)

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseParser) and obj is not BaseParser:
                parser_classes.append(obj)

    parser_names = ", ".join(sorted(parser.get_name() for parser in parser_classes))
    logger.debug("Discovered parsers: %s", parser_names or "<none>")
    return parser_classes


ALL_PARSERS = discover_parsers()

__all__ = ["ALL_PARSERS"]

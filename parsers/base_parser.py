"""Base interface that all parser implementations must follow."""

from __future__ import annotations

import re


class BaseParser:
    """
    Abstract base class for website parsers.
    Each parser should be able to identify if it can handle a given URL/soup,
    and if so, extract the necessary information.
    """

    @staticmethod
    def get_name() -> str:
        """
        Returns the name of the parser (e.g., 'Bato_V1').
        """
        raise NotImplementedError

    @staticmethod
    def can_parse(soup, url: str) -> bool:
        """
        A quick check to see if this parser is likely to handle the page.
        This should be a lightweight check.

        :param soup: BeautifulSoup object of the page.
        :param url: The URL of the page.
        :return: True if the parser can handle it, False otherwise.
        """
        raise NotImplementedError

    @staticmethod
    def parse(soup, url: str) -> dict[str, object] | None:
        """
        Parses the page to extract manga information.

        :param soup: BeautifulSoup object of the page.
        :param url: The URL of the page.
        :return: A dictionary containing 'title', 'chapter', and 'image_urls',
                 or None if parsing fails.
        """
        raise NotImplementedError

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Return a filesystem-friendly representation of a filename.

        This implementation:
        - Replaces colons with " - " for readability
        - Removes only truly invalid filesystem characters: \\ / * ? " < > |
        - Handles Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
        - Preserves spaces and readable characters
        - Collapses multiple spaces and dashes
        """
        from pathlib import PurePath

        candidate = name.replace(":", " - ")
        candidate = candidate.replace("\n", " ").replace("\r", " ")
        candidate = re.sub(r"[\\/*?\"<>|]", " ", candidate)
        candidate = candidate.replace("_", " ")
        candidate = re.sub(r"\s+", " ", candidate)
        candidate = re.sub(r"-{2,}", "-", candidate)
        sanitized = candidate.strip(" .")
        if not sanitized:
            return "item"

        # Windows reserved filenames must not be used without a suffix.
        reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        upper_name = PurePath(sanitized).name.upper()
        if upper_name in reserved:
            sanitized = f"{sanitized} -"

        return sanitized

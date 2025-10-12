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
        A utility function to remove illegal characters from filenames.
        """
        sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
        sanitized = re.sub(r'_{3,}', '__', sanitized)
        return sanitized.strip('_')

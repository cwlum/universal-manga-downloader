"""Plugin implementing MangaDex chapter support via the public API."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from services.mangadex_service import MangaDexService

from .base import BasePlugin, ParsedChapter

logger = logging.getLogger(__name__)


class MangaDexParser(BasePlugin):
    """Parse MangaDex chapters by leveraging the official API."""

    _CHAPTER_REGEX = re.compile(r"/chapter/([0-9a-f-]{10,})", re.IGNORECASE)

    def __init__(self) -> None:
        self._service = MangaDexService()

    def get_name(self) -> str:
        return "MangaDex"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return "mangadex.org" in host and "/chapter/" in parsed.path

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
        chapter_id = self._extract_chapter_id(url)
        if chapter_id is None:
            logger.debug("%s skipping unsupported URL %s", self.get_name(), url)
            return None

        try:
            chapter_data = self._service.fetch_chapter(chapter_id)
        except requests.RequestException as exc:
            logger.error("%s API request failed for %s: %s", self.get_name(), url, exc)
            return None
        if chapter_data is None:
            logger.warning("%s could not resolve chapter data for %s", self.get_name(), url)
            return None

        return ParsedChapter(
            title=self.sanitize_filename(chapter_data.title),
            chapter=self.sanitize_filename(chapter_data.chapter),
            image_urls=chapter_data.image_urls,
        )

    def on_load(self) -> None:
        logger.info("Loaded %s parser plugin", self.get_name())

    def _extract_chapter_id(self, url: str) -> str | None:
        match = self._CHAPTER_REGEX.search(url)
        if match:
            return match.group(1)
        return None

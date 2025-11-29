"""
Universal Manga Downloader Plugin

Name: Example Remote Parser
Author: UMD Community
Version: 0.1.0
Description: Skeleton parser demonstrating remote plugin metadata and structure.
Repository: https://github.com/umd-plugins/official
License: MIT
Dependencies:
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from plugins.base import BasePlugin, ParsedChapter


class ExampleRemoteParser(BasePlugin):
    """Minimal parser template that can be extended by contributors."""

    def get_name(self) -> str:
        return "Example Remote Parser"

    def can_handle(self, url: str) -> bool:
        return "example-remote" in url

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
        title = soup.select_one("h1")
        images = [img["src"] for img in soup.select("img") if img.get("src")]
        if not title or not images:
            return None
        return ParsedChapter(
            title=self.sanitize_filename(title.get_text(strip=True)),
            chapter="Remote-1",
            image_urls=images,
        )

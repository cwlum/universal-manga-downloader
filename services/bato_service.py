from __future__ import annotations

import logging
from urllib.parse import urljoin

import cloudscraper
from bs4 import BeautifulSoup

from config import CONFIG

logger = logging.getLogger(__name__)


class BatoService:
    """Lightweight helper that scrapes search and series pages from Bato.to."""

    def __init__(self, scraper: cloudscraper.CloudScraper | None = None) -> None:
        # Reuse the downloader's scraper if available to play nicely with Cloudflare.
        self._scraper = scraper or cloudscraper.create_scraper()
        self.base_url = CONFIG.service.bato_base_url
        self.search_path = CONFIG.service.bato_search_path
        self.max_search_pages = CONFIG.service.bato_max_search_pages

    def search_manga(self, query: str, max_pages: int | None = None) -> list[dict[str, str]]:
        """Return a list of search results for the supplied query."""
        normalized_query = query.strip()
        if not normalized_query:
            return []

        if max_pages is None:
            max_pages = self.max_search_pages

        results: list[dict[str, str]] = []
        seen_urls: set[str] = set()

        for page in range(1, max(1, max_pages) + 1):
            params = {"word": normalized_query, "page": page}
            response = self._scraper.get(
                urljoin(self.base_url, self.search_path),
                params=params,
                timeout=CONFIG.download.search_timeout,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            page_count = 0

            for item in soup.select("div.item-text"):
                link = item.select_one("a.item-title")
                if not link:
                    continue

                href = link.get("href")
                if not isinstance(href, str):
                    continue

                series_url = urljoin(self.base_url, href)
                if series_url in seen_urls:
                    continue

                subtitle_tag = item.select_one("p.item-subtitle")
                subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ""

                results.append(
                    {
                        "title": link.get_text(strip=True),
                        "url": series_url,
                        "subtitle": subtitle,
                    }
                )
                seen_urls.add(series_url)
                page_count += 1

            if page_count == 0:
                break

        return results

    def get_series_info(self, series_url: str) -> dict[str, object]:
        """Fetch title, metadata, and chapter listing for a series page."""
        response = self._scraper.get(series_url, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.select_one("h3.item-title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

        description = self._extract_description(soup)
        attributes = self._extract_attributes(soup)
        chapters = self._extract_chapters(soup)

        return {
            "title": title,
            "description": description,
            "attributes": attributes,
            "chapters": chapters,
            "url": series_url,
        }

    def _extract_description(self, soup: BeautifulSoup) -> str:
        description_container = soup.select_one("#limit-height-body-summary")
        if not description_container:
            return ""

        return description_container.get_text(" ", strip=True)

    def _extract_attributes(self, soup: BeautifulSoup) -> dict[str, object]:
        attributes: dict[str, object] = {}

        for attr_item in soup.select("div.attr-item"):
            label_tag = attr_item.select_one("b.text-muted")
            value_container = attr_item.select_one("span")
            if not label_tag or not value_container:
                continue

            label = label_tag.get_text(strip=True).rstrip(":")

            collected: list[str] = []
            for child in value_container.find_all(["a", "u", "span"], recursive=True):
                text = child.get_text(strip=True)
                if text:
                    collected.append(text)

            if not collected:
                fallback = value_container.get_text(" ", strip=True)
                if fallback:
                    collected.append(fallback)

            if not collected:
                continue

            attributes[label] = collected if len(collected) > 1 else collected[0]

        return attributes

    def _extract_chapters(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        chapters: list[dict[str, str]] = []

        for anchor in soup.select("a.chapt"):
            href = anchor.get("href")
            if not isinstance(href, str):
                continue

            base_title_tag = anchor.select_one("b")
            subtitle_tag = anchor.select_one("span")

            base_title = base_title_tag.get_text(strip=True) if base_title_tag else ""
            subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ""
            full_title = " ".join(part for part in [base_title, subtitle] if part).strip()

            text_content = anchor.get_text(" ", strip=True)
            display_title = full_title or text_content

            chapters.append(
                {
                    "title": display_title,
                    "url": urljoin(self.base_url, href),
                    "label": base_title or display_title,
                }
            )

        chapters.reverse()  # Oldest first keeps numbering increasing in the UI.
        return chapters

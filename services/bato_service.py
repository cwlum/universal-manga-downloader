from __future__ import annotations

import logging
import time
from urllib.parse import urljoin

import cloudscraper
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from config import CONFIG
from services.bato_mirror_manager import get_mirror_manager
from utils.http_client import create_scraper_session

logger = logging.getLogger(__name__)


class BatoService:
    """Lightweight helper that scrapes search and series pages from Bato.to."""

    def __init__(self, scraper: cloudscraper.CloudScraper | None = None) -> None:
        # Reuse the downloader's scraper if available to play nicely with Cloudflare.
        self._scraper = scraper or create_scraper_session()
        self._mirror_manager = get_mirror_manager()
        self.max_search_pages = CONFIG.service.bato_max_search_pages
        self._last_request_time: float = 0.0
        self._rate_limit_delay = CONFIG.service.rate_limit_delay

    @property
    def base_url(self) -> str:
        """Get the current active mirror URL."""
        return self._mirror_manager.current_base_url

    @property
    def mirror_manager(self):
        """Expose mirror manager for external configuration."""
        return self._mirror_manager

    def _apply_rate_limit(self) -> None:
        """Ensure minimum delay between requests to avoid triggering anti-bot measures."""
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._rate_limit_delay:
                sleep_time = self._rate_limit_delay - elapsed
                logger.debug("Rate limiting: sleeping %.2fs", sleep_time)
                time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _request_with_fallback(
        self,
        path: str,
        params: dict[str, object] | None = None,
        timeout: int | None = None,
    ) -> tuple[str, str]:
        """Make a request with automatic mirror fallback on failure.

        Args:
            path: URL path to append to the base URL
            params: Optional query parameters
            timeout: Request timeout in seconds

        Returns:
            Tuple of (response_text, base_url_used)

        Raises:
            RequestException: If all mirrors fail
        """
        if timeout is None:
            timeout = CONFIG.download.request_timeout

        last_error: Exception | None = None
        tried_mirrors: list[str] = []
        start_mirror = self._mirror_manager.current_base_url

        # Try current mirror first, then fallback to others
        while True:
            current_base = self._mirror_manager.current_base_url
            if current_base in tried_mirrors:
                # We've cycled through all mirrors
                break
            tried_mirrors.append(current_base)

            url = urljoin(current_base, path)
            try:
                self._apply_rate_limit()
                response = self._scraper.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                if current_base != start_mirror:
                    logger.info("Successfully using mirror: %s", current_base)
                return response.text, current_base
            except RequestException as exc:
                last_error = exc
                logger.warning(
                    "Mirror %s failed: %s. Trying next mirror...",
                    current_base,
                    exc,
                )
                next_mirror = self._mirror_manager.next_mirror()
                if next_mirror is None:
                    break

        # Reset to primary mirror for next time
        self._mirror_manager.reset_to_primary()

        if last_error is not None:
            raise last_error
        raise RequestException(f"All mirrors failed for path: {path}")

    def _search_with_fallback(
        self,
        query: str,
        page: int,
        timeout: int | None = None,
    ) -> tuple[list[dict], str]:
        """Make a search request using GraphQL API with automatic mirror fallback.

        Each mirror may have different search paths and parameters.

        Args:
            query: Search query
            page: Page number
            timeout: Request timeout in seconds

        Returns:
            Tuple of (search_results, base_url_used)

        Raises:
            RequestException: If all mirrors fail
        """
        if timeout is None:
            timeout = CONFIG.download.search_timeout

        last_error: Exception | None = None
        tried_mirrors: list[str] = []
        start_mirror = self._mirror_manager.current_base_url

        # GraphQL query for search
        graphql_query = """
        query get_content_searchComic($select: SearchComic_Select) {
          get_content_searchComic(select: $select) {
            reqWord reqPage
            paging { pages page }
            items {
              id
              data {
                id slug name urlPath
              }
            }
          }
        }
        """

        # Try current mirror first, then fallback to others
        while True:
            mirror = self._mirror_manager.current_mirror
            current_base = mirror["base_url"]

            if current_base in tried_mirrors:
                # We've cycled through all mirrors
                break
            tried_mirrors.append(current_base)

            # Build GraphQL request
            api_url = urljoin(current_base, "/apo/")
            payload = {
                "query": graphql_query,
                "variables": {
                    "select": {
                        "where": "browse",
                        "word": query,
                        "page": page,
                    }
                }
            }

            try:
                self._apply_rate_limit()
                response = self._scraper.post(
                    api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=timeout,
                )
                response.raise_for_status()

                data = response.json()
                if "errors" in data:
                    raise RequestException(f"GraphQL error: {data['errors']}")

                results = data.get("data", {}).get("get_content_searchComic", {})
                items = results.get("items", [])

                if current_base != start_mirror:
                    logger.info("Successfully using mirror: %s", current_base)
                return items, current_base
            except RequestException as exc:
                last_error = exc
                logger.warning(
                    "Mirror %s failed: %s. Trying next mirror...",
                    current_base,
                    exc,
                )
                next_mirror = self._mirror_manager.next_mirror()
                if next_mirror is None:
                    break

        # Reset to primary mirror for next time
        self._mirror_manager.reset_to_primary()

        if last_error is not None:
            raise last_error
        raise RequestException(f"All mirrors failed for search: {query}")

    def search_manga(self, query: str, max_pages: int | None = None) -> list[dict[str, str]]:
        """Return a list of search results for the supplied query.

        Automatically falls back to mirror sites if the current mirror fails.
        Uses GraphQL API for reliable results.
        """
        normalized_query = query.strip()
        if not normalized_query:
            return []

        if max_pages is None:
            max_pages = self.max_search_pages

        results: list[dict[str, str]] = []
        seen_urls: set[str] = set()

        for page in range(1, max(1, max_pages) + 1):
            items, base_url = self._search_with_fallback(
                normalized_query,
                page,
                timeout=CONFIG.download.search_timeout,
            )

            if not items:
                break

            for item in items:
                data = item.get("data", {})
                url_path = data.get("urlPath", "")
                if not url_path:
                    continue

                series_url = urljoin(base_url, url_path)
                if series_url in seen_urls:
                    continue

                results.append(
                    {
                        "title": data.get("name", "Unknown"),
                        "url": series_url,
                        "subtitle": data.get("slug", ""),
                    }
                )
                seen_urls.add(series_url)

        return results

    def get_series_info(self, series_url: str) -> dict[str, object]:
        """Fetch title, metadata, and chapter listing for a series page.

        Uses GraphQL API for reliable results.
        Automatically falls back to mirror sites if the current mirror fails.
        """
        import re
        from urllib.parse import urlparse

        # Extract comic ID from URL (e.g., /title/91934-slug -> 91934)
        parsed = urlparse(series_url)
        path = parsed.path
        match = re.search(r"/title/(\d+)", path)
        if not match:
            raise ValueError(f"Cannot extract comic ID from URL: {series_url}")
        comic_id = match.group(1)

        # Get comic info and chapters via GraphQL
        comic_data, chapters_data, base_url = self._get_series_info_graphql(comic_id)

        # Extract data
        data = comic_data.get("data", {})
        title = data.get("name", "Unknown Title")
        description = ""
        summary = data.get("summary")
        if summary and isinstance(summary, dict):
            description = summary.get("code", "")

        attributes: dict[str, object] = {}
        if data.get("authors"):
            attributes["Authors"] = data["authors"]
        if data.get("genres"):
            attributes["Genres"] = data["genres"]

        # Build chapters list
        chapters: list[dict[str, str]] = []
        for ch in chapters_data:
            ch_data = ch.get("data", {})
            url_path = ch_data.get("urlPath", "")
            if not url_path:
                continue
            chapters.append({
                "title": ch_data.get("dname", "Unknown"),
                "url": urljoin(base_url, url_path),
                "label": ch_data.get("dname", "Unknown"),
            })

        return {
            "title": title,
            "description": description,
            "attributes": attributes,
            "chapters": chapters,
            "url": urljoin(base_url, path),
        }

    def _get_series_info_graphql(self, comic_id: str) -> tuple[dict, list, str]:
        """Fetch series info and chapters using GraphQL API with fallback.

        Args:
            comic_id: The numeric comic ID

        Returns:
            Tuple of (comic_data, chapters_list, base_url_used)
        """
        last_error: Exception | None = None
        tried_mirrors: list[str] = []
        start_mirror = self._mirror_manager.current_base_url

        # GraphQL queries
        comic_query = """
        query get_content_comicNode($id: ID!) {
          get_content_comicNode(id: $id) {
            data {
              id slug name urlPath
              authors
              genres
              summary { code }
            }
          }
        }
        """

        chapters_query = """
        query get_content_chapterList($comicId: ID!) {
          get_content_chapterList(comicId: $comicId) {
            id
            data {
              id urlPath dname
            }
          }
        }
        """

        while True:
            mirror = self._mirror_manager.current_mirror
            current_base = mirror["base_url"]

            if current_base in tried_mirrors:
                break
            tried_mirrors.append(current_base)

            api_url = urljoin(current_base, "/apo/")
            headers = {"Content-Type": "application/json"}

            try:
                self._apply_rate_limit()

                # Get comic info
                response = self._scraper.post(
                    api_url,
                    json={"query": comic_query, "variables": {"id": comic_id}},
                    headers=headers,
                    timeout=CONFIG.download.series_info_timeout,
                )
                response.raise_for_status()
                comic_result = response.json()
                if "errors" in comic_result:
                    raise RequestException(f"GraphQL error: {comic_result['errors']}")

                self._apply_rate_limit()

                # Get chapters
                response = self._scraper.post(
                    api_url,
                    json={"query": chapters_query, "variables": {"comicId": comic_id}},
                    headers=headers,
                    timeout=CONFIG.download.series_info_timeout,
                )
                response.raise_for_status()
                chapters_result = response.json()
                if "errors" in chapters_result:
                    raise RequestException(f"GraphQL error: {chapters_result['errors']}")

                comic_data = comic_result.get("data", {}).get("get_content_comicNode", {})
                chapters_data = chapters_result.get("data", {}).get("get_content_chapterList", [])

                if current_base != start_mirror:
                    logger.info("Successfully using mirror: %s", current_base)

                return comic_data, chapters_data, current_base

            except RequestException as exc:
                last_error = exc
                logger.warning(
                    "Mirror %s failed: %s. Trying next mirror...",
                    current_base,
                    exc,
                )
                next_mirror = self._mirror_manager.next_mirror()
                if next_mirror is None:
                    break

        self._mirror_manager.reset_to_primary()

        if last_error is not None:
            raise last_error
        raise RequestException(f"All mirrors failed for comic ID: {comic_id}")

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

    def _extract_chapters(self, soup: BeautifulSoup, base_url: str | None = None) -> list[dict[str, str]]:
        chapters: list[dict[str, str]] = []
        url_base = base_url or self.base_url

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
                    "url": urljoin(url_base, href),
                    "label": base_title or display_title,
                }
            )

        chapters.reverse()  # Oldest first keeps numbering increasing in the UI.
        return chapters

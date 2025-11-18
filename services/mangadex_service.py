"""Service helper that interacts with the MangaDex REST API."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]

from config import CONFIG

logger = logging.getLogger(__name__)

_MANGA_ID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)


@dataclass(slots=True)
class MangaDexChapter:
    """Structured chapter information returned by MangaDexService."""

    title: str
    chapter: str
    image_urls: list[str]


class MangaDexService:
    """API client exposing search, metadata, and chapter helpers for MangaDex."""

    def __init__(self, session: requests.Session | None = None) -> None:
        service_cfg = CONFIG.service
        self._session = session or requests.Session()
        self._api_base = service_cfg.mangadex_api_base.rstrip("/")
        self._site_base = service_cfg.mangadex_site_base.rstrip("/")
        self._search_limit = max(1, service_cfg.mangadex_search_limit)
        self._max_chapter_pages = max(1, service_cfg.mangadex_max_chapter_pages)
        self._languages = tuple(lang for lang in service_cfg.mangadex_languages if lang)

        download_cfg = CONFIG.download
        self._request_timeout = download_cfg.request_timeout
        self._search_timeout = download_cfg.search_timeout
        self._series_timeout = download_cfg.series_info_timeout

        self._last_request_time: float = 0.0
        self._rate_limit_delay = service_cfg.rate_limit_delay
        self._cache_ttl = 300.0  # seconds
        self._cache_max_entries = 128
        self._search_cache: dict[tuple[str, int], tuple[float, list[dict[str, str]]]] = {}
        self._manga_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._chapter_list_cache: dict[str, tuple[float, list[dict[str, str]]]] = {}
        self._chapter_metadata_cache: dict[str, tuple[float, dict[str, str]]] = {}
        self._chapter_images_cache: dict[str, tuple[float, list[str]]] = {}

    def _apply_rate_limit(self) -> None:
        """Ensure minimum delay between API requests to respect rate limits."""
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._rate_limit_delay:
                sleep_time = self._rate_limit_delay - elapsed
                logger.debug("Rate limiting: sleeping %.2fs", sleep_time)
                time.sleep(sleep_time)
        self._last_request_time = time.time()

    # --- Public API -----------------------------------------------------
    def search_manga(self, query: str, limit: int | None = None) -> list[dict[str, str]]:
        """Return basic search results for the supplied title query."""

        normalized = query.strip()
        if not normalized:
            return []

        limit_value = min(max(1, limit or self._search_limit), 100)
        cache_key = (normalized, limit_value)
        cached = self._cache_get(self._search_cache, cache_key)
        if cached is not None:
            return cached

        params: list[tuple[str, str]] = [
            ("title", normalized),
            ("limit", str(limit_value)),
            ("order[relevance]", "desc"),
        ]
        for include in ("author", "artist", "cover_art"):
            params.append(("includes[]", include))

        self._apply_rate_limit()
        response = self._session.get(
            f"{self._api_base}/manga",
            params=params,
            timeout=self._search_timeout,
        )
        response.raise_for_status()

        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, list):
            return []

        results: list[dict[str, str]] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            manga_id = entry.get("id")
            if not isinstance(manga_id, str):
                continue

            attributes = entry.get("attributes") or {}
            relationships = entry.get("relationships") or []

            title = self._pick_localized_text(attributes.get("title")) or "Untitled Manga"
            subtitle = self._build_search_subtitle(attributes, relationships)
            results.append(
                {
                    "title": title,
                    "url": self._build_series_url(manga_id),
                    "subtitle": subtitle,
                    "provider": "MangaDex",
                }
            )

        self._cache_set(self._search_cache, cache_key, results)
        return results

    def get_series_info(self, series_url: str) -> dict[str, object]:
        """Fetch full metadata and chapter listing for a MangaDex title."""

        manga_id = self._extract_manga_id(series_url)
        if manga_id is None:
            raise ValueError(f"Unsupported MangaDex URL: {series_url}")

        data = self._fetch_manga_payload(manga_id)
        attributes = data.get("attributes") or {}
        relationships = data.get("relationships") or []

        title = self._pick_localized_text(attributes.get("title")) or "Untitled Manga"
        description = self._pick_localized_text(attributes.get("description")) or ""

        series_attributes: dict[str, object] = {}
        author_names = self._collect_relationship_names(relationships, {"author"})
        if author_names:
            series_attributes["Author(s)"] = author_names

        artist_names = self._collect_relationship_names(relationships, {"artist"})
        if artist_names:
            series_attributes["Artist(s)"] = artist_names

        tags = self._collect_tags(relationships)
        if tags:
            series_attributes["Tags"] = tags

        status = self._safe_str(attributes.get("status"))
        if status:
            series_attributes["Status"] = status.title()

        original_language = self._safe_str(attributes.get("originalLanguage"))
        if original_language:
            series_attributes["Original Language"] = original_language

        content_rating = self._safe_str(attributes.get("contentRating"))
        if content_rating:
            series_attributes["Content Rating"] = content_rating.replace("_", " ").title()

        year = attributes.get("year")
        if isinstance(year, int):
            series_attributes["Year"] = year

        chapters = self._fetch_chapter_list(manga_id)

        return {
            "title": title,
            "description": description,
            "attributes": series_attributes,
            "chapters": chapters,
            "url": self._build_series_url(manga_id),
            "provider": "MangaDex",
        }

    def fetch_chapter(self, chapter_id: str) -> MangaDexChapter | None:
        """Return chapter metadata and image URLs for ``chapter_id``."""

        metadata = self._fetch_chapter_metadata(chapter_id)
        if metadata is None:
            return None

        image_urls = self._fetch_chapter_images(chapter_id)
        if not image_urls:
            return None

        return MangaDexChapter(
            title=metadata["title"],
            chapter=metadata["chapter"],
            image_urls=image_urls,
        )

    # --- Internal helpers -----------------------------------------------
    def _fetch_manga_payload(self, manga_id: str) -> dict[str, Any]:
        cached = self._cache_get(self._manga_cache, manga_id)
        if cached is not None:
            return cached

        params = [
            ("includes[]", "author"),
            ("includes[]", "artist"),
            ("includes[]", "cover_art"),
            ("includes[]", "tag"),
        ]
        self._apply_rate_limit()
        response = self._session.get(
            f"{self._api_base}/manga/{manga_id}",
            params=params,
            timeout=self._series_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError(f"MangaDex returned an unexpected payload for manga {manga_id}")
        self._cache_set(self._manga_cache, manga_id, data)
        return data

    def _fetch_chapter_list(self, manga_id: str) -> list[dict[str, str]]:
        cached = self._cache_get(self._chapter_list_cache, manga_id)
        if cached is not None:
            return cached

        chapters: list[dict[str, str]] = []
        limit = 100
        offset = 0

        for _page in range(self._max_chapter_pages):
            params: list[tuple[str, str]] = [
                ("manga", manga_id),
                ("limit", str(limit)),
                ("offset", str(offset)),
                ("order[chapter]", "asc"),
            ]
            for language in self._languages or ("en",):
                params.append(("translatedLanguage[]", language))

            self._apply_rate_limit()
            response = self._session.get(
                f"{self._api_base}/chapter",
                params=params,
                timeout=self._series_timeout,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data")

            if not isinstance(data, list):
                break

            for entry in data:
                chapter_entry = self._build_chapter_entry(entry)
                if chapter_entry is not None:
                    chapters.append(chapter_entry)

            total = payload.get("total")
            offset += limit

            if isinstance(total, int) and offset >= total:
                break
            if len(data) < limit:
                break

        self._cache_set(self._chapter_list_cache, manga_id, chapters)
        return chapters

    def _fetch_chapter_metadata(self, chapter_id: str) -> dict[str, str] | None:
        cached = self._cache_get(self._chapter_metadata_cache, chapter_id)
        if cached is not None:
            return cached

        params = [("includes[]", "manga")]
        self._apply_rate_limit()
        response = self._session.get(
            f"{self._api_base}/chapter/{chapter_id}",
            params=params,
            timeout=self._request_timeout,
        )
        response.raise_for_status()

        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, dict):
            logger.warning("MangaDex metadata missing chapter data for %s", chapter_id)
            return None

        attributes = data.get("attributes", {})
        if not isinstance(attributes, dict):
            logger.warning("MangaDex metadata missing attributes for %s", chapter_id)
            return None

        chapter_number = self._safe_str(attributes.get("chapter"))
        chapter_title = self._safe_str(attributes.get("title"))
        volume = self._safe_str(attributes.get("volume"))

        chapter_label = self._build_chapter_label(chapter_number, chapter_title, volume)
        manga_title = self._extract_manga_title(data.get("relationships", [])) or "MangaDex"

        metadata = {"title": manga_title, "chapter": chapter_label}
        self._cache_set(self._chapter_metadata_cache, chapter_id, metadata)
        return metadata

    def _fetch_chapter_images(self, chapter_id: str) -> list[str]:
        cached = self._cache_get(self._chapter_images_cache, chapter_id)
        if cached is not None:
            return cached

        self._apply_rate_limit()
        response = self._session.get(
            f"{self._api_base}/at-home/server/{chapter_id}",
            timeout=self._request_timeout,
        )
        response.raise_for_status()

        payload = response.json()
        base_url = payload.get("baseUrl")
        chapter_info = payload.get("chapter")

        if not isinstance(base_url, str) or not isinstance(chapter_info, dict):
            logger.warning("MangaDex missing baseUrl or chapter info for %s", chapter_id)
            return []

        hash_value = self._safe_str(chapter_info.get("hash"))
        if not hash_value:
            logger.warning("MangaDex missing chapter hash for %s", chapter_id)
            return []

        images = self._collect_image_files(chapter_info)
        if not images:
            logger.warning("MangaDex returned no image files for %s", chapter_id)
            return []

        urls = [f"{base_url}/{path}/{hash_value}/{filename}" for path, filename in images]
        self._cache_set(self._chapter_images_cache, chapter_id, urls)
        return urls

    def _build_chapter_entry(self, entry: Any) -> dict[str, str] | None:
        if not isinstance(entry, dict):
            return None

        chapter_id = entry.get("id")
        attributes = entry.get("attributes", {})
        if not isinstance(chapter_id, str) or not isinstance(attributes, dict):
            return None

        chapter_number = self._safe_str(attributes.get("chapter"))
        chapter_title = self._safe_str(attributes.get("title"))
        volume = self._safe_str(attributes.get("volume"))

        label = self._build_chapter_label(chapter_number, chapter_title, volume)
        display_title = chapter_title or label or "Chapter"

        return {
            "title": display_title,
            "label": label or display_title,
            "url": f"{self._site_base}/chapter/{chapter_id}",
        }

    # --- Utility methods ------------------------------------------------
    def _build_series_url(self, manga_id: str) -> str:
        return f"{self._site_base}/title/{manga_id}"

    def _extract_manga_id(self, url: str) -> str | None:
        if not url:
            return None

        if _MANGA_ID_PATTERN.fullmatch(url.strip()):
            return url.strip()

        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] == "title" and _MANGA_ID_PATTERN.fullmatch(parts[1]):
            return parts[1]
        return None

    def _pick_localized_text(self, value: Any) -> str | None:
        if isinstance(value, dict):
            for language in self._languages or ("en",):
                text = value.get(language)
                if isinstance(text, str) and text.strip():
                    return text.strip()
            for text in value.values():
                if isinstance(text, str) and text.strip():
                    return text.strip()
            return None

        if isinstance(value, list):
            for item in value:
                text = self._pick_localized_text(item)
                if text:
                    return text
            return None

        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _build_search_subtitle(self, attributes: Any, relationships: Any) -> str:
        original_language = None
        status = None
        if isinstance(attributes, dict):
            original_language = self._safe_str(attributes.get("originalLanguage"))
            status = self._safe_str(attributes.get("status"))

        author = None
        if isinstance(relationships, list):
            names = self._collect_relationship_names(relationships, {"author"})
            if names:
                author = names[0]

        subtitle_parts = []
        if author:
            subtitle_parts.append(author)
        if status:
            subtitle_parts.append(status.title())
        if original_language:
            subtitle_parts.append(original_language.upper())
        return " • ".join(subtitle_parts)

    def _collect_relationship_names(self, relationships: Any, rel_types: set[str]) -> list[str]:
        if not isinstance(relationships, list):
            return []

        names: list[str] = []
        for rel in relationships:
            if not isinstance(rel, dict) or rel.get("type") not in rel_types:
                continue
            attributes = rel.get("attributes")
            if not isinstance(attributes, dict):
                continue
            name = self._safe_str(attributes.get("name"))
            if name:
                names.append(name)
        return names

    def _collect_tags(self, relationships: Any) -> list[str]:
        if not isinstance(relationships, list):
            return []

        tags: list[str] = []
        for rel in relationships:
            if not isinstance(rel, dict) or rel.get("type") != "tag":
                continue
            attributes = rel.get("attributes")
            if not isinstance(attributes, dict):
                continue
            tag_name = self._pick_localized_text(attributes.get("name"))
            if tag_name:
                tags.append(tag_name)
        return tags

    def _collect_image_files(self, chapter_info: dict[str, Any]) -> list[tuple[str, str]]:
        originals = self._filter_filenames(chapter_info.get("data"))
        if originals:
            return [("data", filename) for filename in originals]

        data_saver = self._filter_filenames(chapter_info.get("dataSaver"))
        if data_saver:
            return [("data-saver", filename) for filename in data_saver]

        return []

    def _filter_filenames(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str) and item]
        return []

    def _extract_manga_title(self, relationships: Any) -> str | None:
        if not isinstance(relationships, list):
            return None

        for rel in relationships:
            if not isinstance(rel, dict) or rel.get("type") != "manga":
                continue

            attributes = rel.get("attributes")
            if not isinstance(attributes, dict):
                continue

            title = attributes.get("title")
            selected = self._pick_localized_text(title)
            if selected:
                return selected

        return None

    def _build_chapter_label(
        self,
        chapter_number: str | None,
        chapter_title: str | None,
        volume: str | None,
    ) -> str:
        label_parts: list[str] = []
        if volume:
            label_parts.append(f"Vol. {volume}")
        if chapter_number:
            label_parts.append(f"Ch. {chapter_number}")
        if chapter_title:
            label_parts.append(chapter_title)

        if not label_parts:
            return "Chapter"

        return " - ".join(part for part in label_parts if part)

    def _safe_str(self, value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _cache_get(self, cache: dict[Any, tuple[float, Any]], key: Any) -> Any | None:
        expiry = self._cache_ttl
        now = time.monotonic()
        cached = cache.get(key)
        if cached is None:
            return None
        timestamp, value = cached
        if now - timestamp > expiry:
            cache.pop(key, None)
            return None
        return value

    def _cache_set(self, cache: dict[Any, tuple[float, Any]], key: Any, value: Any) -> None:
        if len(cache) >= self._cache_max_entries:
            cache.pop(next(iter(cache)))
        cache[key] = (time.monotonic(), value)

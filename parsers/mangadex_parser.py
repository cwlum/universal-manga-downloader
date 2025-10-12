"""Parser that leverages the MangaDex API for chapter downloads."""

from __future__ import annotations

import logging
import re

import requests  # type: ignore[import-untyped]

from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class MangaDexParser(BaseParser):
    """
    Parser for mangadex.org.
    This parser uses the MangaDex API, so it ignores the 'soup' argument.
    """

    @staticmethod
    def get_name() -> str:
        return "MangaDex"

    @staticmethod
    def can_parse(soup, url: str) -> bool:
        """Check if the URL is a MangaDex chapter URL."""
        return "mangadex.org/chapter/" in url

    @staticmethod
    def parse(soup, url: str) -> dict[str, object] | None:
        """
        Parses the page to extract manga information using the MangaDex API.
        """
        chapter_id_match = re.search(r'mangadex\.org/chapter/([a-f0-9-]+)', url)
        if not chapter_id_match:
            return None

        chapter_id = chapter_id_match.group(1)

        try:
            # --- 1. Get Chapter and Manga details ---
            chapter_api_url = f"https://api.mangadex.org/chapter/{chapter_id}"
            # We need to include the manga relationship to get the title
            params = {"includes[]": "manga"}

            response = requests.get(chapter_api_url, params=params)
            response.raise_for_status()
            chapter_data = response.json().get('data', {})

            manga_title = "Unknown Title"
            # Find the manga relationship to get the title
            for rel in chapter_data.get('relationships', []):
                if rel.get('type') == 'manga':
                    # The title is usually in 'en' or a default language
                    manga_title = rel.get('attributes', {}).get('title', {}).get('en', 'Unknown Title')
                    break

            chapter_number = chapter_data.get('attributes', {}).get('chapter', 'N/A')

            # Sanitize title and chapter for folder names
            title = MangaDexParser.sanitize_filename(manga_title)
            chapter = MangaDexParser.sanitize_filename(f"Ch_{chapter_number}")

            # --- 2. Get Image URLs ---
            image_server_url = f"https://api.mangadex.org/at-home/server/{chapter_id}"
            response = requests.get(image_server_url)
            response.raise_for_status()
            server_data = response.json()

            base_url = server_data.get('baseUrl')
            chapter_hash = server_data.get('chapter', {}).get('hash')
            image_files: list[str] = server_data.get('chapter', {}).get('data', [])  # Use 'data' for original quality

            if not all([base_url, chapter_hash, image_files]):
                logger.warning("%s missing critical image server data", MangaDexParser.get_name())
                return None

            image_urls = [f"{base_url}/data/{chapter_hash}/{filename}" for filename in image_files]

            return {
                'title': title,
                'chapter': chapter,
                'image_urls': image_urls
            }

        except requests.RequestException:
            logger.exception("%s API request failed", MangaDexParser.get_name())
            return None
        except (KeyError, IndexError, TypeError, ValueError):
            logger.exception("%s failed to parse API response", MangaDexParser.get_name())
            return None

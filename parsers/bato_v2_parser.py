"""Parser for Bato.to deployments embedding image URLs in script variables."""

from __future__ import annotations

import json
import logging
import re

from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class BatoV2Parser(BaseParser):
    """
    Parser for the newer Bato.to page structure (e.g., zbato.org)
    that uses a script tag with 'imgHttps' to store image information.
    """

    @staticmethod
    def get_name() -> str:
        return "Bato_V2"

    @staticmethod
    def can_parse(soup, url: str) -> bool:
        """Check for the presence of the 'imgHttps' script variable."""
        return soup.find('script', string=re.compile(r'const imgHttps =')) is not None

    @staticmethod
    def parse(soup, url: str) -> dict[str, object] | None:
        """Extracts data from the script tag."""
        try:
            # --- Title and Chapter ---
            title = "Manga"
            chapter = "Chapter"

            title_tag = soup.find('a', href=re.compile(r'/series/\d+'))
            if title_tag:
                title = BatoV2Parser.sanitize_filename(title_tag.text.strip())

            try:
                chapter_id = url.strip('/').split('/')[-1]
                chapter_option = soup.find('option', {'value': chapter_id})
                if chapter_option:
                    chapter = BatoV2Parser.sanitize_filename(chapter_option.text.strip())
            except (IndexError, AttributeError):
                pass  # Stick to default if parsing fails

            # --- Image URLs ---
            script_tag = soup.find('script', string=re.compile(r'const imgHttps ='))
            script_content = script_tag.string
            match = re.search(r'const imgHttps = (\[.*?\]);', script_content)

            if not match:
                return None

            json_str = match.group(1)
            image_urls: list[str] = json.loads(json_str)

            if not image_urls:
                return None

            return {
                'title': title,
                'chapter': chapter,
                'image_urls': image_urls
            }
        except (AttributeError, json.JSONDecodeError, IndexError, KeyError):
            logger.exception("%s parsing failed", BatoV2Parser.get_name())
            return None

"""Parser for the legacy Bato.to layout that embeds data in astro components."""

from __future__ import annotations

import json
import logging
import re

from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class BatoV1Parser(BaseParser):
    """
    Parser for the older Bato.to page structure that uses 'astro-island'
    to store image information.
    """

    @staticmethod
    def get_name() -> str:
        return "Bato_V1"

    @staticmethod
    def can_parse(soup, url: str) -> bool:
        """Check for the presence of the astro-island component."""
        return soup.find('astro-island', {'component-url': re.compile(r'ImageList')}) is not None

    @staticmethod
    def parse(soup, url: str) -> dict[str, object] | None:
        """Extracts data from the astro-island component."""
        try:
            # --- Title and Chapter ---
            title_tag = soup.find('a', href=re.compile(r'/title/\d+'))
            chapter_info = soup.find('h6', class_='text-lg')

            if not title_tag or not chapter_info:
                return None

            title = BatoV1Parser.sanitize_filename(title_tag.text.strip())
            chapter = BatoV1Parser.sanitize_filename(chapter_info.text.strip())

            # --- Image URLs ---
            astro_island = soup.find('astro-island', {'component-url': re.compile(r'ImageList')})
            props_str = astro_island.get('props', '{}')
            try:
                props_json = json.loads(props_str)
            except json.JSONDecodeError:
                props_json = json.loads(props_str.replace("'", '"'))
            image_files_str = props_json.get('imageFiles', [0, '[]'])[1]
            image_urls: list[str] = [img[1] for img in json.loads(image_files_str)]

            if not image_urls:
                return None

            return {
                'title': title,
                'chapter': chapter,
                'image_urls': image_urls
            }
        except (AttributeError, json.JSONDecodeError, IndexError, KeyError):
            logger.exception("%s parsing failed", BatoV1Parser.get_name())
            return None

"""Parser for comick.fun pages using embedded Next.js data payloads."""

from __future__ import annotations

import json
import logging

from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class ComickParser(BaseParser):
    """
    Parser for comick.fun.
    """

    @staticmethod
    def get_name() -> str:
        return "Comick"

    @staticmethod
    def can_parse(soup, url: str) -> bool:
        """Check if the URL is from comick.fun."""
        return "comick.fun" in url

    @staticmethod
    def parse(soup, url: str) -> dict[str, object] | None:
        """Extracts data from the page."""
        try:
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            if not script_tag:
                return None

            json_data = json.loads(script_tag.string)
            chapter_data = json_data.get('props', {}).get('pageProps', {}).get('chapter', {})

            if not chapter_data:
                return None

            title = ComickParser.sanitize_filename(chapter_data.get('md_comics', {}).get('title', ''))
            chapter = ComickParser.sanitize_filename(chapter_data.get('chap', ''))

            image_urls: list[str] = [
                f"https://meo.comick.pictures/{image.get('b2key')}"
                for image in chapter_data.get('md_images', [])
                if image.get('b2key')
            ]

            if not title or not chapter or not image_urls:
                return None

            return {
                'title': title,
                'chapter': chapter,
                'image_urls': image_urls
            }
        except (AttributeError, json.JSONDecodeError, IndexError, KeyError, TypeError):
            logger.exception("%s parsing failed", ComickParser.get_name())
            return None

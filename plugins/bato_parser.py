"""Plugin implementing support for Bato.to and Bato.si chapters."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import BasePlugin, ParsedChapter

logger = logging.getLogger(__name__)


class BatoParser(BasePlugin):
    """Parse Bato chapters rendered with Qwik."""

    _TOKEN_PATTERN = re.compile(r"^[0-9a-z]+$")

    def get_name(self) -> str:
        return "Bato"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return "bato" in host

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
        try:
            script_tag = soup.find("script", {"type": "qwik/json"})
            if not script_tag or not script_tag.string:
                return None

            data = json.loads(script_tag.string)
            objs = data.get("objs", [])
            if not isinstance(objs, list):
                return None

            cache: dict[str, Any] = {}
            chapter_state = next(
                (
                    obj
                    for obj in objs
                    if isinstance(obj, dict) and obj.get("chapterData") and obj.get("comicData")
                ),
                None,
            )
            if not isinstance(chapter_state, dict):
                return None

            chapter_data = self._resolve(chapter_state.get("chapterData"), objs, cache)
            comic_data = self._resolve(chapter_state.get("comicData"), objs, cache)

            if not isinstance(chapter_data, dict) or not isinstance(comic_data, dict):
                return None

            image_file = self._resolve(chapter_data.get("imageFile"), objs, cache)
            if isinstance(image_file, dict):
                image_urls = self._resolve(image_file.get("urlList"), objs, cache)
            else:
                image_urls = image_file

            if not isinstance(image_urls, list):
                return None

            filtered = [item for item in image_urls if isinstance(item, str) and item]
            if not filtered:
                return None

            title = comic_data.get("name") or comic_data.get("title") or "Manga"
            chapter = chapter_data.get("dname") or chapter_data.get("title") or "Chapter"

            return ParsedChapter(
                title=self.sanitize_filename(str(title)),
                chapter=self.sanitize_filename(str(chapter)),
                image_urls=filtered,
            )
        except (json.JSONDecodeError, TypeError):
            logger.exception("%s failed to parse %s", self.get_name(), url)
            return None

    def on_load(self) -> None:
        logger.info("Loaded %s parser plugin", self.get_name())

    def _resolve(self, value: Any, objs: list[Any], cache: dict[str, Any]) -> Any:
        if isinstance(value, str):
            cached = cache.get(value)
            if cached is not None:
                return cached

            if self._TOKEN_PATTERN.match(value):
                try:
                    index = int(value, 36)
                except ValueError:
                    cache[value] = value
                    return value

                if 0 <= index < len(objs):
                    resolved = objs[index]
                    if resolved == value:
                        cache[value] = resolved
                        return resolved
                    result = self._resolve(resolved, objs, cache)
                    cache[value] = result
                    return result

            cache[value] = value
            return value

        if isinstance(value, list):
            return [self._resolve(item, objs, cache) for item in value]

        if isinstance(value, dict):
            return {key: self._resolve(val, objs, cache) for key, val in value.items()}

        return value

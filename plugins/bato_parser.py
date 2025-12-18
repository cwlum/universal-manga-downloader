"""Plugin implementing support for Bato.to and Bato.si chapters."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag

from .base import BasePlugin, ParsedChapter

logger = logging.getLogger(__name__)


class BatoParser(BasePlugin):
    """Parse Bato chapters rendered with Qwik."""

    _IMG_HTTPS_PATTERN = re.compile(r"const\s+imgHttps\s*=\s*(\[[\s\S]*?\])\s*;", re.IGNORECASE)
    _TOKEN_PATTERN = re.compile(r"^[0-9a-z]+$")

    # Bato uses multiple CDN hosts for image delivery. When one host is
    # unreliable or returns errors, we can try alternative hosts.
    # The pattern is: k00.domain.org -> n00.domain.org
    # This regex matches Bato CDN hostnames like k00.mbuul.org, k05.mbxma.org, etc.
    _CDN_HOST_PATTERN = re.compile(r"^k(\d+)\.(mb[a-z]+\.org)$")

    # Known Bato mirror domain patterns for URL detection.
    # These patterns match various mirror sites that use the same Bato backend.
    _KNOWN_HOSTS: frozenset[str] = frozenset({
        # Primary domains
        "bato.to", "batoto.in", "batoto.tv", "batotoo.com", "batotwo.com",
        # Alternative domains
        "mangatoto.com", "comiko.net", "batpub.com", "batread.com", "batocomic.com",
        "readtoto.com", "kuku.to", "okok.to", "ruru.to", "xdxd.to",
    })
    # Short domain pattern: single letter + to.to (e.g., mto.to, xto.to)
    _SHORT_DOMAIN_PATTERN = re.compile(r"^[a-z]to\.to$")

    def get_name(self) -> str:
        return "Bato"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        # Match known hosts exactly
        if host in self._KNOWN_HOSTS:
            return True
        # Match bato.* pattern (e.g., bato.si, bato.ing, bato.cc)
        if host.startswith("bato."):
            return True
        # Match short domain pattern (e.g., mto.to, xto.to)
        if self._SHORT_DOMAIN_PATTERN.match(host):
            return True
        # Fallback: check if "bato" is in the host
        return "bato" in host

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
        modern_payload = self._parse_modern_script(soup)
        if modern_payload is not None:
            return modern_payload

        try:
            return self._parse_qwik_payload(soup)
        except (json.JSONDecodeError, TypeError):
            logger.exception("%s failed to parse %s", self.get_name(), url)
            return None

    def on_load(self) -> None:
        logger.info("Loaded %s parser plugin", self.get_name())

    def _parse_modern_script(self, soup: BeautifulSoup) -> ParsedChapter | None:
        for script_tag in soup.find_all("script"):
            if not isinstance(script_tag, Tag):
                continue

            content = script_tag.string or script_tag.get_text()
            if not content:
                continue

            match = self._IMG_HTTPS_PATTERN.search(content)
            if not match:
                continue

            try:
                image_urls = json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.debug("%s encountered invalid JSON in imgHttps payload", self.get_name())
                continue

            if not isinstance(image_urls, list):
                continue

            filtered = [item for item in image_urls if isinstance(item, str) and item]
            if not filtered:
                continue

            title = self._extract_js_string(content, "local_text_sub") or "Manga"
            chapter = self._extract_js_string(content, "local_text_epi") or "Chapter"

            return ParsedChapter(
                title=self.sanitize_filename(title),
                chapter=self.sanitize_filename(chapter),
                image_urls=filtered,
            )

        return None

    def _parse_qwik_payload(self, soup: BeautifulSoup) -> ParsedChapter | None:
        script_tag = soup.find("script", {"type": "qwik/json"})
        if not isinstance(script_tag, Tag):
            return None

        script_content = script_tag.string
        if script_content is None:
            return None

        data = json.loads(script_content)
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

    def _extract_js_string(self, content: str, variable_name: str) -> str | None:
        pattern = re.compile(rf"const\s+{re.escape(variable_name)}\s*=\s*(['\"])(.*?)\1\s*;", re.DOTALL)
        match = pattern.search(content)
        if match:
            return match.group(2)
        return None

    def get_image_fallback(self, failed_url: str) -> str | None:
        """Return an alternative CDN URL when a Bato image download fails.

        Bato's image servers use hostnames like k00.mbuul.org, k05.mbxma.org,
        etc. When these fail, replacing 'k' prefix with 'n' often resolves
        the issue (e.g., k00.mbuul.org -> n00.mbuul.org).

        Args:
            failed_url: The image URL that failed to download.

        Returns:
            URL with alternative CDN host, or None if no fallback available.
        """
        from urllib.parse import urlparse, urlunparse

        try:
            parsed = urlparse(failed_url)
            host = parsed.netloc.lower()

            # Check if this is a Bato CDN host (kXX.mbXXX.org pattern)
            match = self._CDN_HOST_PATTERN.match(host)
            if match:
                number = match.group(1)  # e.g., "00", "05"
                domain = match.group(2)  # e.g., "mbuul.org", "mbxma.org"

                # Replace 'k' prefix with 'n' prefix
                new_host = f"n{number}.{domain}"
                fallback_url = urlunparse(parsed._replace(netloc=new_host))

                logger.debug(
                    "Bato image fallback: %s -> %s",
                    host,
                    new_host,
                )
                return fallback_url

        except Exception:  # noqa: BLE001 - don't let fallback logic break downloads
            logger.debug("Failed to generate fallback URL for %s", failed_url)

        return None

"""Tests for MangaDex parser plugin behavior."""

from __future__ import annotations

from typing import Any

import pytest
import requests
from bs4 import BeautifulSoup

from plugins.mangadex_parser import MangaDexParser
from services.mangadex_service import MangaDexChapter


class FakeService:
    def __init__(self, chapter: MangaDexChapter | None = None, error: Exception | None = None) -> None:
        self.chapter = chapter
        self.error = error
        self.calls: list[str] = []

    def fetch_chapter(self, chapter_id: str) -> MangaDexChapter | None:
        self.calls.append(chapter_id)
        if self.error:
            raise self.error
        return self.chapter


def test_mangadex_parser_can_parse_chapter(monkeypatch: pytest.MonkeyPatch) -> None:
    chapter = MangaDexChapter(title="My Manga", chapter="Ch. 1", image_urls=["https://img/1.png"])
    parser = MangaDexParser()
    parser._service = FakeService(chapter=chapter)  # type: ignore[attr-defined]

    soup = BeautifulSoup("<html></html>", "html.parser")
    result = parser.parse(soup, "https://mangadex.org/chapter/123e4567-e89b-12d3-a456-426614174000")

    assert result is not None
    assert result["title"] == "My Manga"
    assert result["chapter"] == "Ch. 1"
    assert result["image_urls"] == ["https://img/1.png"]


def test_mangadex_parser_handles_request_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = MangaDexParser()
    parser._service = FakeService(error=requests.RequestException("boom"))  # type: ignore[attr-defined]

    soup = BeautifulSoup("<html></html>", "html.parser")
    result = parser.parse(soup, "https://mangadex.org/chapter/123e4567-e89b-12d3-a456-426614174000")

    assert result is None


def test_mangadex_parser_skips_unsupported_url() -> None:
    parser = MangaDexParser()
    soup = BeautifulSoup("<html></html>", "html.parser")

    result = parser.parse(soup, "https://mangadex.org/title/invalid")

    assert result is None


def test_mangadex_parser_can_handle_and_extract_id() -> None:
    parser = MangaDexParser()
    assert parser.can_handle("https://mangadex.org/chapter/123e4567-e89b-12d3-a456-426614174000")
    assert not parser.can_handle("https://example.com/chapter/123")
    assert parser._extract_chapter_id("https://mangadex.org/chapter/123e4567-e89b-12d3-a456-426614174000") is not None
    assert parser._extract_chapter_id("https://mangadex.org/title/123") is None

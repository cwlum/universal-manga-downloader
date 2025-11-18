"""Tests for ``BatoService`` HTML parsing helpers."""

from __future__ import annotations

from typing import Any

import pytest

from services.bato_service import BatoService


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:  # pragma: no cover - trivial
        return None


class FakeScraper:
    def __init__(self, pages: dict[int, str], series_page: str | None = None) -> None:
        self.pages = pages
        self.series_page = series_page
        self.calls: list[tuple[str, dict[str, Any] | None, float | None]] = []

    def get(self, url: str, params: dict[str, Any] | None = None, timeout: float | None = None) -> FakeResponse:
        self.calls.append((url, params, timeout))
        if params and "page" in params:
            page = int(params["page"])
            return FakeResponse(self.pages.get(page, ""))
        return FakeResponse(self.series_page or "")


def test_search_manga_parses_results(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        1: """
        <div class="item-text">
            <a class="item-title" href="/series/1"> Series One </a>
            <p class="item-subtitle"> SubOne </p>
        </div>
        <div class="item-text">
            <a class="item-title" href="/series/1"> Series One Duplicate </a>
        </div>
        """,
        2: """
        <div class="item-text">
            <a class="item-title" href="/series/2"> Series Two </a>
            <p class="item-subtitle">Latest</p>
        </div>
        """,
        3: "",  # Stops when empty
    }
    scraper = FakeScraper(pages)
    service = BatoService(scraper=scraper)
    service._rate_limit_delay = 0  # Avoid sleeps
    monkeypatch.setattr("time.sleep", lambda _: None)

    results = service.search_manga(" query ", max_pages=3)

    assert [item["title"] for item in results] == ["Series One", "Series Two"]
    assert results[0]["subtitle"] == "SubOne"
    assert results[0]["url"].endswith("/series/1")
    assert len(scraper.calls) == 3  # Stops after empty page is encountered


def test_search_manga_returns_empty_for_blank_query() -> None:
    service = BatoService(scraper=FakeScraper({}))
    assert service.search_manga("   ") == []


def test_get_series_info_extracts_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    series_html = """
    <html>
        <body>
            <h3 class="item-title">Sample Series</h3>
            <div id="limit-height-body-summary">A <b>short</b> description.</div>
            <div class="attr-item">
                <b class="text-muted">Authors:</b>
                <span><a>Author One</a></span>
            </div>
            <div class="attr-item">
                <b class="text-muted">Genres:</b>
                <span><a>Action</a><a>Comedy</a></span>
            </div>
            <a class="chapt" href="/chapter/2">
                <b>Ch 2</b><span>Title Two</span>
            </a>
            <a class="chapt" href="/chapter/1">
                <b>Ch 1</b><span>Title One</span>
            </a>
        </body>
    </html>
    """
    scraper = FakeScraper({}, series_page=series_html)
    service = BatoService(scraper=scraper)
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    result = service.get_series_info("https://bato.to/series/1")

    assert result["title"] == "Sample Series"
    assert result["description"] == "A short description."
    assert result["attributes"] == {"Authors": "Author One", "Genres": ["Action", "Comedy"]}
    chapters = result["chapters"]
    assert [chapter["label"] for chapter in chapters] == ["Ch 1", "Ch 2"]
    assert chapters[0]["url"].endswith("/chapter/1")

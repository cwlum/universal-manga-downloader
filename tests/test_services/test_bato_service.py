"""Tests for ``BatoService`` GraphQL API helpers."""

from __future__ import annotations

from typing import Any

import pytest

from services.bato_service import BatoService


class FakeResponse:
    def __init__(self, text: str = "", json_data: dict[str, Any] | None = None) -> None:
        self.text = text
        self._json_data = json_data or {}

    def raise_for_status(self) -> None:  # pragma: no cover - trivial
        return None

    def json(self) -> dict[str, Any]:
        return self._json_data


class FakeScraper:
    """Fake scraper that supports both GET and POST requests for GraphQL API testing."""

    def __init__(
        self,
        search_responses: dict[int, dict[str, Any]] | None = None,
        comic_response: dict[str, Any] | None = None,
        chapters_response: dict[str, Any] | None = None,
    ) -> None:
        self.search_responses = search_responses or {}
        self.comic_response = comic_response
        self.chapters_response = chapters_response
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self._post_call_count = 0

    def get(
        self, url: str, params: dict[str, Any] | None = None, timeout: float | None = None
    ) -> FakeResponse:
        self.calls.append(("GET", url, params))
        return FakeResponse("")

    def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> FakeResponse:
        self.calls.append(("POST", url, json))
        self._post_call_count += 1

        if json and "query" in json:
            query = json["query"]
            variables = json.get("variables", {})

            # Search query
            if "get_content_searchComic" in query:
                page = variables.get("select", {}).get("page", 1)
                response_data = self.search_responses.get(page, {"data": {"get_content_searchComic": {"items": []}}})
                return FakeResponse(json_data=response_data)

            # Comic info query
            if "get_content_comicNode" in query:
                return FakeResponse(json_data=self.comic_response or {"data": {"get_content_comicNode": {}}})

            # Chapter list query
            if "get_content_chapterList" in query:
                return FakeResponse(json_data=self.chapters_response or {"data": {"get_content_chapterList": []}})

        return FakeResponse(json_data={"data": {}})


def test_search_manga_parses_results(monkeypatch: pytest.MonkeyPatch) -> None:
    search_responses = {
        1: {
            "data": {
                "get_content_searchComic": {
                    "reqWord": "query",
                    "reqPage": 1,
                    "paging": {"pages": 2, "page": 1},
                    "items": [
                        {"id": "1", "data": {"id": "1", "slug": "series-one", "name": "Series One", "urlPath": "/title/1-series-one"}},
                        {"id": "2", "data": {"id": "2", "slug": "series-one-dup", "name": "Series One Duplicate", "urlPath": "/title/1-series-one"}},
                    ],
                }
            }
        },
        2: {
            "data": {
                "get_content_searchComic": {
                    "reqWord": "query",
                    "reqPage": 2,
                    "paging": {"pages": 2, "page": 2},
                    "items": [
                        {"id": "3", "data": {"id": "3", "slug": "series-two", "name": "Series Two", "urlPath": "/title/2-series-two"}},
                    ],
                }
            }
        },
        3: {
            "data": {
                "get_content_searchComic": {
                    "items": [],
                }
            }
        },
    }
    scraper = FakeScraper(search_responses=search_responses)
    service = BatoService(scraper=scraper)
    service._rate_limit_delay = 0  # Avoid sleeps
    monkeypatch.setattr("time.sleep", lambda _: None)

    results = service.search_manga(" query ", max_pages=3)

    assert len(results) == 2  # Deduped by URL
    assert results[0]["title"] == "Series One"
    assert results[1]["title"] == "Series Two"
    assert "/title/1-series-one" in results[0]["url"]


def test_search_manga_returns_empty_for_blank_query() -> None:
    service = BatoService(scraper=FakeScraper())
    assert service.search_manga("   ") == []


def test_get_series_info_extracts_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    comic_response = {
        "data": {
            "get_content_comicNode": {
                "data": {
                    "id": "12345",
                    "slug": "sample-series",
                    "name": "Sample Series",
                    "urlPath": "/title/12345-sample-series",
                    "authors": ["Author One"],
                    "genres": ["Action", "Comedy"],
                    "summary": {"code": "A short description."},
                }
            }
        }
    }
    chapters_response = {
        "data": {
            "get_content_chapterList": [
                {"id": "ch2", "data": {"id": "ch2", "urlPath": "/chapter/2", "dname": "Ch 2 Title Two"}},
                {"id": "ch1", "data": {"id": "ch1", "urlPath": "/chapter/1", "dname": "Ch 1 Title One"}},
            ]
        }
    }
    scraper = FakeScraper(comic_response=comic_response, chapters_response=chapters_response)
    service = BatoService(scraper=scraper)
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    result = service.get_series_info("https://bato.to/title/12345-sample-series")

    assert result["title"] == "Sample Series"
    assert result["description"] == "A short description."
    assert result["attributes"] == {"Authors": ["Author One"], "Genres": ["Action", "Comedy"]}
    chapters = result["chapters"]
    assert isinstance(chapters, list)
    assert len(chapters) == 2
    assert chapters[0]["title"] == "Ch 2 Title Two"
    assert chapters[1]["title"] == "Ch 1 Title One"


def test_get_series_info_invalid_url() -> None:
    scraper = FakeScraper()
    service = BatoService(scraper=scraper)

    with pytest.raises(ValueError, match="Cannot extract comic ID"):
        service.get_series_info("https://bato.to/series/invalid")

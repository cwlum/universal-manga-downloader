"""Tests for MangaDexService behaviors and parsing."""

from __future__ import annotations

import time
from typing import Any

import pytest

from services.mangadex_service import MangaDexChapter, MangaDexService


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def json(self) -> Any:  # pragma: no cover - trivial passthrough
        return self._payload

    def raise_for_status(self) -> None:  # pragma: no cover - trivial
        return None


class FakeSession:
    def __init__(self, payloads: list[Any]) -> None:
        self.payloads = list(payloads)
        self.calls: list[tuple[str, Any, Any]] = []
        self.proxies: dict[str, str] = {}
        self.trust_env = True

    def get(self, url: str, params: Any | None = None, timeout: Any | None = None) -> FakeResponse:
        self.calls.append((url, params, timeout))
        if not self.payloads:
            raise AssertionError(f"No payload available for {url}")
        return FakeResponse(self.payloads.pop(0))


def _service_with_payloads(payloads: list[Any]) -> MangaDexService:
    return MangaDexService(session=FakeSession(payloads))


def test_mangadex_service_uses_configured_session(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = FakeSession([])
    calls: list[FakeSession | None] = []

    def fake_configure(session=None):
        calls.append(session)
        return sentinel

    monkeypatch.setattr("services.mangadex_service.configure_requests_session", fake_configure)

    service = MangaDexService()

    assert service._session is sentinel  # type: ignore[attr-defined]
    assert len(calls) == 1


def test_search_manga_returns_results(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = [
        {
            "data": [
                {
                    "id": "abc123",
                    "attributes": {
                        "title": {"en": "Manga Title"},
                        "originalLanguage": "ja",
                        "status": "ongoing",
                    },
                    "relationships": [
                        {"type": "author", "attributes": {"name": "Author One"}},
                        {"type": "cover_art", "attributes": {"fileName": "cover.jpg"}},
                    ],
                }
            ]
        }
    ]
    service = _service_with_payloads(payloads)
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    results = service.search_manga("  my title  ", limit=5)

    assert results == [
        {
            "title": "Manga Title",
            "url": "https://mangadex.org/title/abc123",
            "subtitle": "Author One • Ongoing • JA",
            "provider": "MangaDex",
        }
    ]
    session = service._session  # type: ignore[attr-defined]
    assert len(session.calls) == 1
    called_params = session.calls[0][1]
    assert ("limit", "5") in called_params


def test_search_manga_blank_returns_empty() -> None:
    service = _service_with_payloads([])
    assert service.search_manga("   ") == []
    session = service._session  # type: ignore[attr-defined]
    assert getattr(session, "calls", []) == []


def test_search_manga_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads: list[dict[str, list[object]]] = [{"data": []}]
    service = _service_with_payloads(payloads)
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    service.search_manga("title", limit=1)
    service.search_manga("title", limit=1)

    session = service._session  # type: ignore[attr-defined]
    assert len(session.calls) == 1


def test_get_series_info_parses_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    manga_payload = {
        "data": {
            "id": "series-id",
            "attributes": {
                "title": {"en": "Series Title"},
                "description": {"en": "An epic description"},
                "status": "completed",
                "originalLanguage": "en",
                "contentRating": "safe",
                "year": 2024,
            },
            "relationships": [
                {"type": "author", "attributes": {"name": "Author One"}},
                {"type": "artist", "attributes": {"name": "Artist One"}},
                {"type": "tag", "attributes": {"name": {"en": "Action"}}},
                {"type": "tag", "attributes": {"name": {"en": "Comedy"}}},
            ],
        }
    }
    chapter_payload = {
        "data": [
            {
                "id": "chap-1",
                "attributes": {"chapter": "1", "title": "Start", "volume": "2"},
            }
        ],
        "total": 1,
    }
    service = _service_with_payloads([manga_payload, chapter_payload])
    service._rate_limit_delay = 0
    service._max_chapter_pages = 1
    monkeypatch.setattr("time.sleep", lambda _: None)

    info = service.get_series_info("https://mangadex.org/title/123e4567-e89b-12d3-a456-426614174000/foo")

    assert info["title"] == "Series Title"
    assert info["description"] == "An epic description"
    attributes = info["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["Author(s)"] == ["Author One"]
    assert attributes["Artist(s)"] == ["Artist One"]
    assert attributes["Tags"] == ["Action", "Comedy"]
    assert attributes["Status"] == "Completed"
    assert attributes["Original Language"] == "en"
    assert attributes["Year"] == 2024

    chapters = info["chapters"]
    assert isinstance(chapters, list) and len(chapters) > 0
    assert chapters[0]["title"] == "Start"
    assert chapters[0]["label"] == "Vol. 2 - Ch. 1 - Start"
    assert chapters[0]["url"].endswith("/chap-1")

    second = service.get_series_info("https://mangadex.org/title/123e4567-e89b-12d3-a456-426614174000/foo")
    assert second["title"] == "Series Title"
    session = service._session  # type: ignore[attr-defined]
    assert len(session.calls) == 2  # manga + chapters once


def test_fetch_chapter_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata_payload = {
        "data": {
            "id": "chap-99",
            "attributes": {"chapter": "10", "title": "Ten", "volume": "1"},
            "relationships": [
                {"type": "manga", "attributes": {"title": {"en": "Series Title"}}},
            ],
        }
    }
    images_payload = {
        "baseUrl": "https://server.cdn",
        "chapter": {
            "hash": "abc123",
            "data": ["a.png", "b.png"],
            "dataSaver": ["c.png"],
        },
    }

    service = _service_with_payloads([metadata_payload, images_payload])
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    chapter = service.fetch_chapter("chap-99")

    assert isinstance(chapter, MangaDexChapter)
    assert chapter.title == "Series Title"
    assert chapter.chapter == "Vol. 1 - Ch. 10 - Ten"
    assert chapter.image_urls == [
        "https://server.cdn/data/abc123/a.png",
        "https://server.cdn/data/abc123/b.png",
    ]


def test_fetch_chapter_missing_payload_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_payloads(
        [
            {"data": None},  # metadata missing
            {"chapter": {}, "baseUrl": ""},  # images missing, should not be used
        ]
    )
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert service.fetch_chapter("invalid") is None


def test_fetch_chapter_metadata_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_payloads([{"data": None}])
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert service._fetch_chapter_metadata("missing") is None


def test_fetch_chapter_metadata_missing_attributes(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_payloads([{"data": {"attributes": None}}])
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert service._fetch_chapter_metadata("missing-attrs") is None


def test_fetch_chapter_images_missing_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_payloads([{"baseUrl": "", "chapter": {}}])
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert service._fetch_chapter_images("chap-1") == []


def test_fetch_chapter_images_missing_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"baseUrl": "https://cdn", "chapter": {"hash": "", "data": ["a.png"]}}
    service = _service_with_payloads([payload])
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert service._fetch_chapter_images("chap-1") == []


def test_fetch_chapter_list_handles_non_list(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_payloads([{"data": None}])
    service._max_chapter_pages = 1
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert service._fetch_chapter_list("series-id") == []
    assert service._fetch_chapter_list("series-id") == []  # cached


def test_fetch_chapter_list_stops_on_short_page(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_payloads([{"data": [], "total": 500}])
    service._max_chapter_pages = 1
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert service._fetch_chapter_list("series-id") == []
    assert service._fetch_chapter_list("series-id") == []  # cached


def test_collect_image_files_prefers_data_saver() -> None:
    service = _service_with_payloads([])
    images = service._collect_image_files({"data": [], "dataSaver": ["a.jpg", ""]})
    assert images == [("data-saver", "a.jpg")]


def test_collect_image_files_returns_empty_when_missing() -> None:
    service = _service_with_payloads([])
    assert service._collect_image_files({}) == []
    assert service._filter_filenames("not-a-list") == []
    assert service._collect_image_files({"data": [], "dataSaver": []}) == []


def test_pick_localized_text_list_and_fallbacks() -> None:
    service = _service_with_payloads([])
    text = service._pick_localized_text([{"en": ""}, {"ja": "こんにちは"}])
    assert text == "こんにちは"
    assert service._pick_localized_text(" Title ") == "Title"
    assert service._pick_localized_text({}) is None
    assert service._pick_localized_text(["", {}]) is None


def test_extract_manga_title_and_label_helpers() -> None:
    service = _service_with_payloads([])
    title = service._extract_manga_title(
        [{"type": "manga", "attributes": {"title": {"en": "Title EN", "fr": "Titre FR"}}}]
    )
    assert title == "Title EN"
    assert service._build_chapter_label(None, None, None) == "Chapter"
    assert service._build_chapter_label("1", None, "2") == "Vol. 2 - Ch. 1"
    assert service._build_chapter_entry("invalid") is None
    assert service._build_chapter_entry({"id": None, "attributes": {}}) is None


def test_apply_rate_limit_sleeps_when_recent(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_payloads([])
    service._last_request_time = time.time()
    service._rate_limit_delay = 0.1
    called = {"sleep": 0.0}

    def fake_sleep(seconds: float) -> None:
        called["sleep"] = seconds

    monkeypatch.setattr("time.sleep", fake_sleep)
    service._apply_rate_limit()
    assert called["sleep"] > 0
    # Cache helper uses monotonic timestamps; ensure expiry clears entries.
    service._cache_set(service._search_cache, ("k", 1), ["v"])  # type: ignore[arg-type]
    service._cache_ttl = -1
    assert service._cache_get(service._search_cache, ("k", 1)) is None


def test_extract_manga_id_variants() -> None:
    service = _service_with_payloads([])
    assert service._extract_manga_id("a1b2c3d4-e5f6-7890-ab12-abcdefabcdef") == "a1b2c3d4-e5f6-7890-ab12-abcdefabcdef"
    assert (
        service._extract_manga_id("https://mangadex.org/title/a1b2c3d4-e5f6-7890-ab12-abcdefabcdef")
        == "a1b2c3d4-e5f6-7890-ab12-abcdefabcdef"
    )
    assert service._extract_manga_id("https://example.com/not-manga") is None
    assert service._extract_manga_id("") is None


def test_build_search_subtitle_and_tags_helpers() -> None:
    service = _service_with_payloads([])
    subtitle = service._build_search_subtitle({"originalLanguage": "en", "status": "completed"}, [])
    assert subtitle == "Completed • EN"
    assert service._collect_relationship_names(None, {"author"}) == []
    assert service._collect_relationship_names([{"type": "author", "attributes": None}], {"author"}) == []
    assert service._collect_tags(None) == []
    assert service._collect_tags([{"type": "tag", "attributes": None}]) == []
    assert service._collect_tags([{"type": "other"}]) == []


def test_search_manga_handles_non_list_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_payloads([{"data": "oops"}])
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert service.search_manga("query") == []


def test_fetch_manga_payload_raises_on_unexpected(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_payloads([{"data": None}])
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    with pytest.raises(ValueError):
        service._fetch_manga_payload("123e4567-e89b-12d3-a456-426614174000")


def test_fetch_chapter_returns_none_for_missing_images(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata_payload = {
        "data": {
            "id": "chap-99",
            "attributes": {"chapter": "10", "title": "Ten", "volume": "1"},
            "relationships": [{"type": "manga", "attributes": {"title": {"en": "Series Title"}}}],
        }
    }
    service = _service_with_payloads(
        [
            metadata_payload,
            {"baseUrl": "https://cdn", "chapter": {"hash": "abc123", "data": []}},
        ]
    )
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert service.fetch_chapter("chap-99") is None
    session = service._session  # type: ignore[attr-defined]
    assert len(session.calls) == 2  # metadata + images once


def test_fetch_chapter_uses_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata_payload = {
        "data": {
            "id": "chap-50",
            "attributes": {"chapter": "5", "title": "Five", "volume": "1"},
            "relationships": [{"type": "manga", "attributes": {"title": {"en": "Series Title"}}}],
        }
    }
    images_payload = {
        "baseUrl": "https://cdn",
        "chapter": {"hash": "hash", "data": ["a.png"], "dataSaver": ["b.png"]},
    }
    service = _service_with_payloads([metadata_payload, images_payload])
    service._rate_limit_delay = 0
    monkeypatch.setattr("time.sleep", lambda _: None)

    result = service.fetch_chapter("chap-50")
    assert result is not None
    # Second call should be served from caches.
    second = service.fetch_chapter("chap-50")
    assert second is not None
    session = service._session  # type: ignore[attr-defined]
    assert len(session.calls) == 2

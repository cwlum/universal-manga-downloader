"""Tests for HTTP client helpers."""

from __future__ import annotations

from utils import http_client


class DummyScraper:
    def __init__(self) -> None:
        self.proxies: dict[str, str] = {}
        self.trust_env = True

    def close(self) -> None:  # pragma: no cover - not exercised here
        return None


def test_create_scraper_session_sanitizes_ipv6_proxy(monkeypatch) -> None:
    created: list[DummyScraper] = []

    def factory() -> DummyScraper:
        scraper = DummyScraper()
        created.append(scraper)
        return scraper

    monkeypatch.setattr(http_client.cloudscraper, "create_scraper", factory)
    monkeypatch.setattr(
        http_client.requests.utils,
        "get_environ_proxies",
        lambda _url: {"http": "http://::1:6152", "https": "http://::1:6152"},
    )

    scraper = http_client.create_scraper_session()

    assert scraper.trust_env is False
    assert scraper.proxies["http"] == "http://[::1]:6152"
    assert scraper.proxies["https"] == "http://[::1]:6152"
    assert len(created) == 1


def test_create_scraper_session_ignores_invalid_proxy(monkeypatch) -> None:
    def factory() -> DummyScraper:
        return DummyScraper()

    monkeypatch.setattr(http_client.cloudscraper, "create_scraper", factory)
    monkeypatch.setattr(
        http_client.requests.utils,
        "get_environ_proxies",
        lambda _url: {"http": "not a url"},
    )

    scraper = http_client.create_scraper_session()

    assert scraper.trust_env is False
    assert scraper.proxies == {}


def test_configure_requests_session_applies_sanitized_proxy(monkeypatch) -> None:
    class DummySession:
        def __init__(self) -> None:
            self.proxies: dict[str, str] = {}
            self.trust_env = True

    monkeypatch.setattr(
        http_client,
        "get_sanitized_proxies",
        lambda: {"http": "http://[::1]:6152"},
    )

    session = DummySession()
    configured = http_client.configure_requests_session(session)  # type: ignore[arg-type]

    assert configured is session
    assert session.trust_env is False
    assert session.proxies["http"] == "http://[::1]:6152"


def test_configure_requests_session_creates_session_when_missing(monkeypatch) -> None:
    created: list[object] = []

    class DummySession:
        def __init__(self) -> None:
            self.proxies: dict[str, str] = {}
            self.trust_env = True
            created.append(self)

    monkeypatch.setattr(http_client.requests, "Session", DummySession)
    monkeypatch.setattr(http_client, "get_sanitized_proxies", lambda: {})

    configured = http_client.configure_requests_session()

    assert isinstance(configured, DummySession)
    assert configured.trust_env is False
    assert configured.proxies == {}
    assert len(created) == 1

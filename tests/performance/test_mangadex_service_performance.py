from __future__ import annotations

import time

import pytest

from services.mangadex_service import MangaDexService


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:  # pragma: no cover - trivial
        return self._payload

    def raise_for_status(self) -> None:  # pragma: no cover - trivial
        return None


class FakeSession:
    def __init__(self, payloads: list[object]) -> None:
        self.payloads = list(payloads)
        self.calls: list[tuple[str, object | None, object | None]] = []
        self.proxies: dict[str, str] = {}
        self.trust_env = True

    def get(self, url: str, params: object | None = None, timeout: object | None = None) -> FakeResponse:
        self.calls.append((url, params, timeout))
        if not self.payloads:
            raise AssertionError(f"No payload available for {url}")
        return FakeResponse(self.payloads.pop(0))


@pytest.mark.performance
def test_mangadex_search_caching_performance() -> None:
    payloads: list[object] = [
        {"data": []},  # First request
    ]
    service = MangaDexService(session=FakeSession(payloads))
    service._rate_limit_delay = 0

    start = time.perf_counter()
    for _ in range(300):
        service.search_manga("title", limit=5)
    elapsed = time.perf_counter() - start

    # First call uses the network; subsequent calls should hit cache and remain fast.
    session = service._session  # type: ignore[attr-defined]
    assert len(session.calls) == 1
    assert elapsed < 0.5, f"Caching path too slow: {elapsed:.3f}s"

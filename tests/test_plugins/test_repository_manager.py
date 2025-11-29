from __future__ import annotations

import json
from pathlib import Path

import pytest

from plugins.repository_manager import RepositoryManager


class DummyResponse:
    def __init__(self, data: str) -> None:
        self._payload = data.encode("utf-8")

    def read(self) -> bytes:  # pragma: no cover - trivial
        return self._payload

    def __enter__(self) -> DummyResponse:  # pragma: no cover
        return self

    def __exit__(self, *_: object) -> None:  # pragma: no cover
        return None


def test_repository_sync_and_search(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload = json.dumps(
        {
            "plugins": [
                {
                    "id": "example_remote_parser",
                    "name": "Example Remote Parser",
                    "type": "parser",
                    "author": "Tester",
                    "version": "1.0.0",
                    "description": "Parses test sites",
                    "source_url": "https://raw.githubusercontent.com/org/repo/parser.py",
                    "repository": "https://github.com/org/repo",
                    "license": "MIT",
                    "tags": ["test"],
                    "dependencies": [],
                    "checksum": "sha256:123",
                    "downloads": 42,
                    "rating": 4.5,
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-02T00:00:00Z",
                },
                {
                    "id": "example_converter",
                    "name": "Example Converter",
                    "type": "converter",
                    "author": "Tester",
                    "version": "0.3.0",
                    "description": "Converts stuff",
                    "source_url": "https://raw.githubusercontent.com/org/repo/converter.py",
                    "repository": "https://github.com/org/repo",
                    "license": "MIT",
                    "tags": ["convert"],
                    "dependencies": ["ebooklib>=0.18"],
                    "checksum": "sha256:456",
                    "downloads": 7,
                    "rating": 5.0,
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-05T00:00:00Z",
                },
            ]
        }
    )

    monkeypatch.setattr("plugins.repository_manager.urlopen", lambda _url, timeout=30: DummyResponse(payload))

    data_dir = tmp_path / "plugins"
    manager = RepositoryManager(data_dir)

    ok, message = manager.sync()
    assert ok, message
    assert len(manager.cache) == 2
    assert manager.last_sync is not None

    search_results = manager.search(query="Parser")
    assert search_results and search_results[0].name == "Example Remote Parser"

    converters = manager.search(plugin_type="converter")
    assert len(converters) == 1
    assert converters[0].id == "example_converter"


def test_repository_add_remove(tmp_path: Path) -> None:
    manager = RepositoryManager(tmp_path / "plugins")
    ok, message = manager.add_repository("https://example.com/index.json")
    assert ok, message
    assert "https://example.com/index.json" in manager.list_repositories()
    ok, message = manager.remove_repository("https://example.com/index.json")
    assert ok, message

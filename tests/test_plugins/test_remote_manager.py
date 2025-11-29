from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from plugins.remote_manager import RemotePluginManager

PLUGIN_CODE = """from __future__ import annotations\n\nfrom plugins.base import BasePlugin, ParsedChapter\n\nclass RemoteSampleParser(BasePlugin):\n    def get_name(self) -> str:\n        return \"RemoteSample\"\n\n    def can_handle(self, url: str) -> bool:\n        return \"remote-sample\" in url\n\n    def parse(self, soup, url: str) -> ParsedChapter | None:  # pragma: no cover - demo plugin\n        return None\n"""


class DummyResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> DummyResponse:  # pragma: no cover - trivial
        return self

    def __exit__(self, *_: object) -> None:  # pragma: no cover - trivial
        return None


def _mock_urlopen(payload: str) -> Callable[[str, int], DummyResponse]:
    def _open(_url: str, timeout: int = 30) -> DummyResponse:  # pragma: no cover - simple lambda
        return DummyResponse(payload)

    return _open


def test_install_remote_plugin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path)
    monkeypatch.setattr("plugins.remote_manager.urlopen", _mock_urlopen(PLUGIN_CODE))
    success, message = manager.install_from_url(
        "https://raw.githubusercontent.com/org/repo/main/remote_sample.py"
    )
    assert success, message
    registry = manager.list_installed()
    assert registry and registry[0]["name"] == "RemoteSampleParser"
    assert (tmp_path / "remote_sample.py").exists()


def test_install_rejects_invalid_url(tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path)
    success, message = manager.install_from_url("https://example.com/plugin.py")
    assert not success
    assert "raw.githubusercontent.com" in message


def test_uninstall_removes_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path)
    monkeypatch.setattr("plugins.remote_manager.urlopen", _mock_urlopen(PLUGIN_CODE))
    success, _ = manager.install_from_url(
        "https://raw.githubusercontent.com/org/repo/main/remote_sample.py"
    )
    assert success
    success, _ = manager.uninstall("RemoteSampleParser")
    assert success
    assert manager.list_installed() == []
    assert not (tmp_path / "remote_sample.py").exists()

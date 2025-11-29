from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from plugins.remote_manager import RemotePluginManager

PLUGIN_CODE = '''"""
Universal Manga Downloader Plugin

Name: Remote Sample Parser
Author: Test Author
Version: 1.2.3
Description: Example remote parser for tests.
Repository: https://github.com/example/repo
License: MIT
Dependencies: Pillow>=10
"""

from __future__ import annotations

from plugins.base import BasePlugin, ParsedChapter


class RemoteSampleParser(BasePlugin):
    def get_name(self) -> str:
        return "RemoteSample"

    def can_handle(self, url: str) -> bool:
        return "remote-sample" in url

    def parse(self, soup, url: str) -> ParsedChapter | None:  # pragma: no cover - demo plugin
        return None
'''


UPDATED_PLUGIN_CODE = PLUGIN_CODE.replace("Version: 1.2.3", "Version: 2.0.0")

PACKAGE_PLUGIN_CODE = '''"""
Universal Manga Downloader Plugin

Name: Remote Package Parser
Author: Zip Test
Version: 0.5.0
Description: Example multi-file parser.
Dependencies: requests>=2.0.0
"""

from __future__ import annotations

from plugins.base import BasePlugin, ParsedChapter


class RemotePackageParser(BasePlugin):
    def get_name(self) -> str:
        return "RemotePackage"

    def can_handle(self, url: str) -> bool:
        return url.endswith("/zip")

    def parse(self, soup, url: str) -> ParsedChapter | None:  # pragma: no cover - example
        return None
'''


class DummyResponse:
    def __init__(self, payload: str | bytes) -> None:
        self._payload = payload if isinstance(payload, bytes) else payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> DummyResponse:  # pragma: no cover - trivial
        return self

    def __exit__(self, *_: object) -> None:  # pragma: no cover - trivial
        return None


def _mock_urlopen(payload: str | bytes) -> Callable[[str, int], DummyResponse]:
    def _open(_url: str, timeout: int = 30) -> DummyResponse:  # pragma: no cover - simple lambda
        return DummyResponse(payload)

    return _open


class SequentialOpener:
    def __init__(self, payloads: list[str]) -> None:
        self._payloads = payloads
        self._cursor = 0

    def __call__(self, _url: str, timeout: int = 30) -> DummyResponse:  # pragma: no cover - deterministic
        if self._cursor >= len(self._payloads):
            payload = self._payloads[-1]
        else:
            payload = self._payloads[self._cursor]
        self._cursor += 1
        return DummyResponse(payload)


def _build_zip_payload() -> bytes:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("remote_package/__init__.py", PACKAGE_PLUGIN_CODE)
        archive.writestr("remote_package/utils.py", "HELPER = True")
    return buffer.getvalue()


def test_prepare_and_commit_remote_plugin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path, allowed_sources=["https://raw.githubusercontent.com/org/repo/"])
    monkeypatch.setattr("plugins.remote_manager.urlopen", _mock_urlopen(PLUGIN_CODE))
    ok, prepared, message = manager.prepare_install(
        "https://raw.githubusercontent.com/org/repo/main/remote_sample.py"
    )
    assert ok, message
    assert prepared is not None
    assert prepared.metadata["name"] == "Remote Sample Parser"
    ok, message = manager.commit_install(prepared)
    assert ok, message
    registry = manager.list_installed()
    assert registry and registry[0]["display_name"] == "Remote Sample Parser"
    assert registry[0]["version"] == "1.2.3"
    assert registry[0]["dependencies"] == ["Pillow>=10"]
    assert (tmp_path / "remote_sample.py").exists()
    assert registry[0]["artifact_type"] == "file"


def test_install_rejects_invalid_url(tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path)
    success, message = manager.install_from_url("https://example.com/plugin.py")
    assert not success
    assert "raw.githubusercontent.com" in message


def test_uninstall_removes_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path, allowed_sources=["https://raw.githubusercontent.com/org/repo/"])
    monkeypatch.setattr("plugins.remote_manager.urlopen", _mock_urlopen(PLUGIN_CODE))
    success, _ = manager.install_from_url(
        "https://raw.githubusercontent.com/org/repo/main/remote_sample.py"
    )
    assert success
    success, _ = manager.uninstall("RemoteSampleParser")
    assert success
    assert manager.list_installed() == []
    assert not (tmp_path / "remote_sample.py").exists()


def test_disallows_unapproved_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path)
    monkeypatch.setattr("plugins.remote_manager.urlopen", _mock_urlopen(PLUGIN_CODE))
    success, _, message = manager.prepare_install(
        "https://raw.githubusercontent.com/other/repo/main/remote_sample.py"
    )
    assert not success
    assert "白名单" in message


def test_whitelist_management(tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path)
    success, message = manager.add_allowed_source("https://raw.githubusercontent.com/org/repo")
    assert success, message
    assert any(prefix.startswith("https://raw.githubusercontent.com/org/repo") for prefix in manager.list_allowed_sources())
    success, message = manager.remove_allowed_source("https://raw.githubusercontent.com/umd-plugins/official/")
    assert not success  # default source cannot be removed


def test_check_updates_and_update(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path, allowed_sources=["https://raw.githubusercontent.com/org/repo/"])
    opener = SequentialOpener([PLUGIN_CODE, UPDATED_PLUGIN_CODE, UPDATED_PLUGIN_CODE])
    monkeypatch.setattr("plugins.remote_manager.urlopen", opener)

    ok, prepared, _ = manager.prepare_install("https://raw.githubusercontent.com/org/repo/main/remote_sample.py")
    assert ok and prepared
    ok, _ = manager.commit_install(prepared)
    assert ok

    updates = manager.check_updates()
    assert updates and updates[0]["latest"] == "2.0.0"

    success, message = manager.update_plugin("RemoteSampleParser")
    assert success, message
    record = manager.get_record("RemoteSampleParser")
    assert record is not None
    assert record["version"] == "2.0.0"


def test_history_and_rollback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path, allowed_sources=["https://raw.githubusercontent.com/org/repo/"])
    opener = SequentialOpener([PLUGIN_CODE, UPDATED_PLUGIN_CODE, UPDATED_PLUGIN_CODE])
    monkeypatch.setattr("plugins.remote_manager.urlopen", opener)

    ok, prepared, _ = manager.prepare_install("https://raw.githubusercontent.com/org/repo/main/remote_sample.py")
    assert ok and prepared
    ok, _ = manager.commit_install(prepared)
    assert ok

    ok, msg = manager.update_plugin("RemoteSampleParser")
    assert ok, msg

    history = manager.list_history("RemoteSampleParser")
    assert history
    assert history[0]["version"] == "1.2.3"
    snapshot_path = Path(history[0]["file_path"])
    assert snapshot_path.exists()

    success, message = manager.rollback_plugin("RemoteSampleParser", version="1.2.3")
    assert success, message
    record = manager.get_record("RemoteSampleParser")
    assert record is not None
    assert record["version"] == "1.2.3"
    assert record["history"]
    assert record["history"][0]["version"] == "2.0.0"


def test_install_zip_plugin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = RemotePluginManager(tmp_path, allowed_sources=["https://raw.githubusercontent.com/org/repo/"])
    zip_payload = _build_zip_payload()
    monkeypatch.setattr("plugins.remote_manager.urlopen", _mock_urlopen(zip_payload))

    success, message = manager.install_from_url("https://raw.githubusercontent.com/org/repo/main/remote_package.zip")
    assert success, message
    record = manager.get_record("RemotePackageParser")
    assert record is not None
    assert record["artifact_type"] == "package"
    plugin_dir = Path(record["file_path"])
    assert plugin_dir.is_dir()
    assert (plugin_dir / "__init__.py").exists()

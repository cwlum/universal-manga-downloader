"""CLI tests for remote plugin subcommands."""

from __future__ import annotations

from types import SimpleNamespace

import umd_cli


class StubManager:
    def __init__(self) -> None:
        self.prepare_calls: list[str] = []
        self.replace_flags: list[bool] = []
        self.history_calls: list[str] = []
        self.rollback_calls: list[tuple[str, str | None, str | None]] = []

    # --- helpers used by tests ---
    def list_installed(self) -> list[dict[str, str]]:
        return [
            {
                "name": "RemoteSampleParser",
                "display_name": "Remote Sample Parser",
                "plugin_type": "parser",
                "version": "1.2.3",
                "source_url": "https://raw.githubusercontent.com/org/repo/main/plugin.py",
            }
        ]

    def prepare_install(self, url: str):  # pragma: no cover - trivial tuple
        self.prepare_calls.append(url)
        return True, SimpleNamespace(), "ready"

    def commit_install(self, _prepared: object, replace_existing: bool = False):  # pragma: no cover - trivial tuple
        self.replace_flags.append(replace_existing)
        return True, "installed"


def test_cli_plugins_list(monkeypatch, capsys) -> None:
    stub = StubManager()
    monkeypatch.setattr(umd_cli, "_get_remote_plugin_manager", lambda: stub)

    result = umd_cli.main(["plugins", "list"])

    assert result == 0
    captured = capsys.readouterr().out
    assert "Remote Sample Parser" in captured


def test_cli_plugins_install_supports_force(monkeypatch) -> None:
    stub = StubManager()
    monkeypatch.setattr(umd_cli, "_get_remote_plugin_manager", lambda: stub)

    result = umd_cli.main(
        [
            "plugins",
            "install",
            "--force",
            "https://raw.githubusercontent.com/org/repo/main/remote_sample.py",
        ]
    )

    assert result == 0
    assert stub.prepare_calls == ["https://raw.githubusercontent.com/org/repo/main/remote_sample.py"]
    assert stub.replace_flags == [True]

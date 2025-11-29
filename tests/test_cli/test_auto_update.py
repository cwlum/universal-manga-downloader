"""Tests for the auto-update helpers."""

from __future__ import annotations

from types import SimpleNamespace

import umd_cli


def test_build_update_environment_strips_invalid_proxy(monkeypatch) -> None:
    monkeypatch.setattr(umd_cli, "get_sanitized_proxies", lambda: {})

    env = umd_cli._build_update_environment({"http_proxy": "http://::1:6152", "KEEP": "1"})

    assert "http_proxy" not in env
    assert "HTTP_PROXY" not in env
    assert env["KEEP"] == "1"


def test_build_update_environment_injects_sanitized_proxy(monkeypatch) -> None:
    monkeypatch.setattr(
        umd_cli,
        "get_sanitized_proxies",
        lambda: {"http": "http://[::1]:6152", "https": "http://[::1]:7000"},
    )

    env = umd_cli._build_update_environment({})

    assert env["http_proxy"] == "http://[::1]:6152"
    assert env["HTTP_PROXY"] == "http://[::1]:6152"
    assert env["https_proxy"] == "http://[::1]:7000"
    assert env["HTTPS_PROXY"] == "http://[::1]:7000"


def test_run_auto_update_uses_sanitized_environment(monkeypatch) -> None:
    monkeypatch.setattr(umd_cli, "_build_update_command", lambda _pkg: ["true"])
    monkeypatch.setattr(
        umd_cli,
        "get_sanitized_proxies",
        lambda: {"http": "http://[::1]:6152"},
    )

    captured: dict[str, str] = {}

    def fake_run(cmd, check, env):  # type: ignore[unused-argument]
        captured.update(env)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(umd_cli.subprocess, "run", fake_run)

    assert umd_cli.run_auto_update() is True
    assert captured["http_proxy"] == "http://[::1]:6152"
    assert captured["HTTP_PROXY"] == "http://[::1]:6152"

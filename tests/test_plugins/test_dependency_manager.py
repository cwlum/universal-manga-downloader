from __future__ import annotations

from types import SimpleNamespace

import plugins.dependency_manager as dep


def test_dependency_check(monkeypatch) -> None:
    versions = {"requests": "2.32.0"}

    def fake_version(package: str) -> str:
        if package in versions:
            return versions[package]
        raise dep.importlib_metadata.PackageNotFoundError

    monkeypatch.setattr(dep.importlib_metadata, "version", fake_version)

    statuses = dep.DependencyManager.check(["requests>=2.0.0", "lxml>=4.9.0"])

    assert statuses[0].installed and statuses[0].satisfies
    assert not statuses[1].installed


def test_dependency_install_invokes_pip(monkeypatch) -> None:
    captured = {}

    def fake_run(cmd, check, env):  # type: ignore[unused-argument]
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(dep.subprocess, "run", fake_run)
    monkeypatch.setattr(dep, "get_sanitized_proxies", lambda: {})

    success, message = dep.DependencyManager.install(["requests>=2.0.0"])

    assert success
    assert "pip" in " ".join(captured["cmd"])

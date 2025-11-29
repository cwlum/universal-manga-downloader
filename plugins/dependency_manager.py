"""Utilities for checking and installing plugin dependencies."""

from __future__ import annotations

import importlib.metadata as importlib_metadata
import logging
import os
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass

from packaging.requirements import Requirement

from utils.http_client import get_sanitized_proxies

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DependencyStatus:
    """Represents the installation status of a dependency requirement."""

    requirement: str
    package: str
    specifier: str
    installed: bool
    installed_version: str | None
    satisfies: bool


class DependencyManager:
    """Check and install third-party dependencies declared by plugins."""

    @staticmethod
    def check(requirements: Iterable[str]) -> list[DependencyStatus]:
        statuses: list[DependencyStatus] = []
        for raw_req in requirements:
            req = raw_req.strip()
            if not req:
                continue
            try:
                parsed = Requirement(req)
            except Exception:  # noqa: BLE001 - user supplied strings may be invalid
                logger.warning("Unable to parse dependency %s", req)
                statuses.append(
                    DependencyStatus(
                        requirement=req,
                        package=req,
                        specifier="",
                        installed=False,
                        installed_version=None,
                        satisfies=False,
                    )
                )
                continue

            package = parsed.name
            specifier = str(parsed.specifier) if parsed.specifier else ""
            try:
                installed_version = importlib_metadata.version(package)
                satisfies = parsed.specifier.contains(installed_version, prereleases=True)
                status = DependencyStatus(
                    requirement=req,
                    package=package,
                    specifier=specifier,
                    installed=True,
                    installed_version=installed_version,
                    satisfies=satisfies or not specifier,
                )
            except importlib_metadata.PackageNotFoundError:
                status = DependencyStatus(
                    requirement=req,
                    package=package,
                    specifier=specifier,
                    installed=False,
                    installed_version=None,
                    satisfies=False,
                )
            statuses.append(status)
        return statuses

    @staticmethod
    def missing(requirements: Iterable[str]) -> list[str]:
        return [status.requirement for status in DependencyManager.check(requirements) if not status.satisfies]

    @staticmethod
    def install(requirements: Iterable[str]) -> tuple[bool, str]:
        reqs = [req.strip() for req in requirements if req.strip()]
        if not reqs:
            return True, "没有需要安装的依赖"
        cmd = [sys.executable, "-m", "pip", "install", *reqs]
        env = os.environ.copy()
        proxies = get_sanitized_proxies()
        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
            env.pop(key, None)
        for scheme, proxy in proxies.items():
            env[f"{scheme}_proxy"] = proxy
            env[f"{scheme.upper()}_PROXY"] = proxy
        logger.info("Installing plugin dependencies: %s", reqs)
        result = subprocess.run(cmd, check=False, env=env)  # noqa: S603, S607 - controlled args
        if result.returncode == 0:
            return True, "依赖安装完成"
        return False, f"依赖安装失败，退出码 {result.returncode}"


__all__ = ["DependencyManager", "DependencyStatus"]

"""Helpers for comparing remote plugin versions."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from packaging import version

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VersionInfo:
    plugin_name: str
    current: str
    latest: str

    @property
    def has_update(self) -> bool:
        try:
            return version.parse(self.latest) > version.parse(self.current)
        except Exception:  # noqa: BLE001
            return False


def compare_versions(current: str, latest: str) -> int:
    """Compare semantic versions returning 1 if latest>current, 0 if equal, -1 otherwise."""

    try:
        v_current = version.parse(current)
        v_latest = version.parse(latest)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to parse versions %s vs %s: %s", current, latest, exc)
        return 0
    if v_latest > v_current:
        return 1
    if v_latest == v_current:
        return 0
    return -1


__all__ = ["VersionInfo", "compare_versions"]

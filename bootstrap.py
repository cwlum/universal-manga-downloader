"""Bootstrapping utilities to launch the manga downloader with zero setup."""

from __future__ import annotations

import importlib
import logging
import subprocess
import sys
from collections.abc import Iterable

logger = logging.getLogger(__name__)

MODULE_TO_PACKAGE: dict[str, str] = {
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "PIL": "Pillow",
    "cloudscraper": "cloudscraper",
    "sv_ttk": "sv-ttk",
}


def _missing_packages() -> list[str]:
    """Return pip package names that are required but not importable."""

    missing: list[str] = []
    for module_name, package_name in MODULE_TO_PACKAGE.items():
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            missing.append(package_name)
    return missing


def _install_packages(packages: Iterable[str]) -> None:
    """Install the provided pip packages using the active interpreter."""

    command = [sys.executable, "-m", "pip", "install", *packages]
    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to install required packages: {packages}") from exc
    except OSError as exc:  # pragma: no cover - defensive
        raise RuntimeError("Unable to invoke pip; please ensure it is available.") from exc


def ensure_runtime() -> None:
    """Ensure Python version and third-party dependencies are ready."""

    if sys.version_info < (3, 10):  # noqa: UP036 - enforce runtime version gate
        raise RuntimeError(
            "Universal Manga Downloader requires Python 3.10 or newer. "
            f"Detected Python {sys.version.split()[0]}."
        )

    missing = _missing_packages()
    if not missing:
        return

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s:%(name)s:%(message)s",
        )
    logger.info("Installing missing dependencies: %s", ", ".join(missing))
    _install_packages(missing)


def launch() -> None:
    """Ensure environment is ready and start the GUI application."""

    ensure_runtime()
    from manga_downloader import main  # Import after dependencies are ready

    main()


if __name__ == "__main__":
    launch()

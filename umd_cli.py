"""Command-line entry point for the Universal Manga Downloader."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Sequence
from importlib import metadata, util
from pathlib import Path

from manga_downloader import configure_logging
from manga_downloader import main as launch_gui

MINIMUM_PYTHON = (3, 11)
REQUIRED_MODULES: list[tuple[str, str]] = [
    ("requests", "requests"),
    ("bs4", "beautifulsoup4"),
    ("PIL", "Pillow"),
    ("cloudscraper", "cloudscraper"),
    ("sv_ttk", "sv-ttk"),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="umd",
        description="Universal Manga Downloader launcher and diagnostic tool.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run environment diagnostics instead of starting the GUI.",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Override the root logger level for this session.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the installed application version and exit.",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Validate configuration without launching the GUI.",
    )
    parser.add_argument(
        "--auto-update",
        action="store_true",
        help="Upgrade the installed package before launching.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(_get_version())
        return 0

    if args.doctor:
        return run_doctor()

    log_level: str | None = args.log_level.upper() if args.log_level else None
    configure_logging(log_level)

    if args.auto_update:
        if not run_auto_update():
            return 1
        # Refresh version metadata after upgrade.
        configure_logging(log_level)

    if args.no_gui:
        print("Configuration OK. GUI launch skipped (--no-gui).")
        return 0

    try:
        launch_gui(log_level=log_level)
    except Exception as exc:  # noqa: BLE001 - surface crashes
        print(f"umd: fatal error - {exc}", file=sys.stderr)
        return 1
    return 0


def run_doctor() -> int:
    print("Universal Manga Downloader — environment check")
    print("-" * 60)

    status = True
    status &= _check_python()
    status &= _check_tkinter()
    status &= _check_dependencies()

    print("-" * 60)
    if status:
        print("All required components look good! You're ready to run `umd` 🎉")
        return 0

    print("One or more checks failed. Please address the issues above.")
    return 1


def _check_python() -> bool:
    print("Python version:", sys.version.replace("\n", " "))
    if sys.version_info < MINIMUM_PYTHON:
        print(f"  ✗ Requires Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer.")
        return False
    print("  ✓ Meets minimum Python version requirement.")
    return True


def _check_tkinter() -> bool:
    try:
        import tkinter as tk
    except ModuleNotFoundError as exc:
        print("Tkinter: ✗ Missing tkinter module (GUI cannot start).")
        print(f"  Detail: {exc}")
        return False

    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
    except Exception as exc:  # noqa: BLE001 - platform-specific failures
        print("Tkinter: ⚠️  Installed but encountered an issue while testing the display.")
        print(f"  Detail: {exc}")
        return False

    print("Tkinter: ✓ GUI toolkit is available.")
    return True


def _check_dependencies() -> bool:
    all_ok = True
    for module_name, package_name in REQUIRED_MODULES:
        if util.find_spec(module_name) is None:
            print(f"{package_name:15s}: ✗ Not installed")
            all_ok = False
        else:
            print(f"{package_name:15s}: ✓")
    return all_ok


def _get_version() -> str:
    try:
        return metadata.version("universal-manga-downloader")
    except metadata.PackageNotFoundError:
        return "universal-manga-downloader (uninstalled workspace copy)"


def run_auto_update() -> bool:
    """Attempt to upgrade the installed package and report status."""

    package_spec = "universal-manga-downloader"
    print("Updating Universal Manga Downloader…")
    try:
        cmd = _build_update_command(package_spec)
    except RuntimeError as exc:
        print(f"  ✗ Unable to determine update command: {exc}")
        return False

    result = subprocess.run(cmd, check=False)  # noqa: S603,S607 - trusted command selection
    if result.returncode == 0:
        print("  ✓ Update complete.")
        return True

    print(f"  ✗ Update failed with exit code {result.returncode}.")
    return False


def _build_update_command(package_spec: str) -> list[str]:
    pipx_path = shutil.which("pipx")
    if pipx_path and _running_inside_pipx():
        return [pipx_path, "upgrade", package_spec]

    python_executable = sys.executable
    if not python_executable:
        raise RuntimeError("Unable to locate active Python executable.")

    return [python_executable, "-m", "pip", "install", "--upgrade", package_spec]


def _running_inside_pipx() -> bool:
    try:
        prefix_parts = Path(sys.prefix).parts
    except Exception:  # noqa: BLE001 - guard against unusual sys.prefix values
        return False

    return "pipx" in prefix_parts


if __name__ == "__main__":
    raise SystemExit(main())

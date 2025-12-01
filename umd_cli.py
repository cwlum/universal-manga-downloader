"""Command-line entry point for the Universal Manga Downloader."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from importlib import metadata, util
from pathlib import Path
from typing import Any

from manga_downloader import configure_logging
from manga_downloader import main as launch_gui
from plugins.base import PluginManager
from plugins.dependency_manager import DependencyManager
from plugins.remote_manager import RemotePluginManager
from utils.http_client import get_sanitized_proxies

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
        description="Universal Manga Downloader - A powerful manga downloader with retry logic and rate limiting.",
        epilog="For more information, visit: https://github.com/lum-muu/universal-manga-downloader",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run comprehensive environment diagnostics (Python, Tkinter, dependencies, disk space).",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default=None,
        metavar="LEVEL",
        help="Set logging level: debug, info, warning, error, or critical.",
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Display version information and exit.",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Validate configuration and dependencies without launching the GUI.",
    )
    parser.add_argument(
        "--auto-update",
        action="store_true",
        help="Automatically upgrade to the latest version before launching.",
    )
    parser.add_argument(
        "--config-info",
        action="store_true",
        help="Display current configuration settings and exit.",
    )

    subparsers = parser.add_subparsers(dest="command")

    plugins_parser = subparsers.add_parser(
        "plugins",
        help="Manage remote plugins without launching the GUI.",
    )
    plugins_subparsers = plugins_parser.add_subparsers(dest="plugins_command", required=True)

    plugins_subparsers.add_parser("list", help="List installed remote plugins.")

    install_parser = plugins_subparsers.add_parser("install", help="Install a remote plugin from a GitHub raw URL.")
    install_parser.add_argument("url", help="GitHub raw URL of the plugin to install.")
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing plugin with the downloaded version.",
    )

    uninstall_parser = plugins_subparsers.add_parser("uninstall", help="Uninstall a remote plugin by class name.")
    uninstall_parser.add_argument("name", help="Plugin class name to uninstall.")

    plugins_subparsers.add_parser("check-updates", help="Check all remote plugins for updates.")

    update_parser = plugins_subparsers.add_parser("update", help="Update remote plugins.")
    update_parser.add_argument("names", nargs="*", help="Specific plugin class names to update.")
    update_parser.add_argument("--all", action="store_true", help="Update every plugin with an available update.")

    history_parser = plugins_subparsers.add_parser("history", help="Show stored history for a remote plugin.")
    history_parser.add_argument("name", help="Plugin class name to inspect.")
    history_parser.add_argument("--limit", type=int, default=5, help="Maximum number of history entries to display (default: 5).")

    rollback_parser = plugins_subparsers.add_parser("rollback", help="Rollback a plugin to a previous version.")
    rollback_parser.add_argument("name", help="Plugin class name to rollback.")
    rollback_parser.add_argument("--version", help="Target version to restore.")
    rollback_parser.add_argument("--checksum", help="Specific checksum snapshot to restore.")

    install_deps_parser = plugins_subparsers.add_parser(
        "install-deps",
        help="Install missing dependencies for a remote plugin.",
    )
    install_deps_parser.add_argument("name", help="Plugin class name to process.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        return show_version()

    if args.config_info:
        return show_config_info()

    if args.doctor:
        return run_doctor()

    log_level: str | None = args.log_level.upper() if args.log_level else None

    if args.command == "plugins":
        configure_logging(log_level)
        return _handle_plugins_command(args)

    configure_logging(log_level)

    if args.auto_update:
        if not run_auto_update():
            return 1
        # Refresh version metadata after upgrade.
        configure_logging(log_level)

    if args.no_gui:
        print("✓ Configuration validated successfully.")
        print("  GUI launch skipped (--no-gui flag).")
        return 0

    try:
        launch_gui(log_level=log_level)
    except Exception as exc:  # noqa: BLE001 - surface crashes
        print(f"✗ Fatal error: {exc}", file=sys.stderr)
        print("  Run 'umd --doctor' for diagnostic information.", file=sys.stderr)
        return 1
    return 0


def show_version() -> int:
    """Display version information."""
    version = _get_version()
    print(f"Universal Manga Downloader v{version}")
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"Platform: {sys.platform}")
    return 0


def show_config_info() -> int:
    """Display current configuration settings."""
    try:
        from config import CONFIG

        print("Universal Manga Downloader — Configuration")
        print("=" * 60)

        print("\n[UI Configuration]")
        print(f"  Window size: {CONFIG.ui.default_width}x{CONFIG.ui.default_height}")
        print(f"  Progress update interval: {CONFIG.ui.progress_update_interval_ms}ms")

        print("\n[Download Configuration]")
        print(f"  Default chapter workers: {CONFIG.download.default_chapter_workers}")
        print(f"  Default image workers: {CONFIG.download.default_image_workers}")
        print(f"  Max total image workers: {CONFIG.download.max_total_image_workers}")
        print(f"  Request timeout: {CONFIG.download.request_timeout}s")
        print(f"  Max retries: {CONFIG.download.max_retries}")
        print(f"  Retry delay: {CONFIG.download.retry_delay}s")

        print("\n[Service Configuration]")
        print(f"  Bato base URL: {CONFIG.service.bato_base_url}")
        print(f"  MangaDex API: {CONFIG.service.mangadex_api_base}")
        print(f"  Rate limit delay: {CONFIG.service.rate_limit_delay}s")
        print(f"  Languages: {', '.join(CONFIG.service.mangadex_languages)}")

        print("\n[PDF Configuration]")
        print(f"  Resolution: {CONFIG.pdf.resolution} DPI")

        print("\n" + "=" * 60)
        return 0
    except Exception as exc:
        print(f"✗ Error loading configuration: {exc}", file=sys.stderr)
        return 1


def run_doctor() -> int:
    """Run comprehensive environment diagnostics."""
    print("Universal Manga Downloader — Environment Diagnostics")
    print("=" * 60)

    status = True
    status &= _check_python()
    status &= _check_tkinter()
    status &= _check_dependencies()
    status &= _check_disk_space()
    status &= _check_download_dir()

    print("=" * 60)
    if status:
        print("✓ All checks passed! System is ready to run.")
        print("\n  Start with: umd")
        print("  Get help:   umd --help")
        return 0

    print("✗ Some checks failed. Please address the issues above.")
    print("  For installation help, see: README.md")
    return 1


def _check_python() -> bool:
    """Check Python version compatibility."""
    print(f"\n[Python] {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    if sys.version_info < MINIMUM_PYTHON:
        print(f"  ✗ Requires Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer")
        return False
    print(f"  ✓ Version requirement satisfied (>= {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]})")
    return True


def _check_tkinter() -> bool:
    """Check Tkinter availability and display support."""
    print("\n[Tkinter]")
    try:
        import tkinter as tk
    except ModuleNotFoundError as exc:
        print("  ✗ Tkinter module not found (GUI cannot start)")
        print("     Install: apt-get install python3-tk  # Linux")
        print(f"     Detail: {exc}")
        return False

    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
    except Exception as exc:  # noqa: BLE001 - platform-specific failures
        print("  ⚠️  Tkinter installed but display test failed")
        print("     This may be normal in headless environments")
        print(f"     Detail: {exc}")
        return False

    print("  ✓ GUI toolkit available and functional")
    return True


def _check_dependencies() -> bool:
    """Check required Python package dependencies."""
    print("\n[Dependencies]")
    all_ok = True
    for module_name, package_name in REQUIRED_MODULES:
        if util.find_spec(module_name) is None:
            print(f"  ✗ {package_name:20s} - Not installed")
            all_ok = False
        else:
            # Try to get version if available
            try:
                version = metadata.version(package_name)
                print(f"  ✓ {package_name:20s} - v{version}")
            except metadata.PackageNotFoundError:
                print(f"  ✓ {package_name:20s} - Installed")

    if not all_ok:
        print("\n  Install missing packages:")
        print("    pip install universal-manga-downloader")

    return all_ok


def _check_disk_space() -> bool:
    """Check available disk space in default download directory."""
    print("\n[Disk Space]")
    try:
        from utils.file_utils import get_default_download_root, get_free_disk_space

        download_dir = get_default_download_root()
        free_bytes = get_free_disk_space(download_dir)

        if free_bytes < 0:
            print("  ⚠️  Unable to determine free space")
            return True  # Don't fail, just warn

        free_gb = free_bytes / (1024 ** 3)
        print(f"  Download directory: {download_dir}")
        print(f"  ✓ Free space: {free_gb:.2f} GB")

        if free_gb < 1:
            print("  ⚠️  Less than 1 GB free - consider freeing up space")

        return True
    except Exception as exc:
        print(f"  ⚠️  Could not check disk space: {exc}")
        return True  # Don't fail on disk space check


def _check_download_dir() -> bool:
    """Check download directory accessibility."""
    print("\n[Download Directory]")
    try:
        from utils.file_utils import ensure_directory, get_default_download_root

        download_dir = get_default_download_root()
        result = ensure_directory(download_dir)

        if result is None:
            print(f"  ✗ Cannot create/access: {download_dir}")
            return False

        print(f"  ✓ Accessible: {download_dir}")

        # Check write permissions
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(dir=download_dir, delete=True):
                pass
            print("  ✓ Write permissions confirmed")
        except OSError:
            print("  ✗ No write permission")
            return False

        return True
    except Exception as exc:
        print(f"  ✗ Error checking directory: {exc}")
        return False


def _handle_plugins_command(args: argparse.Namespace) -> int:
    manager = _get_remote_plugin_manager()
    command = args.plugins_command
    if command == "list":
        return _plugins_cmd_list(manager)
    if command == "install":
        return _plugins_cmd_install(manager, args.url, replace=args.force)
    if command == "uninstall":
        return _plugins_cmd_uninstall(manager, args.name)
    if command == "check-updates":
        return _plugins_cmd_check_updates(manager)
    if command == "update":
        return _plugins_cmd_update(manager, args.names, args.all)
    if command == "history":
        return _plugins_cmd_history(manager, args.name, args.limit)
    if command == "rollback":
        return _plugins_cmd_rollback(manager, args.name, args.version, args.checksum)
    if command == "install-deps":
        return _plugins_cmd_install_deps(manager, args.name)
    print("Unknown plugins subcommand", command)
    return 1


def _get_remote_plugin_manager() -> RemotePluginManager:
    plugin_manager = PluginManager()
    return RemotePluginManager(plugin_manager.plugin_dir)


def _plugins_cmd_list(manager: RemotePluginManager) -> int:
    records = manager.list_installed()
    if not records:
        print("No remote plugins installed.")
        return 0

    header = f"{'Name':24} {'Type':8} {'Version':10} Source"
    print(header)
    print("-" * len(header))
    for record in records:
        name = record.get("display_name", record["name"])[:24]
        plugin_type = record.get("plugin_type", "?")
        version = record.get("version", "?")[:10]
        print(f"{name:24} {plugin_type:8} {version:10} {record.get('source_url', '')}")
    return 0


def _plugins_cmd_install(manager: RemotePluginManager, url: str, *, replace: bool = False) -> int:
    success, prepared, message = manager.prepare_install(url)
    if message:
        print(message)
    if not success or prepared is None:
        return 1
    success, commit_message = manager.commit_install(prepared, replace_existing=replace)
    print(commit_message)
    if success and prepared.validation.plugin_name:
        _report_missing_dependencies(manager, prepared.validation.plugin_name)
    return 0 if success else 1


def _plugins_cmd_uninstall(manager: RemotePluginManager, name: str) -> int:
    success, message = manager.uninstall(name)
    print(message)
    return 0 if success else 1


def _plugins_cmd_check_updates(manager: RemotePluginManager) -> int:
    updates = manager.check_updates()
    if not updates:
        print("All remote plugins are up to date.")
        return 0
    print("Pending updates:")
    for update in updates:
        print(f"  - {update['display_name']} ({update['current']} → {update['latest']})")
    return 0


def _plugins_cmd_update(manager: RemotePluginManager, names: list[str], update_all: bool) -> int:
    targets: list[str]
    if update_all:
        pending = manager.check_updates()
        if not pending:
            print("All remote plugins are up to date.")
            return 0
        targets = [item["name"] for item in pending]
    else:
        if not names:
            print("Specify plugin names or use --all to update everything.")
            return 1
        targets = names

    exit_code = 0
    for plugin_name in targets:
        success, message = manager.update_plugin(plugin_name)
        print(message)
        if not success:
            exit_code = 1
        else:
            _report_missing_dependencies(manager, plugin_name)
    return exit_code


def _plugins_cmd_history(manager: RemotePluginManager, name: str, limit: int) -> int:
    entries = manager.list_history(name)
    if not entries:
        print("No saved history for this plugin.")
        return 0
    limit = max(1, limit)
    print(f"History for {name} (showing {min(limit, len(entries))} of {len(entries)}):")
    for entry in entries[:limit]:
        checksum = entry.get("checksum", "")
        short_checksum = checksum[:12] + "…" if len(checksum) > 12 else checksum
        print(
            f"  - {entry.get('version', '?'):>10} | saved {entry.get('saved_at', '')} | checksum {short_checksum}"
        )
    return 0


def _plugins_cmd_rollback(
    manager: RemotePluginManager,
    name: str,
    version: str | None,
    checksum: str | None,
) -> int:
    success, message = manager.rollback_plugin(name, version=version, checksum=checksum)
    print(message)
    return 0 if success else 1


def _plugins_cmd_install_deps(manager: RemotePluginManager, name: str) -> int:
    record = manager.get_record(name)
    if record is None:
        print("未找到插件")
        return 1
    deps = record.get("dependencies", [])
    if not deps:
        print("插件未声明依赖。")
        return 0
    missing = DependencyManager.missing(deps)
    if not missing:
        print("所有依赖均已满足。")
        return 0
    success, message = DependencyManager.install(missing)
    print(message)
    return 0 if success else 1


def _report_missing_dependencies(manager: RemotePluginManager, plugin_name: str) -> None:
    record = manager.get_record(plugin_name)
    if record is None:
        return
    deps = record.get("dependencies", [])
    if not deps:
        return
    missing = DependencyManager.missing(deps)
    if missing:
        print(f"⚠️  依赖未满足: {', '.join(missing)} (运行 'umd plugins install-deps {plugin_name}' 安装)")


def _get_version() -> str:
    pyproject_version = _load_version_from_pyproject()
    try:
        installed_version = metadata.version("universal-manga-downloader")
        if pyproject_version and pyproject_version != installed_version:
            return pyproject_version
        return installed_version
    except metadata.PackageNotFoundError:
        if pyproject_version:
            return pyproject_version
        return "universal-manga-downloader (uninstalled workspace copy)"


def _load_version_from_pyproject() -> str | None:
    """Read the version from pyproject.toml when the package is not installed."""
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - python <3.11 not supported
        return None

    pyproject_path = Path(__file__).resolve().parent / "pyproject.toml"
    if not pyproject_path.exists():
        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"

    try:
        content = pyproject_path.read_bytes()
    except OSError:
        return None

    try:
        data: dict[str, Any] = tomllib.loads(content.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None

    project = data.get("project")
    if isinstance(project, dict):
        version = project.get("version")
        if isinstance(version, str):
            return version.strip()
    return None


def run_auto_update() -> bool:
    """Attempt to upgrade the installed package and report status."""

    package_spec = "universal-manga-downloader"
    print("Updating Universal Manga Downloader…")
    try:
        cmd = _build_update_command(package_spec)
    except RuntimeError as exc:
        print(f"  ✗ Unable to determine update command: {exc}")
        return False

    env = _build_update_environment()
    result = subprocess.run(cmd, check=False, env=env)  # noqa: S603,S607 - trusted command selection
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


def _build_update_environment(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an environment with sanitized proxy variables for pip upgrades."""

    env = dict(base_env) if base_env is not None else os.environ.copy()
    proxies = get_sanitized_proxies()
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        env.pop(key, None)
    for scheme, value in proxies.items():
        env[f"{scheme}_proxy"] = value
        env[f"{scheme.upper()}_PROXY"] = value
    return env


def _running_inside_pipx() -> bool:
    try:
        prefix_parts = Path(sys.prefix).parts
    except Exception:  # noqa: BLE001 - guard against unusual sys.prefix values
        return False

    return "pipx" in prefix_parts


if __name__ == "__main__":
    raise SystemExit(main())

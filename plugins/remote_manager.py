"""Remote plugin download and registry management for Universal Manga Downloader."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from urllib.error import URLError
from urllib.request import urlopen

logger = logging.getLogger(__name__)

RAW_GITHUB_HOST = "raw.githubusercontent.com"


class RemotePluginInfo(TypedDict):
    """Metadata describing an installed remote plugin."""

    name: str
    plugin_type: str
    source_url: str
    install_date: str
    file_path: str


@dataclass(slots=True)
class RemoteValidationResult:
    """Outcome of validating a plugin source."""

    valid: bool
    reason: str | None = None
    plugin_name: str | None = None
    plugin_type: str | None = None


class RemotePluginManager:
    """Download, validate, and track remote plugins installed by the user."""

    def __init__(self, plugin_dir: Path) -> None:
        self._plugin_dir = plugin_dir
        self._registry_file = self._plugin_dir / "plugin_registry.json"
        self._registry: list[RemotePluginInfo] = self._load_registry()

    # --- Registry helpers ---

    def _load_registry(self) -> list[RemotePluginInfo]:
        if not self._registry_file.exists():
            return []
        try:
            raw_entries = json.loads(self._registry_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Remote plugin registry %s is corrupted; resetting", self._registry_file)
            return []

        entries: list[RemotePluginInfo] = []
        expected_keys = {"name", "plugin_type", "source_url", "install_date", "file_path"}
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                continue
            if not expected_keys.issubset(raw_entry):
                logger.debug("Skipping malformed registry entry: %s", raw_entry)
                continue
            entries.append(
                RemotePluginInfo(
                    name=str(raw_entry["name"]),
                    plugin_type=str(raw_entry["plugin_type"]),
                    source_url=str(raw_entry["source_url"]),
                    install_date=str(raw_entry["install_date"]),
                    file_path=str(raw_entry["file_path"]),
                )
            )
        return entries

    def _save_registry(self) -> None:
        self._registry_file.parent.mkdir(parents=True, exist_ok=True)
        with self._registry_file.open("w", encoding="utf-8") as handle:
            json.dump(self._registry, handle, indent=2, ensure_ascii=False)

    def list_installed(self) -> list[RemotePluginInfo]:
        """Return copies of installed plugin records."""

        return list(self._registry)

    # --- Installation / removal ---

    def install_from_url(self, url: str) -> tuple[bool, str]:
        url = url.strip()
        if not url:
            return False, "请输入插件的 GitHub Raw 链接"
        if not self._is_valid_github_url(url):
            return False, "仅支持 raw.githubusercontent.com 链接"

        try:
            content = self._download(url)
        except URLError as exc:  # pragma: no cover - urllib already tested elsewhere
            logger.warning("Failed to download plugin from %s: %s", url, exc)
            return False, "下载失败，请检查网络或 URL 是否正确"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error while downloading %s", url)
            return False, str(exc)

        validation = self._validate_plugin_code(content)
        if not validation.valid:
            return False, validation.reason or "插件验证失败"
        assert validation.plugin_name is not None
        assert validation.plugin_type is not None

        filename = self._extract_filename(url)
        if not filename.endswith(".py"):
            filename = f"{filename}.py"
        file_path = self._plugin_dir / filename
        if self._is_installed(validation.plugin_name):
            return False, f"插件 {validation.plugin_name} 已安装"

        try:
            file_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            logger.exception("Failed to write plugin %s", file_path)
            return False, f"无法写入插件文件: {exc}"

        record: RemotePluginInfo = RemotePluginInfo(
            name=validation.plugin_name,
            plugin_type=validation.plugin_type,
            source_url=url,
            install_date=datetime.utcnow().isoformat(),
            file_path=str(file_path),
        )
        self._registry.append(record)
        self._save_registry()
        logger.info("Installed remote plugin %s from %s", validation.plugin_name, url)
        return True, f"成功安装 {validation.plugin_name}"

    def uninstall(self, plugin_name: str) -> tuple[bool, str]:
        record = next((item for item in self._registry if item["name"] == plugin_name), None)
        if record is None:
            return False, "未在注册表中找到该插件"
        file_path = Path(record["file_path"])
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError as exc:
            logger.exception("Failed to remove plugin file %s", file_path)
            return False, f"无法删除插件文件: {exc}"

        self._registry.remove(record)
        self._save_registry()
        return True, f"已卸载 {plugin_name}"

    # --- Validation helpers ---

    def _download(self, url: str) -> str:
        with urlopen(url, timeout=30) as response:  # noqa: S310 - intended external download
            data = response.read()
            return data.decode("utf-8")

    def _is_valid_github_url(self, url: str) -> bool:
        pattern = rf"^https://{RAW_GITHUB_HOST}/[\w-]+/[\w.-]+/.+\.py$"
        return bool(re.match(pattern, url))

    def _validate_plugin_code(self, code: str) -> RemoteValidationResult:
        has_base_plugin = bool(re.search(r"class\s+\w+\s*\(\s*BasePlugin", code))
        has_base_converter = bool(re.search(r"class\s+\w+\s*\(\s*BaseConverter", code))
        if not (has_base_plugin or has_base_converter):
            return RemoteValidationResult(valid=False, reason="未找到 BasePlugin/BaseConverter 定义")

        class_pattern = re.compile(r"class\s+(\w+)\s*\(\s*(BasePlugin|BaseConverter)\s*\)")
        match = class_pattern.search(code)
        if not match:
            return RemoteValidationResult(valid=False, reason="缺少插件类定义")

        plugin_type = "parser" if match.group(2) == "BasePlugin" else "converter"
        return RemoteValidationResult(valid=True, plugin_name=match.group(1), plugin_type=plugin_type)

    def _extract_filename(self, url: str) -> str:
        return Path(url.split("?")[0]).name

    def _is_installed(self, plugin_name: str) -> bool:
        return any(record["name"] == plugin_name for record in self._registry)


__all__ = ["RemotePluginManager", "RemotePluginInfo"]

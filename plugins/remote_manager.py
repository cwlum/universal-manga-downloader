"""Remote plugin download and registry management for Universal Manga Downloader."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from urllib.error import URLError
from urllib.request import urlopen

from plugins.metadata_parser import PluginMetadata, calculate_checksum, parse_plugin_metadata
from plugins.version_manager import compare_versions

logger = logging.getLogger(__name__)

RAW_GITHUB_HOST = "raw.githubusercontent.com"
REGISTRY_SCHEMA_VERSION = 2
DEFAULT_ALLOWED_SOURCES = (
    "https://raw.githubusercontent.com/umd-plugins/official/",
)


class RemotePluginRecord(TypedDict):
    """Metadata describing an installed remote plugin."""

    name: str
    plugin_type: str
    source_url: str
    install_date: str
    file_path: str
    display_name: str
    version: str
    author: str
    description: str
    dependencies: list[str]
    checksum: str


class RemoteRegistryPayload(TypedDict):
    schema_version: int
    entries: list[RemotePluginRecord]


class UpdateInfo(TypedDict):
    name: str
    display_name: str
    current: str
    latest: str


@dataclass(slots=True)
class RemoteValidationResult:
    """Outcome of validating a plugin source."""

    valid: bool
    reason: str | None = None
    plugin_name: str | None = None
    plugin_type: str | None = None


@dataclass(slots=True)
class PreparedRemotePlugin:
    """Container holding downloaded plugin info prior to commit."""

    url: str
    code: str
    validation: RemoteValidationResult
    metadata: PluginMetadata
    checksum: str


class RemotePluginManager:
    """Download, validate, and track remote plugins installed by the user."""

    def __init__(self, plugin_dir: Path, allowed_sources: Sequence[str] | None = None) -> None:
        self._plugin_dir = plugin_dir
        self._registry_file = self._plugin_dir / "plugin_registry.json"
        self._whitelist_file = self._plugin_dir / "remote_sources.json"
        self._registry: list[RemotePluginRecord] = self._load_registry()
        if allowed_sources is not None:
            self._allowed_sources = [self._ensure_trailing_slash(prefix) for prefix in allowed_sources]
        else:
            self._allowed_sources = self._load_allowed_sources()

    # --- Registry helpers ---

    def _load_registry(self) -> list[RemotePluginRecord]:
        if not self._registry_file.exists():
            return []
        try:
            raw_entries = json.loads(self._registry_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Remote plugin registry %s is corrupted; resetting", self._registry_file)
            return []

        if isinstance(raw_entries, dict) and "entries" in raw_entries:
            entries_payload = raw_entries.get("entries", [])
        else:
            # Legacy schema v1 was a plain list
            entries_payload = raw_entries

        entries: list[RemotePluginRecord] = []
        for raw_entry in entries_payload:
            if not isinstance(raw_entry, dict):
                continue
            record = self._normalize_record(raw_entry)
            if record is not None:
                entries.append(record)
        return entries

    def _save_registry(self) -> None:
        self._registry_file.parent.mkdir(parents=True, exist_ok=True)
        payload: RemoteRegistryPayload = {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "entries": self._registry,
        }
        with self._registry_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    def list_installed(self) -> list[RemotePluginRecord]:
        """Return copies of installed plugin records."""

        return list(self._registry)

    def get_record(self, plugin_name: str) -> RemotePluginRecord | None:
        for record in self._registry:
            if record["name"] == plugin_name:
                return record
        return None

    def list_allowed_sources(self) -> list[str]:
        return list(self._allowed_sources)

    def add_allowed_source(self, prefix: str) -> tuple[bool, str]:
        prefix = prefix.strip()
        if not prefix:
            return False, "请输入来源前缀"
        if not prefix.startswith(f"https://{RAW_GITHUB_HOST}/"):
            return False, "仅允许 raw.githubusercontent.com 域名"
        normalized = self._ensure_trailing_slash(prefix)
        if normalized in self._allowed_sources:
            return False, "该来源已存在"
        self._allowed_sources.append(normalized)
        self._save_allowed_sources()
        return True, "已添加白名单来源"

    def remove_allowed_source(self, prefix: str) -> tuple[bool, str]:
        normalized = self._ensure_trailing_slash(prefix.strip())
        if normalized not in self._allowed_sources:
            return False, "来源不存在"
        if normalized in DEFAULT_ALLOWED_SOURCES:
            return False, "无法移除默认来源"
        self._allowed_sources.remove(normalized)
        self._save_allowed_sources()
        return True, "已移除白名单来源"

    # --- Installation / removal ---

    def install_from_url(self, url: str) -> tuple[bool, str]:
        prepared_success, prepared, message = self.prepare_install(url)
        if not prepared_success or prepared is None:
            return False, message
        return self.commit_install(prepared)

    def prepare_install(self, url: str) -> tuple[bool, PreparedRemotePlugin | None, str]:
        url = url.strip()
        if not url:
            return False, None, "请输入插件的 GitHub Raw 链接"
        if not self._is_valid_github_url(url):
            return False, None, "仅支持 raw.githubusercontent.com 链接"
        if not self._is_allowed_source(url):
            return False, None, "该来源不在白名单，先添加后再尝试"

        try:
            content = self._download(url)
        except URLError as exc:  # pragma: no cover - urllib already tested elsewhere
            logger.warning("Failed to download plugin from %s: %s", url, exc)
            return False, None, "下载失败，请检查网络或 URL 是否正确"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error while downloading %s", url)
            return False, None, str(exc)

        validation = self._validate_plugin_code(content)
        if not validation.valid:
            return False, None, validation.reason or "插件验证失败"
        assert validation.plugin_name is not None
        assert validation.plugin_type is not None

        metadata = parse_plugin_metadata(content)
        if "dependencies" not in metadata:
            metadata["dependencies"] = []
        checksum = calculate_checksum(content)
        prepared = PreparedRemotePlugin(
            url=url,
            code=content,
            validation=validation,
            metadata=metadata,
            checksum=checksum,
        )
        return True, prepared, ""

    def commit_install(self, prepared: PreparedRemotePlugin, *, replace_existing: bool = False) -> tuple[bool, str]:
        validation = prepared.validation
        assert validation.plugin_name is not None
        assert validation.plugin_type is not None

        filename = self._extract_filename(prepared.url)
        if not filename.endswith(".py"):
            filename = f"{filename}.py"
        file_path = self._plugin_dir / filename
        if self._is_installed(validation.plugin_name):
            if not replace_existing:
                return False, f"插件 {validation.plugin_name} 已安装"
            self._remove_record(validation.plugin_name)

        metadata = dict(prepared.metadata)
        display_name = str(metadata.get("name") or validation.plugin_name or "Unnamed")
        version = str(metadata.get("version", "0.0.0"))
        author = str(metadata.get("author", "Unknown"))
        description = str(metadata.get("description", ""))
        deps_value = metadata.get("dependencies", [])
        if not isinstance(deps_value, list):
            deps_value = []
        dependencies = [str(dep) for dep in deps_value]

        try:
            file_path.write_text(prepared.code, encoding="utf-8")
        except OSError as exc:
            logger.exception("Failed to write plugin %s", file_path)
            return False, f"无法写入插件文件: {exc}"

        record: RemotePluginRecord = RemotePluginRecord(
            name=validation.plugin_name,
            plugin_type=validation.plugin_type,
            source_url=prepared.url,
            install_date=datetime.utcnow().isoformat(),
            file_path=str(file_path),
            display_name=display_name,
            version=version,
            author=author,
            description=description,
            dependencies=list(dependencies),
            checksum=prepared.checksum,
        )
        self._registry.append(record)
        self._save_registry()
        logger.info("Installed remote plugin %s from %s", validation.plugin_name, prepared.url)
        return True, f"成功安装 {display_name}"

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

    def check_updates(self) -> list[UpdateInfo]:
        updates: list[UpdateInfo] = []
        for record in self._registry:
            latest_version = self._fetch_remote_version(record["source_url"])
            if latest_version is None:
                continue
            comparison = compare_versions(record["version"], latest_version)
            if comparison <= 0:
                continue
            updates.append(
                UpdateInfo(
                    name=record["name"],
                    display_name=record["display_name"],
                    current=record["version"],
                    latest=latest_version,
                )
            )
        return updates

    def update_plugin(self, plugin_name: str) -> tuple[bool, str]:
        record = self.get_record(plugin_name)
        if record is None:
            return False, "未找到插件"
        success, prepared, message = self.prepare_install(record["source_url"])
        if not success or prepared is None:
            return False, message
        return self.commit_install(prepared, replace_existing=True)

    # --- Validation helpers ---

    def _download(self, url: str) -> str:
        with urlopen(url, timeout=30) as response:  # noqa: S310 - intended external download
            data = response.read()
            return data.decode("utf-8")

    def _is_valid_github_url(self, url: str) -> bool:
        pattern = rf"^https://{RAW_GITHUB_HOST}/[\w-]+/[\w.-]+/.+\.py$"
        return bool(re.match(pattern, url))

    def _is_allowed_source(self, url: str) -> bool:
        return any(url.startswith(prefix) for prefix in self._allowed_sources)

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

    def _remove_record(self, plugin_name: str) -> None:
        self._registry = [record for record in self._registry if record["name"] != plugin_name]

    def _fetch_remote_version(self, url: str) -> str | None:
        try:
            code = self._download(url)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to fetch remote version from %s: %s", url, exc)
            return None
        metadata = parse_plugin_metadata(code)
        version_value = metadata.get("version")
        if isinstance(version_value, str) and version_value.strip():
            return version_value.strip()
        return None

    def _normalize_record(self, raw_entry: dict[str, object]) -> RemotePluginRecord | None:
        if {"name", "plugin_type", "source_url", "install_date", "file_path"}.issubset(raw_entry):
            display_name = str(raw_entry.get("display_name", raw_entry["name"]))
            dependencies = raw_entry.get("dependencies")
            if not isinstance(dependencies, list):
                dependencies = []
            return RemotePluginRecord(
                name=str(raw_entry["name"]),
                plugin_type=str(raw_entry["plugin_type"]),
                source_url=str(raw_entry["source_url"]),
                install_date=str(raw_entry["install_date"]),
                file_path=str(raw_entry["file_path"]),
                display_name=display_name,
                version=str(raw_entry.get("version", "0.0.0")),
                author=str(raw_entry.get("author", "Unknown")),
                description=str(raw_entry.get("description", "")),
                dependencies=[str(dep) for dep in dependencies],
                checksum=str(raw_entry.get("checksum", "")),
            )
        logger.debug("Skipping malformed registry entry: %s", raw_entry)
        return None

    def _load_allowed_sources(self) -> list[str]:
        if not self._whitelist_file.exists():
            return [self._ensure_trailing_slash(prefix) for prefix in DEFAULT_ALLOWED_SOURCES]
        try:
            data = json.loads(self._whitelist_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [self._ensure_trailing_slash(prefix) for prefix in DEFAULT_ALLOWED_SOURCES]
        if not isinstance(data, list):
            return [self._ensure_trailing_slash(prefix) for prefix in DEFAULT_ALLOWED_SOURCES]
        normalized = [self._ensure_trailing_slash(str(item)) for item in data if isinstance(item, str)]
        return normalized or [self._ensure_trailing_slash(prefix) for prefix in DEFAULT_ALLOWED_SOURCES]

    def _save_allowed_sources(self) -> None:
        self._whitelist_file.parent.mkdir(parents=True, exist_ok=True)
        self._whitelist_file.write_text(json.dumps(self._allowed_sources, indent=2), encoding="utf-8")

    def _ensure_trailing_slash(self, value: str) -> str:
        return value if value.endswith("/") else f"{value}/"


__all__ = [
    "RemotePluginManager",
    "RemotePluginRecord",
    "PreparedRemotePlugin",
]

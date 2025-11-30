"""Remote plugin download and registry management for Universal Manga Downloader."""

from __future__ import annotations

import io
import json
import logging
import re
import shutil
import tempfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, TypedDict, cast
from urllib.error import URLError
from urllib.request import urlopen

from plugins.metadata_parser import PluginMetadata, calculate_checksum, parse_plugin_metadata
from plugins.version_manager import compare_versions

logger = logging.getLogger(__name__)

RAW_GITHUB_HOST = "raw.githubusercontent.com"
REGISTRY_SCHEMA_VERSION = 2
DEFAULT_ALLOWED_SOURCES = (
    "https://raw.githubusercontent.com/cwlum/universal-manga-downloader/main/community-plugins/",
)
MAX_HISTORY_ENTRIES = 10
ArtifactType = Literal["file", "package"]


class RemotePluginHistoryEntry(TypedDict):
    """Snapshot metadata for a historical plugin version."""

    version: str
    checksum: str
    saved_at: str
    file_path: str
    artifact_type: ArtifactType
    display_name: str
    author: str
    description: str
    dependencies: list[str]
    source_url: str


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
    artifact_type: ArtifactType
    history: list[RemotePluginHistoryEntry]


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
    artifact_type: ArtifactType
    temp_dir: Path | None = None
    package_root: Path | None = None
    filename: str | None = None


class RemotePluginManager:
    """Download, validate, and track remote plugins installed by the user."""

    def __init__(self, plugin_dir: Path, allowed_sources: Sequence[str] | None = None) -> None:
        self._plugin_dir = plugin_dir
        self._registry_file = self._plugin_dir / "plugin_registry.json"
        self._whitelist_file = self._plugin_dir / "remote_sources.json"
        self._history_dir = self._plugin_dir / "remote_history"
        self._registry: list[RemotePluginRecord] = self._load_registry()
        self._allow_all_github_raw = False
        if allowed_sources is not None:
            self._allowed_sources = [self._ensure_trailing_slash(prefix) for prefix in allowed_sources]
        else:
            sources, allow_any = self._load_allowed_sources()
            self._allowed_sources = sources
            self._allow_all_github_raw = allow_any

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

    def allow_any_github_raw(self) -> bool:
        return self._allow_all_github_raw

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

    def set_allow_any_github_raw(self, enabled: bool) -> None:
        self._allow_all_github_raw = bool(enabled)
        self._save_allowed_sources()

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
            if self._is_archive_url(url):
                binary = self._download_bytes(url)
                return self._prepare_archive(url, binary)
            content = self._download_text(url)
        except URLError as exc:  # pragma: no cover - urllib already tested elsewhere
            logger.warning("Failed to download plugin from %s: %s", url, exc)
            return False, None, "下载失败，请检查网络或 URL 是否正确"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error while downloading %s", url)
            return False, None, str(exc)
        return self._prepare_from_code(url, content)

    def commit_install(self, prepared: PreparedRemotePlugin, *, replace_existing: bool = False) -> tuple[bool, str]:
        validation = prepared.validation
        assert validation.plugin_name is not None
        assert validation.plugin_type is not None

        history: list[RemotePluginHistoryEntry] = []
        existing_record = self.get_record(validation.plugin_name)

        filename = prepared.filename or self._extract_filename(prepared.url)
        if prepared.artifact_type == "file" and not filename.endswith(".py"):
            filename = f"{filename}.py"
        file_path = (
            self._plugin_dir / validation.plugin_name
            if prepared.artifact_type == "package"
            else self._plugin_dir / filename
        )
        if existing_record is not None:
            if not replace_existing:
                return False, f"插件 {validation.plugin_name} 已安装"
            history = self._archive_record(existing_record)
            self._remove_artifact(Path(existing_record["file_path"]))
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
            if prepared.artifact_type == "package":
                if file_path.exists():
                    shutil.rmtree(file_path)
                if prepared.package_root is None:
                    return False, "缺少解压后的插件目录"
                shutil.copytree(prepared.package_root, file_path)
            else:
                file_path.write_text(prepared.code, encoding="utf-8")
        except OSError as exc:
            logger.exception("Failed to write plugin %s", file_path)
            if prepared.temp_dir is not None:
                shutil.rmtree(prepared.temp_dir, ignore_errors=True)
            return False, f"无法写入插件文件: {exc}"
        finally:
            if prepared.temp_dir is not None and prepared.temp_dir.exists():
                shutil.rmtree(prepared.temp_dir, ignore_errors=True)

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
            artifact_type=prepared.artifact_type,
            history=history,
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
            self._remove_artifact(file_path)
        except OSError as exc:
            logger.exception("Failed to remove plugin file %s", file_path)
            return False, f"无法删除插件文件: {exc}"

        self._registry.remove(record)
        self._save_registry()
        history_dir = (self._history_dir / plugin_name)
        if history_dir.exists():
            try:
                shutil.rmtree(history_dir)
            except OSError:
                logger.debug("Failed to remove history directory %s", history_dir)
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

    def _prepare_from_code(
        self,
        url: str,
        content: str,
        *,
        artifact_type: ArtifactType = "file",
        temp_dir: Path | None = None,
        package_root: Path | None = None,
        validation: RemoteValidationResult | None = None,
    ) -> tuple[bool, PreparedRemotePlugin | None, str]:
        validation = validation or self._validate_plugin_code(content)
        if not validation.valid:
            if temp_dir is not None:
                shutil.rmtree(temp_dir, ignore_errors=True)
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
            artifact_type=artifact_type,
            temp_dir=temp_dir,
            package_root=package_root,
        )
        return True, prepared, ""

    def _prepare_archive(self, url: str, payload: bytes) -> tuple[bool, PreparedRemotePlugin | None, str]:
        temp_dir = Path(tempfile.mkdtemp(prefix="umd_remote_", dir=str(self._plugin_dir)))
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                archive.extractall(temp_dir)
        except zipfile.BadZipFile:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, None, "ZIP 包损坏或不受支持"

        located = self._locate_plugin_entry(temp_dir)
        if located is None:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, None, "ZIP 包中未找到插件类"
        entry_path, code, validation = located
        package_root = self._determine_package_root(temp_dir)
        success, prepared, message = self._prepare_from_code(
            url,
            code,
            artifact_type="package",
            temp_dir=temp_dir,
            package_root=package_root,
            validation=validation,
        )
        if not success or prepared is None:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, None, message
        prepared.filename = entry_path.name
        return True, prepared, ""

    def list_history(self, plugin_name: str) -> list[RemotePluginHistoryEntry]:
        record = self.get_record(plugin_name)
        if record is None:
            return []
        return list(record.get("history", []))

    def rollback_plugin(self, plugin_name: str, version: str | None = None, checksum: str | None = None) -> tuple[bool, str]:
        record = self.get_record(plugin_name)
        if record is None:
            return False, "未找到插件"
        history_entries = record.get("history", [])
        if not history_entries:
            return False, "没有可用的历史版本"

        target_entry: RemotePluginHistoryEntry | None = None
        if checksum:
            target_entry = next((entry for entry in history_entries if entry["checksum"] == checksum), None)
        if target_entry is None and version is not None:
            target_entry = next((entry for entry in history_entries if entry["version"] == version), None)
        if target_entry is None:
            target_entry = history_entries[0]

        snapshot_path = Path(target_entry["file_path"])
        if not snapshot_path.exists():
            return False, "历史版本文件已丢失"

        updated_history = self._archive_record(record)
        if not updated_history and history_entries:
            updated_history = list(history_entries)
        updated_history = [item for item in updated_history if item["checksum"] != target_entry["checksum"]]

        try:
            destination = Path(record["file_path"])
            self._remove_artifact(destination)
            if snapshot_path.is_dir():
                shutil.copytree(snapshot_path, destination)
            else:
                shutil.copy2(snapshot_path, destination)
        except OSError as exc:
            logger.exception("Failed to rollback plugin %s", plugin_name)
            return False, f"回滚失败: {exc}"

        record["version"] = target_entry["version"]
        record["display_name"] = target_entry["display_name"]
        record["author"] = target_entry["author"]
        record["description"] = target_entry["description"]
        record["dependencies"] = list(target_entry.get("dependencies", []))
        record["checksum"] = target_entry["checksum"]
        record["artifact_type"] = target_entry.get("artifact_type", record.get("artifact_type", "file"))
        record["history"] = updated_history
        self._save_registry()
        return True, f"已回滚 {plugin_name} 至 {target_entry['version']}"

    # --- Validation helpers ---

    def _download_text(self, url: str) -> str:
        return self._download_bytes(url).decode("utf-8")

    def _download_bytes(self, url: str) -> bytes:
        with urlopen(url, timeout=30) as response:  # noqa: S310 - intended external download
            return response.read()

    def _is_valid_github_url(self, url: str) -> bool:
        pattern = rf"^https://{RAW_GITHUB_HOST}/[\w-]+/[\w.-]+/.+\.(py|zip)$"
        return bool(re.match(pattern, url))

    def _is_archive_url(self, url: str) -> bool:
        return url.lower().endswith(".zip")

    def _is_allowed_source(self, url: str) -> bool:
        if self._allow_all_github_raw and self._is_valid_github_url(url):
            return True
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

    def _remove_artifact(self, path: Path) -> None:
        try:
            if not path.exists():
                return
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            logger.debug("Failed to remove artifact %s: %s", path, exc)

    def _archive_record(self, record: RemotePluginRecord) -> list[RemotePluginHistoryEntry]:
        file_path = Path(record["file_path"])
        snapshot_path = ""
        if file_path.exists():
            try:
                history_dir = self._history_dir / record["name"]
                history_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                snapshot_name = f"{timestamp}_{file_path.name}"
                destination = history_dir / snapshot_name
                if file_path.is_dir():
                    shutil.copytree(file_path, destination)
                else:
                    shutil.copy2(file_path, destination)
                snapshot_path = str(destination)
            except OSError as exc:
                logger.exception("Failed to archive plugin %s: %s", record["name"], exc)
                snapshot_path = ""

        if not snapshot_path:
            return list(record.get("history", []))

        entry: RemotePluginHistoryEntry = RemotePluginHistoryEntry(
            version=record.get("version", "0.0.0"),
            checksum=record.get("checksum", ""),
            saved_at=datetime.utcnow().isoformat(),
            file_path=snapshot_path,
            artifact_type=self._coerce_artifact_type(record.get("artifact_type", "file")),
            display_name=record.get("display_name", record["name"]),
            author=record.get("author", "Unknown"),
            description=record.get("description", ""),
            dependencies=list(record.get("dependencies", [])),
            source_url=record.get("source_url", ""),
        )

        history = list(record.get("history", []))
        history.insert(0, entry)
        return history[:MAX_HISTORY_ENTRIES]

    def _fetch_remote_version(self, url: str) -> str | None:
        try:
            code = self._download_text(url)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to fetch remote version from %s: %s", url, exc)
            return None
        metadata = parse_plugin_metadata(code)
        version_value = metadata.get("version")
        if isinstance(version_value, str) and version_value.strip():
            return version_value.strip()
        return None

    def _locate_plugin_entry(
        self, root: Path
    ) -> tuple[Path, str, RemoteValidationResult] | None:
        for candidate in sorted(root.rglob("*.py")):
            try:
                code = candidate.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            validation = self._validate_plugin_code(code)
            if validation.valid:
                return candidate, code, validation
        return None

    def _determine_package_root(self, temp_dir: Path) -> Path:
        candidates = [path for path in temp_dir.iterdir() if path.name != "__MACOSX"]
        if len(candidates) == 1 and candidates[0].is_dir():
            return candidates[0]
        return temp_dir

    def _coerce_artifact_type(self, value: object) -> ArtifactType:
        if isinstance(value, str) and value in ("file", "package"):
            return cast(ArtifactType, value)
        return "file"

    def _normalize_record(self, raw_entry: dict[str, object]) -> RemotePluginRecord | None:
        if {"name", "plugin_type", "source_url", "install_date", "file_path"}.issubset(raw_entry):
            display_name = str(raw_entry.get("display_name", raw_entry["name"]))
            dependencies = raw_entry.get("dependencies")
            if not isinstance(dependencies, list):
                dependencies = []
            artifact_type = self._coerce_artifact_type(raw_entry.get("artifact_type", "file"))
            history_payload = raw_entry.get("history")
            parsed_history: list[RemotePluginHistoryEntry] = []
            if isinstance(history_payload, list):
                for item in history_payload:
                    if not isinstance(item, dict):
                        continue
                    parsed_history.append(
                        RemotePluginHistoryEntry(
                            version=str(item.get("version", "0.0.0")),
                            checksum=str(item.get("checksum", "")),
                            saved_at=str(item.get("saved_at", "")),
                            file_path=str(item.get("file_path", "")),
                            artifact_type=self._coerce_artifact_type(item.get("artifact_type", "file")),
                            display_name=str(item.get("display_name", raw_entry["name"])),
                            author=str(item.get("author", "Unknown")),
                            description=str(item.get("description", "")),
                            dependencies=[str(dep) for dep in item.get("dependencies", [])] if isinstance(item.get("dependencies"), list) else [],
                            source_url=str(item.get("source_url", raw_entry.get("source_url", ""))),
                        )
                    )
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
                artifact_type=artifact_type,
                history=parsed_history,
            )
        logger.debug("Skipping malformed registry entry: %s", raw_entry)
        return None

    def _load_allowed_sources(self) -> tuple[list[str], bool]:
        defaults = [self._ensure_trailing_slash(prefix) for prefix in DEFAULT_ALLOWED_SOURCES]
        if not self._whitelist_file.exists():
            return defaults, False
        try:
            data = json.loads(self._whitelist_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return defaults, False
        if isinstance(data, dict):
            allowed_raw = data.get("allowed", [])
            allow_any = bool(data.get("allow_any_raw_github", False))
        else:
            allowed_raw = data if isinstance(data, list) else []
            allow_any = False
        normalized = [self._ensure_trailing_slash(str(item)) for item in allowed_raw if isinstance(item, str)]
        return (normalized or defaults, allow_any)

    def _save_allowed_sources(self) -> None:
        self._whitelist_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "allowed": self._allowed_sources,
            "allow_any_raw_github": self._allow_all_github_raw,
        }
        self._whitelist_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _ensure_trailing_slash(self, value: str) -> str:
        return value if value.endswith("/") else f"{value}/"


__all__ = [
    "RemotePluginManager",
    "RemotePluginRecord",
    "PreparedRemotePlugin",
    "RemotePluginHistoryEntry",
]

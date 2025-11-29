"""Repository manager for community plugin indexes."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast
from urllib.request import urlopen

logger = logging.getLogger(__name__)

PluginEntryType = Literal["parser", "converter"]


@dataclass(slots=True)
class PluginRepositoryEntry:
    """Structured representation of a plugin entry from the repository index."""

    id: str
    name: str
    type: PluginEntryType
    author: str
    version: str
    description: str
    source_url: str
    repository: str
    license: str
    tags: list[str]
    dependencies: list[str]
    checksum: str
    downloads: int
    rating: float
    created_at: str
    updated_at: str


class RepositoryManager:
    """Synchronize plugin repository indexes and provide cached search results."""

    DEFAULT_REPOSITORIES = [
        "https://raw.githubusercontent.com/umd-plugins/official/main/index.json",
    ]

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._repo_file = data_dir / "plugin_repositories.json"
        self._cache_file = data_dir / "plugin_repository_cache.json"
        self._repositories = self._load_repositories()
        cache, timestamp = self._load_cache()
        self.cache: list[PluginRepositoryEntry] = cache
        self.last_sync: datetime | None = timestamp

    # --- Repository configuration ---

    def list_repositories(self) -> list[str]:
        return list(self._repositories)

    def add_repository(self, url: str) -> tuple[bool, str]:
        candidate = url.strip()
        if not candidate:
            return False, "请输入仓库 URL"
        if candidate in self._repositories:
            return False, "仓库已存在"
        self._repositories.append(candidate)
        self._save_repositories()
        return True, "已添加仓库"

    def remove_repository(self, url: str) -> tuple[bool, str]:
        candidate = url.strip()
        if candidate not in self._repositories:
            return False, "未找到仓库"
        if candidate in self.DEFAULT_REPOSITORIES:
            return False, "无法移除默认仓库"
        self._repositories.remove(candidate)
        self._save_repositories()
        return True, "已移除仓库"

    # --- Synchronization ---

    def sync(self) -> tuple[bool, str]:
        entries: list[PluginRepositoryEntry] = []
        errors: list[str] = []
        for repo_url in self._repositories:
            try:
                entries.extend(self._fetch_repository(repo_url))
            except Exception as exc:  # noqa: BLE001 - network errors bubbled as summary
                logger.warning("Failed to sync repository %s: %s", repo_url, exc)
                errors.append(f"{repo_url}: {exc}")

        if not entries:
            reason = "; ".join(errors) if errors else "无可用插件"
            return False, f"无法同步插件市场: {reason}"

        self.cache = entries
        self.last_sync = datetime.utcnow()
        self._save_cache()
        return True, f"同步完成，共 {len(entries)} 个插件"

    def _fetch_repository(self, repo_url: str) -> list[PluginRepositoryEntry]:
        with urlopen(repo_url, timeout=30) as response:  # noqa: S310 - remote fetch intentional
            payload = json.loads(response.read().decode("utf-8"))

        plugins = payload.get("plugins")
        if not isinstance(plugins, list):
            raise ValueError("仓库索引缺少 plugins 字段")

        entries: list[PluginRepositoryEntry] = []
        for item in plugins:
            entry = self._parse_entry(item)
            if entry is not None:
                entries.append(entry)
        return entries

    # --- Query helpers ---

    def search(
        self,
        query: str = "",
        *,
        plugin_type: PluginEntryType | None = None,
        tags: list[str] | None = None,
        sort_by: str = "name",
    ) -> list[PluginRepositoryEntry]:
        results = list(self.cache)

        if plugin_type:
            results = [entry for entry in results if entry.type == plugin_type]

        if tags:
            tag_set = {tag.lower() for tag in tags}
            results = [entry for entry in results if tag_set.intersection({t.lower() for t in entry.tags})]

        if query:
            query_lower = query.lower()
            results = [
                entry
                for entry in results
                if query_lower in entry.name.lower()
                or query_lower in entry.description.lower()
                or query_lower in entry.author.lower()
            ]

        return self._sort_entries(results, sort_by)

    def get_entry(self, entry_id: str) -> PluginRepositoryEntry | None:
        for entry in self.cache:
            if entry.id == entry_id:
                return entry
        return None

    # --- Internal helpers ---

    def _load_repositories(self) -> list[str]:
        if not self._repo_file.exists():
            return list(self.DEFAULT_REPOSITORIES)
        try:
            data = json.loads(self._repo_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return list(self.DEFAULT_REPOSITORIES)
        if not isinstance(data, list):
            return list(self.DEFAULT_REPOSITORIES)
        cleaned = [str(item).strip() for item in data if isinstance(item, str) and item.strip()]
        return cleaned or list(self.DEFAULT_REPOSITORIES)

    def _save_repositories(self) -> None:
        self._repo_file.parent.mkdir(parents=True, exist_ok=True)
        self._repo_file.write_text(json.dumps(self._repositories, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_cache(self) -> tuple[list[PluginRepositoryEntry], datetime | None]:
        if not self._cache_file.exists():
            return [], None
        try:
            raw = json.loads(self._cache_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [], None
        entries_raw = raw.get("entries", [])
        timestamp_value = raw.get("last_sync")
        timestamp = None
        if isinstance(timestamp_value, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_value)
            except ValueError:
                timestamp = None
        entries: list[PluginRepositoryEntry] = []
        if isinstance(entries_raw, list):
            for item in entries_raw:
                entry = self._parse_entry(item)
                if entry is not None:
                    entries.append(entry)
        return entries, timestamp

    def _save_cache(self) -> None:
        payload = {
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "entries": [asdict(entry) for entry in self.cache],
        }
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _parse_entry(self, raw: dict[str, object] | None) -> PluginRepositoryEntry | None:
        if not isinstance(raw, dict):
            return None
        try:
            raw_type = str(raw.get("type", "parser")).lower()
            if raw_type not in ("parser", "converter"):
                raw_type = "parser"
            entry_type = cast(PluginEntryType, raw_type)
            tags = self._coerce_str_list(raw.get("tags"))
            dependencies = self._coerce_str_list(raw.get("dependencies"))
            downloads = self._coerce_int(raw.get("downloads", 0))
            rating = self._coerce_float(raw.get("rating", 0.0))

            return PluginRepositoryEntry(
                id=str(raw.get("id", raw.get("name", ""))),
                name=str(raw.get("name", "Unnamed")),
                type=entry_type,
                author=str(raw.get("author", "Unknown")),
                version=str(raw.get("version", "0.0.0")),
                description=str(raw.get("description", "")),
                source_url=str(raw.get("source_url", "")),
                repository=str(raw.get("repository", "")),
                license=str(raw.get("license", "")),
                tags=tags,
                dependencies=dependencies,
                checksum=str(raw.get("checksum", "")),
                downloads=downloads,
                rating=rating,
                created_at=str(raw.get("created_at", "")),
                updated_at=str(raw.get("updated_at", "")),
            )
        except Exception as exc:  # noqa: BLE001 - guard against malformed entries
            logger.debug("Failed to parse repository entry %s: %s", raw, exc)
            return None

    def _sort_entries(self, entries: list[PluginRepositoryEntry], sort_by: str) -> list[PluginRepositoryEntry]:
        key = sort_by.lower()
        if key == "downloads":
            return sorted(entries, key=lambda entry: entry.downloads, reverse=True)
        if key == "rating":
            return sorted(entries, key=lambda entry: entry.rating, reverse=True)
        if key == "updated_at":
            return sorted(entries, key=lambda entry: entry.updated_at, reverse=True)
        return sorted(entries, key=lambda entry: entry.name.lower())

    @staticmethod
    def _coerce_str_list(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    @staticmethod
    def _coerce_int(value: object, default: int = 0) -> int:
        try:
            return int(cast(Any, value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_float(value: object, default: float = 0.0) -> float:
        try:
            return float(cast(Any, value))
        except (TypeError, ValueError):
            return default


__all__ = ["RepositoryManager", "PluginRepositoryEntry"]

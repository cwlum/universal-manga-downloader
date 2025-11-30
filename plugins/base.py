"""Plugin base classes and dynamic loader for Universal Manga Downloader."""

from __future__ import annotations

import importlib.util
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import TypedDict, cast

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ParsedChapter(TypedDict):
    """Structured chapter data emitted by parser plugins."""

    title: str
    chapter: str
    image_urls: list[str]


class ChapterMetadata(TypedDict):
    """Metadata describing a downloaded chapter for converters."""

    title: str
    chapter: str
    source_url: str


class BasePlugin(ABC):
    """Abstract base class for parser plugins."""

    @abstractmethod
    def get_name(self) -> str:
        """Return a human friendly plugin name."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return ``True`` when the plugin can process the provided URL."""

    @abstractmethod
    def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
        """Extract chapter information from the given page."""

    def on_load(self) -> None:  # pragma: no cover - optional hook
        """Hook executed after the plugin instance has been created."""
        return None

    def on_unload(self) -> None:  # pragma: no cover - optional hook
        """Hook executed right before the plugin is disabled."""
        return None

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Return a filesystem-friendly representation of ``name``."""

        import re
        from pathlib import PurePath

        candidate = name.replace(":", " - ")
        candidate = candidate.replace("\n", " ").replace("\r", " ")
        candidate = re.sub(r"[\\/*?\"<>|]", " ", candidate)
        candidate = candidate.replace("_", " ")
        candidate = re.sub(r"\s+", " ", candidate)
        candidate = re.sub(r"-{2,}", "-", candidate)
        sanitized = candidate.strip(" .")
        if not sanitized:
            return "item"

        # Windows reserved filenames must not be used without a suffix.
        reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        upper_name = PurePath(sanitized).name.upper()
        if upper_name in reserved:
            sanitized = f"{sanitized} -"

        return sanitized


class BaseConverter(ABC):
    """Abstract base class for output converters."""

    @abstractmethod
    def get_name(self) -> str:
        """Return a human friendly converter name."""

    @abstractmethod
    def get_output_extension(self) -> str:
        """Return the file extension (including dot) produced by the converter."""

    @abstractmethod
    def convert(
        self,
        image_files: Sequence[Path],
        output_dir: Path,
        metadata: ChapterMetadata,
    ) -> Path | None:
        """Create an artifact from ``image_files`` and return its path."""

    def on_load(self) -> None:  # pragma: no cover - optional hook
        """Hook executed when the converter becomes active."""
        return None

    def on_unload(self) -> None:  # pragma: no cover - optional hook
        """Hook executed when the converter is disabled."""
        return None


class PluginType(str, Enum):
    """Enumeration describing the plugin category."""

    PARSER = "parser"
    CONVERTER = "converter"


PluginInstance = BasePlugin | BaseConverter


@dataclass(slots=True)
class PluginSource:
    """Description of a discovered plugin class."""

    plugin_type: PluginType
    module_name: str
    cls: type[PluginInstance]

    @property
    def class_name(self) -> str:
        return self.cls.__name__


class PluginLoader:
    """Discover plugin classes from a directory."""

    def __init__(self, plugin_dir: Path) -> None:
        self._plugin_dir = plugin_dir

    @property
    def plugin_dir(self) -> Path:
        return self._plugin_dir

    def discover(self) -> Iterator[PluginSource]:
        """Yield `PluginSource` objects for discoverable plugins."""

        for target_path in self._iter_plugin_targets():
            module = self._load_module(target_path)
            if module is None:
                continue
            yield from self._iter_module_plugins(module)

    def _iter_plugin_targets(self) -> Iterator[Path]:
        if not self._plugin_dir.exists():
            logger.warning("Plugin directory %s does not exist", self._plugin_dir)
            return

        for file_path in sorted(self._plugin_dir.glob("*.py")):
            if file_path.name in {"__init__.py"}:
                continue
            if file_path.name.startswith("_") or file_path.name.startswith("."):
                continue
            yield file_path
        for dir_path in sorted(self._plugin_dir.iterdir()):
            if not dir_path.is_dir():
                continue
            if dir_path.name.startswith("_") or dir_path.name.startswith("."):
                continue
            if not (dir_path / "__init__.py").exists():
                continue
            yield dir_path

    def _load_module(self, path: Path) -> ModuleType | None:
        if path.is_dir():
            module_name = f"{self._plugin_dir.name}.{path.name}"
            spec = importlib.util.spec_from_file_location(module_name, path / "__init__.py")
        else:
            module_name = f"{self._plugin_dir.name}.{path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            logger.warning("Skipping plugin %s: unable to create module spec", path)
            return None

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:  # noqa: BLE001 - surface plugin loader errors
            logger.exception("Failed to load plugin module %s", path)
            return None
        return module

    def _iter_module_plugins(self, module: ModuleType) -> Iterator[PluginSource]:
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                yield PluginSource(PluginType.PARSER, module.__name__, cast(type[PluginInstance], obj))
            elif issubclass(obj, BaseConverter) and obj is not BaseConverter:
                yield PluginSource(PluginType.CONVERTER, module.__name__, cast(type[PluginInstance], obj))


@dataclass(slots=True)
class PluginRecord:
    """Container describing a loaded plugin instance."""

    name: str
    plugin_type: PluginType
    instance: PluginInstance
    enabled: bool = True
    module_name: str = ""
    class_name: str = ""


class PluginManager:
    """Discover and manage parser and converter plugins."""

    def __init__(self, plugin_dir: Path | None = None, loader: PluginLoader | None = None) -> None:
        plugin_dir = plugin_dir or Path(__file__).resolve().parent
        self._loader = loader or PluginLoader(plugin_dir)
        self._plugin_dir = self._loader.plugin_dir
        self._records: list[PluginRecord] = []
        self._record_index: dict[tuple[PluginType, str], PluginRecord] = {}

    @property
    def plugin_dir(self) -> Path:
        """Return the directory used for plugin discovery."""

        return self._plugin_dir

    def load_plugins(self) -> None:
        """Discover plugins via the configured loader and instantiate them."""

        if self._records:
            self.shutdown()
        for source in self._loader.discover():
            self._register_plugin(source.cls, source.plugin_type, source.module_name)

    def _register_module(self, module: ModuleType) -> None:
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                self._register_plugin(obj, PluginType.PARSER, module.__name__)
            elif issubclass(obj, BaseConverter) and obj is not BaseConverter:
                self._register_plugin(obj, PluginType.CONVERTER, module.__name__)

    def _register_plugin(self, cls: type[PluginInstance], plugin_type: PluginType, module_name: str) -> None:
        try:
            instance = cast(PluginInstance, cls())
        except Exception:  # noqa: BLE001 - plugin constructors may raise
            logger.exception("Failed to instantiate plugin %s.%s", module_name, cls.__name__)
            return

        name = instance.get_name()
        key = (plugin_type, name)
        if key in self._record_index:
            logger.warning(
                "Duplicate plugin detected: %s (%s). Keeping the first instance.",
                name,
                plugin_type.value,
            )
            return

        record = PluginRecord(
            name=name,
            plugin_type=plugin_type,
            instance=instance,
            module_name=module_name,
            class_name=cls.__name__,
        )
        self._records.append(record)
        self._record_index[key] = record

        try:
            instance.on_load()
        except Exception:  # noqa: BLE001 - plugin hooks may raise
            logger.exception("Plugin %s failed during on_load", name)

    def get_records(self, plugin_type: PluginType | None = None) -> list[PluginRecord]:
        """Return metadata about loaded plugins, optionally filtered by type."""

        if plugin_type is None:
            return list(self._records)
        return [record for record in self._records if record.plugin_type is plugin_type]

    def get_record(self, plugin_type: PluginType, name: str) -> PluginRecord | None:
        """Return plugin metadata for the specified name, if present."""

        return self._record_index.get((plugin_type, name))

    def iter_enabled_parsers(self) -> Iterator[BasePlugin]:
        """Yield active parser plugins."""

        for record in self._records:
            if record.plugin_type is PluginType.PARSER and record.enabled:
                yield cast(BasePlugin, record.instance)

    def iter_enabled_converters(self) -> Iterator[BaseConverter]:
        """Yield active converter plugins."""

        for record in self._records:
            if record.plugin_type is PluginType.CONVERTER and record.enabled:
                yield cast(BaseConverter, record.instance)

    def set_enabled(self, plugin_type: PluginType, name: str, enabled: bool) -> None:
        """Update the enabled state of the specified plugin."""

        record = self._record_index.get((plugin_type, name))
        if record is None:
            logger.warning("Attempted to toggle unknown plugin %s (%s)", name, plugin_type.value)
            return

        if record.enabled == enabled:
            return

        record.enabled = enabled
        hook = record.instance.on_load if enabled else record.instance.on_unload
        try:
            hook()
        except Exception:  # noqa: BLE001 - plugin hooks may raise
            logger.exception(
                "Plugin %s raised an exception during %s", name, "on_load" if enabled else "on_unload"
            )

    def shutdown(self) -> None:
        """Invoke ``on_unload`` for all active plugins."""

        for record in self._records:
            if not record.enabled:
                continue
            try:
                record.instance.on_unload()
            except Exception:  # noqa: BLE001
                logger.exception("Plugin %s failed during shutdown", record.name)

        self._records.clear()
        self._record_index.clear()


def compose_chapter_name(title: str | None, chapter: str | None) -> str:
    """Return a consistent human-friendly chapter label."""

    parts = [part.strip() for part in (title, chapter) if part and part.strip()]
    if not parts:
        return "Chapter"
    label = " - ".join(parts)
    return label.strip(" -")


__all__ = [
    "BaseConverter",
    "BasePlugin",
    "ChapterMetadata",
    "compose_chapter_name",
    "ParsedChapter",
    "PluginLoader",
    "PluginManager",
    "PluginRecord",
    "PluginSource",
    "PluginType",
]

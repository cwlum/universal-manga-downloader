# Plugin Development Guide

UMD plugins are small, focused modules that add site parsers or output converters without touching core code. This guide explains discovery, required interfaces, and validation steps.

## Discovery Rules

- Files under `plugins/` ending in `.py` (excluding `__init__.py` and names starting with `_`) are loaded in isolation.
- Classes inheriting `BasePlugin` (parser) or `BaseConverter` (converter) register automatically with `PluginManager`.
- Duplicate `get_name()` values per plugin type are ignored after the first successful load.
- Plugin state should be local to each module; shared helpers belong in `services/` or `utils/`.

## Parser Plugins

Parsers receive a `BeautifulSoup` document and the requested URL, and must return a `ParsedChapter`.

Required methods:
- `get_name() -> str`
- `can_handle(url: str) -> bool`
- `parse(soup: BeautifulSoup, url: str) -> ParsedChapter | None`

Skeleton:

```python
from __future__ import annotations

import logging
from bs4 import BeautifulSoup
from plugins.base import BasePlugin, ParsedChapter

logger = logging.getLogger(__name__)


class ExampleParser(BasePlugin):
    def get_name(self) -> str:
        return "Example"

    def can_handle(self, url: str) -> bool:
        return "example.com" in url

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
        title_el = soup.select_one("h1.chapter-title")
        images = [img["src"] for img in soup.select("img.page") if img.get("src")]
        if not title_el or not images:
            return None
        return ParsedChapter(
            title=self.sanitize_filename(title_el.get_text(strip=True)),
            chapter="Chapter_1",
            image_urls=images,
        )
```

Guidelines:
- Use `BasePlugin.sanitize_filename` before writing files.
- Keep network access out of plugins; add helpers under `services/` instead.
- Return `None` for recoverable failures (missing elements, empty image lists).
- Use module-level loggers (`logging.getLogger(__name__)`) instead of `print`.

## Converter Plugins

Converters transform downloaded images into another format and return the created file path (or `None` on failure).

Required methods:
- `get_name() -> str`
- `get_output_extension() -> str`
- `convert(image_files: Sequence[Path], output_dir: Path, metadata: ChapterMetadata) -> Path | None`

Guidelines:
- Assume `output_dir` already exists; only write inside it.
- Close file handles promptly (prefer context managers).
- Keep conversions deterministic and avoid side effects outside the target file.
- Add runtime dependencies to `requirements.txt` and document them in `README.md`.

## Lifecycle Hooks

Both plugin types can optionally implement:

- `on_load(self) -> None` — allocate caches, warm up resources.
- `on_unload(self) -> None` — release handles when disabled or on shutdown.

Exceptions in hooks are logged but should not crash the application; handle failures defensively.

## Testing and Validation

- Unit tests: `pytest tests/test_plugins -q`
- Linting and types: `ruff check .` and `mypy ...plugins/`
- Manual: start the GUI, enable/disable the plugin in Settings, and run a download end-to-end.
- Ensure `get_name()` strings are unique per plugin type and match what users should see in the Settings tab.

## Submission Checklist

- [ ] Parser/converter inherits the correct base class and implements required methods.
- [ ] Filenames are sanitized; no filesystem assumptions outside `output_dir`.
- [ ] Logging uses the standard logger; no `print` or runtime dependency installs.
- [ ] Tests, lint, and types pass; documentation for new behavior is added where relevant.

## Sharing Remote Plugins

- Use the scaffold in `plugin_repository/official` as the canonical wiki/repository for community plugins.
- Ensure your plugin passes `plugin_repository/official/scripts/validate_plugin.py` before publishing.
- Provide a GitHub Raw URL so users can install through Settings → Remote Plugins.
- See [`docs/REMOTE_PLUGINS.md`](docs/REMOTE_PLUGINS.md) for installation & safety guidance.

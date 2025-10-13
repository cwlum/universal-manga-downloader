# Plugin Development Guide

Universal Manga Downloader exposes a small but powerful plugin surface so contributors can add support for new manga sources or output formats without touching the GUI code. This guide documents the expectations for parser and converter plugins, shares naming and packaging conventions, and highlights how to validate your work locally.

## How Discovery Works

- Plugins live in the `plugins/` package. Every top-level `*.py` module (excluding `__init__.py`, hidden files, and names that start with an underscore) is inspected.
- `PluginLoader` creates an isolated module namespace per file, catches import errors, and logs failures without interrupting other plugins.
- All classes that inherit from `BasePlugin` or `BaseConverter` are registered automatically by `PluginManager`. No manual registration is required.
- Duplicate `get_name()` values for the same `PluginType` are ignored to keep the first successfully loaded implementation.

Keeping modules focused—one parser or converter per file—is encouraged. Shared helpers should live under `core/` or `services/` instead of being duplicated across plugins.

## Authoring Parser Plugins

Parser plugins receive a `BeautifulSoup` document together with the requested URL. They must emit a `ParsedChapter` describing the chapter metadata and image URLs.

```python
from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from plugins.base import BasePlugin, ParsedChapter


logger = logging.getLogger(__name__)


class ExampleParser(BasePlugin):
    """Minimal parser demonstrating required methods."""

    def get_name(self) -> str:
        return "Example"

    def can_handle(self, url: str) -> bool:
        return "example.com" in url

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
        title = soup.find("h1", class_="chapter-title")
        images = [img["src"] for img in soup.select(".reader img") if img.get("src")]
        if not images or title is None:
            return None
        return ParsedChapter(
            title=self.sanitize_filename(title.get_text(strip=True) or "Example"),
            chapter="Chapter_1",
            image_urls=images,
        )

    def on_load(self) -> None:
        logger.info("Example parser ready")
```

Guidelines:

- Use logging instead of `print` and prefer `logger.debug` for noisy events. Create a module-level logger via `logging.getLogger(__name__)`.
- Always sanitize filenames using `BasePlugin.sanitize_filename` before writing files.
- Keep network access out of plugins; rely on existing services or add new ones under `services/`.
- Handle HTML changes defensively—early `None` returns signal the GUI that parsing failed without crashing the app.

## Authoring Converter Plugins

Converter plugins transform downloaded image files into another format. Implementations receive an ordered `Sequence[Path]`, an `output_dir`, and a `ChapterMetadata` mapping.

```python
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from plugins.base import BaseConverter, ChapterMetadata


class ExampleConverter(BaseConverter):
    """Stores images without transformation."""

    def get_name(self) -> str:
        return "Example"

    def get_output_extension(self) -> str:
        return ".zip"

    def convert(
        self,
        image_files: Sequence[Path],
        output_dir: Path,
        metadata: ChapterMetadata,
    ) -> Path | None:
        if not image_files:
            return None
        destination = output_dir / f"{metadata['title']}_{metadata['chapter']}{self.get_output_extension()}"
        # Implement conversion logic here
        return destination
```

Guidelines:

- Close files promptly to avoid leaking handles. Use context managers where possible.
- Write to the provided `output_dir` only; the manager handles directory creation.
- Return `None` to indicate failure—`PluginManager` will log the event and continue processing the queue.
- Never install dependencies at runtime. If your converter needs a library (for example, `Pillow`), add it to `requirements.txt` and document the requirement in `README.md`.

## Lifecycle Hooks

Both parser and converter plugins may implement optional `on_load` and `on_unload` methods. These are useful for allocating caches or releasing resources when a plugin is toggled in the GUI. Exceptions raised inside hooks are logged but do not stop the application, so prefer defensive error handling.

## Testing Plugins

- Use `PluginLoader` directly in unit tests to ensure your plugin is discoverable.
- For parser plugins, feed saved HTML fixtures into `BeautifulSoup` and assert that `parse` returns the expected `ParsedChapter`.
- For converter plugins, create temporary directories with a few image stubs and verify the produced archive or document.
- Run `ruff check .` and `mypy .` locally before submitting changes. The codebase targets Python 3.11.

Following these conventions keeps the plugin ecosystem consistent and makes it easier for maintainers to review contributions quickly.

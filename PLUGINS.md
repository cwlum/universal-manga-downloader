# Plugin Development Guide

UMD plugins are small, focused modules that add site parsers or output converters without touching core code. This guide explains the plugin architecture, required interfaces, and submission process.

## Table of Contents

- [Where to Submit Your Plugin](#-where-to-submit-your-plugin)
  - [For Community Developers (Recommended)](#for-community-developers-recommended)
  - [For Official Plugins](#for-official-plugins)
- [Plugin Architecture](#plugin-architecture)
- [Discovery Rules](#discovery-rules)
- [Parser Plugins](#parser-plugins)
  - [Required Methods](#required-methods)
  - [Complete Template](#complete-template-for-community-plugins)
  - [Guidelines](#guidelines)
- [Converter Plugins](#converter-plugins)
  - [Required Methods](#required-methods-1)
  - [Complete Template](#complete-template-for-community-plugins-1)
  - [Guidelines](#guidelines-1)
- [Metadata Format](#metadata-format)
  - [Required Fields](#required-fields)
  - [Optional Fields](#optional-fields)
- [Lifecycle Hooks](#lifecycle-hooks)
- [Testing Community Plugins Locally](#testing-community-plugins-locally)
  - [Option 1: Test as a Built-in Plugin (Quick)](#option-1-test-as-a-built-in-plugin-quick)
  - [Option 2: Test as a Remote Plugin (Realistic)](#option-2-test-as-a-remote-plugin-realistic)
  - [Validation](#validation)
- [Testing and Validation (Official Plugins)](#testing-and-validation-official-plugins)
- [Submission Checklist](#submission-checklist)
  - [For Community Plugins](#for-community-plugins-community-plugins)
  - [For Official Plugins](#for-official-plugins-plugins)
- [Sharing Community Plugins](#sharing-community-plugins)
- [Common Pitfalls](#common-pitfalls)

---

## 📍 Where to Submit Your Plugin

### For Community Developers (Recommended)

**Submit plugins to `community-plugins/` directory:**
- ✅ Community-contributed parsers and converters
- ✅ Users install via Remote Plugin system (opt-in, from wiki)
- ✅ Maintained by plugin authors
- ✅ See [community-plugins/README.md](community-plugins/README.md) for submission guide

### For Official Plugins

**The `plugins/` directory is for officially maintained plugins:**
- 🔒 Bundled with UMD (users get them automatically when cloning)
- 🔒 Requires maintainer approval and ongoing support commitment
- 🔒 Only accept PRs for critical features, bug fixes, or widely-used sites

---

## Plugin Architecture

UMD has two plugin directories:

| Directory | Purpose | Installation | Maintenance | In Git |
|-----------|---------|--------------|-------------|--------|
| `plugins/` | Official built-in plugins | Automatic (bundled with UMD) | UMD maintainers | ✅ Yes |
| `community-plugins/` | Community plugin repository | Manual (via Remote Plugins UI) | Plugin authors | ✅ Yes (for developers) |
| `plugins/*.py` (user-downloaded) | User's installed remote plugins | Via Settings → Remote Plugins | N/A | ❌ No (gitignored) |

**📝 Note for users:** When you clone the repository, you get all official plugins in `plugins/`. The `community-plugins/` directory is for developers who want to submit plugins—you can safely ignore it. Install community plugins via the Remote Plugins feature in Settings instead.

**📝 Note for developers:** Develop your plugin for `community-plugins/` and submit a PR. Do not add plugins directly to `plugins/` unless you're fixing an official plugin bug.

---

## Discovery Rules

- Files under `plugins/` ending in `.py` (excluding `__init__.py` and names starting with `_`) are loaded automatically when UMD starts.
- Classes inheriting `BasePlugin` (parser) or `BaseConverter` (converter) register automatically with `PluginManager`.
- Duplicate `get_name()` values per plugin type are ignored after the first successful load.
- Plugin state should be local to each module; shared helpers belong in `services/` or `utils/`.

For `community-plugins/`, users install plugins manually via:
1. Settings → Remote Plugins
2. Paste the raw GitHub URL (e.g., `https://raw.githubusercontent.com/.../community-plugins/converters/your_plugin.py`)
3. Click Install

---

## Parser Plugins

Parsers receive a `BeautifulSoup` document and the requested URL, and must return a `ParsedChapter`.

### Required Methods
- `get_name() -> str`
- `can_handle(url: str) -> bool`
- `parse(soup: BeautifulSoup, url: str) -> ParsedChapter | None`

### Complete Template (for `community-plugins/`)

**⚠️ IMPORTANT:** `from __future__ import annotations` **MUST** be the first line of your file (before the docstring).

```python
from __future__ import annotations

"""
Universal Manga Downloader Plugin

Name: Your Parser Name
Author: Your Name
Version: 1.0.0
Description: Parser for example.com manga chapters
Repository: https://github.com/yourusername/your-repo
License: MIT
Dependencies:
"""

import logging
from bs4 import BeautifulSoup
from plugins.base import BasePlugin, ParsedChapter

logger = logging.getLogger(__name__)


class ExampleParser(BasePlugin):
    def get_name(self) -> str:
        return "Example Parser"

    def can_handle(self, url: str) -> bool:
        return "example.com" in url

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
        title_el = soup.select_one("h1.chapter-title")
        images = [img["src"] for img in soup.select("img.page") if img.get("src")]
        if not title_el or not images:
            logger.warning("Failed to extract chapter data from %s", url)
            return None
        return ParsedChapter(
            title=self.sanitize_filename(title_el.get_text(strip=True)),
            chapter="Chapter_1",
            image_urls=images,
        )
```

### Guidelines
- Use `BasePlugin.sanitize_filename` before writing files.
- Keep network access out of plugins; add helpers under `services/` instead.
- Return `None` for recoverable failures (missing elements, empty image lists).
- Use module-level loggers (`logging.getLogger(__name__)`) instead of `print`.

---

## Converter Plugins

Converters transform downloaded images into another format and return the created file path (or `None` on failure).

### Required Methods
- `get_name() -> str`
- `get_output_extension() -> str`
- `convert(image_files: Sequence[Path], output_dir: Path, metadata: ChapterMetadata) -> Path | None`

### Complete Template (for `community-plugins/`)

**⚠️ IMPORTANT:** `from __future__ import annotations` **MUST** be the first line of your file (before the docstring).

```python
from __future__ import annotations

"""
Universal Manga Downloader Plugin

Name: Your Converter Name
Author: Your Name
Version: 1.0.0
Description: Convert manga chapters to XYZ format
Repository: https://github.com/yourusername/your-repo
License: MIT
Dependencies: some-library>=1.0.0
"""

import logging
from collections.abc import Sequence
from pathlib import Path

from plugins.base import BaseConverter, ChapterMetadata

logger = logging.getLogger(__name__)


class YourConverter(BaseConverter):
    def get_name(self) -> str:
        return "XYZ Converter"

    def get_output_extension(self) -> str:
        return ".xyz"

    def convert(
        self,
        image_files: Sequence[Path],
        output_dir: Path,
        metadata: ChapterMetadata,
    ) -> Path | None:
        """Convert image files to XYZ format."""
        if not image_files:
            logger.warning("No images provided for conversion")
            return None

        try:
            # Import dependencies only when needed
            import some_library
        except ImportError:
            logger.error("some-library is not installed. Install it with: pip install some-library>=1.0.0")
            return None

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Your conversion logic here
        title = metadata.get("title", "Unknown")
        chapter = metadata.get("chapter", "Chapter")
        output_path = output_dir / f"{title} - {chapter}.xyz"

        try:
            # Perform conversion
            # ...
            logger.info("Conversion successful: %s", output_path)
            return output_path
        except Exception as e:
            logger.error("Conversion failed: %s", e)
            return None
```

### Guidelines
- Assume `output_dir` already exists; only write inside it.
- Close file handles promptly (prefer context managers).
- Keep conversions deterministic and avoid side effects outside the target file.
- Import heavy dependencies inside methods (lazy loading) to avoid startup overhead.
- Handle `ImportError` gracefully with helpful error messages.

---

## Metadata Format

The metadata docstring is **required** for community plugins (validated by `scripts/validate_community_plugin.py`).

### Required Fields
- `Name:` — Human-friendly plugin name (displayed in UI)
- `Author:` — Your name or GitHub username
- `Version:` — Semantic version (e.g., `1.0.0`)
- `Description:` — Brief description of what the plugin does

### Optional Fields
- `Repository:` — Link to plugin's source repository
- `License:` — License identifier (e.g., `MIT`, `Apache-2.0`)
- `Dependencies:` — Comma-separated list of pip packages with versions

### Example
```python
"""
Universal Manga Downloader Plugin

Name: EPUB Converter
Author: UMD Community
Version: 1.0.0
Description: Convert manga chapters to EPUB format with cover support
Repository: https://github.com/cwlum/universal-manga-downloader
License: MIT
Dependencies: ebooklib>=0.18, pillow>=10.0.0
"""
```

---

## Lifecycle Hooks

Both plugin types can optionally implement:

- `on_load(self) -> None` — allocate caches, warm up resources.
- `on_unload(self) -> None` — release handles when disabled or on shutdown.

Exceptions in hooks are logged but should not crash the application; handle failures defensively.

---

## Testing Community Plugins Locally

Before submitting to `community-plugins/`, test your plugin:

### Option 1: Test as a Built-in Plugin (Quick)

1. **Copy your plugin to `plugins/` temporarily:**
   ```bash
   cp my_plugin.py plugins/
   ```

2. **Restart UMD** — your plugin will load automatically

3. **Test the functionality** in the GUI or CLI

4. **Move it to `community-plugins/` for submission:**
   ```bash
   mv plugins/my_plugin.py community-plugins/parsers/  # or converters/
   ```

### Option 2: Test as a Remote Plugin (Realistic)

1. **Place your plugin in `community-plugins/`:**
   ```bash
   cp my_plugin.py community-plugins/parsers/
   ```

2. **Commit and push to your fork:**
   ```bash
   git add community-plugins/
   git commit -m "Add my plugin"
   git push
   ```

3. **Install via Remote Plugins UI** using the raw GitHub URL:
   ```
   https://raw.githubusercontent.com/YOUR_USERNAME/universal-manga-downloader/YOUR_BRANCH/community-plugins/parsers/my_plugin.py
   ```

4. **Test the functionality**

### Validation

Before submitting, **always** run the validation script:

```bash
python3 scripts/validate_community_plugin.py community-plugins/parsers/my_plugin.py
```

This checks:
- ✅ Python syntax is valid
- ✅ `from __future__ import annotations` is at the top
- ✅ Metadata docstring is present with `Name:` field
- ✅ Correct base class is imported and used
- ✅ No dangerous code patterns (will be manually reviewed)

---

## Testing and Validation (Official Plugins)

For official plugins in `plugins/`:

- Unit tests: `pytest tests/test_plugins -q`
- Linting and types: `ruff check .` and `mypy plugins/`
- Manual: start the GUI, enable/disable the plugin in Settings, and run a download end-to-end.
- Ensure `get_name()` strings are unique per plugin type and match what users should see in the Settings tab.

---

## Submission Checklist

### For Community Plugins (`community-plugins/`)

- [ ] Plugin file added to `community-plugins/parsers/` or `community-plugins/converters/`
- [ ] `from __future__ import annotations` is **the first line** of the file
- [ ] Metadata docstring is complete with all required fields
- [ ] Passes validation: `python3 scripts/validate_community_plugin.py <file>`
- [ ] Parser/converter inherits the correct base class and implements required methods
- [ ] Filenames are sanitized; no filesystem assumptions outside `output_dir`
- [ ] Logging uses the standard logger; no `print` statements
- [ ] No dangerous code (exec, eval, os.system, etc.)
- [ ] Tested and works as described
- [ ] PR title follows format: `[Plugin] Add YourPluginName`
- [ ] PR description explains what sites/formats your plugin supports

### For Official Plugins (`plugins/`)

- [ ] Parser/converter inherits the correct base class and implements required methods
- [ ] Filenames are sanitized; no filesystem assumptions outside `output_dir`
- [ ] Logging uses the standard logger; no `print` or runtime dependency installs
- [ ] Tests, lint, and types pass
- [ ] Documentation for new behavior is added where relevant
- [ ] Maintainer has approved the addition

---

## Sharing Community Plugins

Once your plugin is merged into `community-plugins/`:

1. **It appears in the wiki** — Users can browse available plugins at the wiki page
2. **Users install via URL** — They copy the raw GitHub URL from the wiki
3. **You maintain it** — Update your plugin by submitting new PRs with version bumps
4. **Users get updates** — They can check for updates via Settings → Remote Plugins → Check Updates

See [`docs/REMOTE_PLUGINS.md`](docs/REMOTE_PLUGINS.md) for user installation & safety guidance.

---

## Common Pitfalls

### ❌ Wrong: Metadata after `from __future__`
```python
"""Metadata"""
from __future__ import annotations  # ← Validation fails!
```

### ✅ Correct: `from __future__` first
```python
from __future__ import annotations  # ← Must be first!
"""Metadata"""
```

### ❌ Wrong: Missing metadata for community plugins
```python
from __future__ import annotations
import logging
# No docstring = validation fails!
```

### ✅ Correct: Complete metadata
```python
from __future__ import annotations
"""
Universal Manga Downloader Plugin
Name: My Plugin
...
"""
```

### ❌ Wrong: Submitting to wrong directory
```bash
# Don't add community plugins to plugins/
cp my_plugin.py plugins/  # ← Wrong!
```

### ✅ Correct: Submit to community-plugins
```bash
cp my_plugin.py community-plugins/parsers/  # ← Correct!
```

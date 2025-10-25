# Developer Onboarding Guide

Welcome to the Universal Manga Downloader project! This guide will help you get started contributing to the codebase.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** installed (Python 3.11 recommended)
- **Git** for version control
- A code editor with Python support (VS Code, PyCharm, etc.)
- Basic knowledge of Python, Tkinter, and web scraping

## Quick Start (5 Minutes)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/cwlum/bato-downloader.git
cd bato-downloader

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install ruff mypy pytest
```

### 2. Run the Application

```bash
# On macOS/Linux
./manga

# On Windows
manga.bat

# Fallback
python bootstrap.py
```

The GUI should open. Try searching for a manga and downloading a chapter.

### 3. Run Quality Checks

```bash
# Linting
ruff check .

# Type checking
mypy .

# Run tests (if available)
pytest
```

## Project Structure Tour

### Entry Point
- **`manga_downloader.py`**: Main application entry point and GUI coordinator

### Core Modules
- **`core/queue_manager.py`**: Thread-safe download queue management

### Services
- **`services/bato_service.py`**: Web scraping for Bato.to search and series info

### Plugin System
- **`plugins/base.py`**: Plugin infrastructure (loaders, managers, base classes)
- **`plugins/bato_parser.py`**: Parser for Bato.to chapter pages
- **`plugins/pdf_converter.py`**: PDF converter plugin
- **`plugins/cbz_converter.py`**: CBZ converter plugin

### Utilities
- **`utils/file_utils.py`**: File system helpers
- **`utils/ui_helpers.py`**: Tkinter UI helpers
- **`config.py`**: Centralized configuration

### Documentation
- **`README.md`**: User-facing documentation
- **`DEVELOPMENT.md`**: Development setup and workflows
- **`ARCHITECTURE.md`**: System design and patterns
- **`ONBOARDING.md`**: This file!
- **`AGENTS.md`**: AI agent guidelines
- **`PLUGINS.md`**: Plugin development guide
- **`CONTRIBUTING.md`**: Contribution guidelines

## Common Tasks

### Task 1: Add a New Website Parser

1. **Create a new parser file**:
   ```bash
   touch plugins/mysite_parser.py
   ```

2. **Implement the BasePlugin interface**:
   ```python
   from plugins.base import BasePlugin, ParsedChapter
   from bs4 import BeautifulSoup
   
   class MySiteParser(BasePlugin):
       def get_name(self) -> str:
           return "MySite Parser"
       
       def can_handle(self, url: str) -> bool:
           return "mysite.com" in url
       
       def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
           # Extract title, chapter, and image URLs from the page
           title = soup.find("h1", class_="title").get_text(strip=True)
           chapter = soup.find("span", class_="chapter").get_text(strip=True)
           images = [img["src"] for img in soup.select("img.chapter-image")]
           
           return {
               "title": title,
               "chapter": chapter,
               "image_urls": images,
           }
   ```

3. **Test your parser**:
   ```bash
   python manga_downloader.py
   # The plugin will be automatically discovered
   # Try downloading a chapter from mysite.com
   ```

### Task 2: Add a New Output Format

1. **Create a converter file**:
   ```bash
   touch plugins/epub_converter.py
   ```

2. **Implement the BaseConverter interface**:
   ```python
   from pathlib import Path
   from collections.abc import Sequence
   from plugins.base import BaseConverter, ChapterMetadata
   
   class EPUBConverter(BaseConverter):
       def get_name(self) -> str:
           return "EPUB Converter"
       
       def get_output_extension(self) -> str:
           return ".epub"
       
       def convert(
           self,
           image_files: Sequence[Path],
           output_dir: Path,
           metadata: ChapterMetadata,
       ) -> Path | None:
           # Create EPUB file from images
           output_path = output_dir / f"{metadata['title']}_{metadata['chapter']}.epub"
           # ... EPUB creation logic ...
           return output_path
   ```

### Task 3: Fix a Bug

1. **Create a feature branch**:
   ```bash
   git checkout -b fix/issue-123-description
   ```

2. **Make your changes** and test locally

3. **Run quality checks**:
   ```bash
   ruff check --fix .
   mypy .
   pytest
   ```

4. **Commit and push**:
   ```bash
   git add .
   git commit -m "Fix: Brief description of the fix"
   git push origin fix/issue-123-description
   ```

5. **Open a Pull Request** on GitHub

### Task 4: Add Configuration

1. **Update `config.py`**:
   ```python
   @dataclass(frozen=True)
   class DownloadConfig:
       # ... existing fields ...
       my_new_setting: int = 42
   ```

2. **Use the config** in your code:
   ```python
   from config import CONFIG
   
   value = CONFIG.download.my_new_setting
   ```

## Understanding Key Concepts

### Threading Model

The app uses a multi-threaded architecture:

- **Main Thread**: Tkinter event loop (all UI updates)
- **Chapter Workers**: ThreadPoolExecutor for downloading chapters
- **Image Workers**: Nested ThreadPoolExecutor for downloading images

All UI updates **must** use `self.after(0, callback)` to schedule work on the main thread.

### Plugin Discovery

Plugins are discovered automatically:

1. `PluginLoader` scans `plugins/` directory
2. Loads all `.py` files (except `__init__.py` and private modules)
3. Finds subclasses of `BasePlugin` or `BaseConverter`
4. `PluginManager` instantiates and registers them
5. Plugins can be enabled/disabled from the Settings tab

### Queue State Management

Downloads go through these states:

- `PENDING`: Queued but not started
- `RUNNING`: Currently downloading
- `SUCCESS`: Completed successfully
- `ERROR`: Failed with an error
- `PAUSED`: User paused the download
- `CANCELLED`: User cancelled the download

The `QueueManager` class handles all state transitions with thread-safe locking.

### Type Hints

This project uses comprehensive type hints:

- Import types from `typing` or `collections.abc`
- Use `from __future__ import annotations` for forward references
- Run `mypy .` to catch type errors

## Coding Standards

### Style Guide

- Follow PEP 8 (enforced by `ruff`)
- Use descriptive variable and function names
- Add docstrings to public functions and classes
- Keep functions focused and small

### Type Safety

- Add type hints to all function signatures
- Use `TypedDict` for structured dictionaries
- Use `@dataclass` for data classes
- Avoid `Any` type when possible

### Logging

- Use `logging` module instead of `print()`
- Configure loggers at module scope
- Use appropriate log levels (INFO, WARNING, ERROR)

Example:
```python
import logging

logger = logging.getLogger(__name__)

logger.info("Starting download: %s", chapter_title)
logger.warning("Failed to parse: %s", url)
logger.error("Network error: %s", str(exc))
```

### Error Handling

- Catch specific exceptions (not bare `except:`)
- Use `# noqa: BLE001` only when catching all exceptions is intentional
- Log exceptions with `logger.exception()` for stack traces
- Surface errors to the UI via queue state

## Testing Strategy

### Manual Testing

1. Launch the app
2. Test search functionality
3. Test series browsing
4. Test downloading (single chapter, range, all)
5. Test pause/resume/cancel
6. Test plugin enable/disable

### Automated Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=plugins --cov=services --cov-report=html

# Run specific test file
pytest tests/test_core/test_queue_manager.py -v
```

## Debugging Tips

### Enable Debug Logging

```python
# In manga_downloader.py
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Queue State

Add breakpoints or logging in `QueueManager` methods to track state changes.

### Test Parser in Isolation

```python
from plugins.bato_parser import BatoParser
from bs4 import BeautifulSoup
import requests

parser = BatoParser()
response = requests.get("https://bato.to/chapter/...")
soup = BeautifulSoup(response.text, "html.parser")
result = parser.parse(soup, response.url)
print(result)
```

## Getting Help

- **Documentation**: Read `ARCHITECTURE.md` for design details
- **Plugin Guide**: See `PLUGINS.md` for plugin development
- **Issues**: Check GitHub Issues for known bugs and feature requests
- **Code Review**: Open a draft PR for early feedback

## Next Steps

1. Pick an issue labeled `good-first-issue`
2. Read the relevant documentation
3. Set up your development environment
4. Make your changes
5. Run quality checks
6. Open a pull request

Welcome aboard, and happy coding! 🚀

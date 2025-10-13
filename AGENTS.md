# AI Agent Guidelines for Universal Manga Downloader

> **Purpose**: This document serves as the definitive guide for AI agents (like me!) working on this project. Follow these guidelines to ensure high-quality, consistent contributions.

## Table of Contents

- [Quick Start Checklist](#quick-start-checklist)
- [Project Understanding](#project-understanding)
- [Mandatory Workflow](#mandatory-workflow)
- [Code Standards](#code-standards)
- [Architecture Principles](#architecture-principles)
- [Quality Gates](#quality-gates)
- [Common Tasks](#common-tasks)
- [Pitfalls to Avoid](#pitfalls-to-avoid)
- [Decision Framework](#decision-framework)

---

## Quick Start Checklist

**Before making ANY changes**, complete this checklist:

- [ ] Read `ARCHITECTURE.md` to understand system design
- [ ] Check `ONBOARDING.md` for project setup
- [ ] Review `DEVELOPMENT.md` for workflows
- [ ] Understand the plugin architecture (`plugins/base.py`)
- [ ] Locate relevant files before proposing changes
- [ ] Verify you're on a feature branch (not `main`)

**For every task**:
1. ✅ Understand the request fully before coding
2. ✅ Create a feature branch
3. ✅ Make changes with clear intent
4. ✅ Run quality checks (ruff, mypy)
5. ✅ Commit with descriptive messages
6. ✅ Push and prepare PR description

---

## Project Understanding

### Core Architecture

```
Universal Manga Downloader
├── UI Layer (manga_downloader.py)
│   └── Tkinter GUI, event handling, user interaction
├── Core Layer (core/)
│   ├── queue_manager.py - Thread-safe queue management
│   └── pdf_converter.py - DEPRECATED (use plugins instead)
├── Service Layer (services/)
│   └── bato_service.py - Web scraping for Bato.to
├── Plugin System (plugins/)
│   ├── base.py - Plugin infrastructure
│   ├── bato_parser.py - Chapter parsing
│   ├── pdf_converter.py - PDF generation
│   └── cbz_converter.py - CBZ archives
├── Utilities (utils/)
│   ├── file_utils.py - File system operations
│   └── ui_helpers.py - Tkinter helpers
└── Configuration (config.py)
    └── Centralized application settings
```

### Key Concepts

1. **Plugin Architecture**: Parsers and converters are auto-discovered from `plugins/`
2. **Thread Safety**: All queue operations use `QueueManager` with proper locking
3. **Type Safety**: Comprehensive type hints throughout (Python 3.10+ syntax)
4. **Separation of Concerns**: UI, business logic, and data access are separate

### Critical Files

- **DO NOT MODIFY** without understanding:
  - `manga_downloader.py` - Main GUI (1500+ lines, complex threading)
  - `plugins/base.py` - Plugin infrastructure (breaks all plugins if changed)
  - `config.py` - Global configuration (immutable dataclasses)

- **SAFE TO MODIFY**:
  - Documentation files (`*.md`)
  - Utility modules (`utils/`)
  - New plugin files (in `plugins/`)

### Dependencies

**Runtime** (in `requirements.txt`):
- `requests`, `beautifulsoup4` - Web scraping
- `Pillow` - Image processing
- `cloudscraper` - Cloudflare bypass
- `sv-ttk` - Tkinter theme

**Development** (installed separately):
- `ruff` - Linting
- `mypy` - Type checking
- `pytest` - Testing

---

## Mandatory Workflow

### Phase 1: Environment Setup (BLOCKING)

**Every implementation task MUST start with**:

```bash
# 1. Git synchronization
git fetch --all --prune
git pull --ff-only

# 2. Dependency installation
pip install -r requirements.txt

# 3. Validation
python --version  # Must be 3.10+
pip list | grep -E '(requests|beautifulsoup4|Pillow|cloudscraper|sv-ttk)'
```

**If any step fails**, STOP and report. Do not proceed.

### Phase 2: Implementation

```bash
# 1. Create feature branch
git checkout -b feature/your-task-description

# 2. Make changes
# ... edit files ...

# 3. Quality checks (MANDATORY)
ruff check .
mypy .
# Fix all errors before proceeding

# 4. Commit
git add -A
git commit -m "type: description"

# 5. Push
git push -u origin feature/your-task-description
```

### Phase 3: Pull Request (MANDATORY)

**Every implementation MUST end with a PR**. Include:

1. **Title**: `type: Brief description`
2. **Description**:
   - What changed and why
   - Testing steps
   - Breaking changes (if any)
3. **Quality Evidence**:
   - ✅ `ruff check .` passed
   - ✅ `mypy .` passed
   - ✅ Manual testing completed

---

## Code Standards

### Python Style

```python
# ✅ GOOD
from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)

class ChapterData(TypedDict):
    """Chapter metadata structure."""
    title: str
    chapter: str
    url: str

def process_chapter(data: ChapterData) -> Path | None:
    """Process a chapter and return output path."""
    try:
        logger.info("Processing: %s", data["title"])
        # ... implementation ...
        return output_path
    except Exception as exc:
        logger.exception("Failed to process chapter")
        return None

# ❌ BAD
def process_chapter(data):  # No type hints
    print(f"Processing {data['title']}")  # Use logging, not print
    # No error handling
    return output_path
```

### Type Hints Rules

1. **ALWAYS use type hints** for function signatures
2. **Use Python 3.10+ syntax**: `list[str]`, `dict[str, int]`, `X | None`
3. **Import from `__future__`**: `from __future__ import annotations`
4. **Prefer concrete types**: `TypedDict`, `dataclass` over `dict`, `tuple`
5. **Use `TYPE_CHECKING`** for circular imports:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
```

### Logging Rules

```python
import logging

logger = logging.getLogger(__name__)

# ✅ GOOD
logger.debug("Detailed trace info")
logger.info("Processing chapter: %s", title)
logger.warning("Missing element: %s", selector)
logger.error("Parse failed: %s", error)
logger.exception("Unexpected error")  # Includes traceback

# ❌ BAD
print("Processing chapter")  # Never use print()
logger.info(f"Processing {title}")  # Don't use f-strings in logs
```

### Error Handling

```python
# ✅ GOOD - Specific exceptions
try:
    result = parse_chapter(soup)
except ValueError as exc:
    logger.error("Invalid data: %s", exc)
    return None
except requests.RequestException as exc:
    logger.error("Network error: %s", exc)
    return None

# ❌ BAD - Bare except
try:
    result = parse_chapter(soup)
except:  # Too broad, hides bugs
    return None
```

### Documentation

```python
# ✅ GOOD - Complete docstring
def convert_images(
    image_files: Sequence[Path],
    output_dir: Path,
    metadata: ChapterMetadata,
) -> Path | None:
    """
    Convert a sequence of images to PDF format.

    Args:
        image_files: Ordered list of image file paths
        output_dir: Directory for output file
        metadata: Chapter metadata for naming

    Returns:
        Path to created PDF file, or None on failure

    Raises:
        OSError: If output directory is not writable
    """
    ...

# ❌ BAD - No docstring or minimal docstring
def convert_images(image_files, output_dir, metadata):
    # Convert images
    ...
```

---

## Architecture Principles

### 1. Plugin System

**When adding support for a new site or format**:

- ✅ Create a new plugin file in `plugins/`
- ✅ Inherit from `BasePlugin` or `BaseConverter`
- ✅ Implement required abstract methods
- ❌ DON'T modify `manga_downloader.py`
- ❌ DON'T modify `plugins/base.py` unless absolutely necessary

**Example**: See `plugins/bato_parser.py` or `plugins/pdf_converter.py`

### 2. Thread Safety

**Rules for multi-threaded code**:

1. **Queue operations**: Always use `QueueManager` methods
2. **UI updates**: Schedule via `self.after(0, callback)`
3. **Shared state**: Use locks (via `QueueManager`)
4. **Never**: Access Tkinter widgets from worker threads

```python
# ✅ GOOD - UI update from worker thread
def _worker_function(self):
    result = do_work()
    # Schedule UI update on main thread
    self.after(0, lambda: self._update_ui(result))

# ❌ BAD - Direct UI access from worker
def _worker_function(self):
    result = do_work()
    self.status_label.config(text=result)  # CRASH!
```

### 3. Configuration Management

**All configuration goes in `config.py`**:

```python
# ✅ GOOD - Use CONFIG
from config import CONFIG

max_workers = CONFIG.download.max_chapter_workers
timeout = CONFIG.download.request_timeout

# ❌ BAD - Hardcoded values
max_workers = 10
timeout = 30
```

### 4. File System Operations

**Use `utils/file_utils.py` helpers**:

```python
# ✅ GOOD
from utils.file_utils import sanitize_filename, ensure_directory

safe_name = sanitize_filename(user_input)
output_dir = ensure_directory(path)

# ❌ BAD - Reimplementing utilities
safe_name = user_input.replace("/", "_").replace("\\", "_")
os.makedirs(path, exist_ok=True)
```

---

## Quality Gates

### Mandatory Checks (BLOCKING)

**Before EVERY commit**:

```bash
# 1. Linting (must pass)
ruff check .

# 2. Type checking (must pass)
mypy .

# 3. Manual verification
python manga_downloader.py  # GUI should launch
```

### Fix Common Issues

**Ruff errors**:
```bash
# Auto-fix safe issues
ruff check --fix .

# Review remaining issues
ruff check .
```

**Mypy errors**:
```bash
# Add type hints to resolve
# Use # type: ignore[error-code] as last resort with comment
```

### Testing Strategy

**For new features**:
1. **Manual testing**: Run the GUI and test the feature
2. **Edge cases**: Test with invalid input
3. **Error handling**: Verify errors are logged, not crashed

**For plugins**:
1. **Parser**: Test with real URLs or HTML fixtures
2. **Converter**: Test with sample images
3. **Lifecycle**: Test enable/disable in Settings tab

---

## Common Tasks

### Task 1: Add a New Parser Plugin

```python
# 1. Create plugins/mysite_parser.py
from __future__ import annotations

import logging
from bs4 import BeautifulSoup
from plugins.base import BasePlugin, ParsedChapter

logger = logging.getLogger(__name__)

class MySiteParser(BasePlugin):
    def get_name(self) -> str:
        return "MySite Parser"
    
    def can_handle(self, url: str) -> bool:
        return "mysite.com/reader/" in url
    
    def parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None:
        try:
            title_elem = soup.select_one("h1.title")
            if not title_elem:
                return None
            
            title = self.sanitize_filename(title_elem.get_text(strip=True))
            chapter = "Chapter_1"  # Extract from page
            
            images = [
                img["src"]
                for img in soup.select("img.page")
                if img.get("src")
            ]
            
            if not images:
                return None
            
            return ParsedChapter(
                title=title,
                chapter=chapter,
                image_urls=images,
            )
        except Exception as exc:
            logger.exception("Parse error for %s", url)
            return None

# 2. Test manually
# 3. Run quality checks
# 4. Commit and push
```

### Task 2: Update Documentation

```bash
# 1. Identify which file to update
# - User-facing changes → README.md
# - Developer setup → DEVELOPMENT.md
# - Architecture → ARCHITECTURE.md
# - Plugin API → PLUGINS.md
# - AI agents → AGENTS.md

# 2. Make changes with clear diffs

# 3. Preview markdown rendering (optional)

# 4. Commit with docs: prefix
git commit -m "docs: Update installation instructions"
```

### Task 3: Fix a Bug

```bash
# 1. Reproduce the bug
# 2. Locate the relevant code
# 3. Write a fix with error handling
# 4. Test thoroughly
# 5. Commit with fix: prefix
git commit -m "fix: Handle missing title element in parser"
```

### Task 4: Refactor Code

```bash
# 1. Ensure tests pass before refactoring
# 2. Make incremental changes
# 3. Run quality checks after each change
# 4. Commit with refactor: prefix
git commit -m "refactor: Extract UI helpers into utils module"
```

---

## Pitfalls to Avoid

### ❌ Common Mistakes

1. **Skipping Environment Setup**
   - Always run `pip install -r requirements.txt` first
   - Verify git is synced before starting

2. **Modifying Core Files Without Understanding**
   - Read `ARCHITECTURE.md` before touching `manga_downloader.py`
   - Plugin changes go in `plugins/`, not core code

3. **Ignoring Type Errors**
   - Fix mypy errors, don't use `# type: ignore` without understanding
   - Add type hints, don't remove them

4. **Breaking Thread Safety**
   - Use `QueueManager` for all queue operations
   - Never access Tkinter widgets from worker threads

5. **Hardcoding Values**
   - Use `config.py` for constants
   - Don't duplicate configuration

6. **Poor Error Messages**
   - Log context: `logger.error("Parse failed for %s: %s", url, error)`
   - Not: `logger.error("Parse failed")`

7. **Forgetting Documentation**
   - Update docs when behavior changes
   - Add docstrings to new public functions

8. **Not Testing Edge Cases**
   - Test with missing elements
   - Test with malformed input
   - Test with network failures

### ✅ Best Practices

1. **Read Before Writing**
   - Inspect existing code before adding similar functionality
   - Check for existing utilities before reimplementing

2. **Small, Focused Commits**
   - One logical change per commit
   - Clear commit messages following conventions

3. **Defensive Programming**
   - Check for None before accessing
   - Validate input early
   - Return None on failure, don't raise in plugins

4. **Performance Awareness**
   - Use generators for large datasets
   - Close file handles promptly
   - Don't load all images in memory at once

---

## Decision Framework

### When Uncertain

**Follow this decision tree**:

1. **Is this a parser/converter addition?**
   - YES → Create plugin in `plugins/`
   - NO → Continue

2. **Is this a bug fix?**
   - YES → Locate code, fix, test, commit
   - NO → Continue

3. **Is this a refactoring?**
   - YES → Ensure tests pass first, refactor incrementally
   - NO → Continue

4. **Is this a new feature?**
   - YES → Check if it requires architecture changes
     - Significant changes? → Discuss in issue first
     - Minor changes? → Implement with tests
   - NO → Continue

5. **Is this documentation?**
   - YES → Update appropriate files, commit
   - NO → Ask for clarification

### When to Ask for Help

**STOP and ask if**:

1. Change requires modifying `plugins/base.py`
2. Change requires significant architecture changes
3. Uncertain about thread safety implications
4. Breaking changes are necessary
5. Multiple approaches seem valid

### Commit Message Conventions

```
feat: Add EPUB converter plugin
fix: Resolve race condition in queue manager
docs: Update architecture documentation
refactor: Extract UI helpers into utils module
test: Add tests for queue state transitions
chore: Update dependencies
style: Fix linting issues
```

---

## Reference Commands

### Essential Commands

```bash
# Setup
pip install -r requirements.txt

# Quality checks
ruff check .
ruff check --fix .
mypy .

# Git workflow
git checkout -b feature/task-name
git add -A
git status
git diff --cached
git commit -m "type: description"
git push -u origin feature/task-name

# Testing
python manga_downloader.py  # Launch GUI
```

### Quick Reference

| Task | Command |
|------|---------|
| Check Python version | `python --version` |
| List dependencies | `pip list` |
| Lint code | `ruff check .` |
| Type check | `mypy .` |
| Run app | `python manga_downloader.py` |
| View git status | `git status` |
| View recent commits | `git log --oneline -5` |

---

## Summary

**Golden Rules for AI Agents**:

1. 📖 **Read documentation first** (ARCHITECTURE.md, ONBOARDING.md)
2. 🔍 **Inspect before modifying** (understand existing code)
3. 🧪 **Test thoroughly** (manual + quality checks)
4. 📝 **Document changes** (code + docs)
5. ✅ **Pass quality gates** (ruff, mypy)
6. 🚀 **Deliver via PR** (always, no exceptions)

**Remember**: The goal is maintainable, type-safe, well-documented code that follows project conventions. When in doubt, prefer clarity over cleverness.

---

*Last updated: 2025-01-13*
*For questions or clarifications, open an issue on GitHub.*

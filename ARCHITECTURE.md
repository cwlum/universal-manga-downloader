# Architecture Overview

This document describes the high-level architecture and design patterns used in the Universal Manga Downloader.

## Design Philosophy

The Universal Manga Downloader follows these core principles:

1. **Separation of Concerns**: UI, business logic, and data access are kept separate
2. **Plugin Architecture**: Parsers and converters can be added without modifying core code
3. **Thread Safety**: Queue management and downloads use proper locking mechanisms
4. **Type Safety**: Comprehensive type hints throughout the codebase (targeting Python 3.11+)
5. **Extensibility**: New websites and output formats can be added via plugins

## System Components

### Layer 1: User Interface (`manga_downloader.py`)

The main GUI application built with Tkinter:

- **Responsibilities**:
  - Display search interface, series browser, and download queue
  - Handle user input and navigation
  - Orchestrate download workflows
  - Display progress and status updates
  
- **Key Classes**:
  - `MangaDownloader`: Main application window and event coordinator
  - `QueueItem`: UI representation of a download in progress
  
- **Communication**: Interacts with services, plugins, and core modules

### Layer 2: Core Business Logic

#### `core/queue_manager.py`
Thread-safe queue state management:

- **Purpose**: Centralize all queue state mutations with proper locking
- **Key Classes**:
  - `QueueManager`: Thread-safe queue operations with RLock
  - `QueueItemData`: Immutable data for queue items
  - `QueueState`: Enum defining lifecycle states (pending, running, success, error, paused, cancelled)
  - `QueueStats`: Aggregate statistics

- **Thread Safety**: All operations use context managers for safe concurrent access

### Layer 3: Services

#### `services/bato_service.py`
Scraping and search functionality for Bato.to:

- **Responsibilities**:
  - Execute search queries
  - Parse series pages for metadata and chapter lists
  - Handle pagination

- **Dependencies**: Uses `cloudscraper` for Cloudflare bypass

#### `services/mangadex_service.py`
Thin API client for MangaDex chapters:

- **Responsibilities**:
  - Request chapter metadata via the official REST API
  - Resolve image server URLs and file lists
  - Provide sanitized data structures for parser plugins

- **Dependencies**: Uses `requests` with configurable timeouts

### Layer 4: Plugin System

#### `plugins/base.py`
Plugin infrastructure:

- **Key Classes**:
  - `BasePlugin`: Abstract base for parser plugins
  - `BaseConverter`: Abstract base for converter plugins
  - `PluginManager`: Discovery, loading, and lifecycle management
  - `PluginLoader`: File system scanner for plugin discovery

- **Plugin Types**:
  - **Parsers**: Extract chapter data from HTML (title, chapter number, image URLs)
  - **Converters**: Transform downloaded images into archives (PDF, CBZ, etc.)

- **Discovery**: Automatically scans `plugins/` directory for subclasses

#### Parser Plugins
- `bato_parser.py`: Parses Bato.to chapter pages
- `mangadex_parser.py`: Retrieves MangaDex chapter images via the API
- Additional parsers can be added by subclassing `BasePlugin`

#### Converter Plugins
- `pdf_converter.py`: Converts images to PDF
- `cbz_converter.py`: Converts images to CBZ (comic book archive)
- Additional converters can be added by subclassing `BaseConverter`

### Layer 5: Utilities

#### `utils/file_utils.py`
File system operations:
- Default directory resolution
- Filename sanitization
- Image file collection
- Directory creation with error handling

#### `utils/ui_helpers.py`
Tkinter helper functions:
- Value clamping for spinboxes
- Mouse wheel scrolling normalization
- Text widget updates

#### `config.py`
Centralized configuration:

- **Config Classes** (frozen dataclasses):
  - `UIConfig`: Window dimensions and timing
  - `DownloadConfig`: Worker limits and network timeouts
  - `ServiceConfig`: External service endpoints (Bato.to + MangaDex)
  - `PDFConfig`: PDF generation settings
  - `AppConfig`: Aggregates all configuration

- **Global Instance**: `CONFIG` provides read-only access

## Data Flow

### Search Workflow

```
User Input → MangaDownloader (UI)
           → Selected service (`BatoService` / `MangaDexService`).search_manga()
           → HTTP Request + HTML Parsing
           → List[SearchResult]
           → Display in UI
```

Only parser plugins enabled under **Settings → Plugins** appear as selectable search providers.

### Series Info Workflow

```
Series URL → Selected service (`BatoService` / `MangaDexService`).get_series_info()
           → Parse title, description, attributes, chapters
           → Display in UI
           → User selects chapters
```

### Download Workflow

```
User Queues Chapter
  ↓
QueueManager.add_item()
  ↓
ThreadPoolExecutor submits download task
  ↓
_download_chapter_worker():
  1. Fetch chapter page HTML
  2. Try each enabled parser plugin until one succeeds
  3. Extract image URLs from parsed data
  4. Download images concurrently (ThreadPoolExecutor)
  5. Run enabled converter plugins
  6. Update queue status to SUCCESS or ERROR
  ↓
QueueManager.complete_item()
  ↓
UI updates progress bars and status labels
```

## Threading Model

### Main Thread (Tk Event Loop)
- Handles all UI updates via `after(0, callback)`
- Receives status updates from worker threads

### Chapter Workers (ThreadPoolExecutor)
- Configurable pool size (1-10 workers)
- Each worker processes one chapter at a time
- Orchestrates image download and conversion

### Image Workers (ThreadPoolExecutor)
- Configurable pool size (1-32 workers)
- Downloads images concurrently within a chapter
- Nested within chapter worker threads

### Thread Safety
- `QueueManager` uses `threading.RLock()` for all state mutations
- UI updates always scheduled via `Tk.after(0, ...)`
- Futures tracked in `_chapter_futures` dict for cancellation

## Plugin Discovery

1. `PluginLoader` scans `plugins/` directory
2. Loads `.py` files (excluding `__init__.py` and private modules)
3. Inspects each module for subclasses of `BasePlugin` or `BaseConverter`
4. `PluginManager` instantiates and calls `on_load()` hook
5. Plugins appear in Settings tab with enable/disable toggles

## Configuration Management

- **Immutable**: All config classes use `@dataclass(frozen=True)`
- **Type-Safe**: Full type hints on all fields
- **Centralized**: Single `CONFIG` instance accessed throughout codebase
- **Layered**: Separate concerns (UI, download, service, PDF)

## Error Handling Strategy

1. **Network Errors**: Caught at service/worker level, surfaced to UI with `QueueState.ERROR`
2. **Parser Failures**: Try next available parser; fail if none succeed
3. **Plugin Errors**: Logged but don't crash the application
4. **File System Errors**: Return `None` from utilities; UI displays error status
5. **Thread Pool Shutdown**: Handled gracefully on app close

## Extension Points

### Adding a New Website

1. Create `plugins/mysite_parser.py`
2. Subclass `BasePlugin`
3. Implement `can_handle(url)`, `parse(soup, url)`, `get_name()`
4. Plugin manager auto-discovers on next startup

### Adding a New Output Format

1. Create `plugins/myformat_converter.py`
2. Subclass `BaseConverter`
3. Implement `convert(images, output_dir, metadata)`, `get_name()`, `get_output_extension()`
4. Plugin manager auto-discovers on next startup

### Adding Configuration

1. Add fields to appropriate config class in `config.py`
2. Use `CONFIG.section.field` throughout codebase
3. UI widgets can bind to config values if needed

## Future Architecture Improvements

1. **Separate UI Module**: Extract `MangaDownloader` UI building into `ui/` submodules
2. **Service Registry**: Generalize `BatoService` pattern for multiple manga sites
3. **Async/Await**: Consider migrating from ThreadPoolExecutor to asyncio for I/O
4. **State Machine**: Formalize queue state transitions
5. **Plugin Entry Points**: Support pip-installable plugin packages
6. **Database Layer**: Persist download history and user preferences
7. **Testing**: Expand test coverage for core business logic

## Dependencies

### Runtime
- `requests`: HTTP client (via cloudscraper)
- `beautifulsoup4`: HTML parsing
- `Pillow`: Image processing for converters
- `cloudscraper`: Cloudflare bypass
- `sv-ttk`: Modern Tkinter theme

### Development
- `ruff`: Linting and formatting
- `mypy`: Static type checking
- `pytest`: Unit testing framework

## Performance Considerations

- **Concurrency**: Configurable worker pools balance speed vs. server load
- **Memory**: Images loaded one at a time; converters work with file paths
- **UI Responsiveness**: All I/O operations run in background threads
- **Network**: Connection pooling via `cloudscraper` session

## Security Considerations

- **User Input**: URLs are validated before processing
- **File System**: Downloads restricted to user-configured directory
- **Dependencies**: Regular updates to address security vulnerabilities
- **Plugins**: Run in same process; trust model assumes plugins are reviewed

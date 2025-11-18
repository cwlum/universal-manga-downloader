# Architecture Overview

This document explains how Universal Manga Downloader (UMD) 1.3.1 is structured and how data moves through the system.

## Design Principles

- Separate UI, orchestration, plugins, and infrastructure concerns.
- Auto-discover plugins; avoid code changes when adding parsers or converters.
- Keep threading predictable: UI on the Tk loop, work in executors, with lock-backed queue state.
- Prefer defensive error handling and strong typing (Python 3.11+ syntax).

## Layers and Responsibilities

| Layer | Modules | Responsibilities |
| --- | --- | --- |
| UI | `manga_downloader.py`, `ui/app.py`, `ui/logging_utils.py` | Tkinter app (Browser, Downloads, Settings tabs), event wiring, log setup |
| Core | `core/queue_manager.py`, `core/download_task.py` | Queue state, worker coordination, pause/resume, cancellation, converter orchestration |
| Services | `services/bato_service.py`, `services/mangadex_service.py` | Search and metadata retrieval for Bato and MangaDex |
| Plugins | `plugins/base.py` + parsers/converters | Auto-discovered implementations that turn pages into images and archives |
| Utilities | `utils/file_utils.py`, `utils/http_client.py` | Download paths, filename sanitization, disk checks, HTTP session pooling |
| Configuration | `config.py` | Frozen dataclasses exposed via `CONFIG` for UI sizes, worker counts, timeouts, endpoints, and PDF settings |

## Data Flow

### Search and Series Browsing

1. User selects provider (Bato/MangaDex) and submits a query from the Browser tab.
2. The UI delegates to the corresponding service to fetch search results.
3. Selecting a series triggers chapter list retrieval and populates the chapter view.

### Download Workflow

1. Queueing a chapter registers it with `QueueManager` and refreshes the chapter executor.
2. Each queued item runs a `DownloadTask` inside a ThreadPoolExecutor sized by `CONFIG.download`.
3. The task fetches the chapter HTML/JSON via `ScraperPool`, then asks `PluginManager` to pick a parser that can handle the URL.
4. Parsed image URLs are downloaded concurrently with a bounded image worker pool guarded by a semaphore (`max_total_image_workers`).
5. When downloads finish, enabled converters (PDF/CBZ) run in sequence using the downloaded files.
6. `QueueManager` records status transitions; UI updates are marshalled via Tk `after(...)` to keep thread safety.

## Threading Model

- **Main thread**: Tk event loop; all widget updates occur here via scheduled callbacks.
- **Chapter workers**: ThreadPoolExecutor limited by `default_chapter_workers`–`max_chapter_workers` (1–10 by default).
- **Image workers**: Per-chapter ThreadPoolExecutor capped by `default_image_workers`–`max_image_workers` (4–32), plus a global `max_total_image_workers` limit (48).
- **Pause/Resume**: A shared `threading.Event` (`_pause_event`) blocks progress when cleared; resume sets the event.
- **Cancellation**: Futures are tracked by queue ID; cancelling stops work after the current safe checkpoint.

## Plugin System

- `PluginLoader` scans `plugins/` for `.py` files (excluding `__init__.py` and private files), loading them in isolation.
- Classes inheriting `BasePlugin` (parsers) or `BaseConverter` (converters) register automatically with `PluginManager`.
- Duplicate `get_name()` values per plugin type are ignored after the first successful load.
- Optional hooks: `on_load` and `on_unload` allow caching or cleanup when toggled in the Settings tab.
- Parser output uses `ParsedChapter` (title, chapter label, image URLs); converters accept file paths plus `ChapterMetadata`.

## Configuration

`config.py` defines frozen dataclasses surfaced through `CONFIG`:

- `UIConfig`: window dimensions (1100x850 default), minimum sizes, queue/progress update intervals.
- `DownloadConfig`: chapter/image worker bounds (1–10 and 1–32), global image worker cap (48), timeouts (30s requests/15s search/20s series), retries (3 with 1.0s backoff), scraper pool size (8).
- `ServiceConfig`: Bato and MangaDex endpoints, paging limits, language defaults, and rate-limit delay (0.5s).
- `PDFConfig`: default resolution (100 DPI) and supported input formats.

Use `CONFIG` instead of hardcoded values; expose changes here so CLI and UI stay in sync.

## Extension Points

- **New site parser**: add `plugins/<site>_parser.py`, subclass `BasePlugin`, implement `get_name`, `can_handle`, and `parse`. Keep network access in `services/`.
- **New converter**: add `plugins/<format>_converter.py`, subclass `BaseConverter`, return the output file path or `None` on failure.
- **New service helper**: extend `services/` to encapsulate HTTP interactions and reuse shared scraper sessions.

## Reliability and Safety Notes

- Network retries back off per chapter (`max_retries=3`, `retry_delay=1.0s`).
- Download directory access and disk space are validated before workers run.
- Exceptions in plugins are logged and surfaced to the UI without crashing the application.
- All state mutations in `QueueManager` are guarded by an `RLock` to keep progress consistent across threads.

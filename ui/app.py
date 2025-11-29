"""Tkinter-based GUI application that orchestrates manga downloads."""

from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from collections.abc import Callable
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from queue import Empty, Queue
from tkinter import ttk
from typing import Any, cast
from urllib.parse import urlparse

import sv_ttk

from config import CONFIG
from core.download_task import DownloadTask, DownloadUIHooks
from core.queue_manager import QueueManager, QueueState
from plugins.base import PluginManager, PluginType
from plugins.remote_manager import RemotePluginManager
from services import BatoService, MangaDexService
from ui.logging_utils import configure_logging
from ui.models import QueueItem, SearchResult, SeriesChapter
from ui.tabs import BrowserTabMixin, DownloadsTabMixin, SettingsTabMixin
from ui.widgets import MouseWheelHandler, clamp_value
from utils.file_utils import ensure_directory, get_default_download_root
from utils.http_client import ScraperPool

configure_logging()
logger = logging.getLogger(__name__)


class MangaDownloader(BrowserTabMixin, DownloadsTabMixin, SettingsTabMixin, tk.Tk):  # type: ignore[misc]
    """Main application window orchestrating search, queue, and download workflows."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Universal Manga Downloader")
        self.geometry("1100x850")
        self.minsize(1000, 800)

        sv_ttk.set_theme("dark")

        # Initialize services and state
        self._init_services()
        self._init_state()
        self._init_variables()

        # Build UI
        self._build_ui()

        # Bind mousewheel handlers
        self._bind_browser_mousewheel()
        self._bind_downloads_mousewheel()

        # Final setup
        self._refresh_provider_options()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._ensure_chapter_executor(force_reset=True)
        self._update_queue_status()
        self._update_queue_progress()

    def _init_services(self) -> None:
        """Initialize external services and plugins."""
        self.search_services: dict[str, Any] = {
            "Bato": BatoService(),
            "MangaDex": MangaDexService(),
        }
        self.provider_plugin_map: dict[str, tuple[PluginType, str]] = {
            "Bato": (PluginType.PARSER, "Bato"),
            "MangaDex": (PluginType.PARSER, "MangaDex"),
        }
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()
        self.remote_plugin_manager = RemotePluginManager(self.plugin_manager.plugin_dir)
        self.scraper_pool = ScraperPool(CONFIG.download.scraper_pool_size)
        self.queue_manager = QueueManager()

    def _init_state(self) -> None:
        """Initialize application state."""
        default_provider = next(iter(self.search_services))
        self.search_provider_var = tk.StringVar(value=default_provider)
        self.series_provider: str | None = None
        self._search_results_provider: str | None = None
        self._available_providers: list[str] = []

        self.search_results: list[SearchResult] = []
        self.series_data: dict[str, object] | None = None
        self.series_chapters: list[SeriesChapter] = []

        self.chapter_executor_lock = threading.Lock()
        self.chapter_executor: ThreadPoolExecutor | None = None
        self._chapter_executor_workers: int | None = None
        self._image_worker_semaphore = threading.Semaphore(
            CONFIG.download.max_total_image_workers
        )

        self.queue_items: dict[int, QueueItem] = {}
        self._queue_item_sequence = 0
        self._mousewheel_handler = MouseWheelHandler()
        self._chapter_futures: dict[int, Future[None]] = {}
        self._downloads_paused = False
        self.pause_button: ttk.Button | None = None
        self.cancel_pending_button: ttk.Button | None = None
        self.plugin_vars: dict[tuple[PluginType, str], tk.BooleanVar] = {}
        # Event for pause/resume: when SET, downloads can proceed; when CLEAR, downloads wait
        self._can_proceed_event = threading.Event()
        self._can_proceed_event.set()  # Start in "can proceed" state
        # Cross-thread UI callback queue
        self._ui_callback_queue: Queue[Callable[[], None]] = Queue()
        self._ui_callback_job: str | None = None
        self._ui_callback_interval_ms = max(16, CONFIG.ui.progress_update_interval_ms // 2)

    def _init_variables(self) -> None:
        """Initialize Tk variables."""
        self.chapter_workers_var = tk.IntVar(value=CONFIG.download.default_chapter_workers)
        self.image_workers_var = tk.IntVar(value=CONFIG.download.default_image_workers)
        self.range_start_var = tk.StringVar()
        self.range_end_var = tk.StringVar()
        self.queue_status_var = tk.StringVar(value="Queue: idle")
        self.download_dir_var = tk.StringVar(value=get_default_download_root())
        self.download_dir_path = self.download_dir_var.get()
        self.download_dir_var.trace_add("write", self._on_download_dir_var_write)

        self._chapter_workers_value = clamp_value(
            self.chapter_workers_var.get(),
            CONFIG.download.min_chapter_workers,
            CONFIG.download.max_chapter_workers,
            CONFIG.download.default_chapter_workers,
        )
        self.chapter_workers_var.set(self._chapter_workers_value)

        self._image_workers_value = clamp_value(
            self.image_workers_var.get(),
            CONFIG.download.min_image_workers,
            CONFIG.download.max_image_workers,
            CONFIG.download.default_image_workers,
        )
        self.image_workers_var.set(self._image_workers_value)

    def _build_ui(self) -> None:
        """Build the main application UI."""
        self.configure(padx=15, pady=15)

        # Create notebook with tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.search_tab = ttk.Frame(self.notebook)
        self.queue_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.search_tab, text="Browser")
        self.notebook.add(self.queue_tab, text="Downloads")
        self.notebook.add(self.settings_tab, text="Settings")

        # Build each tab using mixins
        self._build_browser_tab(self.search_tab)
        self._build_downloads_tab(self.queue_tab)
        self._build_settings_tab(self.settings_tab)
        self._start_ui_callback_pump()

        # Status bar
        status_bar = ttk.Frame(self)
        status_bar.pack(fill="x", side="bottom", pady=(10, 0))
        self.status_label = ttk.Label(status_bar, text="Status: Ready")
        self.status_label.pack(anchor="w", padx=4, pady=(0, 4))

    # --- Provider Resolution ---

    def _is_provider_enabled(self, provider: str) -> bool:
        """Check if a provider's parser plugin is enabled."""
        mapping = self.provider_plugin_map.get(provider)
        if mapping is None:
            return True
        plugin_type, plugin_name = mapping
        record = self.plugin_manager.get_record(plugin_type, plugin_name)
        return record is not None and record.enabled

    def _normalize_provider(self, provider_key: str | None) -> str:
        """Normalize provider key to an available provider."""
        available = self._available_providers or [
            provider
            for provider in self.search_services
            if self._is_provider_enabled(provider)
        ]
        if provider_key in available:
            return cast(str, provider_key)
        if available:
            return available[0]
        return next(iter(self.search_services))

    def _resolve_service(self, provider_key: str | None) -> tuple[str, Any]:
        """Resolve a provider key to (normalized_key, service) tuple."""
        normalized = self._normalize_provider(provider_key)
        candidates = [normalized] + [
            provider for provider in self._available_providers if provider != normalized
        ]
        for provider in candidates:
            service = self.search_services.get(provider)
            if service is not None and self._is_provider_enabled(provider):
                return provider, service
        raise RuntimeError("No enabled search providers are available.")

    def _provider_from_url(self, url: str) -> str | None:
        """Infer provider from URL hostname."""
        if not url:
            return None
        host = urlparse(url).netloc.lower()
        if "mangadex" in host:
            return "MangaDex"
        if "bato" in host:
            return "Bato"
        return None

    def _determine_series_provider(self, series_url: str) -> str:
        """Determine the appropriate provider for a series URL."""
        if self.series_provider in self.search_services and self._is_provider_enabled(
            cast(str, self.series_provider)
        ):
            return cast(str, self.series_provider)
        url_provider = self._provider_from_url(series_url)
        if url_provider in self.search_services and self._is_provider_enabled(
            cast(str, url_provider)
        ):
            return cast(str, url_provider)
        if self._search_results_provider in self.search_services and self._is_provider_enabled(
            cast(str, self._search_results_provider)
        ):
            return cast(str, self._search_results_provider)
        return self._normalize_provider(self.search_provider_var.get())

    # --- Download Management ---

    def start_download_thread(self) -> None:
        """Start a download from the manual URL entry."""
        url = self.url_var.get().strip()
        if not url:
            self._set_status("Status: Error - URL is empty")
            return
        self._enqueue_chapter_downloads([(url, None)])

    def _enqueue_chapter_downloads(
        self, chapter_items: list[tuple[str, str | None]]
    ) -> None:
        """Queue multiple chapters for download."""
        queued = 0
        for url, label in chapter_items:
            if not url:
                continue
            self._submit_download_task(url, label)
            queued += 1

        if queued:
            label_text = "chapter" if queued == 1 else "chapters"
            self._set_status(f"Status: Queued {queued} {label_text} for download.")
        else:
            self._set_status("Status: No chapters were queued for download.")

    def _submit_download_task(self, url: str, initial_label: str | None) -> None:
        """Submit a single download task to the queue."""
        queue_label = initial_label or self._derive_queue_label(url)
        queue_id = self._register_queue_item(queue_label, url, initial_label)
        self._update_queue_status()
        self._update_queue_progress()

        if self._downloads_paused or self.queue_manager.is_paused():
            self._queue_set_status(queue_id, "Paused", state=QueueState.PAUSED)
            self.queue_manager.pause_item(queue_id)
            self.queue_manager.add_deferred(queue_id, url, initial_label)
            return

        self._start_download_future(queue_id, url, initial_label)

    def _start_download_future(
        self, queue_id: int, url: str, initial_label: str | None
    ) -> None:
        """Start a download future for a queue item."""
        if self._downloads_paused or self.queue_manager.is_paused():
            self._queue_set_status(queue_id, "Paused", state=QueueState.PAUSED)
            self.queue_manager.pause_item(queue_id)
            self.queue_manager.add_deferred(queue_id, url, initial_label)
            return

        self._ensure_chapter_executor()
        assert self.chapter_executor is not None
        task = self._create_download_task(queue_id, url, initial_label)
        future: Future[None] = self.chapter_executor.submit(task.run)
        self._chapter_futures[queue_id] = future
        self._queue_set_status(queue_id, "Queued", state=QueueState.PENDING)
        self.queue_manager.clear_paused(queue_id)

        def _on_done(fut: Future[None], *, qid: int = queue_id) -> None:
            self._on_download_task_done(qid, fut)

        future.add_done_callback(_on_done)

    def _create_download_task(
        self, queue_id: int, url: str, initial_label: str | None
    ) -> DownloadTask:
        """Create a DownloadTask for a queue item."""
        return DownloadTask(
            queue_id,
            url,
            initial_label,
            plugin_manager=self.plugin_manager,
            scraper_pool=self.scraper_pool,
            image_semaphore=self._image_worker_semaphore,
            image_worker_count=self._get_image_worker_count(),
            resolve_download_dir=self._resolve_download_base_dir,
            ui_hooks=self._build_download_ui_hooks(),
            should_abort=lambda: self.queue_manager.is_cancelled(queue_id),
            wait_if_paused=self._can_proceed_event.wait,
        )

    def _build_download_ui_hooks(self) -> DownloadUIHooks:
        """Build UI hooks for download task callbacks."""
        return DownloadUIHooks(
            on_start=self._on_download_start,
            on_end=self._on_download_end,
            queue_set_status=self._queue_set_status,
            queue_mark_finished=self._queue_mark_finished,
            queue_update_title=self._queue_update_title,
            queue_reset_progress=self._queue_reset_progress,
            queue_update_progress=self._queue_update_progress,
            set_status=self._set_status,
        )

    def _on_download_start(self, label: str | None, queue_id: int) -> None:
        """Handle download start event."""
        nice_label = label or "chapter"
        self.queue_manager.start_item(queue_id)
        self._update_queue_status()
        self._update_queue_progress()
        self._queue_set_status(queue_id, "Starting download…", state=QueueState.RUNNING)
        self._queue_reset_progress(queue_id, 1)
        self._set_status(f"Status: Downloading {nice_label}...")

    def _on_download_end(self, label: str | None, _queue_id: int) -> None:
        """Handle download end event."""
        self._update_queue_status()
        self._update_queue_progress()
        stats = self.queue_manager.get_stats()
        if stats.active == 0 and stats.pending == 0 and not self.queue_manager.is_paused():
            self._set_status("Status: Ready")

    def _on_download_task_done(self, queue_id: int, future: Future[None]) -> None:
        """Handle completion of a download task future."""
        self._chapter_futures.pop(queue_id, None)

        if self.queue_manager.is_item_paused(queue_id):
            self.queue_manager.clear_paused(queue_id)
            return

        if self.queue_manager.is_cancelled(queue_id):
            self.queue_manager.clear_cancelled(queue_id)
            return

        try:
            future.result()
        except CancelledError:
            return
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            self._queue_set_status(queue_id, f"Failed: {message}", state=QueueState.ERROR)
            logger.exception("Queue item %s failed", queue_id)
        finally:
            self._update_queue_status()
            self._update_queue_progress()

    # --- Executor Management ---

    def _ensure_chapter_executor(self, force_reset: bool = False) -> None:
        """Ensure the chapter executor is ready with the correct worker count."""
        desired_workers = clamp_value(
            self._chapter_workers_value,
            CONFIG.download.min_chapter_workers,
            CONFIG.download.max_chapter_workers,
            CONFIG.download.default_chapter_workers,
        )
        if desired_workers != self._chapter_workers_value:
            self._chapter_workers_value = desired_workers
            self.chapter_workers_var.set(desired_workers)

        with self.chapter_executor_lock:
            if (
                force_reset
                or self.chapter_executor is None
                or self._chapter_executor_workers != desired_workers
            ):
                if self.chapter_executor is not None:
                    self.chapter_executor.shutdown(wait=False)
                self.chapter_executor = ThreadPoolExecutor(
                    max_workers=desired_workers,
                    thread_name_prefix="chapter-download",
                )
                self._chapter_executor_workers = desired_workers

    # --- Utility Methods ---

    def _derive_queue_label(self, url: str) -> str:
        """Derive a queue label from URL when no label is provided."""
        if not url:
            return "Chapter"
        parsed = urlparse(url)
        tail = os.path.basename(parsed.path.rstrip("/"))
        return tail or url

    def _resolve_download_base_dir(self) -> str | None:
        """Resolve and ensure the download directory exists."""
        base = self.download_dir_path or get_default_download_root()
        ensured = ensure_directory(base)
        if ensured is None:
            self._set_status("Status: Error - Cannot access download directory.")
            return None
        return ensured

    def _set_status(self, message: str) -> None:
        """Safely update the status label from any thread."""
        def _update() -> None:
            self.status_label.config(text=message)

        self._post_to_ui(_update)

    def _post_to_ui(self, callback: Callable[[], None]) -> None:
        """Submit a callable to run on the Tk thread."""
        self._ui_callback_queue.put(callback)

    def _start_ui_callback_pump(self) -> None:
        """Start (or restart) the UI callback drain loop."""
        if self._ui_callback_job is not None:
            self.after_cancel(self._ui_callback_job)
        self._ui_callback_job = self.after(
            self._ui_callback_interval_ms, self._drain_ui_callbacks
        )

    def _drain_ui_callbacks(self) -> None:
        """Execute queued UI callbacks on the Tk thread."""
        self._ui_callback_job = None
        while True:
            try:
                callback = self._ui_callback_queue.get_nowait()
            except Empty:
                break
            try:
                callback()
            except Exception:  # noqa: BLE001
                logger.exception("UI callback execution failed")
        self._ui_callback_job = self.after(
            self._ui_callback_interval_ms, self._drain_ui_callbacks
        )

    # --- Shutdown ---

    def on_close(self) -> None:
        """Clean shutdown of all resources when closing the application."""
        logger.info("Application shutting down...")

        with self.chapter_executor_lock:
            if self.chapter_executor is not None:
                logger.debug("Shutting down chapter executor...")
                try:
                    self.chapter_executor.shutdown(wait=True, cancel_futures=False)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Error during executor shutdown: %s", exc)
                finally:
                    self.chapter_executor = None

        try:
            self.scraper_pool.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error closing scraper pool: %s", exc)

        try:
            self.plugin_manager.shutdown()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error shutting down plugin manager: %s", exc)

        if self._ui_callback_job is not None:
            try:
                self.after_cancel(self._ui_callback_job)
            except Exception:  # noqa: BLE001
                logger.debug("UI callback job already cancelled")
            self._ui_callback_job = None

        logger.info("Shutdown complete")
        self.destroy()


def main(log_level: int | str | None = None) -> None:
    """Entrypoint to launch the GUI application."""
    configure_logging(log_level)
    app = MangaDownloader()
    app.mainloop()


if __name__ == "__main__":
    main()

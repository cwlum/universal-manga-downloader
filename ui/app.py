"""Tkinter-based GUI application that orchestrates manga downloads."""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import tkinter as tk
from collections.abc import Iterable
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from functools import partial
from numbers import Real
from tkinter import filedialog, ttk
from typing import Any, cast
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]
import sv_ttk

from config import CONFIG
from core.download_task import DownloadTask, DownloadUIHooks
from core.queue_manager import QueueManager, QueueState
from plugins.base import PluginManager, PluginType
from services import BatoService, MangaDexService
from ui.logging_utils import configure_logging
from ui.models import STATUS_COLORS, QueueItem, SearchResult, SeriesChapter
from ui.widgets import MouseWheelHandler, clamp_value
from utils.file_utils import ensure_directory, get_default_download_root
from utils.http_client import ScraperPool


configure_logging()
logger = logging.getLogger(__name__)


class MangaDownloader(tk.Tk):
    """Main application window orchestrating search, queue, and download workflows."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Universal Manga Downloader")
        self.geometry("1100x850")
        self.minsize(1000, 800)

        sv_ttk.set_theme("dark")

        self.search_services: dict[str, Any] = {
            "Bato": BatoService(),
            "MangaDex": MangaDexService(),
        }
        self.provider_plugin_map: dict[str, tuple[PluginType, str]] = {
            "Bato": (PluginType.PARSER, "Bato"),
            "MangaDex": (PluginType.PARSER, "MangaDex"),
        }
        default_provider = next(iter(self.search_services))
        self.search_provider_var = tk.StringVar(value=default_provider)
        self.series_provider: str | None = None
        self._search_results_provider: str | None = None
        self._available_providers: list[str] = []
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()
        self.scraper_pool = ScraperPool(CONFIG.download.scraper_pool_size)
        self.search_results: list[SearchResult] = []
        self.series_data: dict[str, object] | None = None
        self.series_chapters: list[SeriesChapter] = []
        self.queue_manager = QueueManager()
        self.chapter_executor_lock = threading.Lock()
        self.chapter_executor: ThreadPoolExecutor | None = None
        self._chapter_executor_workers: int | None = None
        self._image_worker_semaphore = threading.Semaphore(CONFIG.download.max_total_image_workers)

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
        self.queue_items: dict[int, QueueItem] = {}
        self._queue_item_sequence = 0
        self._mousewheel_handler = MouseWheelHandler()
        self._chapter_futures: dict[int, Future[None]] = {}
        self._downloads_paused = False
        self.pause_button: ttk.Button | None = None
        self.cancel_pending_button: ttk.Button | None = None
        self.plugin_vars: dict[tuple[PluginType, str], tk.BooleanVar] = {}
        self._pause_event = threading.Event()
        self._pause_event.set()

        self._build_ui()
        self._mousewheel_handler.bind_mousewheel(self.search_results_listbox)
        self._mousewheel_handler.bind_mousewheel(self.series_info_text)
        self._mousewheel_handler.bind_mousewheel(self.chapters_listbox)
        self._mousewheel_handler.bind_mousewheel(self.queue_canvas)
        self._mousewheel_handler.bind_mousewheel(self.queue_items_container, target=self.queue_canvas)
        self._refresh_provider_options()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._ensure_chapter_executor(force_reset=True)
        self._update_queue_status()
        self._update_queue_progress()

    def _build_ui(self):
        self.configure(padx=15, pady=15)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.search_tab = ttk.Frame(self.notebook)
        self.queue_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.search_tab, text="Browser")
        self.notebook.add(self.queue_tab, text="Downloads")
        self.notebook.add(self.settings_tab, text="Settings")

        # --- Search Tab ---
        search_frame = ttk.LabelFrame(self.search_tab, text="Search Manga")
        search_frame.pack(fill="x", expand=False, padx=10, pady=(12, 10))

        search_entry_frame = ttk.Frame(search_frame)
        search_entry_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(search_entry_frame, text="Source:").pack(side="left", padx=(0, 8))
        self.provider_combo = ttk.Combobox(
            search_entry_frame,
            state="readonly",
            values=tuple(self.search_services.keys()),
            textvariable=self.search_provider_var,
            width=12,
        )
        self.provider_combo.pack(side="left", padx=(0, 12))
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_changed)

        self.search_entry = ttk.Entry(search_entry_frame)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda _event: self.start_search_thread())

        self.search_button = ttk.Button(search_entry_frame, text="Search", command=self.start_search_thread)
        self.search_button.pack(side="left", padx=(10, 0))

        results_frame = ttk.Frame(search_frame)
        results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.search_results_listbox = tk.Listbox(results_frame, height=6, exportselection=False)
        self.search_results_listbox.pack(side="left", fill="both", expand=True)

        search_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.search_results_listbox.yview)
        search_scrollbar.pack(side="right", fill="y")
        self.search_results_listbox.configure(yscrollcommand=search_scrollbar.set)

        self.search_results_listbox.bind("<<ListboxSelect>>", self.on_search_select)
        self.search_results_listbox.bind("<Double-1>", self.on_search_double_click)
        self.search_results_listbox.bind("<Return>", self.on_search_double_click)

        # --- Series Details ---
        series_frame = ttk.LabelFrame(self.search_tab, text="Series Details")
        series_frame.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        controls_frame = ttk.Frame(series_frame)
        controls_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(controls_frame, text="Series URL:").pack(side="left")
        self.series_url_var = tk.StringVar()
        self.series_url_entry = ttk.Entry(controls_frame, textvariable=self.series_url_var)
        self.series_url_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.load_series_button = ttk.Button(controls_frame, text="Load Series", command=self.start_series_info_thread)
        self.load_series_button.pack(side="left")

        self.series_title_var = tk.StringVar(value="Series title will appear here")
        ttk.Label(series_frame, textvariable=self.series_title_var, font=("TkDefaultFont", 14, "bold")).pack(
            anchor="w", padx=10, pady=(0, 4)
        )

        info_and_chapters_frame = ttk.Frame(series_frame)
        info_and_chapters_frame.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        info_frame = ttk.Frame(info_and_chapters_frame)
        info_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(info_frame, text="Summary & Info:").pack(anchor="w")

        info_text_container = ttk.Frame(info_frame)
        info_text_container.pack(fill="both", expand=True, pady=(4, 0))

        self.series_info_text = tk.Text(info_text_container, height=12, wrap="word", state="disabled")
        self.series_info_text.pack(side="left", fill="both", expand=True)

        info_scrollbar = ttk.Scrollbar(info_text_container, orient="vertical", command=self.series_info_text.yview)
        info_scrollbar.pack(side="right", fill="y")
        self.series_info_text.configure(yscrollcommand=info_scrollbar.set)

        chapters_frame = ttk.Frame(info_and_chapters_frame)
        chapters_frame.pack(side="left", fill="both", expand=False, padx=(12, 0))

        ttk.Label(chapters_frame, text="Chapters:").pack(anchor="w")

        chapters_list_container = ttk.Frame(chapters_frame)
        chapters_list_container.pack(fill="both", expand=True, pady=(4, 0))

        self.chapters_listbox = tk.Listbox(chapters_list_container, height=12, selectmode="extended", exportselection=False)
        self.chapters_listbox.pack(side="left", fill="both", expand=True)

        chapters_scrollbar = ttk.Scrollbar(chapters_list_container, orient="vertical", command=self.chapters_listbox.yview)
        chapters_scrollbar.pack(side="right", fill="y")
        self.chapters_listbox.configure(yscrollcommand=chapters_scrollbar.set)

        self.chapters_listbox.bind("<<ListboxSelect>>", self.on_chapter_select)
        self.chapters_listbox.bind("<Double-1>", self.on_chapter_double_click)
        self.chapters_listbox.bind("<Return>", lambda _event: self.download_selected_chapter())
        self.chapters_listbox.bind("<Control-a>", self._on_select_all_chapters)

        range_frame = ttk.Frame(chapters_frame)
        range_frame.pack(fill="x", pady=(6, 0))

        ttk.Label(range_frame, text="Range:").pack(side="left")
        range_start_entry = ttk.Entry(range_frame, width=6, textvariable=self.range_start_var)
        range_start_entry.pack(side="left", padx=(6, 3))
        range_start_entry.bind("<Return>", lambda _event: self._highlight_range_selection())
        ttk.Label(range_frame, text="to").pack(side="left")
        range_end_entry = ttk.Entry(range_frame, width=6, textvariable=self.range_end_var)
        range_end_entry.pack(side="left", padx=(3, 6))
        range_end_entry.bind("<Return>", lambda _event: self._highlight_range_selection())

        ttk.Button(chapters_frame, text="Highlight Range", command=self._highlight_range_selection).pack(
            fill="x", pady=(8, 0)
        )
        ttk.Button(chapters_frame, text="Queue Selected", command=self.download_selected_chapter).pack(
            fill="x", pady=(4, 2)
        )
        ttk.Button(chapters_frame, text="Queue Range", command=self.download_range).pack(fill="x", pady=(0, 2))
        ttk.Button(chapters_frame, text="Queue All", command=self.download_all_chapters).pack(fill="x")

        # --- Manual Queue Section ---
        manual_frame = ttk.LabelFrame(self.search_tab, text="Quick Queue")
        manual_frame.pack(fill="x", expand=False, padx=10, pady=(0, 12))

        download_entry_frame = ttk.Frame(manual_frame)
        download_entry_frame.pack(fill="x", padx=10, pady=6)

        ttk.Label(download_entry_frame, text="Chapter URL:").pack(side="left")
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(download_entry_frame, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self.url_entry.bind("<Return>", lambda _event: self.start_download_thread())
        self.download_button = ttk.Button(download_entry_frame, text="Queue Download", command=self.start_download_thread)
        self.download_button.pack(side="left")

        # --- Queue Tab ---
        queue_wrapper = ttk.LabelFrame(self.queue_tab, text="Download Queue")
        queue_wrapper.pack(fill="both", expand=True, padx=10, pady=(12, 10))

        queue_canvas_frame = ttk.Frame(queue_wrapper)
        queue_canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.queue_canvas = tk.Canvas(queue_canvas_frame, borderwidth=0, highlightthickness=0)
        self.queue_canvas.pack(side="left", fill="both", expand=True)

        self.queue_items_container = ttk.Frame(self.queue_canvas)
        self.queue_canvas_window = self.queue_canvas.create_window(
            (0, 0), window=self.queue_items_container, anchor="nw"
        )

        def _sync_queue_width(event):
            self.queue_canvas.itemconfigure(self.queue_canvas_window, width=event.width)

        self.queue_canvas.bind("<Configure>", _sync_queue_width)

        queue_scrollbar = ttk.Scrollbar(queue_canvas_frame, orient="vertical", command=self.queue_canvas.yview)
        queue_scrollbar.pack(side="right", fill="y")
        self.queue_canvas.configure(yscrollcommand=queue_scrollbar.set)

        def _sync_queue_scrollregion(event):
            self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))

        self.queue_items_container.bind("<Configure>", _sync_queue_scrollregion)

        queue_footer = ttk.LabelFrame(self.queue_tab, text="Queue Overview")
        queue_footer.pack(fill="x", expand=False, padx=10, pady=(0, 12))

        ttk.Label(queue_footer, text="Overall queue:").pack(anchor="w", padx=10, pady=(6, 0))
        self.queue_progress = ttk.Progressbar(queue_footer, orient="horizontal", mode="determinate")
        self.queue_progress.pack(fill="x", padx=10, pady=(0, 6))

        queue_controls_frame = ttk.Frame(queue_footer)
        queue_controls_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.queue_label = ttk.Label(queue_controls_frame, textvariable=self.queue_status_var)
        self.queue_label.pack(side="left", anchor="w")

        ttk.Button(queue_controls_frame, text="Clear Finished", command=self._clear_finished_queue_items).pack(
            side="right"
        )
        self.cancel_pending_button = ttk.Button(
            queue_controls_frame,
            text="Cancel Pending",
            command=self._cancel_pending_downloads,
        )
        self.cancel_pending_button.pack(side="right", padx=(0, 8))
        self.pause_button = ttk.Button(
            queue_controls_frame,
            text="Pause Downloads",
            command=self._toggle_download_pause,
        )
        self.pause_button.pack(side="right", padx=(0, 8))

        # --- Settings Tab ---
        settings_frame = ttk.LabelFrame(self.settings_tab, text="Download Settings")
        settings_frame.pack(fill="x", expand=False, padx=10, pady=(12, 10))

        directory_frame = ttk.Frame(settings_frame)
        directory_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(directory_frame, text="Save to:").pack(side="left")
        self.download_dir_entry = ttk.Entry(directory_frame, textvariable=self.download_dir_var)
        self.download_dir_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(directory_frame, text="Browse…", command=self._browse_download_dir).pack(side="left")

        concurrency_frame = ttk.Frame(settings_frame)
        concurrency_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(concurrency_frame, text="Chapter workers:").pack(side="left")
        self.chapter_workers_spinbox = ttk.Spinbox(
            concurrency_frame,
            from_=1,
            to=10,
            width=4,
            textvariable=self.chapter_workers_var,
            command=self._on_chapter_workers_change,
        )
        self.chapter_workers_spinbox.pack(side="left", padx=(6, 18))
        self.chapter_workers_spinbox.bind("<FocusOut>", self._on_chapter_workers_change)

        ttk.Label(concurrency_frame, text="Image workers:").pack(side="left")
        self.image_workers_spinbox = ttk.Spinbox(
            concurrency_frame,
            from_=1,
            to=32,
            width=4,
            textvariable=self.image_workers_var,
            command=self._on_image_workers_change,
        )
        self.image_workers_spinbox.pack(side="left", padx=(6, 0))
        self.image_workers_spinbox.bind("<FocusOut>", self._on_image_workers_change)

        self._build_plugin_settings()

        status_bar = ttk.Frame(self)
        status_bar.pack(fill="x", side="bottom", pady=(10, 0))
        self.status_label = ttk.Label(status_bar, text="Status: Ready")
        self.status_label.pack(anchor="w", padx=4, pady=(0, 4))

    def _refresh_provider_options(self) -> None:
        """Update search provider options based on enabled parser plugins."""

        available = [provider for provider in self.search_services if self._is_provider_enabled(provider)]
        self._available_providers = available

        if not hasattr(self, "provider_combo"):
            return

        if not available:
            self.provider_combo.configure(values=(), state="disabled")
            self.search_button.config(state="disabled")
            self.search_provider_var.set("")
            self.search_results_listbox.delete(0, tk.END)
            self.chapters_listbox.delete(0, tk.END)
            self._update_text_widget(self.series_info_text, "Enable a parser plugin to search.")
            return

        self.provider_combo.configure(values=tuple(available), state="readonly")
        if self.search_provider_var.get() not in available:
            self.search_provider_var.set(available[0])
        self.search_button.config(state="normal")

    def _build_plugin_settings(self) -> None:
        """Render plugin toggle controls within the settings tab."""

        plugin_records = self.plugin_manager.get_records()
        if not plugin_records:
            return

        container = ttk.LabelFrame(self.settings_tab, text="Plugins")
        container.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        ttk.Label(
            container,
            text="Enable or disable plugins for this session. Changes apply immediately.",
            wraplength=420,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(8, 6))

        for plugin_type in PluginType:
            records = self.plugin_manager.get_records(plugin_type)
            if not records:
                continue

            section = ttk.LabelFrame(container, text=f"{plugin_type.value.title()} Plugins")
            section.pack(fill="x", expand=False, padx=10, pady=(0, 10))

            for record in records:
                name = record.name
                var = tk.BooleanVar(value=record.enabled)
                self.plugin_vars[(plugin_type, name)] = var
                ttk.Checkbutton(
                    section,
                    text=name,
                    variable=var,
                    command=partial(self._on_plugin_toggle, plugin_type, name),
                ).pack(anchor="w", padx=8, pady=2)

    def _on_plugin_toggle(self, plugin_type: PluginType, plugin_name: str) -> None:
        """Respond to plugin enable/disable events from the UI."""

        var = self.plugin_vars.get((plugin_type, plugin_name))
        if var is None:
            return

        enabled = bool(var.get())
        self.plugin_manager.set_enabled(plugin_type, plugin_name, enabled)
        status = "enabled" if enabled else "disabled"
        self._set_status(f"Status: Plugin {plugin_name} {status}.")
        if plugin_type is PluginType.PARSER:
            self._refresh_provider_options()

    # --- Search Handlers ---
    def _is_provider_enabled(self, provider: str) -> bool:
        mapping = self.provider_plugin_map.get(provider)
        if mapping is None:
            return True
        plugin_type, plugin_name = mapping
        record = self.plugin_manager.get_record(plugin_type, plugin_name)
        return record is not None and record.enabled

    def _on_provider_changed(self, _event=None):
        provider_key = self._normalize_provider(self.search_provider_var.get())
        self.search_provider_var.set(provider_key)
        self.series_provider = None
        self._search_results_provider = None
        self.search_results = []
        self.series_data = None
        self.series_chapters = []
        self.search_results_listbox.delete(0, tk.END)
        self.chapters_listbox.delete(0, tk.END)
        if hasattr(self, "series_url_var"):
            self.series_url_var.set("")
        self._update_text_widget(self.series_info_text, "Select a series to load.")
        self.status_label.config(text=f"Status: Switched to {provider_key}.")

    def start_search_thread(self):
        query = self.search_entry.get().strip()
        if not query:
            self.status_label.config(text="Status: Enter a search query.")
            return

        if not self._available_providers:
            self.status_label.config(text="Status: Enable a parser plugin before searching.")
            return

        provider_key = self._normalize_provider(self.search_provider_var.get())
        self.search_provider_var.set(provider_key)

        if provider_key not in self._available_providers:
            self.status_label.config(text="Status: Selected provider is disabled.")
            return

        self.search_button.config(state="disabled")
        self.status_label.config(text=f'Status: Searching {provider_key} for "{query}"...')
        thread = threading.Thread(target=self._perform_search, args=(query, provider_key), daemon=True)
        thread.start()

    def _perform_search(self, query, provider_key):
        try:
            provider_key, service = self._resolve_service(provider_key)
        except RuntimeError as error:
            message = f"Status: {error}"
            self.after(0, lambda msg=message: self._on_search_failure(msg))
            return
        try:
            results = service.search_manga(query)
        except requests.RequestException as error:
            message = f"Status: {provider_key} search failed - Network error: {error}"
            logger.warning("Network error during search for %s: %s", query, error)
            self.after(0, lambda msg=message: self._on_search_failure(msg))
        except (json.JSONDecodeError, KeyError, ValueError, AttributeError):
            logger.exception("Data parsing error during search for %s with %s", query, provider_key)
            message = f"Status: {provider_key} search error - Invalid response format"
            self.after(0, lambda msg=message: self._on_search_failure(msg))
        except Exception as error:  # noqa: BLE001 - catch remaining unexpected failures
            logger.exception("Unexpected error in search for %s with %s", query, provider_key)
            message = f"Status: {provider_key} search error - {error}"
            self.after(0, lambda msg=message: self._on_search_failure(msg))
        else:
            self.after(0, lambda: self._on_search_success(results, query, provider_key))

    def _on_search_success(self, results, query, provider_key):
        for result in results:
            if isinstance(result, dict) and "provider" not in result:
                result["provider"] = provider_key

        self._search_results_provider = provider_key
        self.series_provider = provider_key
        self.search_results = results
        self.search_results_listbox.delete(0, tk.END)
        for result in results:
            title = result.get("title", "Unknown")
            subtitle = result.get("subtitle")
            display = f"{title} — {subtitle}" if subtitle else title
            self.search_results_listbox.insert(tk.END, display)

        if results:
            self.status_label.config(
                text=f'Status: Found {len(results)} {provider_key} result(s) for "{query}".'
            )
        else:
            self.status_label.config(text=f'Status: No {provider_key} results for "{query}".')

        self.search_button.config(state="normal")

    def _on_search_failure(self, message):
        self.search_button.config(state="normal")
        self.status_label.config(text=message)

    def on_search_select(self, event):
        selection = event.widget.curselection()
        if not selection:
            return
        index = selection[0]
        if 0 <= index < len(self.search_results):
            series_url = self.search_results[index].get("url", "")
            if series_url:
                self.series_url_var.set(series_url)
            provider = self.search_results[index].get("provider")
            if isinstance(provider, str):
                self.series_provider = provider
                if provider in self.search_services:
                    self.search_provider_var.set(provider)

    def on_search_double_click(self, event):
        self.on_search_select(event)
        self.start_series_info_thread()

    def _get_selected_search_url(self):
        selection = self.search_results_listbox.curselection()
        if not selection:
            return ""
        index = selection[0]
        if 0 <= index < len(self.search_results):
            result = self.search_results[index]
            provider = result.get("provider")
            if isinstance(provider, str):
                self.series_provider = provider
                if provider in self.search_services:
                    self.search_provider_var.set(provider)
            return result.get("url", "")
        return ""

    # --- Series Handlers ---
    def start_series_info_thread(self):
        series_url = self.series_url_var.get().strip()
        if not series_url:
            series_url = self._get_selected_search_url()
            if not series_url:
                self.status_label.config(text="Status: Select a series or paste its URL.")
                return
            self.series_url_var.set(series_url)

        provider_key = self._determine_series_provider(series_url)
        self.series_provider = provider_key
        if provider_key in self.search_services:
            self.search_provider_var.set(provider_key)

        if provider_key not in self._available_providers:
            self.status_label.config(text="Status: Enable the corresponding parser plugin to load this series.")
            self.load_series_button.config(state="normal")
            return

        self.load_series_button.config(state="disabled")
        self.status_label.config(text=f"Status: Fetching {provider_key} series info...")
        thread = threading.Thread(
            target=self._perform_series_fetch,
            args=(series_url, provider_key),
            daemon=True,
        )
        thread.start()

    def _perform_series_fetch(self, series_url, provider_key):
        try:
            provider_key, service = self._resolve_service(provider_key)
        except RuntimeError as error:
            message = f"Status: {error}"
            self.after(0, lambda msg=message: self._on_series_failure(msg))
            return
        try:
            data = service.get_series_info(series_url)
        except requests.RequestException as error:
            message = f"Status: {provider_key} series fetch failed - Network error: {error}"
            logger.warning("Network error fetching series %s: %s", series_url, error)
            self.after(0, lambda msg=message: self._on_series_failure(msg))
        except (json.JSONDecodeError, KeyError, ValueError, AttributeError):
            logger.exception("Data parsing error for series %s with %s", series_url, provider_key)
            message = f"Status: {provider_key} series parsing error - Invalid response format"
            self.after(0, lambda msg=message: self._on_series_failure(msg))
        except Exception as error:  # noqa: BLE001 - catch remaining unexpected failures
            logger.exception("Unexpected error processing series %s with %s", series_url, provider_key)
            message = f"Status: {provider_key} error - {error}"
            self.after(0, lambda msg=message: self._on_series_failure(msg))
        else:
            self.after(0, lambda: self._on_series_success(data, provider_key))

    def _on_series_success(self, data, provider_key):
        payload = data if isinstance(data, dict) else {}
        payload.setdefault("provider", provider_key)
        self.series_data = payload
        self.series_provider = provider_key
        self.series_chapters = payload.get("chapters", []) or []

        title = payload.get("title") or "Unknown Title"
        self.series_title_var.set(title)

        info_lines = []
        description = payload.get("description")
        if description:
            info_lines.append(description)

        attributes = payload.get("attributes") or {}
        for label, value in attributes.items():
            if isinstance(value, Iterable) and not isinstance(value, str | bytes | dict):
                value_text = ", ".join(str(item) for item in value)
            else:
                value_text = str(value)
            info_lines.append(f"{label}: {value_text}")

        info_content = "\n\n".join(info_lines) if info_lines else "No additional information available."
        self._update_text_widget(self.series_info_text, info_content)

        self.chapters_listbox.delete(0, tk.END)
        for idx, chapter in enumerate(self.series_chapters, start=1):
            chapter_title = chapter.get("title") or chapter.get("label") or f"Chapter {idx}"
            self.chapters_listbox.insert(tk.END, f"{idx:03d} • {chapter_title}")

        if self.series_chapters:
            first_url = self.series_chapters[0].get("url", "")
            if first_url:
                self.url_var.set(first_url)

        self.status_label.config(
            text=f"Status: Loaded {len(self.series_chapters)} {provider_key} chapter(s)."
        )
        self.load_series_button.config(state="normal")

    def _on_series_failure(self, message):
        self.load_series_button.config(state="normal")
        self.status_label.config(text=message)

    def _update_text_widget(self, widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state="disabled")

    def on_chapter_select(self, event):
        selection = sorted(idx for idx in event.widget.curselection() if 0 <= idx < len(self.series_chapters))
        if not selection:
            return

        first_index = selection[0]
        chapter = self.series_chapters[first_index]
        chapter_url = chapter.get("url", "")
        if chapter_url:
            self.url_var.set(chapter_url)

        last_index = selection[-1]
        self._update_range_from_indices(selection)

        if len(selection) == 1:
            chapter_title = chapter.get("title") or chapter.get("label") or f"Chapter {first_index + 1}"
            self.status_label.config(text=f"Status: Selected {chapter_title}")
        else:
            self.status_label.config(
                text=f"Status: Selected {len(selection)} chapter(s) ({first_index + 1}–{last_index + 1})"
            )

    def on_chapter_double_click(self, event):
        self.download_selected_chapter()

    def _on_select_all_chapters(self, _event=None):
        if not self.series_chapters:
            return "break"
        self.chapters_listbox.selection_set(0, tk.END)
        selection = list(range(len(self.series_chapters)))
        self._update_range_from_indices(selection)
        self._set_status(f"Status: Selected all {len(selection)} chapter(s).")
        return "break"

    def _update_range_from_indices(self, indices):
        if not indices:
            return
        first_index = indices[0]
        last_index = indices[-1]
        self.range_start_var.set(str(first_index + 1))
        self.range_end_var.set(str(last_index + 1))

    def download_selected_chapter(self):
        selection = self.chapters_listbox.curselection()
        if not selection:
            self._set_status("Status: Select one or more chapters to download.")
            return
        indices = sorted({idx for idx in selection if 0 <= idx < len(self.series_chapters)})
        chapter_items = []
        for index in indices:
            chapter = self.series_chapters[index]
            chapter_url = chapter.get("url", "")
            if not chapter_url:
                continue
            label = self._format_chapter_label(index, chapter)
            chapter_items.append((chapter_url, label))

        if not chapter_items:
            self._set_status("Status: Selected chapters are missing download URLs.")
            return

        self.url_var.set(chapter_items[0][0])
        self._enqueue_chapter_downloads(chapter_items)

    def download_range(self):
        range_bounds = self._get_range_indices()
        if range_bounds is None:
            return

        start_index, end_index = range_bounds
        self._highlight_range_selection(notify=False, bounds=range_bounds)

        chapter_items = []
        for idx in range(start_index, end_index + 1):
            chapter = self.series_chapters[idx]
            chapter_url = chapter.get("url", "")
            if not chapter_url:
                continue
            label = self._format_chapter_label(idx, chapter)
            chapter_items.append((chapter_url, label))

        if not chapter_items:
            self._set_status("Status: No downloadable chapters in the requested range.")
            return

        self.url_var.set(chapter_items[0][0])
        self._enqueue_chapter_downloads(chapter_items)

    def _get_range_indices(self):
        if not self.series_chapters:
            self._set_status("Status: Load a series before selecting a range.")
            return None

        try:
            start = int(self.range_start_var.get())
            end = int(self.range_end_var.get())
        except (TypeError, ValueError):
            self._set_status("Status: Invalid range. Use numeric values like 1 and 5.")
            return None

        if start <= 0 or end <= 0:
            self._set_status("Status: Range values must be positive integers.")
            return None

        if start > end:
            start, end = end, start

        max_index = len(self.series_chapters)
        start_index = max(1, start) - 1
        end_index = min(max_index, end) - 1
        if start_index > end_index:
            self._set_status("Status: Range does not match any chapters.")
            return None

        return start_index, end_index

    def _highlight_range_selection(self, notify=True, bounds=None):
        range_bounds = bounds or self._get_range_indices()
        if range_bounds is None:
            return

        start_index, end_index = range_bounds
        self.chapters_listbox.selection_clear(0, tk.END)
        self.chapters_listbox.selection_set(start_index, end_index)
        self.chapters_listbox.see(start_index)
        self.chapters_listbox.see(end_index)
        selection = list(range(start_index, end_index + 1))
        self._update_range_from_indices(selection)
        if notify:
            self._set_status(
                f"Status: Highlighted chapters {start_index + 1}–{end_index + 1}."
            )

    def download_all_chapters(self):
        if not self.series_chapters:
            self._set_status("Status: No chapters available to download.")
            return

        chapter_items = []
        for idx, chapter in enumerate(self.series_chapters):
            chapter_url = chapter.get("url", "")
            if not chapter_url:
                continue
            label = self._format_chapter_label(idx, chapter)
            chapter_items.append((chapter_url, label))

        if not chapter_items:
            self._set_status("Status: Unable to queue downloads because no chapter URLs were found.")
            return

        self.url_var.set(chapter_items[0][0])
        self._enqueue_chapter_downloads(chapter_items)

    # --- Download Handlers ---
    def start_download_thread(self):
        url = self.url_var.get().strip()
        if not url:
            self._set_status("Status: Error - URL is empty")
            return

        self._enqueue_chapter_downloads([(url, None)])

    def _enqueue_chapter_downloads(self, chapter_items):
        queued = 0
        for url, label in chapter_items:
            if not url:
                continue
            self._submit_download_task(url, label)
            queued += 1

        if queued:
            label = "chapter" if queued == 1 else "chapters"
            self._set_status(f"Status: Queued {queued} {label} for download.")
        else:
            self._set_status("Status: No chapters were queued for download.")

    def _submit_download_task(self, url: str, initial_label: str | None) -> None:
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

    def _start_download_future(self, queue_id: int, url: str, initial_label: str | None) -> None:
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

        def _on_done(fut: Future[None], *, queue_id: int = queue_id) -> None:
            self._on_download_task_done(queue_id, fut)

        future.add_done_callback(_on_done)

    def _create_download_task(self, queue_id: int, url: str, initial_label: str | None) -> DownloadTask:
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
            wait_if_paused=self._pause_event.wait,
        )

    def _build_download_ui_hooks(self) -> DownloadUIHooks:
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

    def _toggle_download_pause(self):
        if self._downloads_paused:
            self._resume_downloads()
        else:
            self._pause_downloads()

    def _pause_downloads(self):
        if self._downloads_paused or self.queue_manager.is_paused():
            return

        self._downloads_paused = True
        self._pause_event.clear()
        self.queue_manager.pause()
        if self.pause_button is not None:
            self.pause_button.config(text="Resume Downloads")

        paused_now = 0
        for queue_id, future in list(self._chapter_futures.items()):
            if future.cancel():
                self._chapter_futures.pop(queue_id, None)
                item = self.queue_items.get(queue_id)
                url = item.url if item else None
                initial_label = item.initial_label if item else None
                if url:
                    already_paused = self.queue_manager.is_item_paused(queue_id)
                    self.queue_manager.pause_item(queue_id)
                    if not already_paused:
                        self.queue_manager.add_deferred(queue_id, url, initial_label)
                    self._queue_set_status(queue_id, "Paused", state=QueueState.PAUSED)
                    paused_now += 1

        message = "Status: Downloads paused."
        if paused_now:
            message = f"Status: Paused downloads (moved {paused_now} pending job(s))."
        self._set_status(message)
        self._update_queue_status()

    def _resume_downloads(self):
        if not self._downloads_paused and not self.queue_manager.is_paused():
            return

        self._downloads_paused = False
        self._pause_event.set()
        self.queue_manager.resume()
        if self.pause_button is not None:
            self.pause_button.config(text="Pause Downloads")

        deferred = self.queue_manager.get_deferred()
        resumed = 0
        for queue_id, url, initial_label in deferred:
            self.queue_manager.clear_paused(queue_id)
            self._start_download_future(queue_id, url, initial_label)
            resumed += 1

        if resumed:
            self._set_status(f"Status: Resumed {resumed} paused download(s).")
        else:
            self._set_status("Status: Downloads resumed.")
        self._update_queue_status()

    def _cancel_pending_downloads(self) -> None:
        cancelled_ids: set[int] = set()
        remaining_active = 0

        deferred = self.queue_manager.get_deferred()
        if deferred:
            for queue_id, *_ in deferred:
                cancelled_ids.add(queue_id)
                self.queue_manager.clear_paused(queue_id)

        for queue_id, future in list(self._chapter_futures.items()):
            if future.cancel():
                self._chapter_futures.pop(queue_id, None)
                cancelled_ids.add(queue_id)
                self.queue_manager.clear_paused(queue_id)
            else:
                remaining_active += 1

        if not cancelled_ids:
            if remaining_active:
                self._set_status("Status: Unable to cancel active downloads.")
            else:
                self._set_status("Status: No pending downloads to cancel.")
            return

        for queue_id in cancelled_ids:
            self._mark_queue_cancelled(queue_id)

        self._update_queue_status()
        self._update_queue_progress()
        self._set_status(f"Status: Cancelled {len(cancelled_ids)} download(s).")

    def _mark_queue_cancelled(self, queue_id: int) -> None:
        self.queue_manager.cancel_item(queue_id)
        self._queue_reset_progress(queue_id, 1)
        self._queue_set_status(queue_id, "Cancelled", state=QueueState.CANCELLED)

    def _ensure_chapter_executor(self, force_reset=False):
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

    def _on_chapter_workers_change(self, event=None):
        value = clamp_value(
            self.chapter_workers_var.get(),
            CONFIG.download.min_chapter_workers,
            CONFIG.download.max_chapter_workers,
            self._chapter_workers_value or CONFIG.download.default_chapter_workers,
        )
        if value != self.chapter_workers_var.get():
            self.chapter_workers_var.set(value)
        if value != self._chapter_workers_value or event is None:
            self._chapter_workers_value = value
            self._ensure_chapter_executor(force_reset=True)

    def _on_image_workers_change(self, event=None):
        value = clamp_value(
            self.image_workers_var.get(),
            CONFIG.download.min_image_workers,
            CONFIG.download.max_image_workers,
            self._image_workers_value or CONFIG.download.default_image_workers,
        )
        if value != self.image_workers_var.get():
            self.image_workers_var.set(value)
        if value != self._image_workers_value or event is None:
            self._image_workers_value = value

    def _get_image_worker_count(self) -> int:
        value = clamp_value(
            self._image_workers_value or CONFIG.download.default_image_workers,
            CONFIG.download.min_image_workers,
            CONFIG.download.max_image_workers,
            CONFIG.download.default_image_workers,
        )
        return min(value, CONFIG.download.max_total_image_workers)

    def _on_download_start(self, label: str | None, queue_id: int) -> None:
        nice_label = label or "chapter"
        self.queue_manager.start_item(queue_id)
        self._update_queue_status()
        self._update_queue_progress()
        self._queue_set_status(queue_id, "Starting download…", state=QueueState.RUNNING)
        self._queue_reset_progress(queue_id, 1)
        self._set_status(f"Status: Downloading {nice_label}...")

    def _on_download_end(self, label: str | None, _queue_id: int) -> None:
        self._update_queue_status()
        self._update_queue_progress()
        stats = self.queue_manager.get_stats()
        if stats.active == 0 and stats.pending == 0 and not self.queue_manager.is_paused():
            self._set_status("Status: Ready")

    def _update_queue_status(self) -> None:
        stats = self.queue_manager.get_stats()
        paused = self._downloads_paused or self.queue_manager.is_paused()

        def _update() -> None:
            queue_text = f"Queue • Active: {stats.active} | Pending: {stats.pending}"
            if stats.failed:
                queue_text += f" | Failed: {stats.failed}"
            if stats.cancelled:
                queue_text += f" | Cancelled: {stats.cancelled}"
            if paused:
                queue_text += " • Paused"
            self.queue_status_var.set(queue_text)

        self.after(0, _update)

    def _update_queue_progress(self) -> None:
        stats = self.queue_manager.get_stats()
        total = stats.total
        completed = min(stats.completed + stats.cancelled, total)

        def update() -> None:
            if total > 0:
                self.queue_progress["maximum"] = max(1, total)
                self.queue_progress["value"] = completed
            else:
                self.queue_progress["maximum"] = 1
                self.queue_progress["value"] = 0

        self.after(0, update)

    def _set_status(self, message: str) -> None:
        """Safely update the status label from any worker context."""

        self.after(0, lambda: self.status_label.config(text=message))

    def _browse_download_dir(self) -> None:
        initial_dir = self.download_dir_path or get_default_download_root()
        directory = filedialog.askdirectory(initialdir=initial_dir)
        if directory:
            self.download_dir_var.set(directory)

    def _on_download_dir_var_write(self, *_: object) -> None:
        value = self.download_dir_var.get()
        self.download_dir_path = value.strip() if isinstance(value, str) else ""

    def _resolve_download_base_dir(self) -> str | None:
        base = self.download_dir_path or get_default_download_root()
        ensured = ensure_directory(base)
        if ensured is None:
            self._set_status("Status: Error - Cannot access download directory.")
            return None
        return ensured

    def _format_chapter_label(self, index: int, chapter: SeriesChapter) -> str:
        """Return a human-readable label for a queued chapter."""

        chapter_title = chapter.get("title") or chapter.get("label") or f"Chapter {index + 1}"
        return f"{index + 1:03d} • {chapter_title}"

    def _derive_queue_label(self, url: str) -> str:
        """Fallback label when we only know the chapter URL."""

        if not url:
            return "Chapter"
        parsed = urlparse(url)
        tail = os.path.basename(parsed.path.rstrip("/"))
        return tail or url

    def _normalize_provider(self, provider_key: str | None) -> str:
        available = self._available_providers or [
            provider for provider in self.search_services if self._is_provider_enabled(provider)
        ]
        if provider_key in available:
            return cast(str, provider_key)
        if available:
            return available[0]
        return next(iter(self.search_services))

    def _resolve_service(self, provider_key: str | None) -> tuple[str, Any]:
        normalized = self._normalize_provider(provider_key)
        candidates = [normalized] + [provider for provider in self._available_providers if provider != normalized]
        for provider in candidates:
            service = self.search_services.get(provider)
            if service is not None and self._is_provider_enabled(provider):
                return provider, service
        raise RuntimeError("No enabled search providers are available.")

    def _provider_from_url(self, url: str) -> str | None:
        if not url:
            return None
        host = urlparse(url).netloc.lower()
        if "mangadex" in host:
            return "MangaDex"
        if "bato" in host:
            return "Bato"
        return None

    def _determine_series_provider(self, series_url: str) -> str:
        if self.series_provider in self.search_services and self._is_provider_enabled(cast(str, self.series_provider)):
            return cast(str, self.series_provider)
        url_provider = self._provider_from_url(series_url)
        if url_provider in self.search_services and self._is_provider_enabled(cast(str, url_provider)):
            return cast(str, url_provider)
        if self._search_results_provider in self.search_services and self._is_provider_enabled(
            cast(str, self._search_results_provider)
        ):
            return cast(str, self._search_results_provider)
        return self._normalize_provider(self.search_provider_var.get())

    def _register_queue_item(
        self,
        label: str | None,
        url: str,
        initial_label: str | None,
    ) -> int:
        display = label or url or "Pending chapter"
        queue_id = self._queue_item_sequence
        self._queue_item_sequence += 1

        item_frame = ttk.Frame(self.queue_items_container)
        item_frame.pack(fill="x", expand=False, padx=8, pady=4)

        title_var = tk.StringVar(value=display)
        title_label = ttk.Label(item_frame, textvariable=title_var, font=("TkDefaultFont", 10, "bold"))
        title_label.pack(anchor="w")

        status_var = tk.StringVar(value="Pending")
        status_label = ttk.Label(item_frame, textvariable=status_var)
        status_label.pack(anchor="w", pady=(2, 0))

        progress = ttk.Progressbar(item_frame, orient="horizontal", mode="determinate")
        progress.pack(fill="x", pady=(4, 0))
        progress["maximum"] = 1
        progress["value"] = 0

        self.queue_items[queue_id] = QueueItem(
            frame=item_frame,
            title_var=title_var,
            status_var=status_var,
            status_label=status_label,
            progress=progress,
            url=url,
            initial_label=initial_label,
        )
        self.queue_manager.add_item(queue_id, url, initial_label)

        self._mousewheel_handler.bind_mousewheel(item_frame, target=self.queue_canvas)

        self._scroll_queue_to_bottom()
        return queue_id

    def _queue_update_title(self, queue_id: int, title: str) -> None:
        def _update() -> None:
            item = self.queue_items.get(queue_id)
            if not item:
                return
            item.title_var.set(title)

        self.after(0, _update)

    def _queue_set_status(
        self,
        queue_id: int,
        text: str,
        state: QueueState | None = None,
    ) -> None:
        def _update() -> None:
            item = self.queue_items.get(queue_id)
            if not item:
                return
            item.status_var.set(text)
            if state is not None:
                item.state = state
                item.status_label.configure(foreground=STATUS_COLORS.get(state, ""))
            elif item.state not in (QueueState.SUCCESS, QueueState.ERROR):
                item.status_label.configure(foreground="")

        self.after(0, _update)

    def _queue_reset_progress(self, queue_id: int, maximum: int) -> None:
        maximum = max(1, maximum)

        def _update() -> None:
            item = self.queue_items.get(queue_id)
            if not item:
                return
            item.maximum = maximum
            progress = item.progress
            progress["maximum"] = maximum
            progress["value"] = 0

        self.after(0, _update)

    def _queue_update_progress(
        self,
        queue_id: int,
        completed: int,
        total: int | None = None,
    ) -> None:
        def _update() -> None:
            item = self.queue_items.get(queue_id)
            if not item:
                return
            if total is not None:
                maximum = max(1, total)
                item.maximum = maximum
                item.progress["maximum"] = maximum
            maximum = item.maximum or 1
            value = max(0, min(maximum, completed))
            item.progress["value"] = value

        self.after(0, _update)

    def _queue_mark_finished(
        self,
        queue_id: int,
        success: bool = True,
        message: str | None = None,
    ) -> None:
        if self.queue_manager.is_cancelled(queue_id):
            return
        text = message or ("Completed" if success else "Failed")
        state = QueueState.SUCCESS if success else QueueState.ERROR
        error_message = message if not success else None
        self.queue_manager.complete_item(queue_id, success=success, error=error_message)

        def _update() -> None:
            item = self.queue_items.get(queue_id)
            if not item:
                return
            maximum = item.maximum or 1
            progress = item.progress
            progress["maximum"] = maximum
            if success:
                progress["value"] = maximum

        self.after(0, _update)
        self._queue_set_status(queue_id, text, state=state)

    def _scroll_queue_to_bottom(self) -> None:
        """Ensure the queue canvas keeps the newest items in view."""

        def _scroll() -> None:
            self.queue_canvas.update_idletasks()
            self.queue_canvas.yview_moveto(1.0)

        self.after(CONFIG.ui.queue_scroll_delay_ms, _scroll)

    def _bind_mousewheel_area(
        self,
        widget: tk.Misc | None,
        target: tk.Misc | None = None,
    ) -> None:
        """Bind wheel events so nested widgets share the same scroll target."""

        if widget is None:
            return

        actual_target = target or widget

        # Track which widgets have been bound to prevent duplicate bindings
        if not hasattr(self, "_bound_widgets"):
            self._bound_widgets: set[tk.Misc] = set()

        # Skip if already bound
        if widget in self._bound_widgets:
            return

        def _on_mousewheel(event: tk.Event, scroll_target: tk.Misc = actual_target):
            delta = self._normalize_mousewheel_delta(event)
            if abs(delta) < 0.001:  # Ignore very small deltas
                return "break"
            self._scroll_target(scroll_target, delta)
            return "break"

        def _on_linux_wheel(event: tk.Event, scroll_target: tk.Misc = actual_target):
            if event.num == 4:
                delta = -1.0
            elif event.num == 5:
                delta = 1.0
            else:
                return "break"
            self._scroll_target(scroll_target, delta)
            return "break"

        # Bind events (add=True ensures we don't override other handlers)
        widget.bind("<MouseWheel>", _on_mousewheel, add=True)
        widget.bind("<Button-4>", _on_linux_wheel, add=True)
        widget.bind("<Button-5>", _on_linux_wheel, add=True)

        # Mark as bound
        self._bound_widgets.add(widget)

        # Recursively bind children
        for child in widget.winfo_children():
            self._bind_mousewheel_area(child, target=actual_target)

    def _normalize_mousewheel_delta(self, event: tk.Event) -> float:
        """Normalise OS-specific wheel events into consistent unit steps.

        Returns positive values for scrolling down, negative for scrolling up.
        Handles both trackpad (small deltas) and mouse wheel (large deltas).
        """

        delta = getattr(event, "delta", 0)
        if delta == 0:
            return 0.0

        platform = sys.platform

        if platform.startswith("linux"):
            # Linux: delta is typically ±120 per notch
            if abs(delta) >= 120:
                return -delta / 120.0
            return -1.0 if delta > 0 else 1.0

        if platform == "darwin":
            # macOS: Complex handling for both trackpad and mouse
            # Trackpad: sends small precise deltas (1-10)
            # Mouse wheel: sends large deltas (120 multiples)

            abs_delta = abs(delta)

            # Mouse wheel: large discrete steps
            if abs_delta >= 40:
                # Standard mouse wheel gives ±120 per notch
                # Scale it down for smoother scrolling
                normalized = -delta / 30.0  # Changed from /120 to /30 for better feel
                return max(-5.0, min(5.0, normalized))  # Clamp to ±5 units

            # Trackpad: small continuous scrolling
            # These are already smooth, just invert and scale slightly
            normalized = -delta * 0.3  # Scale for comfortable speed
            return max(-2.0, min(2.0, normalized))  # Clamp to ±2 units

        # Windows: typically ±120 per notch
        return -delta / 120.0

    def _scroll_target(self, target: tk.Misc, delta: float) -> None:
        """Scroll widgets with smooth fractional delta support.

        For Canvas widgets, uses pixel-based scrolling for smoother feel.
        For Listbox/Text widgets, accumulates fractional deltas.
        """

        if not hasattr(target, "yview_scroll"):
            return

        try:
            # Canvas widgets benefit from pixel scrolling
            if isinstance(target, tk.Canvas):
                # Convert delta to pixels (20 pixels per unit)
                pixels = int(delta * 20)
                if pixels != 0:
                    target.yview_scroll(pixels, "pixels")
                return

            # For Listbox and Text widgets, use unit scrolling with accumulation
            if not hasattr(self, "_scroll_remainders"):
                self._scroll_remainders = {}

            # Accumulate fractional scrolling for smoother feel
            remainder = self._scroll_remainders.get(target, 0.0) + float(delta)
            steps = int(remainder)
            remainder -= steps
            self._scroll_remainders[target] = remainder

            # Only scroll if we have at least one full step
            if steps != 0:
                target.yview_scroll(steps, "units")

        except tk.TclError:
            # Widget might not be scrollable in current state
            pass



    def _clear_finished_queue_items(self) -> None:
        removable_states = {QueueState.SUCCESS, QueueState.ERROR, QueueState.CANCELLED}
        ids_to_remove = [
            qid
            for qid, item in self.queue_items.items()
            if item.state in removable_states
        ]
        if not ids_to_remove:
            self._set_status("Status: No finished items to clear.")
            return

        for qid in ids_to_remove:
            item = self.queue_items.pop(qid, None)
            if item:
                item.frame.destroy()
            self.queue_manager.remove_item(qid)
        self.queue_manager.reset_counters()

        self._set_status(f"Status: Cleared {len(ids_to_remove)} finished item(s) from the queue.")

    def _on_download_task_done(self, queue_id: int, future: Future[None]) -> None:
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

    def on_close(self):
        """Clean shutdown of all resources when closing the application."""
        logger.info("Application shutting down...")

        # Gracefully shutdown thread pool with timeout
        with self.chapter_executor_lock:
            if self.chapter_executor is not None:
                logger.debug("Shutting down chapter executor...")
                try:
                    # Wait up to 10 seconds for tasks to complete
                    self.chapter_executor.shutdown(wait=True, cancel_futures=False)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Error during executor shutdown: %s", exc)
                finally:
                    self.chapter_executor = None

        # Close other resources
        try:
            self.scraper_pool.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error closing scraper pool: %s", exc)

        try:
            self.plugin_manager.shutdown()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error shutting down plugin manager: %s", exc)

        logger.info("Shutdown complete")
        self.destroy()

def main(log_level: int | str | None = None) -> None:
    """Entrypoint to launch the GUI application."""

    configure_logging(log_level)
    app = MangaDownloader()
    app.mainloop()


if __name__ == "__main__":
    main()

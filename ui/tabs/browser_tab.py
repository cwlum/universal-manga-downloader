"""Browser tab UI components and event handlers for manga search and selection."""

from __future__ import annotations

import functools
import json
import logging
import threading
import tkinter as tk
from collections.abc import Callable, Iterable
from tkinter import ttk
from typing import TYPE_CHECKING, Any, cast

import requests  # type: ignore[import-untyped]

from ui.models import SearchResult, SeriesChapter

if TYPE_CHECKING:
    from plugins.base import PluginManager
    from ui.widgets import MouseWheelHandler

logger = logging.getLogger(__name__)


class BrowserTabMixin:
    """Mixin providing Browser tab UI construction and event handlers."""

    # Type hints for attributes expected from host class
    search_services: dict[str, Any]
    search_provider_var: tk.StringVar
    series_provider: str | None
    plugin_manager: PluginManager
    search_results: list[SearchResult]
    series_data: dict[str, object] | None
    series_chapters: list[SeriesChapter]
    _available_providers: list[str]
    _search_results_provider: str | None
    _mousewheel_handler: MouseWheelHandler
    range_start_var: tk.StringVar
    range_end_var: tk.StringVar
    url_var: tk.StringVar
    status_label: ttk.Label
    provider_combo: ttk.Combobox
    search_button: ttk.Button
    search_entry: ttk.Entry
    search_results_listbox: tk.Listbox
    series_url_var: tk.StringVar
    series_url_entry: ttk.Entry
    load_series_button: ttk.Button
    series_title_var: tk.StringVar
    series_info_text: tk.Text
    chapters_listbox: tk.Listbox
    url_entry: ttk.Entry
    download_button: ttk.Button
    _search_in_progress: bool
    _search_debounce_id: str | None

    if TYPE_CHECKING:
        # Methods expected from host class (inherited from tk.Tk)
        def after(self, ms: int, func: Any = ...) -> str: ...

        def after_cancel(self, id: str) -> None: ...

    def _set_status(self, message: str) -> None:  # type: ignore[empty-body]
        """Update status label."""

    def _is_provider_enabled(self, provider: str) -> bool:  # type: ignore[empty-body]
        """Check if provider is enabled."""

    def _normalize_provider(self, provider: str | None) -> str:  # type: ignore[empty-body]
        """Normalize provider name."""

    def _enqueue_chapter_downloads(self, items: list[tuple[str, str | None]]) -> None:  # type: ignore[empty-body]
        """Queue chapter downloads."""

    def start_download_thread(self) -> None:  # type: ignore[empty-body]
        """Start download thread."""

    def _resolve_service(self, provider_key: str | None) -> tuple[str, Any]:  # type: ignore[empty-body]
        """Resolve service for provider."""

    def _determine_series_provider(self, series_url: str) -> str:  # type: ignore[empty-body]
        """Determine provider for series URL."""
    def _post_to_ui(self, callback: Callable[[], None]) -> None:  # type: ignore[empty-body]
        """Schedule a callable on the Tk thread."""

    def _build_browser_tab(self, parent: ttk.Frame) -> None:
        """Construct the Browser tab UI within the given parent frame."""
        # --- Search Section ---
        search_frame = ttk.LabelFrame(parent, text="Search Manga")
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

        self.search_button = ttk.Button(
            search_entry_frame, text="Search", command=self.start_search_thread
        )
        self.search_button.pack(side="left", padx=(10, 0))

        results_frame = ttk.Frame(search_frame)
        results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.search_results_listbox = tk.Listbox(
            results_frame, height=6, exportselection=False
        )
        self.search_results_listbox.pack(side="left", fill="both", expand=True)

        search_scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=self.search_results_listbox.yview
        )
        search_scrollbar.pack(side="right", fill="y")
        self.search_results_listbox.configure(yscrollcommand=search_scrollbar.set)

        self.search_results_listbox.bind("<<ListboxSelect>>", self.on_search_select)
        self.search_results_listbox.bind("<Double-1>", self.on_search_double_click)
        self.search_results_listbox.bind("<Return>", self.on_search_double_click)

        # --- Series Details Section ---
        series_frame = ttk.LabelFrame(parent, text="Series Details")
        series_frame.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        controls_frame = ttk.Frame(series_frame)
        controls_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(controls_frame, text="Series URL:").pack(side="left")
        self.series_url_var = tk.StringVar()
        self.series_url_entry = ttk.Entry(
            controls_frame, textvariable=self.series_url_var
        )
        self.series_url_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.load_series_button = ttk.Button(
            controls_frame, text="Load Series", command=self.start_series_info_thread
        )
        self.load_series_button.pack(side="left")

        self.series_title_var = tk.StringVar(value="Series title will appear here")
        ttk.Label(
            series_frame,
            textvariable=self.series_title_var,
            font=("TkDefaultFont", 14, "bold"),
        ).pack(anchor="w", padx=10, pady=(0, 4))

        info_and_chapters_frame = ttk.Frame(series_frame)
        info_and_chapters_frame.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        # Info panel
        info_frame = ttk.Frame(info_and_chapters_frame)
        info_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(info_frame, text="Summary & Info:").pack(anchor="w")

        info_text_container = ttk.Frame(info_frame)
        info_text_container.pack(fill="both", expand=True, pady=(4, 0))

        self.series_info_text = tk.Text(
            info_text_container, height=12, wrap="word", state="disabled"
        )
        self.series_info_text.pack(side="left", fill="both", expand=True)

        info_scrollbar = ttk.Scrollbar(
            info_text_container, orient="vertical", command=self.series_info_text.yview
        )
        info_scrollbar.pack(side="right", fill="y")
        self.series_info_text.configure(yscrollcommand=info_scrollbar.set)

        # Chapters panel
        chapters_frame = ttk.Frame(info_and_chapters_frame)
        chapters_frame.pack(side="left", fill="both", expand=False, padx=(12, 0))

        ttk.Label(chapters_frame, text="Chapters:").pack(anchor="w")

        chapters_list_container = ttk.Frame(chapters_frame)
        chapters_list_container.pack(fill="both", expand=True, pady=(4, 0))

        self.chapters_listbox = tk.Listbox(
            chapters_list_container,
            height=12,
            selectmode="extended",
            exportselection=False,
        )
        self.chapters_listbox.pack(side="left", fill="both", expand=True)

        chapters_scrollbar = ttk.Scrollbar(
            chapters_list_container,
            orient="vertical",
            command=self.chapters_listbox.yview,
        )
        chapters_scrollbar.pack(side="right", fill="y")
        self.chapters_listbox.configure(yscrollcommand=chapters_scrollbar.set)

        self.chapters_listbox.bind("<<ListboxSelect>>", self.on_chapter_select)
        self.chapters_listbox.bind("<Double-1>", self.on_chapter_double_click)
        self.chapters_listbox.bind(
            "<Return>", lambda _event: self.download_selected_chapter()
        )
        self.chapters_listbox.bind("<Control-a>", self._on_select_all_chapters)

        # Range controls
        range_frame = ttk.Frame(chapters_frame)
        range_frame.pack(fill="x", pady=(6, 0))

        ttk.Label(range_frame, text="Range:").pack(side="left")
        range_start_entry = ttk.Entry(
            range_frame, width=6, textvariable=self.range_start_var
        )
        range_start_entry.pack(side="left", padx=(6, 3))
        range_start_entry.bind(
            "<Return>", lambda _event: self._highlight_range_selection()
        )
        ttk.Label(range_frame, text="to").pack(side="left")
        range_end_entry = ttk.Entry(
            range_frame, width=6, textvariable=self.range_end_var
        )
        range_end_entry.pack(side="left", padx=(3, 6))
        range_end_entry.bind(
            "<Return>", lambda _event: self._highlight_range_selection()
        )

        ttk.Button(
            chapters_frame, text="Highlight Range", command=self._highlight_range_selection
        ).pack(fill="x", pady=(8, 0))
        ttk.Button(
            chapters_frame, text="Queue Selected", command=self.download_selected_chapter
        ).pack(fill="x", pady=(4, 2))
        ttk.Button(chapters_frame, text="Queue Range", command=self.download_range).pack(
            fill="x", pady=(0, 2)
        )
        ttk.Button(
            chapters_frame, text="Queue All", command=self.download_all_chapters
        ).pack(fill="x")

        # --- Quick Queue Section ---
        manual_frame = ttk.LabelFrame(parent, text="Quick Queue")
        manual_frame.pack(fill="x", expand=False, padx=10, pady=(0, 12))

        download_entry_frame = ttk.Frame(manual_frame)
        download_entry_frame.pack(fill="x", padx=10, pady=6)

        ttk.Label(download_entry_frame, text="Chapter URL:").pack(side="left")
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(download_entry_frame, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self.url_entry.bind("<Return>", lambda _event: self.start_download_thread())
        self.download_button = ttk.Button(
            download_entry_frame,
            text="Queue Download",
            command=self.start_download_thread,
        )
        self.download_button.pack(side="left")

    def _bind_browser_mousewheel(self) -> None:
        """Bind mousewheel handlers for browser tab scrollable widgets."""
        self._mousewheel_handler.bind_mousewheel(self.search_results_listbox)
        self._mousewheel_handler.bind_mousewheel(self.series_info_text)
        self._mousewheel_handler.bind_mousewheel(self.chapters_listbox)

    # --- Provider Handlers ---

    def _refresh_provider_options(self) -> None:
        """Update search provider options based on enabled parser plugins."""
        available = [
            provider
            for provider in self.search_services
            if self._is_provider_enabled(provider)
        ]
        self._available_providers = available

        if not hasattr(self, "provider_combo"):
            return

        if not available:
            self.provider_combo.configure(values=(), state="disabled")
            self.search_button.config(state="disabled")
            self.search_provider_var.set("")
            self.search_results_listbox.delete(0, tk.END)
            self.chapters_listbox.delete(0, tk.END)
            self._update_text_widget(
                self.series_info_text, "Enable a parser plugin to search."
            )
            return

        self.provider_combo.configure(values=tuple(available), state="readonly")
        if self.search_provider_var.get() not in available:
            self.search_provider_var.set(available[0])
        self.search_button.config(state="normal")

    def _on_provider_changed(self, _event: Any = None) -> None:
        """Handle provider selection change."""
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

    # --- Search Handlers ---

    def start_search_thread(self) -> None:
        """Initiate a manga search in a background thread with debouncing."""
        # Cancel any pending debounced search
        if hasattr(self, "_search_debounce_id") and self._search_debounce_id is not None:
            self.after_cancel(self._search_debounce_id)
            self._search_debounce_id = None

        query = self.search_entry.get().strip()
        if not query:
            self.status_label.config(text="Status: Enter a search query.")
            return

        if not self._available_providers:
            self.status_label.config(
                text="Status: Enable a parser plugin before searching."
            )
            return

        provider_key = self._normalize_provider(self.search_provider_var.get())
        self.search_provider_var.set(provider_key)

        if provider_key not in self._available_providers:
            self.status_label.config(text="Status: Selected provider is disabled.")
            return

        # Check if search is already in progress (debounce)
        if hasattr(self, "_search_in_progress") and self._search_in_progress:
            # Debounce: wait 500ms before allowing another search
            self.status_label.config(text="Status: Search in progress, please wait...")
            return

        self._search_in_progress = True
        self.search_button.config(state="disabled")
        self.status_label.config(
            text=f'Status: Searching {provider_key} for "{query}"...'
        )
        thread = threading.Thread(
            target=self._perform_search, args=(query, provider_key), daemon=True
        )
        thread.start()

    def _perform_search(self, query: str, provider_key: str) -> None:
        """Execute the search request (runs in background thread)."""
        try:
            provider_key, service = self._resolve_service(provider_key)
        except RuntimeError as error:
            message = f"Status: {error}"
            self._post_to_ui(functools.partial(self._on_search_failure, message))
            return
        try:
            results = service.search_manga(query)
        except requests.RequestException as error:
            message = f"Status: {provider_key} search failed - Network error: {error}"
            logger.warning("Network error during search for %s: %s", query, error)
            self._post_to_ui(functools.partial(self._on_search_failure, message))
            return
        except (json.JSONDecodeError, KeyError, ValueError, AttributeError):
            logger.exception(
                "Data parsing error during search for %s with %s", query, provider_key
            )
            message = f"Status: {provider_key} search error - Invalid response format"
            self._post_to_ui(functools.partial(self._on_search_failure, message))
            return
        except Exception as error:  # noqa: BLE001
            logger.exception(
                "Unexpected error in search for %s with %s", query, provider_key
            )
            message = f"Status: {provider_key} search error - {error}"
            self._post_to_ui(functools.partial(self._on_search_failure, message))
            return
        else:
            self._post_to_ui(
                functools.partial(
                    self._on_search_success, results, query, provider_key
                )
            )

    def _on_search_success(
        self, results: list[SearchResult], query: str, provider_key: str
    ) -> None:
        """Handle successful search results (runs on main thread)."""
        self._search_in_progress = False
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
            self.status_label.config(
                text=f'Status: No {provider_key} results for "{query}".'
            )

        self.search_button.config(state="normal")

    def _on_search_failure(self, message: str) -> None:
        """Handle search failure (runs on main thread)."""
        self._search_in_progress = False
        self.search_button.config(state="normal")
        self.status_label.config(text=message)

    def on_search_select(self, event: tk.Event) -> None:
        """Handle selection in search results listbox."""
        widget = cast(tk.Listbox, event.widget)
        selection = widget.curselection()
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

    def on_search_double_click(self, event: tk.Event) -> None:
        """Handle double-click on search result to load series."""
        self.on_search_select(event)
        self.start_series_info_thread()

    def _get_selected_search_url(self) -> str:
        """Return URL of currently selected search result."""
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

    def start_series_info_thread(self) -> None:
        """Initiate series info fetch in a background thread."""
        series_url = self.series_url_var.get().strip()
        if not series_url:
            series_url = self._get_selected_search_url()
            if not series_url:
                self.status_label.config(
                    text="Status: Select a series or paste its URL."
                )
                return
            self.series_url_var.set(series_url)

        provider_key = self._determine_series_provider(series_url)
        self.series_provider = provider_key
        if provider_key in self.search_services:
            self.search_provider_var.set(provider_key)

        if provider_key not in self._available_providers:
            self.status_label.config(
                text="Status: Enable the corresponding parser plugin to load this series."
            )
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

    def _perform_series_fetch(self, series_url: str, provider_key: str) -> None:
        """Execute series info fetch (runs in background thread)."""
        try:
            provider_key, service = self._resolve_service(provider_key)
        except RuntimeError as error:
            message = f"Status: {error}"
            self._post_to_ui(functools.partial(self._on_series_failure, message))
            return
        try:
            data = service.get_series_info(series_url)
        except requests.RequestException as error:
            message = (
                f"Status: {provider_key} series fetch failed - Network error: {error}"
            )
            logger.warning("Network error fetching series %s: %s", series_url, error)
            self._post_to_ui(functools.partial(self._on_series_failure, message))
        except (json.JSONDecodeError, KeyError, ValueError, AttributeError):
            logger.exception(
                "Data parsing error for series %s with %s", series_url, provider_key
            )
            message = (
                f"Status: {provider_key} series parsing error - Invalid response format"
            )
            self._post_to_ui(functools.partial(self._on_series_failure, message))
        except Exception as error:  # noqa: BLE001
            logger.exception(
                "Unexpected error processing series %s with %s", series_url, provider_key
            )
            message = f"Status: {provider_key} error - {error}"
            self._post_to_ui(functools.partial(self._on_series_failure, message))
        else:
            self._post_to_ui(functools.partial(self._on_series_success, data, provider_key))

    def _on_series_success(self, data: dict[str, Any], provider_key: str) -> None:
        """Handle successful series info fetch (runs on main thread)."""
        payload = data if isinstance(data, dict) else {}
        payload.setdefault("provider", provider_key)
        self.series_data = payload
        self.series_provider = provider_key
        self.series_chapters = payload.get("chapters", []) or []

        title = payload.get("title") or "Unknown Title"
        self.series_title_var.set(title)

        info_lines: list[str] = []
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

        info_content = (
            "\n\n".join(info_lines)
            if info_lines
            else "No additional information available."
        )
        self._update_text_widget(self.series_info_text, info_content)

        self.chapters_listbox.delete(0, tk.END)
        for idx, chapter in enumerate(self.series_chapters, start=1):
            chapter_title = (
                chapter.get("title") or chapter.get("label") or f"Chapter {idx}"
            )
            self.chapters_listbox.insert(tk.END, f"{idx:03d} • {chapter_title}")

        if self.series_chapters:
            first_url = self.series_chapters[0].get("url", "")
            if first_url:
                self.url_var.set(first_url)

        self.status_label.config(
            text=f"Status: Loaded {len(self.series_chapters)} {provider_key} chapter(s)."
        )
        self.load_series_button.config(state="normal")

    def _on_series_failure(self, message: str) -> None:
        """Handle series fetch failure (runs on main thread)."""
        self.load_series_button.config(state="normal")
        self.status_label.config(text=message)

    def _update_text_widget(self, widget: tk.Text, content: str) -> None:
        """Update a disabled Text widget with new content."""
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state="disabled")

    # --- Chapter Selection Handlers ---

    def on_chapter_select(self, event: tk.Event) -> None:
        """Handle chapter selection in listbox."""
        widget = cast(tk.Listbox, event.widget)
        selection = sorted(
            idx
            for idx in widget.curselection()
            if 0 <= idx < len(self.series_chapters)
        )
        if not selection:
            return

        first_index = selection[0]
        chapter = self.series_chapters[first_index]
        chapter_url = chapter.get("url", "")
        if chapter_url:
            self.url_var.set(chapter_url)

        self._update_range_from_indices(selection)

        if len(selection) == 1:
            chapter_title = (
                chapter.get("title")
                or chapter.get("label")
                or f"Chapter {first_index + 1}"
            )
            self.status_label.config(text=f"Status: Selected {chapter_title}")
        else:
            last_index = selection[-1]
            self.status_label.config(
                text=f"Status: Selected {len(selection)} chapter(s) ({first_index + 1}–{last_index + 1})"
            )

    def on_chapter_double_click(self, _event: tk.Event) -> None:
        """Handle double-click on chapter to queue download."""
        self.download_selected_chapter()

    def _on_select_all_chapters(self, _event: tk.Event | None = None) -> str:
        """Select all chapters in the listbox."""
        if not self.series_chapters:
            return "break"
        self.chapters_listbox.selection_set(0, tk.END)
        selection = list(range(len(self.series_chapters)))
        self._update_range_from_indices(selection)
        self._set_status(f"Status: Selected all {len(selection)} chapter(s).")
        return "break"

    def _update_range_from_indices(self, indices: list[int]) -> None:
        """Update range entry fields from selection indices."""
        if not indices:
            return
        first_index = indices[0]
        last_index = indices[-1]
        self.range_start_var.set(str(first_index + 1))
        self.range_end_var.set(str(last_index + 1))

    # --- Download Queue Methods ---

    def download_selected_chapter(self) -> None:
        """Queue selected chapters for download."""
        selection = self.chapters_listbox.curselection()
        if not selection:
            self._set_status("Status: Select one or more chapters to download.")
            return
        indices = sorted(
            {idx for idx in selection if 0 <= idx < len(self.series_chapters)}
        )
        chapter_items: list[tuple[str, str | None]] = []
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

    def download_range(self) -> None:
        """Queue chapters in the specified range for download."""
        range_bounds = self._get_range_indices()
        if range_bounds is None:
            return

        start_index, end_index = range_bounds
        self._highlight_range_selection(notify=False, bounds=range_bounds)

        chapter_items: list[tuple[str, str | None]] = []
        for idx in range(start_index, end_index + 1):
            chapter = self.series_chapters[idx]
            chapter_url = chapter.get("url", "")
            if not chapter_url:
                continue
            label = self._format_chapter_label(idx, chapter)
            chapter_items.append((chapter_url, label))

        if not chapter_items:
            self._set_status(
                "Status: No downloadable chapters in the requested range."
            )
            return

        self.url_var.set(chapter_items[0][0])
        self._enqueue_chapter_downloads(chapter_items)

    def _get_range_indices(self) -> tuple[int, int] | None:
        """Parse and validate range input, returning (start_index, end_index)."""
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

    def _highlight_range_selection(
        self,
        notify: bool = True,
        bounds: tuple[int, int] | None = None,
    ) -> None:
        """Highlight chapters in the specified range."""
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

    def download_all_chapters(self) -> None:
        """Queue all chapters for download."""
        if not self.series_chapters:
            self._set_status("Status: No chapters available to download.")
            return

        chapter_items: list[tuple[str, str | None]] = []
        for idx, chapter in enumerate(self.series_chapters):
            chapter_url = chapter.get("url", "")
            if not chapter_url:
                continue
            label = self._format_chapter_label(idx, chapter)
            chapter_items.append((chapter_url, label))

        if not chapter_items:
            self._set_status(
                "Status: Unable to queue downloads because no chapter URLs were found."
            )
            return

        self.url_var.set(chapter_items[0][0])
        self._enqueue_chapter_downloads(chapter_items)

    def _format_chapter_label(self, index: int, chapter: SeriesChapter) -> str:
        """Return a human-readable label for a queued chapter."""
        chapter_title = (
            chapter.get("title") or chapter.get("label") or f"Chapter {index + 1}"
        )
        return f"{index + 1:03d} • {chapter_title}"

"""Settings tab UI components and event handlers."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, ttk
from typing import TYPE_CHECKING

from config import CONFIG
from ui.widgets import clamp_value
from utils.file_utils import get_default_download_root

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SettingsTabMixin:
    """Mixin providing Settings tab UI construction and event handlers."""

    # Type hints for attributes expected from host class
    chapter_workers_var: tk.IntVar
    image_workers_var: tk.IntVar
    download_dir_var: tk.StringVar
    download_dir_path: str
    _chapter_workers_value: int
    _image_workers_value: int
    download_dir_entry: ttk.Entry
    chapter_workers_spinbox: ttk.Spinbox
    image_workers_spinbox: ttk.Spinbox

    # Methods expected from host class
    def _set_status(self, message: str) -> None:  # type: ignore[empty-body]
        """Update status label."""
    def _ensure_chapter_executor(self, force_reset: bool = False) -> None:  # type: ignore[empty-body]
        """Ensure chapter executor is ready."""

    def _build_settings_tab(self, parent: ttk.Frame) -> None:
        """Construct the Settings tab UI within the given parent frame."""
        scroll_container = ttk.Frame(parent)
        scroll_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(scroll_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        content_frame = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=content_frame, anchor="nw")

        def _sync_scroll_region(_event: tk.Event) -> None:
            bbox = canvas.bbox("all")
            if bbox is not None:
                canvas.configure(scrollregion=bbox)

        def _match_canvas_width(event: tk.Event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        content_frame.bind("<Configure>", _sync_scroll_region, add="+")
        canvas.bind("<Configure>", _match_canvas_width, add="+")

        handler = getattr(self, "_mousewheel_handler", None)
        if handler is not None:
            handler.bind_mousewheel(content_frame, target=canvas)

        # --- Download Settings ---
        settings_frame = ttk.LabelFrame(content_frame, text="Download Settings")
        settings_frame.pack(fill="x", expand=False, padx=10, pady=(12, 10))

        # Directory selection
        directory_frame = ttk.Frame(settings_frame)
        directory_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(directory_frame, text="Save to:").pack(side="left")
        self.download_dir_entry = ttk.Entry(
            directory_frame, textvariable=self.download_dir_var
        )
        self.download_dir_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(
            directory_frame, text="Browse...", command=self._browse_download_dir
        ).pack(side="left")

        # Concurrency settings
        concurrency_frame = ttk.Frame(settings_frame)
        concurrency_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(concurrency_frame, text="Chapter workers:").pack(side="left")
        self.chapter_workers_spinbox = ttk.Spinbox(
            concurrency_frame,
            from_=CONFIG.download.min_chapter_workers,
            to=CONFIG.download.max_chapter_workers,
            width=4,
            textvariable=self.chapter_workers_var,
            command=self._on_chapter_workers_change,
        )
        self.chapter_workers_spinbox.pack(side="left", padx=(6, 18))
        self.chapter_workers_spinbox.bind("<FocusOut>", self._on_chapter_workers_change)

        ttk.Label(concurrency_frame, text="Image workers:").pack(side="left")
        self.image_workers_spinbox = ttk.Spinbox(
            concurrency_frame,
            from_=CONFIG.download.min_image_workers,
            to=CONFIG.download.max_image_workers,
            width=4,
            textvariable=self.image_workers_var,
            command=self._on_image_workers_change,
        )
        self.image_workers_spinbox.pack(side="left", padx=(6, 0))
        self.image_workers_spinbox.bind("<FocusOut>", self._on_image_workers_change)

        # --- Bato Mirror Settings ---
        self._build_bato_mirror_section(content_frame)

    # --- Directory Selection ---

    def _browse_download_dir(self) -> None:
        """Open a directory selection dialog."""
        initial_dir = self.download_dir_path or get_default_download_root()
        directory = filedialog.askdirectory(initialdir=initial_dir)
        if directory:
            self.download_dir_var.set(directory)

    def _on_download_dir_var_write(self, *_: object) -> None:
        """Handle changes to the download directory variable."""
        value = self.download_dir_var.get()
        self.download_dir_path = value.strip() if isinstance(value, str) else ""

    # --- Worker Count Handlers ---

    def _on_chapter_workers_change(self, event: tk.Event | None = None) -> None:
        """Handle changes to chapter worker count."""
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

    def _on_image_workers_change(self, event: tk.Event | None = None) -> None:
        """Handle changes to image worker count."""
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
        """Get the current image worker count, clamped to valid range."""
        value = clamp_value(
            self._image_workers_value or CONFIG.download.default_image_workers,
            CONFIG.download.min_image_workers,
            CONFIG.download.max_image_workers,
            CONFIG.download.default_image_workers,
        )
        return min(value, CONFIG.download.max_total_image_workers)

    # --- Bato Mirror Management ---

    def _build_bato_mirror_section(self, parent: ttk.Frame) -> None:
        """Build the Bato mirror site management section."""
        from services.bato_mirror_manager import get_mirror_manager

        self._bato_mirror_manager = get_mirror_manager()
        self._bato_mirror_entry_var = tk.StringVar()

        mirror_frame = ttk.LabelFrame(parent, text="Bato Mirror Sites")
        mirror_frame.pack(fill="x", expand=False, padx=10, pady=(0, 10))

        description = (
            "Paste a search URL from any Bato mirror site to add it. "
            "Example: https://bato.ing/v4x-search?type=comic&word=test\n"
            "The system will auto-detect the search path and parameters for each mirror."
        )
        ttk.Label(mirror_frame, text=description, wraplength=550, justify="left").pack(
            anchor="w", padx=10, pady=(8, 6)
        )

        # Current mirror indicator
        current_frame = ttk.Frame(mirror_frame)
        current_frame.pack(fill="x", padx=10, pady=(0, 6))
        ttk.Label(current_frame, text="Current mirror:").pack(side="left")
        self._current_mirror_label = ttk.Label(
            current_frame,
            text=self._bato_mirror_manager.current_base_url,
            foreground="#1d4ed8",
        )
        self._current_mirror_label.pack(side="left", padx=(6, 0))

        # Mirror list
        list_frame = ttk.Frame(mirror_frame)
        list_frame.pack(fill="x", padx=10, pady=(0, 6))

        self._bato_mirrors_listbox = tk.Listbox(list_frame, height=4, selectmode=tk.SINGLE)
        self._bato_mirrors_listbox.pack(side="left", fill="x", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._bato_mirrors_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._bato_mirrors_listbox.configure(yscrollcommand=scrollbar.set)

        self._refresh_bato_mirrors_list()

        # Entry for adding/updating mirror by pasting search URL
        entry_frame = ttk.Frame(mirror_frame)
        entry_frame.pack(fill="x", padx=10, pady=(0, 6))

        ttk.Label(entry_frame, text="Paste search URL:").pack(side="left")
        entry = ttk.Entry(entry_frame, textvariable=self._bato_mirror_entry_var)
        entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(entry_frame, text="Add/Update", command=self._add_bato_mirror).pack(side="left")

        # Control buttons
        button_frame = ttk.Frame(mirror_frame)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(button_frame, text="Remove Selected", command=self._remove_bato_mirror).pack(side="left")
        ttk.Button(button_frame, text="Move Up", command=self._move_bato_mirror_up).pack(side="left", padx=(6, 0))
        ttk.Button(button_frame, text="Move Down", command=self._move_bato_mirror_down).pack(side="left", padx=(6, 0))
        ttk.Button(button_frame, text="Reset to Defaults", command=self._reset_bato_mirrors).pack(side="left", padx=(6, 0))

    def _refresh_bato_mirrors_list(self) -> None:
        """Refresh the mirror list display."""
        listbox = getattr(self, "_bato_mirrors_listbox", None)
        if listbox is None:
            return
        listbox.delete(0, tk.END)
        mirrors = self._bato_mirror_manager.mirrors
        for i, _mirror in enumerate(mirrors):
            display = self._bato_mirror_manager.format_mirror_display(i)
            listbox.insert(tk.END, display)

        # Update current mirror label
        label = getattr(self, "_current_mirror_label", None)
        if label is not None:
            label.configure(text=self._bato_mirror_manager.current_base_url)

    def _add_bato_mirror(self) -> None:
        """Add or update a mirror by parsing a search URL."""
        url = self._bato_mirror_entry_var.get().strip()
        if not url:
            self._set_status("Status: Please paste a search URL from your browser.")
            return

        success, message = self._bato_mirror_manager.add_mirror_from_url(url)
        self._set_status(f"Status: {message}")
        if success:
            self._bato_mirror_entry_var.set("")
            self._refresh_bato_mirrors_list()

    def _remove_bato_mirror(self) -> None:
        """Remove the selected mirror site."""
        listbox = getattr(self, "_bato_mirrors_listbox", None)
        if listbox is None:
            return
        selection = listbox.curselection()
        if not selection:
            self._set_status("Status: Please select a mirror to remove.")
            return

        index = selection[0]
        success, message = self._bato_mirror_manager.remove_mirror(index)
        self._set_status(f"Status: {message}")
        if success:
            self._refresh_bato_mirrors_list()

    def _move_bato_mirror_up(self) -> None:
        """Move the selected mirror up in the list."""
        listbox = getattr(self, "_bato_mirrors_listbox", None)
        if listbox is None:
            return
        selection = listbox.curselection()
        if not selection:
            self._set_status("Status: Please select a mirror to move.")
            return

        index = selection[0]
        if index == 0:
            return  # Already at top

        if self._bato_mirror_manager.move_mirror(index, index - 1):
            self._refresh_bato_mirrors_list()
            listbox.selection_set(index - 1)

    def _move_bato_mirror_down(self) -> None:
        """Move the selected mirror down in the list."""
        listbox = getattr(self, "_bato_mirrors_listbox", None)
        if listbox is None:
            return
        selection = listbox.curselection()
        if not selection:
            self._set_status("Status: Please select a mirror to move.")
            return

        index = selection[0]
        mirrors = self._bato_mirror_manager.mirrors
        if index >= len(mirrors) - 1:
            return  # Already at bottom

        if self._bato_mirror_manager.move_mirror(index, index + 1):
            self._refresh_bato_mirrors_list()
            listbox.selection_set(index + 1)

    def _reset_bato_mirrors(self) -> None:
        """Reset mirrors to default configuration."""
        self._bato_mirror_manager.reset_to_defaults()
        self._refresh_bato_mirrors_list()
        self._set_status("Status: Mirrors reset to defaults.")

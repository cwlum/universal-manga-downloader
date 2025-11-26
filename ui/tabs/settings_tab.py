"""Settings tab UI components and event handlers."""

from __future__ import annotations

import logging
import tkinter as tk
from functools import partial
from tkinter import filedialog, ttk
from typing import TYPE_CHECKING

from config import CONFIG
from plugins.base import PluginType
from ui.widgets import clamp_value
from utils.file_utils import get_default_download_root

if TYPE_CHECKING:
    from plugins.base import PluginManager

logger = logging.getLogger(__name__)


class SettingsTabMixin:
    """Mixin providing Settings tab UI construction and event handlers."""

    # Type hints for attributes expected from host class
    plugin_manager: PluginManager
    plugin_vars: dict[tuple[PluginType, str], tk.BooleanVar]
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
    def _refresh_provider_options(self) -> None:  # type: ignore[empty-body]
        """Refresh provider options."""
    def _ensure_chapter_executor(self, force_reset: bool = False) -> None:  # type: ignore[empty-body]
        """Ensure chapter executor is ready."""

    def _build_settings_tab(self, parent: ttk.Frame) -> None:
        """Construct the Settings tab UI within the given parent frame."""
        # --- Download Settings ---
        settings_frame = ttk.LabelFrame(parent, text="Download Settings")
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
            directory_frame, text="Browse…", command=self._browse_download_dir
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

        # Plugin settings
        self._build_plugin_settings(parent)

    def _build_plugin_settings(self, parent: ttk.Frame) -> None:
        """Render plugin toggle controls within the settings tab."""
        plugin_records = self.plugin_manager.get_records()
        if not plugin_records:
            return

        container = ttk.LabelFrame(parent, text="Plugins")
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

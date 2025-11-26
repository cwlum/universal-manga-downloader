"""Downloads tab UI components and event handlers for queue management."""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from collections.abc import Callable
from concurrent.futures import Future
from tkinter import ttk
from typing import TYPE_CHECKING, Any

from config import CONFIG
from core.queue_manager import QueueManager, QueueState
from ui.models import STATUS_COLORS, QueueItem

if TYPE_CHECKING:
    import threading

    from ui.widgets import MouseWheelHandler

logger = logging.getLogger(__name__)


class DownloadsTabMixin:
    """Mixin providing Downloads tab UI construction and event handlers."""

    # Type hints for attributes expected from host class
    queue_manager: QueueManager
    queue_items: dict[int, QueueItem]
    queue_status_var: tk.StringVar
    _downloads_paused: bool
    _chapter_futures: dict[int, Future[None]]
    _can_proceed_event: threading.Event
    _mousewheel_handler: MouseWheelHandler
    pause_button: ttk.Button | None
    cancel_pending_button: ttk.Button | None
    _queue_item_sequence: int
    queue_canvas: tk.Canvas
    queue_items_container: ttk.Frame
    queue_canvas_window: int
    queue_progress: ttk.Progressbar
    queue_label: ttk.Label

    if TYPE_CHECKING:
        # Methods expected from host class
        def after(self, ms: int, func: Any = ...) -> str: ...

        def after_cancel(self, id: str) -> None: ...

    def _set_status(self, message: str) -> None:  # type: ignore[empty-body]
        """Update status label."""
    def _start_download_future(self, queue_id: int, url: str, initial_label: str | None) -> None:  # type: ignore[empty-body]
        """Start download future."""
    def _post_to_ui(self, callback: Callable[[], None]) -> None:  # type: ignore[empty-body]
        """Schedule callable on Tk thread."""

    def _build_downloads_tab(self, parent: ttk.Frame) -> None:
        """Construct the Downloads tab UI within the given parent frame."""
        # --- Queue Display ---
        queue_wrapper = ttk.LabelFrame(parent, text="Download Queue")
        queue_wrapper.pack(fill="both", expand=True, padx=10, pady=(12, 10))

        queue_canvas_frame = ttk.Frame(queue_wrapper)
        queue_canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.queue_canvas = tk.Canvas(
            queue_canvas_frame, borderwidth=0, highlightthickness=0
        )
        self.queue_canvas.pack(side="left", fill="both", expand=True)

        self.queue_items_container = ttk.Frame(self.queue_canvas)
        self.queue_canvas_window = self.queue_canvas.create_window(
            (0, 0), window=self.queue_items_container, anchor="nw"
        )

        def _sync_queue_width(event: tk.Event) -> None:
            self.queue_canvas.itemconfigure(self.queue_canvas_window, width=event.width)

        self.queue_canvas.bind("<Configure>", _sync_queue_width)

        queue_scrollbar = ttk.Scrollbar(
            queue_canvas_frame, orient="vertical", command=self.queue_canvas.yview
        )
        queue_scrollbar.pack(side="right", fill="y")
        self.queue_canvas.configure(yscrollcommand=queue_scrollbar.set)

        def _sync_queue_scrollregion(event: tk.Event) -> None:
            self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))

        self.queue_items_container.bind("<Configure>", _sync_queue_scrollregion)

        # --- Queue Footer ---
        queue_footer = ttk.LabelFrame(parent, text="Queue Overview")
        queue_footer.pack(fill="x", expand=False, padx=10, pady=(0, 12))

        ttk.Label(queue_footer, text="Overall queue:").pack(anchor="w", padx=10, pady=(6, 0))
        self.queue_progress = ttk.Progressbar(
            queue_footer, orient="horizontal", mode="determinate"
        )
        self.queue_progress.pack(fill="x", padx=10, pady=(0, 6))

        queue_controls_frame = ttk.Frame(queue_footer)
        queue_controls_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.queue_label = ttk.Label(
            queue_controls_frame, textvariable=self.queue_status_var
        )
        self.queue_label.pack(side="left", anchor="w")

        ttk.Button(
            queue_controls_frame,
            text="Clear Finished",
            command=self._clear_finished_queue_items,
        ).pack(side="right")

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

    def _bind_downloads_mousewheel(self) -> None:
        """Bind mousewheel handlers for downloads tab scrollable widgets."""
        self._mousewheel_handler.bind_mousewheel(self.queue_canvas)
        self._mousewheel_handler.bind_mousewheel(
            self.queue_items_container, target=self.queue_canvas
        )

    # --- Pause/Resume Controls ---

    def _toggle_download_pause(self) -> None:
        """Toggle between paused and resumed download state."""
        if self._downloads_paused:
            self._resume_downloads()
        else:
            self._pause_downloads()

    def _pause_downloads(self) -> None:
        """Pause all pending and queued downloads."""
        if self._downloads_paused or self.queue_manager.is_paused():
            return

        self._downloads_paused = True
        self._can_proceed_event.clear()  # Block downloads from proceeding
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

    def _resume_downloads(self) -> None:
        """Resume paused downloads."""
        if not self._downloads_paused and not self.queue_manager.is_paused():
            return

        self._downloads_paused = False
        self._can_proceed_event.set()  # Allow downloads to proceed
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
        """Cancel all pending (not yet started) downloads."""
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
        """Mark a queue item as cancelled."""
        self.queue_manager.cancel_item(queue_id)
        self._queue_reset_progress(queue_id, 1)
        self._queue_set_status(queue_id, "Cancelled", state=QueueState.CANCELLED)

    # --- Queue Status Updates ---

    def _update_queue_status(self) -> None:
        """Update the queue status label with current stats."""
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

        self._post_to_ui(_update)

    def _update_queue_progress(self) -> None:
        """Update the overall queue progress bar."""
        stats = self.queue_manager.get_stats()
        total = stats.total
        completed = min(stats.completed + stats.cancelled, total)

        def _update() -> None:
            if total > 0:
                self.queue_progress["maximum"] = max(1, total)
                self.queue_progress["value"] = completed
            else:
                self.queue_progress["maximum"] = 1
                self.queue_progress["value"] = 0

        self._post_to_ui(_update)

    # --- Queue Item Management ---

    def _register_queue_item(
        self,
        label: str | None,
        url: str,
        initial_label: str | None,
    ) -> int:
        """Create and register a new queue item widget."""
        display = label or url or "Pending chapter"
        queue_id = self._queue_item_sequence
        self._queue_item_sequence += 1

        item_frame = ttk.Frame(self.queue_items_container)
        item_frame.pack(fill="x", expand=False, padx=8, pady=4)

        title_var = tk.StringVar(value=display)
        title_label = ttk.Label(
            item_frame, textvariable=title_var, font=("TkDefaultFont", 10, "bold")
        )
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
        """Update the title of a queue item."""
        def _update() -> None:
            item = self.queue_items.get(queue_id)
            if not item:
                return
            item.title_var.set(title)

        self._post_to_ui(_update)

    def _queue_set_status(
        self,
        queue_id: int,
        text: str,
        state: QueueState | None = None,
    ) -> None:
        """Update the status text and color of a queue item."""
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

        self._post_to_ui(_update)

    def _queue_reset_progress(self, queue_id: int, maximum: int) -> None:
        """Reset the progress bar for a queue item."""
        maximum = max(1, maximum)

        def _update() -> None:
            item = self.queue_items.get(queue_id)
            if not item:
                return
            item.maximum = maximum
            progress = item.progress
            progress["maximum"] = maximum
            progress["value"] = 0

        self._post_to_ui(_update)

    def _queue_update_progress(
        self,
        queue_id: int,
        completed: int,
        total: int | None = None,
    ) -> None:
        """Update the progress bar for a queue item."""
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

        self._post_to_ui(_update)

    def _queue_mark_finished(
        self,
        queue_id: int,
        success: bool = True,
        message: str | None = None,
    ) -> None:
        """Mark a queue item as finished (success or failure)."""
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

        self._post_to_ui(_update)
        self._queue_set_status(queue_id, text, state=state)

    def _scroll_queue_to_bottom(self) -> None:
        """Ensure the queue canvas keeps the newest items in view."""
        def _scroll() -> None:
            self.queue_canvas.update_idletasks()
            self.queue_canvas.yview_moveto(1.0)

        self.after(CONFIG.ui.queue_scroll_delay_ms, _scroll)

    def _clear_finished_queue_items(self) -> None:
        """Remove completed/failed/cancelled items from the queue display."""
        removable_states = {QueueState.SUCCESS, QueueState.ERROR, QueueState.CANCELLED}
        ids_to_remove = [
            qid for qid, item in self.queue_items.items() if item.state in removable_states
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

        self._set_status(
            f"Status: Cleared {len(ids_to_remove)} finished item(s) from the queue."
        )

    # --- Mousewheel Scrolling Helpers ---

    def _bind_mousewheel_area(
        self,
        widget: tk.Misc | None,
        target: tk.Misc | None = None,
    ) -> None:
        """Bind wheel events so nested widgets share the same scroll target."""
        if widget is None:
            return

        actual_target = target or widget

        if not hasattr(self, "_bound_widgets"):
            self._bound_widgets: set[tk.Misc] = set()

        if widget in self._bound_widgets:
            return

        def _on_mousewheel(
            event: tk.Event, scroll_target: tk.Misc = actual_target
        ) -> str:
            delta = self._normalize_mousewheel_delta(event)
            if abs(delta) < 0.001:
                return "break"
            self._scroll_target(scroll_target, delta)
            return "break"

        def _on_linux_wheel(
            event: tk.Event, scroll_target: tk.Misc = actual_target
        ) -> str:
            if event.num == 4:
                delta = -1.0
            elif event.num == 5:
                delta = 1.0
            else:
                return "break"
            self._scroll_target(scroll_target, delta)
            return "break"

        widget.bind("<MouseWheel>", _on_mousewheel, add=True)
        widget.bind("<Button-4>", _on_linux_wheel, add=True)
        widget.bind("<Button-5>", _on_linux_wheel, add=True)

        self._bound_widgets.add(widget)

        for child in widget.winfo_children():
            self._bind_mousewheel_area(child, target=actual_target)

    def _normalize_mousewheel_delta(self, event: tk.Event) -> float:
        """Normalise OS-specific wheel events into consistent unit steps."""
        delta = getattr(event, "delta", 0)
        if delta == 0:
            return 0.0

        platform = sys.platform

        if platform.startswith("linux"):
            if abs(delta) >= 120:
                return -delta / 120.0
            return -1.0 if delta > 0 else 1.0

        if platform == "darwin":
            abs_delta = abs(delta)
            if abs_delta >= 40:
                normalized = -delta / 30.0
                return max(-5.0, min(5.0, normalized))
            normalized = -delta * 0.3
            return max(-2.0, min(2.0, normalized))

        return -delta / 120.0

    def _scroll_target(self, target: tk.Misc, delta: float) -> None:
        """Scroll widgets with smooth fractional delta support."""
        if not hasattr(target, "yview_scroll"):
            return

        try:
            if isinstance(target, tk.Canvas):
                pixels = int(delta * 20)
                if pixels != 0:
                    target.yview_scroll(pixels, "pixels")
                return

            if not hasattr(self, "_scroll_remainders"):
                self._scroll_remainders: dict[tk.Misc, float] = {}

            remainder = self._scroll_remainders.get(target, 0.0) + float(delta)
            steps = int(remainder)
            remainder -= steps
            self._scroll_remainders[target] = remainder

            if steps != 0:
                target.yview_scroll(steps, "units")

        except tk.TclError:
            pass

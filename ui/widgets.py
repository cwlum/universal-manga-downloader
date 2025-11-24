"""Reusable UI widgets and helper functions."""

from __future__ import annotations

import platform
import tkinter as tk
from typing import Callable


class MouseWheelHandler:
    """Handles cross-platform mouse wheel scrolling for Tkinter widgets."""

    def __init__(self):
        self._scroll_remainders: dict[tk.Misc, float] = {}
        self._system = platform.system()

    def bind_mousewheel(
        self,
        widget: tk.Misc,
        target: tk.Misc | None = None,
        scroll_callback: Callable[[tk.Misc, float], None] | None = None,
    ) -> None:
        """
        Bind mouse wheel events to a widget for smooth scrolling.

        Args:
            widget: Widget to bind mouse wheel events to
            target: Widget to scroll (defaults to widget if None)
            scroll_callback: Custom scroll callback (uses default if None)
        """
        if target is None:
            target = widget

        if scroll_callback is None:
            scroll_callback = self._default_scroll_handler

        def on_enter(_event: tk.Event) -> None:
            if self._system == "Linux":
                widget.bind_all("<Button-4>", lambda e: scroll_callback(target, 1.0), add="+")
                widget.bind_all("<Button-5>", lambda e: scroll_callback(target, -1.0), add="+")
            else:
                widget.bind_all("<MouseWheel>", lambda e: self._on_mousewheel(e, target, scroll_callback), add="+")

        def on_leave(_event: tk.Event) -> None:
            if self._system == "Linux":
                widget.unbind_all("<Button-4>")
                widget.unbind_all("<Button-5>")
            else:
                widget.unbind_all("<MouseWheel>")

        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")

    def _on_mousewheel(
        self,
        event: tk.Event,
        target: tk.Misc,
        scroll_callback: Callable[[tk.Misc, float], None],
    ) -> None:
        """Handle mouse wheel event with platform-specific delta normalization."""
        delta = self._normalize_mousewheel_delta(event)
        scroll_callback(target, delta)

    def _normalize_mousewheel_delta(self, event: tk.Event) -> float:
        """Normalize mouse wheel delta across platforms."""
        raw = event.delta if hasattr(event, "delta") else 0

        if self._system == "Darwin":  # macOS
            return float(raw)
        elif self._system == "Windows":
            return float(raw) / 120.0
        else:  # Linux
            return 1.0 if raw > 0 else -1.0

    def _default_scroll_handler(self, target: tk.Misc, delta: float) -> None:
        """Default scroll handler for canvas and listbox widgets."""
        if not isinstance(target, (tk.Canvas, tk.Listbox, tk.Text)):
            return

        # Get or initialize remainder for this widget
        remainder = self._scroll_remainders.get(target, 0.0)
        total = remainder + delta

        # Calculate integer scroll units
        if abs(total) >= 1.0:
            units = int(total)
            remainder = total - units

            # Scroll the widget
            if isinstance(target, tk.Canvas):
                target.yview_scroll(-units, "units")
            elif isinstance(target, (tk.Listbox, tk.Text)):
                target.yview_scroll(-units, "units")

            self._scroll_remainders[target] = remainder
        else:
            self._scroll_remainders[target] = total


def clamp_value(value: int, min_val: int, max_val: int, default: int) -> int:
    """
    Clamp a value between min and max, returning default if out of range.

    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        default: Default value if out of range

    Returns:
        Clamped value
    """
    if not isinstance(value, int):
        return default
    if value < min_val or value > max_val:
        return default
    return value


__all__ = [
    "MouseWheelHandler",
    "clamp_value",
]

"""Data models and type definitions for the UI layer."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import TypedDict

from core.queue_manager import QueueState

# Status color mapping for queue items
STATUS_COLORS: dict[QueueState, str] = {
    QueueState.SUCCESS: "#1a7f37",
    QueueState.ERROR: "#b91c1c",
    QueueState.RUNNING: "#1d4ed8",
    QueueState.PAUSED: "#d97706",
    QueueState.CANCELLED: "#6b7280",
}


@dataclass(slots=True)
class QueueItem:
    """Container for per-chapter queue widgets and metadata."""

    frame: ttk.Frame
    title_var: tk.StringVar
    status_var: tk.StringVar
    status_label: ttk.Label
    progress: ttk.Progressbar
    maximum: int = 1
    url: str = ""
    initial_label: str | None = None
    state: QueueState = QueueState.PENDING


class SearchResult(TypedDict, total=False):
    """Shape of entries stored for search results."""

    title: str
    url: str
    subtitle: str
    provider: str


class SeriesChapter(TypedDict, total=False):
    """Shape of chapter metadata fetched from manga services."""

    title: str
    url: str
    label: str


__all__ = [
    "STATUS_COLORS",
    "QueueItem",
    "SearchResult",
    "SeriesChapter",
]

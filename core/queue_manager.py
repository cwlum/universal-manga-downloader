"""Thread-safe queue state management."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum


class QueueState(str, Enum):
    """Enumerates the possible lifecycle states for queue items."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class QueueStats:
    """Statistics about the download queue."""

    total: int = 0
    pending: int = 0
    active: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


@dataclass
class QueueItemData:
    """Data associated with a queue item."""

    queue_id: int
    url: str
    initial_label: str | None
    state: QueueState = QueueState.PENDING
    progress: int = 0
    maximum: int = 1
    error_message: str | None = None


class QueueManager:
    """Thread-safe manager for download queue state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending_downloads = 0
        self._active_downloads = 0
        self._total_downloads = 0
        self._completed_downloads = 0
        self._paused = False
        self._queue_items: dict[int, QueueItemData] = {}
        self._deferred_items: list[tuple[int, str, str | None]] = []
        self._cancelled_ids: set[int] = set()
        self._paused_ids: set[int] = set()

    @contextmanager
    def transaction(self) -> Iterator[QueueManager]:
        """Context manager for thread-safe queue operations."""
        with self._lock:
            yield self

    def add_item(self, queue_id: int, url: str, initial_label: str | None) -> None:
        """Add a new item to the queue."""
        with self._lock:
            self._queue_items[queue_id] = QueueItemData(
                queue_id=queue_id,
                url=url,
                initial_label=initial_label,
                state=QueueState.PENDING,
            )
            self._pending_downloads += 1
            self._total_downloads += 1

    def start_item(self, queue_id: int) -> None:
        """Mark item as started."""
        with self._lock:
            if queue_id in self._queue_items:
                self._queue_items[queue_id].state = QueueState.RUNNING
            if self._pending_downloads > 0:
                self._pending_downloads -= 1
            self._active_downloads += 1

    def complete_item(self, queue_id: int, success: bool = True, error: str | None = None) -> None:
        """Mark item as completed."""
        with self._lock:
            if queue_id in self._queue_items:
                item = self._queue_items[queue_id]
                item.state = QueueState.SUCCESS if success else QueueState.ERROR
                item.error_message = error
            if self._active_downloads > 0:
                self._active_downloads -= 1
            if self._total_downloads > 0:
                self._completed_downloads = min(
                    self._completed_downloads + 1,
                    self._total_downloads,
                )

    def cancel_item(self, queue_id: int) -> None:
        """Mark item as cancelled."""
        with self._lock:
            if queue_id in self._queue_items:
                self._queue_items[queue_id].state = QueueState.CANCELLED
            self._cancelled_ids.add(queue_id)
            if self._pending_downloads > 0:
                self._pending_downloads -= 1
            if self._total_downloads > 0:
                self._total_downloads -= 1

    def pause_item(self, queue_id: int) -> None:
        """Mark item as paused."""
        with self._lock:
            if queue_id in self._queue_items:
                self._queue_items[queue_id].state = QueueState.PAUSED
            self._paused_ids.add(queue_id)

    def update_progress(self, queue_id: int, progress: int, maximum: int | None = None) -> None:
        """Update progress for a queue item."""
        with self._lock:
            if queue_id in self._queue_items:
                item = self._queue_items[queue_id]
                if maximum is not None:
                    item.maximum = max(1, maximum)
                item.progress = max(0, min(item.maximum, progress))

    def reset_progress(self, queue_id: int, maximum: int) -> None:
        """Reset progress for a queue item."""
        with self._lock:
            if queue_id in self._queue_items:
                item = self._queue_items[queue_id]
                item.maximum = max(1, maximum)
                item.progress = 0

    def get_item(self, queue_id: int) -> QueueItemData | None:
        """Get queue item data."""
        with self._lock:
            return self._queue_items.get(queue_id)

    def remove_item(self, queue_id: int) -> QueueItemData | None:
        """Remove item from queue."""
        with self._lock:
            return self._queue_items.pop(queue_id, None)

    def get_stats(self) -> QueueStats:
        """Get current queue statistics."""
        with self._lock:
            return QueueStats(
                total=self._total_downloads,
                pending=self._pending_downloads,
                active=self._active_downloads,
                completed=self._completed_downloads,
            )

    def is_paused(self) -> bool:
        """Check if queue is paused."""
        with self._lock:
            return self._paused

    def pause(self) -> None:
        """Pause the queue."""
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        """Resume the queue."""
        with self._lock:
            self._paused = False

    def add_deferred(self, queue_id: int, url: str, initial_label: str | None) -> None:
        """Add item to deferred list."""
        with self._lock:
            self._deferred_items.append((queue_id, url, initial_label))

    def get_deferred(self) -> list[tuple[int, str, str | None]]:
        """Get and clear deferred items."""
        with self._lock:
            items = self._deferred_items.copy()
            self._deferred_items.clear()
            return items

    def is_cancelled(self, queue_id: int) -> bool:
        """Check if item is cancelled."""
        with self._lock:
            return queue_id in self._cancelled_ids

    def is_item_paused(self, queue_id: int) -> bool:
        """Check if specific item is paused."""
        with self._lock:
            return queue_id in self._paused_ids

    def clear_cancelled(self, queue_id: int) -> None:
        """Remove item from cancelled set."""
        with self._lock:
            self._cancelled_ids.discard(queue_id)

    def clear_paused(self, queue_id: int) -> None:
        """Remove item from paused set."""
        with self._lock:
            self._paused_ids.discard(queue_id)

    def reset_counters(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._total_downloads = 0
            self._completed_downloads = 0
            self._pending_downloads = 0
            self._active_downloads = 0

    def get_removable_items(self) -> list[int]:
        """Get list of queue IDs that can be removed (completed/error/cancelled)."""
        removable_states = {QueueState.SUCCESS, QueueState.ERROR, QueueState.CANCELLED}
        with self._lock:
            return [
                qid
                for qid, item in self._queue_items.items()
                if item.state in removable_states
            ]

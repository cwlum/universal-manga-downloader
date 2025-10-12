"""Tests for QueueManager."""

from __future__ import annotations

from core.queue_manager import QueueManager, QueueState


class TestQueueManager:
    """Test cases for QueueManager."""

    def test_add_item(self):
        """Test adding items to queue."""
        manager = QueueManager()
        manager.add_item(1, "http://example.com", "Test Chapter")

        stats = manager.get_stats()
        assert stats.total == 1
        assert stats.pending == 1
        assert stats.active == 0

        item = manager.get_item(1)
        assert item is not None
        assert item.queue_id == 1
        assert item.url == "http://example.com"
        assert item.initial_label == "Test Chapter"
        assert item.state == QueueState.PENDING

    def test_start_item(self):
        """Test starting a queued item."""
        manager = QueueManager()
        manager.add_item(1, "http://example.com", None)
        manager.start_item(1)

        stats = manager.get_stats()
        assert stats.pending == 0
        assert stats.active == 1

        item = manager.get_item(1)
        assert item is not None
        assert item.state == QueueState.RUNNING

    def test_complete_item_success(self):
        """Test completing an item successfully."""
        manager = QueueManager()
        manager.add_item(1, "http://example.com", None)
        manager.start_item(1)
        manager.complete_item(1, success=True)

        stats = manager.get_stats()
        assert stats.active == 0
        assert stats.completed == 1

        item = manager.get_item(1)
        assert item is not None
        assert item.state == QueueState.SUCCESS

    def test_complete_item_failure(self):
        """Test completing an item with failure."""
        manager = QueueManager()
        manager.add_item(1, "http://example.com", None)
        manager.start_item(1)
        manager.complete_item(1, success=False, error="Network error")

        item = manager.get_item(1)
        assert item is not None
        assert item.state == QueueState.ERROR
        assert item.error_message == "Network error"

    def test_cancel_item(self):
        """Test cancelling a queued item."""
        manager = QueueManager()
        manager.add_item(1, "http://example.com", None)
        manager.cancel_item(1)

        assert manager.is_cancelled(1)
        item = manager.get_item(1)
        assert item is not None
        assert item.state == QueueState.CANCELLED

        stats = manager.get_stats()
        assert stats.total == 0  # Cancelled items are removed from total

    def test_pause_resume(self):
        """Test pausing and resuming queue."""
        manager = QueueManager()
        assert not manager.is_paused()

        manager.pause()
        assert manager.is_paused()

        manager.resume()
        assert not manager.is_paused()

    def test_progress_tracking(self):
        """Test progress tracking for items."""
        manager = QueueManager()
        manager.add_item(1, "http://example.com", None)

        manager.update_progress(1, 5, 10)
        item = manager.get_item(1)
        assert item is not None
        assert item.progress == 5
        assert item.maximum == 10

        manager.update_progress(1, 10)
        item = manager.get_item(1)
        assert item is not None
        assert item.progress == 10

    def test_reset_progress(self):
        """Test resetting progress."""
        manager = QueueManager()
        manager.add_item(1, "http://example.com", None)
        manager.update_progress(1, 5, 10)

        manager.reset_progress(1, 20)
        item = manager.get_item(1)
        assert item is not None
        assert item.progress == 0
        assert item.maximum == 20

    def test_deferred_items(self):
        """Test deferred items management."""
        manager = QueueManager()
        manager.add_deferred(1, "http://example.com", "Chapter 1")
        manager.add_deferred(2, "http://example.com/2", "Chapter 2")

        deferred = manager.get_deferred()
        assert len(deferred) == 2
        assert deferred[0] == (1, "http://example.com", "Chapter 1")
        assert deferred[1] == (2, "http://example.com/2", "Chapter 2")

        # Should be cleared after getting
        deferred_again = manager.get_deferred()
        assert len(deferred_again) == 0

    def test_remove_item(self):
        """Test removing items from queue."""
        manager = QueueManager()
        manager.add_item(1, "http://example.com", None)

        removed = manager.remove_item(1)
        assert removed is not None
        assert removed.queue_id == 1

        assert manager.get_item(1) is None

    def test_get_removable_items(self):
        """Test getting removable items."""
        manager = QueueManager()
        manager.add_item(1, "http://example.com", None)
        manager.add_item(2, "http://example.com/2", None)
        manager.add_item(3, "http://example.com/3", None)

        manager.start_item(1)
        manager.complete_item(1, success=True)
        manager.cancel_item(2)

        removable = manager.get_removable_items()
        assert len(removable) == 2
        assert 1 in removable  # Completed
        assert 2 in removable  # Cancelled
        assert 3 not in removable  # Still pending

    def test_transaction_context(self):
        """Test transaction context manager."""
        manager = QueueManager()

        with manager.transaction():
            manager.add_item(1, "http://example.com", None)
            manager.add_item(2, "http://example.com/2", None)

        stats = manager.get_stats()
        assert stats.total == 2

    def test_multiple_items(self):
        """Test managing multiple items."""
        manager = QueueManager()

        # Add multiple items
        for i in range(5):
            manager.add_item(i, f"http://example.com/{i}", f"Chapter {i}")

        stats = manager.get_stats()
        assert stats.total == 5
        assert stats.pending == 5

        # Process some items
        manager.start_item(0)
        manager.complete_item(0, success=True)
        manager.start_item(1)
        manager.complete_item(1, success=False)

        stats = manager.get_stats()
        assert stats.pending == 3
        assert stats.active == 0
        assert stats.completed == 2

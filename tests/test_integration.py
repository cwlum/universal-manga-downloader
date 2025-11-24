"""Integration tests for the download workflow."""

from __future__ import annotations

import tempfile
import threading
from unittest.mock import Mock

import pytest

from core.download_task import DownloadTask, DownloadUIHooks
from core.queue_manager import QueueManager, QueueState
from plugins.base import PluginManager, PluginType
from utils.http_client import ScraperPool


@pytest.fixture
def temp_download_dir():
    """Create a temporary download directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_ui_hooks():
    """Create mock UI hooks for testing."""
    return DownloadUIHooks(
        on_start=Mock(),
        on_end=Mock(),
        queue_set_status=Mock(),
        queue_mark_finished=Mock(),
        queue_update_title=Mock(),
        queue_reset_progress=Mock(),
        queue_update_progress=Mock(),
        set_status=Mock(),
    )


@pytest.fixture
def plugin_manager():
    """Create a plugin manager for testing."""
    return PluginManager()


@pytest.fixture
def scraper_pool():
    """Create a scraper pool for testing."""
    return ScraperPool(max_size=2)


def test_download_task_initialization(
    temp_download_dir: str,
    mock_ui_hooks: DownloadUIHooks,
    plugin_manager: PluginManager,
    scraper_pool: ScraperPool,
):
    """Test that DownloadTask initializes correctly."""
    task = DownloadTask(
        queue_id=1,
        url="https://example.com/chapter/1",
        initial_label="Chapter 1",
        plugin_manager=plugin_manager,
        scraper_pool=scraper_pool,
        image_semaphore=threading.Semaphore(10),
        image_worker_count=4,
        resolve_download_dir=lambda: temp_download_dir,
        ui_hooks=mock_ui_hooks,
    )

    assert task.queue_id == 1
    assert task.url == "https://example.com/chapter/1"
    assert task.initial_label == "Chapter 1"
    assert task.image_worker_count == 4


def test_download_task_abort_before_start(
    temp_download_dir: str,
    mock_ui_hooks: DownloadUIHooks,
    plugin_manager: PluginManager,
    scraper_pool: ScraperPool,
):
    """Test that download task can be aborted before starting."""
    abort_flag = True

    task = DownloadTask(
        queue_id=1,
        url="https://example.com/chapter/1",
        initial_label="Chapter 1",
        plugin_manager=plugin_manager,
        scraper_pool=scraper_pool,
        image_semaphore=threading.Semaphore(10),
        image_worker_count=4,
        resolve_download_dir=lambda: temp_download_dir,
        ui_hooks=mock_ui_hooks,
        should_abort=lambda: abort_flag,
    )

    # Task should detect abort condition
    assert task._should_abort is not None
    assert task._should_abort() is True


def test_queue_manager_thread_safety():
    """Test that QueueManager operations are thread-safe."""
    manager = QueueManager()

    def add_items():
        for i in range(100):
            manager.add_item(i, f"https://example.com/{i}", f"Item {i}")

    def update_items():
        for i in range(100):
            manager.start_item(i)
            manager.complete_item(i, success=True)

    thread1 = threading.Thread(target=add_items)
    thread2 = threading.Thread(target=update_items)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # Verify final state is consistent
    with manager.transaction():
        stats = manager.get_stats()
        assert stats.total == 100


def test_queue_manager_state_transitions():
    """Test QueueManager state transition logic."""
    manager = QueueManager()

    # Add item
    manager.add_item(1, "https://example.com/1", "Item 1")
    item = manager.get_item(1)
    assert item is not None
    assert item.state == QueueState.PENDING

    # Start item
    manager.start_item(1)
    item = manager.get_item(1)
    assert item.state == QueueState.RUNNING

    # Complete successfully
    manager.complete_item(1, success=True)
    item = manager.get_item(1)
    assert item.state == QueueState.SUCCESS

    # Add another item and fail it
    manager.add_item(2, "https://example.com/2", "Item 2")
    manager.start_item(2)
    manager.complete_item(2, success=False, error="Test error")
    item = manager.get_item(2)
    assert item.state == QueueState.ERROR
    assert item.error_message == "Test error"


def test_queue_manager_cancellation():
    """Test queue item cancellation."""
    manager = QueueManager()

    manager.add_item(1, "https://example.com/1", "Item 1")
    manager.start_item(1)

    # Cancel the item
    manager.cancel_item(1)
    assert manager.is_cancelled(1)

    item = manager.get_item(1)
    assert item.state == QueueState.CANCELLED


def test_queue_manager_pause_resume():
    """Test pause and resume functionality."""
    manager = QueueManager()

    assert not manager.is_paused()

    manager.pause()
    assert manager.is_paused()

    manager.resume()
    assert not manager.is_paused()


def test_integration_queue_and_download(
    temp_download_dir: str,
    mock_ui_hooks: DownloadUIHooks,
    plugin_manager: PluginManager,
    scraper_pool: ScraperPool,
):
    """Integration test combining queue manager and download task."""
    manager = QueueManager()

    # Add item to queue
    manager.add_item(1, "https://example.com/chapter/1", "Chapter 1")
    assert manager.get_stats().total == 1
    assert manager.get_stats().pending == 1

    # Simulate starting download
    manager.start_item(1)
    assert manager.get_stats().active == 1

    # Create download task (won't actually download in test)
    task = DownloadTask(
        queue_id=1,
        url="https://example.com/chapter/1",
        initial_label="Chapter 1",
        plugin_manager=plugin_manager,
        scraper_pool=scraper_pool,
        image_semaphore=threading.Semaphore(10),
        image_worker_count=4,
        resolve_download_dir=lambda: temp_download_dir,
        ui_hooks=mock_ui_hooks,
    )
    assert task.queue_id == 1
    assert task.url == "https://example.com/chapter/1"

    # Simulate completion
    manager.complete_item(1, success=True)
    assert manager.get_stats().completed == 1
    assert manager.get_stats().active == 0


def test_plugin_manager_lifecycle():
    """Test plugin manager initialization and lifecycle."""
    manager = PluginManager()
    manager.load_plugins()

    # Should have discovered plugins
    parser_records = manager.get_records(PluginType.PARSER)
    converter_records = manager.get_records(PluginType.CONVERTER)

    assert len(parser_records) > 0
    assert len(converter_records) > 0

    # Test enabling/disabling
    if parser_records:
        parser_record = parser_records[0]
        parser_name = parser_record.name
        manager.set_enabled(PluginType.PARSER, parser_name, False)
        record = manager.get_record(PluginType.PARSER, parser_name)
        assert record is not None
        assert not record.enabled

        manager.set_enabled(PluginType.PARSER, parser_name, True)
        record = manager.get_record(PluginType.PARSER, parser_name)
        assert record is not None
        assert record.enabled

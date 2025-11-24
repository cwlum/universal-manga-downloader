"""UI component tests for Tkinter application."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import Mock, patch

import pytest

# Mark all tests in this module to require display
pytestmark = pytest.mark.skipif(
    not hasattr(tk, "TclError"),
    reason="Tkinter not available or no display",
)


@pytest.fixture
def mock_services():
    """Mock manga services to avoid network calls."""
    with patch("ui.app.BatoService") as bato_mock, patch("ui.app.MangaDexService") as mangadex_mock:
        bato_instance = Mock()
        mangadex_instance = Mock()

        bato_mock.return_value = bato_instance
        mangadex_mock.return_value = mangadex_instance

        bato_instance.search_manga.return_value = []
        mangadex_instance.search_manga.return_value = []

        yield {"bato": bato_instance, "mangadex": mangadex_instance}


def test_app_initialization_without_display():
    """Test that app components can be imported and validated."""
    from ui.app import MangaDownloader

    # This test validates the import and class structure
    assert hasattr(MangaDownloader, "__init__")
    # Check that the class exists and can be imported successfully


def test_queue_item_dataclass():
    """Test QueueItem dataclass structure."""
    from ui.app import QueueItem

    # Verify dataclass has expected fields
    assert hasattr(QueueItem, "frame")
    assert hasattr(QueueItem, "title_var")
    assert hasattr(QueueItem, "status_var")
    assert hasattr(QueueItem, "progress")


def test_search_result_typeddict():
    """Test SearchResult TypedDict structure."""
    from ui.app import SearchResult

    # Create a sample search result
    result: SearchResult = {
        "title": "Test Manga",
        "url": "https://example.com/manga/1",
        "subtitle": "Test Author",
        "provider": "TestProvider",
    }

    assert result["title"] == "Test Manga"
    assert result["url"] == "https://example.com/manga/1"


def test_status_colors_mapping():
    """Test that status colors are properly defined."""
    from core.queue_manager import QueueState
    from ui.app import STATUS_COLORS

    # Verify all queue states have color mappings
    assert QueueState.SUCCESS in STATUS_COLORS
    assert QueueState.ERROR in STATUS_COLORS
    assert QueueState.RUNNING in STATUS_COLORS
    assert QueueState.PAUSED in STATUS_COLORS
    assert QueueState.CANCELLED in STATUS_COLORS

    # Verify colors are hex strings
    for color in STATUS_COLORS.values():
        assert isinstance(color, str)
        assert color.startswith("#")


def test_logging_utils_configuration():
    """Test logging utilities configuration."""
    from ui.logging_utils import configure_logging

    # Should not raise an exception
    configure_logging()

    # Verify logger is configured
    import logging

    logger = logging.getLogger("ui.app")
    assert logger is not None


class TestMockUIOperations:
    """Test UI operations with mocked Tkinter."""

    @pytest.fixture
    def mock_tk_app(self, mock_services):
        """Create a mocked Tkinter app for testing."""
        with patch("ui.app.tk.Tk") as tk_mock, patch("ui.app.sv_ttk"):
            mock_root = Mock(spec=tk.Tk)
            tk_mock.return_value = mock_root

            # Don't actually import/instantiate the app
            # Just verify the structure
            yield mock_root

    def test_queue_manager_integration(self):
        """Test queue manager operations in UI context."""
        from core.queue_manager import QueueManager

        manager = QueueManager()

        # Simulate UI operations
        manager.add_item(1, "https://example.com/1", "Chapter 1")
        manager.start_item(1)

        item = manager.get_item(1)
        assert item is not None
        assert item.queue_id == 1
        assert item.url == "https://example.com/1"

        # Complete the download
        manager.complete_item(1, success=True)
        stats = manager.get_stats()
        assert stats.completed == 1

    def test_download_task_ui_hooks_structure(self):
        """Test DownloadUIHooks structure."""
        from core.download_task import DownloadUIHooks

        # Create mock hooks
        hooks = DownloadUIHooks(
            on_start=Mock(),
            on_end=Mock(),
            queue_set_status=Mock(),
            queue_mark_finished=Mock(),
            queue_update_title=Mock(),
            queue_reset_progress=Mock(),
            queue_update_progress=Mock(),
            set_status=Mock(),
        )

        # Test hook calls
        hooks.on_start("test", 1)
        hooks.on_start.assert_called_once_with("test", 1)

        hooks.queue_update_progress(1, 50, 100)
        hooks.queue_update_progress.assert_called_once_with(1, 50, 100)


def test_config_values():
    """Test that configuration values are accessible."""
    from config import CONFIG

    # UI config
    assert hasattr(CONFIG, "ui")
    assert CONFIG.ui.default_width > 0
    assert CONFIG.ui.default_height > 0

    # Download config
    assert hasattr(CONFIG, "download")
    assert CONFIG.download.default_chapter_workers > 0
    assert CONFIG.download.default_image_workers > 0

    # Service config
    assert hasattr(CONFIG, "service")
    assert CONFIG.service.rate_limit_delay >= 0


def test_plugin_manager_ui_integration():
    """Test plugin manager operations in UI context."""
    from plugins.base import PluginManager, PluginType

    manager = PluginManager()
    manager.load_plugins()

    # Test getting available plugins
    parser_records = manager.get_records(PluginType.PARSER)
    converter_records = manager.get_records(PluginType.CONVERTER)

    assert isinstance(parser_records, list)
    assert isinstance(converter_records, list)

    # Should have at least the default plugins
    assert len(parser_records) >= 2  # Bato and MangaDex
    assert len(converter_records) >= 2  # PDF and CBZ

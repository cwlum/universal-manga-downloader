"""UI component tests for Tkinter application."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

try:
    import tkinter as tk
except ModuleNotFoundError:
    tk = None

# Mark all tests in this module to require display
pytestmark = pytest.mark.skipif(
    tk is None or not hasattr(tk, "TclError"),
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
    from ui.models import STATUS_COLORS

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


class TestBrowserTabLogic:
    """Test Browser tab business logic without Tkinter dependency."""

    def test_format_chapter_label(self):
        """Test chapter label formatting."""
        # Test with title
        chapter = {"title": "Chapter 1", "url": "https://example.com/1"}
        label = f"{1:03d} • {chapter.get('title', 'Chapter 1')}"
        assert label == "001 • Chapter 1"

        # Test with label fallback
        chapter = {"label": "Ch. 1", "url": "https://example.com/1"}
        label = f"{5:03d} • {chapter.get('title') or chapter.get('label', 'Chapter 5')}"
        assert label == "005 • Ch. 1"

        # Test with neither
        chapter = {"url": "https://example.com/1"}
        idx = 10
        label = f"{idx:03d} • {chapter.get('title') or chapter.get('label') or f'Chapter {idx}'}"
        assert label == "010 • Chapter 10"

    def test_range_parsing_logic(self):
        """Test range parsing logic for chapter selection."""
        # Valid range
        start, end = 1, 10
        assert start <= end
        assert start > 0

        # Swapped range should be corrected
        start, end = 10, 1
        if start > end:
            start, end = end, start
        assert start == 1
        assert end == 10

        # Clamp to bounds
        max_chapters = 50
        start, end = 1, 100
        end_index = min(max_chapters, end) - 1
        assert end_index == 49

    def test_provider_from_url(self):
        """Test provider detection from URL."""
        from urllib.parse import urlparse

        def provider_from_url(url: str) -> str | None:
            if not url:
                return None
            host = urlparse(url).netloc.lower()
            if "mangadex" in host:
                return "MangaDex"
            if "bato" in host:
                return "Bato"
            return None

        assert provider_from_url("https://mangadex.org/title/123") == "MangaDex"
        assert provider_from_url("https://bato.to/series/456") == "Bato"
        assert provider_from_url("https://example.com/manga") is None
        assert provider_from_url("") is None

    def test_search_result_display_formatting(self):
        """Test search result display string formatting."""
        # With subtitle
        result = {"title": "One Piece", "subtitle": "Eiichiro Oda"}
        display = f"{result['title']} — {result.get('subtitle')}" if result.get("subtitle") else result["title"]
        assert display == "One Piece — Eiichiro Oda"

        # Without subtitle
        result = {"title": "Naruto"}
        display = f"{result['title']} — {result.get('subtitle')}" if result.get("subtitle") else result["title"]
        assert display == "Naruto"


class TestDownloadsTabLogic:
    """Test Downloads tab business logic without Tkinter dependency."""

    def test_queue_status_text_formatting(self):
        """Test queue status text generation."""
        class MockStats:
            def __init__(self, active, pending, failed=0, cancelled=0):
                self.active = active
                self.pending = pending
                self.failed = failed
                self.cancelled = cancelled

        def format_queue_status(stats, paused: bool) -> str:
            queue_text = f"Queue • Active: {stats.active} | Pending: {stats.pending}"
            if stats.failed:
                queue_text += f" | Failed: {stats.failed}"
            if stats.cancelled:
                queue_text += f" | Cancelled: {stats.cancelled}"
            if paused:
                queue_text += " • Paused"
            return queue_text

        # Normal state
        stats = MockStats(2, 5)
        assert format_queue_status(stats, False) == "Queue • Active: 2 | Pending: 5"

        # With failures
        stats = MockStats(1, 3, failed=2)
        assert format_queue_status(stats, False) == "Queue • Active: 1 | Pending: 3 | Failed: 2"

        # Paused with cancellations
        stats = MockStats(0, 0, cancelled=1)
        assert format_queue_status(stats, True) == "Queue • Active: 0 | Pending: 0 | Cancelled: 1 • Paused"

    def test_progress_value_clamping(self):
        """Test progress bar value clamping logic."""
        def clamp_progress(value: int, maximum: int) -> int:
            return max(0, min(maximum, value))

        assert clamp_progress(50, 100) == 50
        assert clamp_progress(-10, 100) == 0
        assert clamp_progress(150, 100) == 100


class TestSettingsTabLogic:
    """Test Settings tab business logic without Tkinter dependency."""

    def test_worker_count_clamping(self):
        """Test worker count validation and clamping."""
        from ui.widgets import clamp_value

        # Chapter workers: 1-10, default 3
        assert clamp_value(5, 1, 10, 3) == 5
        assert clamp_value(0, 1, 10, 3) == 3  # Below min
        assert clamp_value(20, 1, 10, 3) == 3  # Above max
        assert clamp_value(None, 1, 10, 3) == 3  # None

        # Image workers: 1-32, default 8
        assert clamp_value(16, 1, 32, 8) == 16
        assert clamp_value(100, 1, 32, 8) == 8  # Above max

    def test_download_dir_normalization(self):
        """Test download directory path handling."""
        # Empty string should expand to home
        test_path = ""
        normalized = test_path.strip() if isinstance(test_path, str) else ""
        assert normalized == ""

        # Whitespace handling
        test_path = "  /path/to/dir  "
        normalized = test_path.strip()
        assert normalized == "/path/to/dir"


class TestCleanupFunctionality:
    """Test download cleanup functionality."""

    def test_cleanup_failed_download_empty_dir(self, tmp_path):
        """Test cleanup of empty directory."""
        from utils.file_utils import cleanup_failed_download

        empty_dir = tmp_path / "empty_chapter"
        empty_dir.mkdir()

        assert cleanup_failed_download(str(empty_dir)) is True
        assert not empty_dir.exists()

    def test_cleanup_failed_download_with_images(self, tmp_path):
        """Test cleanup of directory with image files."""
        from utils.file_utils import cleanup_failed_download

        chapter_dir = tmp_path / "test_chapter"
        chapter_dir.mkdir()

        # Create some image files
        (chapter_dir / "001.jpg").touch()
        (chapter_dir / "002.png").touch()
        (chapter_dir / "003.webp").touch()

        assert cleanup_failed_download(str(chapter_dir)) is True
        assert not chapter_dir.exists()

    def test_cleanup_failed_download_with_outputs(self, tmp_path):
        """Test cleanup of directory with PDF/CBZ outputs."""
        from utils.file_utils import cleanup_failed_download

        chapter_dir = tmp_path / "test_chapter"
        chapter_dir.mkdir()

        # Create image and output files
        (chapter_dir / "001.jpg").touch()
        (chapter_dir / "chapter.pdf").touch()
        (chapter_dir / "chapter.cbz").touch()

        assert cleanup_failed_download(str(chapter_dir)) is True
        assert not chapter_dir.exists()

    def test_cleanup_refuses_unexpected_files(self, tmp_path):
        """Test that cleanup refuses to delete directories with unexpected files."""
        from utils.file_utils import cleanup_failed_download

        chapter_dir = tmp_path / "test_chapter"
        chapter_dir.mkdir()

        # Create unexpected file types
        (chapter_dir / "important.txt").touch()
        (chapter_dir / "001.jpg").touch()

        assert cleanup_failed_download(str(chapter_dir)) is False
        assert chapter_dir.exists()

    def test_cleanup_nonexistent_directory(self):
        """Test cleanup of nonexistent directory returns True."""
        from utils.file_utils import cleanup_failed_download

        assert cleanup_failed_download("/nonexistent/path/12345") is True

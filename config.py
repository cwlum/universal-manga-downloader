"""Application configuration and constants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UIConfig:
    """Configuration for UI dimensions and timing."""

    # Window dimensions
    default_width: int = 1100
    default_height: int = 850
    min_width: int = 1000
    min_height: int = 800

    # UI timing (milliseconds)
    scroll_delay_ms: int = 50
    queue_scroll_delay_ms: int = 50


@dataclass(frozen=True)
class DownloadConfig:
    """Configuration for download behavior."""

    # Worker limits
    default_chapter_workers: int = 1
    max_chapter_workers: int = 10
    min_chapter_workers: int = 1

    default_image_workers: int = 4
    max_image_workers: int = 32
    min_image_workers: int = 1

    # Network timeouts (seconds)
    request_timeout: int = 30
    search_timeout: int = 15
    series_info_timeout: int = 20

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass(frozen=True)
class ServiceConfig:
    """Configuration for external services."""

    # Bato.to service
    bato_base_url: str = "https://bato.to"
    bato_search_path: str = "/search"
    bato_max_search_pages: int = 3


@dataclass(frozen=True)
class PDFConfig:
    """Configuration for PDF generation."""

    # PDF resolution
    resolution: float = 100.0

    # Supported image formats
    supported_formats: tuple[str, ...] = ("png", "jpg", "jpeg", "gif", "bmp", "webp")


@dataclass(frozen=True)
class AppConfig:
    """Main application configuration."""

    ui: UIConfig = UIConfig()
    download: DownloadConfig = DownloadConfig()
    service: ServiceConfig = ServiceConfig()
    pdf: PDFConfig = PDFConfig()


# Global configuration instance
CONFIG = AppConfig()


# Status color mapping
STATUS_COLORS: dict[str, str] = {
    "success": "#1a7f37",
    "error": "#b91c1c",
    "running": "#1d4ed8",
    "paused": "#d97706",
    "cancelled": "#6b7280",
}

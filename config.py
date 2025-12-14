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
    progress_update_interval_ms: int = 125


@dataclass(frozen=True)
class DownloadConfig:
    """Configuration for download behavior."""

    # Worker limits
    default_chapter_workers: int = 2
    max_chapter_workers: int = 10
    min_chapter_workers: int = 1

    default_image_workers: int = 8
    max_image_workers: int = 32
    min_image_workers: int = 1
    max_total_image_workers: int = 48

    # Network timeouts (seconds)
    # Using tuple-style timeouts: (connect_timeout, read_timeout)
    connect_timeout: float = 5.0   # Time to establish connection (fast fail)
    read_timeout: float = 20.0     # Time to receive data
    request_timeout: int = 30      # Legacy: total timeout for simple requests
    search_timeout: int = 15
    series_info_timeout: int = 20

    # Retry configuration
    max_retries: int = 1           # Reduced for faster fallback (will try fallback quickly)
    retry_delay: float = 0.3       # Faster retry
    fallback_max_retries: int = 2  # More retries on fallback (it's more likely to work)

    # Networking helpers
    scraper_pool_size: int = 12    # Increased from 8 for better concurrency
    scraper_wait_timeout: float = 10.0  # Max time to wait for available scraper


@dataclass(frozen=True)
class ServiceConfig:
    """Configuration for external services."""

    # Bato.to service
    bato_base_url: str = "https://bato.to"
    bato_search_path: str = "/search"
    bato_max_search_pages: int = 3

    # MangaDex service
    mangadex_api_base: str = "https://api.mangadex.org"
    mangadex_site_base: str = "https://mangadex.org"
    mangadex_search_limit: int = 20
    mangadex_max_chapter_pages: int = 5
    mangadex_languages: tuple[str, ...] = ("en",)

    # Rate limiting (seconds between requests)
    rate_limit_delay: float = 0.5  # 500ms between requests to same service


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

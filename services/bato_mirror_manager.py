"""Bato mirror site management with user-configurable fallback support."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict
from urllib.parse import parse_qs, urlparse

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default config file location (in user's data directory)
_DEFAULT_CONFIG_DIR = Path.home() / ".config" / "universal-manga-downloader"
_MIRRORS_CONFIG_FILE = "bato_mirrors.json"


class MirrorConfig(TypedDict):
    """Configuration for a single mirror site."""

    base_url: str
    search_path: str
    search_params: dict[str, str]  # Extra params like {"type": "comic"}


# Default mirror configurations
DEFAULT_MIRRORS: list[MirrorConfig] = [
    {
        "base_url": "https://bato.to",
        "search_path": "/v4x-search",
        "search_params": {"type": "comic"},
    },
    {
        "base_url": "https://bato.si",
        "search_path": "/v4x-search",
        "search_params": {"type": "comic"},
    },
    {
        "base_url": "https://bato.ing",
        "search_path": "/v4x-search",
        "search_params": {"type": "comic"},
    },
]


def parse_search_url(url: str) -> MirrorConfig | None:
    """Parse a search URL and extract mirror configuration.

    Users can paste URLs like:
    - https://bato.ing/v4x-search?type=comic&word=test
    - https://bato.to/search?word=test

    This function extracts:
    - base_url: The scheme + netloc (e.g., https://bato.ing)
    - search_path: The path (e.g., /v4x-search)
    - search_params: Extra params excluding 'word' and 'page' (e.g., {"type": "comic"})

    Args:
        url: A search URL from the user's browser

    Returns:
        MirrorConfig if parsing succeeded, None otherwise
    """
    url = url.strip()
    if not url:
        return None

    # Add https if missing
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None

        base_url = f"{parsed.scheme}://{parsed.netloc}"
        search_path = parsed.path or "/"

        # Parse query parameters, excluding user-specific ones
        query_params = parse_qs(parsed.query)
        search_params: dict[str, str] = {}

        # Keep only non-user-specific params (exclude word, page, etc.)
        excluded_params = {"word", "page", "q", "query", "search", "keyword"}
        for key, values in query_params.items():
            if key.lower() not in excluded_params and values:
                search_params[key] = values[0]

        return MirrorConfig(
            base_url=base_url,
            search_path=search_path,
            search_params=search_params,
        )
    except Exception as exc:
        logger.debug("Failed to parse URL %s: %s", url, exc)
        return None


class BatoMirrorManager:
    """Manage Bato mirror sites with persistence and automatic fallback.

    This manager handles:
    - Loading/saving user-configured mirror sites with their search paths
    - Automatic fallback when a mirror fails
    - URL parsing for easy configuration
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the mirror manager.

        Args:
            config_dir: Directory for storing mirror configuration.
                        Defaults to ~/.config/universal-manga-downloader/
        """
        self._config_dir = config_dir or _DEFAULT_CONFIG_DIR
        self._config_file = self._config_dir / _MIRRORS_CONFIG_FILE
        self._mirrors: list[MirrorConfig] = []
        self._current_index: int = 0
        self._load_config()

    def _load_config(self) -> None:
        """Load mirror configuration from disk."""
        if not self._config_file.exists():
            self._mirrors = list(DEFAULT_MIRRORS)
            return

        try:
            data = json.loads(self._config_file.read_text(encoding="utf-8"))
            mirrors = data.get("mirrors", [])

            if isinstance(mirrors, list) and mirrors:
                loaded_mirrors: list[MirrorConfig] = []
                for m in mirrors:
                    if isinstance(m, dict) and "base_url" in m:
                        loaded_mirrors.append(
                            MirrorConfig(
                                base_url=str(m.get("base_url", "")).rstrip("/"),
                                search_path=str(m.get("search_path", "/v4x-search")),
                                search_params=dict(m.get("search_params", {})),
                            )
                        )
                    elif isinstance(m, str):
                        # Legacy format: just a URL string
                        loaded_mirrors.append(
                            MirrorConfig(
                                base_url=m.rstrip("/"),
                                search_path="/v4x-search",
                                search_params={"type": "comic"},
                            )
                        )
                self._mirrors = loaded_mirrors if loaded_mirrors else list(DEFAULT_MIRRORS)
            else:
                self._mirrors = list(DEFAULT_MIRRORS)

            self._current_index = min(
                data.get("current_index", 0),
                len(self._mirrors) - 1 if self._mirrors else 0,
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load mirror config: %s", exc)
            self._mirrors = list(DEFAULT_MIRRORS)
            self._current_index = 0

    def _save_config(self) -> None:
        """Save mirror configuration to disk."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "mirrors": self._mirrors,
            "current_index": self._current_index,
        }
        try:
            self._config_file.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Failed to save mirror config: %s", exc)

    @property
    def current_mirror(self) -> MirrorConfig:
        """Get the currently active mirror configuration."""
        if not self._mirrors:
            return DEFAULT_MIRRORS[0]
        return self._mirrors[self._current_index]

    @property
    def current_base_url(self) -> str:
        """Get the base URL of the currently active mirror."""
        return self.current_mirror["base_url"]

    @property
    def mirrors(self) -> list[MirrorConfig]:
        """Get all configured mirrors."""
        return list(self._mirrors)

    def get_search_url(self, word: str, page: int = 1) -> str:
        """Build a search URL using the current mirror's configuration.

        Args:
            word: The search query
            page: Page number (default 1)

        Returns:
            Complete search URL
        """
        mirror = self.current_mirror
        base = mirror["base_url"]
        path = mirror["search_path"]

        # Build query params
        params = dict(mirror["search_params"])
        params["word"] = word
        params["page"] = str(page)

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base}{path}?{query}"

    def get_search_config(self) -> tuple[str, str, dict[str, str]]:
        """Get search configuration for the current mirror.

        Returns:
            Tuple of (base_url, search_path, extra_params)
        """
        mirror = self.current_mirror
        return mirror["base_url"], mirror["search_path"], dict(mirror["search_params"])

    def add_mirror_from_url(self, url: str) -> tuple[bool, str]:
        """Add a new mirror by parsing a search URL.

        Users can paste URLs like:
        - https://bato.ing/v4x-search?type=comic&word=test
        - https://bato.to/search?word=test

        Args:
            url: A search URL from the user's browser

        Returns:
            Tuple of (success, message)
        """
        config = parse_search_url(url)
        if config is None:
            return False, "Invalid URL format. Please paste a search URL from your browser."

        # Check if this mirror already exists
        for existing in self._mirrors:
            if existing["base_url"] == config["base_url"]:
                # Update existing mirror's search config
                existing["search_path"] = config["search_path"]
                existing["search_params"] = config["search_params"]
                self._save_config()
                return True, f"Updated {config['base_url']} search path to {config['search_path']}"

        # Add new mirror
        self._mirrors.append(config)
        self._save_config()
        logger.info("Added mirror from URL: %s", config["base_url"])
        return True, f"Added mirror: {config['base_url']} (path: {config['search_path']})"

    def remove_mirror(self, index: int) -> tuple[bool, str]:
        """Remove a mirror by index.

        Args:
            index: Index of the mirror to remove

        Returns:
            Tuple of (success, message)
        """
        if not (0 <= index < len(self._mirrors)):
            return False, "Invalid mirror index"
        if len(self._mirrors) <= 1:
            return False, "Cannot remove the last mirror"

        removed = self._mirrors.pop(index)

        # Adjust current index if needed
        if self._current_index >= len(self._mirrors):
            self._current_index = len(self._mirrors) - 1
        elif index < self._current_index:
            self._current_index -= 1

        self._save_config()
        logger.info("Removed mirror: %s", removed["base_url"])
        return True, f"Removed mirror: {removed['base_url']}"

    def move_mirror(self, from_index: int, to_index: int) -> bool:
        """Move a mirror from one position to another.

        Args:
            from_index: Current position of the mirror
            to_index: Target position

        Returns:
            True if successful, False otherwise
        """
        if not (0 <= from_index < len(self._mirrors)):
            return False
        if not (0 <= to_index < len(self._mirrors)):
            return False
        if from_index == to_index:
            return True

        mirror = self._mirrors.pop(from_index)
        self._mirrors.insert(to_index, mirror)
        self._save_config()
        return True

    def next_mirror(self) -> MirrorConfig | None:
        """Switch to the next available mirror (for fallback).

        Returns:
            The next mirror config, or None if no more mirrors available
        """
        if len(self._mirrors) <= 1:
            return None
        next_index = (self._current_index + 1) % len(self._mirrors)
        if next_index == 0:
            # We've cycled through all mirrors
            return None
        self._current_index = next_index
        self._save_config()
        logger.info("Switched to mirror: %s", self._mirrors[self._current_index]["base_url"])
        return self._mirrors[self._current_index]

    def reset_to_primary(self) -> None:
        """Reset to the first (primary) mirror."""
        if self._current_index != 0:
            self._current_index = 0
            self._save_config()

    def reset_to_defaults(self) -> None:
        """Reset mirrors to default configuration."""
        self._mirrors = list(DEFAULT_MIRRORS)
        self._current_index = 0
        self._save_config()

    def format_mirror_display(self, index: int) -> str:
        """Format a mirror for display in the UI.

        Args:
            index: Index of the mirror

        Returns:
            Formatted string for display
        """
        if not (0 <= index < len(self._mirrors)):
            return ""
        mirror = self._mirrors[index]
        prefix = "* " if index == self._current_index else "  "
        return f"{prefix}{mirror['base_url']} [{mirror['search_path']}]"


# Singleton instance for app-wide use
_instance: BatoMirrorManager | None = None


def get_mirror_manager() -> BatoMirrorManager:
    """Get the singleton mirror manager instance."""
    global _instance
    if _instance is None:
        _instance = BatoMirrorManager()
    return _instance


def reset_mirror_manager() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _instance
    _instance = None


__all__ = ["BatoMirrorManager", "MirrorConfig", "get_mirror_manager", "parse_search_url", "reset_mirror_manager"]

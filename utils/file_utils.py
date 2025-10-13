"""File system utilities for manga downloading."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]


def get_default_download_root() -> str:
    """Return the default download directory for the current system."""
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(downloads):
        return downloads
    return os.path.expanduser("~")


def sanitize_filename(name: str) -> str:
    """Return a filesystem-friendly representation of a filename."""
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    sanitized = re.sub(r"_{3,}", "__", sanitized)
    return sanitized.strip("_")


def determine_file_extension(img_url: str, response: requests.Response) -> str:
    """Determine the appropriate file extension from URL or content type."""
    parsed_url = urlparse(img_url)
    _, file_ext = os.path.splitext(os.path.basename(parsed_url.path))
    if not file_ext:
        content_type = response.headers.get("content-type")
        ext_match = re.search(r"image/(\w+)", content_type) if content_type else None
        file_ext = f".{ext_match.group(1)}" if ext_match else ".jpg"
    return file_ext


def collect_image_files(download_dir: str) -> list[Path]:
    """Collect all supported image files from a directory."""
    supported = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    directory = Path(download_dir)
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in supported
    )


def ensure_directory(directory: str) -> str | None:
    """
    Ensure a directory exists, creating it if necessary.

    Returns:
        The absolute path if successful, None if an error occurred.
    """
    abs_dir = os.path.abspath(os.path.expanduser(directory))
    try:
        os.makedirs(abs_dir, exist_ok=True)
        return abs_dir
    except OSError:
        return None

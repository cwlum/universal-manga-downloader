"""File system utilities for manga downloading."""

from __future__ import annotations

import os
import re
import shutil
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
    """
    Return a filesystem-friendly representation of a filename.

    This implementation:
    - Replaces colons with " - " for readability
    - Removes only truly invalid filesystem characters: \\ / * ? " < > |
    - Handles Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    - Preserves spaces and readable characters
    - Collapses multiple spaces and dashes
    """
    candidate = name.replace(":", " - ")
    candidate = candidate.replace("\n", " ").replace("\r", " ")
    candidate = re.sub(r"[\\/*?\"<>|]", " ", candidate)
    candidate = candidate.replace("_", " ")
    candidate = re.sub(r"\s+", " ", candidate)
    candidate = re.sub(r"-{2,}", "-", candidate)
    sanitized = candidate.strip(" .")
    if not sanitized:
        return "item"

    # Windows reserved filenames must not be used without a suffix.
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    from pathlib import PurePath
    upper_name = PurePath(sanitized).name.upper()
    if upper_name in reserved:
        sanitized = f"{sanitized} -"

    return sanitized


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


def get_free_disk_space(path: str) -> int:
    """
    Get available disk space in bytes for the given path.

    Args:
        path: Directory path to check (or any path on the target filesystem)

    Returns:
        Free space in bytes, or -1 if unable to determine
    """
    try:
        # Ensure path exists or use parent directory
        check_path = path
        if not os.path.exists(check_path):
            check_path = os.path.dirname(check_path) or "/"

        # Get disk usage statistics
        stat = shutil.disk_usage(check_path)
        return stat.free
    except (OSError, AttributeError):
        return -1


def estimate_chapter_size(num_images: int, avg_image_size_mb: float = 4.0) -> int:
    """
    Estimate download size in bytes for a chapter.

    Args:
        num_images: Number of images in the chapter
        avg_image_size_mb: Average size per image in MB (default 4MB)

    Returns:
        Estimated size in bytes
    """
    if num_images <= 0:
        return 0
    # Add 20% buffer for conversions (PDF, CBZ)
    estimated_bytes = int(num_images * avg_image_size_mb * 1024 * 1024 * 1.2)
    return estimated_bytes


def check_disk_space_sufficient(
    directory: str,
    required_bytes: int,
    safety_margin_mb: int = 100,
) -> tuple[bool, int, int]:
    """
    Check if there's sufficient disk space for download.

    Args:
        directory: Target download directory
        required_bytes: Required space in bytes
        safety_margin_mb: Safety margin in MB (default 100MB)

    Returns:
        Tuple of (is_sufficient, free_bytes, required_with_margin_bytes)
    """
    free_bytes = get_free_disk_space(directory)

    # If we can't determine free space, assume it's sufficient
    if free_bytes < 0:
        return (True, -1, required_bytes)

    # Add safety margin
    safety_bytes = safety_margin_mb * 1024 * 1024
    required_with_margin = required_bytes + safety_bytes

    is_sufficient = free_bytes >= required_with_margin

    return (is_sufficient, free_bytes, required_with_margin)


def cleanup_failed_download(directory: str) -> bool:
    """
    Remove a failed download directory and its contents.

    Args:
        directory: Path to the download directory to remove

    Returns:
        True if cleanup was successful, False otherwise
    """
    if not directory or not os.path.exists(directory):
        return True

    try:
        # Safety check: only remove if it looks like a chapter download directory
        # (contains image files or is empty)
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return False

        # Check contents - only proceed if it contains images or is empty
        contents = list(dir_path.iterdir())
        if contents:
            image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
            has_only_images_or_outputs = all(
                f.suffix.lower() in image_extensions
                or f.suffix.lower() in {".pdf", ".cbz"}
                or f.name.startswith(".")  # Hidden files
                for f in contents
                if f.is_file()
            )
            if not has_only_images_or_outputs:
                # Directory contains unexpected files, don't remove
                return False

        shutil.rmtree(directory)
        return True
    except OSError:
        return False


def is_directory_empty_or_partial(directory: str) -> bool:
    """
    Check if a directory is empty or contains only partial download files.

    Args:
        directory: Path to check

    Returns:
        True if directory is empty or contains only partial/temporary files
    """
    if not directory or not os.path.exists(directory):
        return True

    try:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return False

        contents = list(dir_path.iterdir())
        return len(contents) == 0
    except OSError:
        return False

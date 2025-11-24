"""Input validation and sanitization utilities."""

from __future__ import annotations

import re
from typing import Pattern
from urllib.parse import urlparse

# Comprehensive URL validation pattern
_URL_PATTERN: Pattern[str] = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

# Patterns for supported manga sites
_BATO_PATTERN: Pattern[str] = re.compile(
    r"^https?://(?:www\.)?(?:bato\.to|batotoo?\.(?:com|to))/", re.IGNORECASE
)

_MANGADEX_PATTERN: Pattern[str] = re.compile(
    r"^https?://(?:www\.)?mangadex\.org/", re.IGNORECASE
)

# Dangerous file path characters
_DANGEROUS_PATH_CHARS: Pattern[str] = re.compile(r'[<>:"|?*\x00-\x1f]')

# Path traversal attempts
_PATH_TRAVERSAL_PATTERN: Pattern[str] = re.compile(r"\.\.|/\.|\\\.|\./|\.\\")


class ValidationError(ValueError):
    """Raised when input validation fails."""


def validate_url(url: str, *, allow_empty: bool = False) -> str:
    """
    Validate and normalize a URL.

    Args:
        url: URL to validate
        allow_empty: If True, empty strings are allowed and returned as-is

    Returns:
        Normalized URL

    Raises:
        ValidationError: If URL is invalid
    """
    if not url or not url.strip():
        if allow_empty:
            return ""
        raise ValidationError("URL cannot be empty")

    normalized = url.strip()

    # Parse and validate components first
    try:
        parsed = urlparse(normalized)
    except Exception as e:
        raise ValidationError(f"Failed to parse URL: {e}") from e

    if not parsed.scheme in ("http", "https"):
        raise ValidationError(f"URL must use http or https scheme, got: {parsed.scheme}")

    if not parsed.netloc:
        raise ValidationError("URL must have a valid domain")

    # Check basic URL format
    if not _URL_PATTERN.match(normalized):
        raise ValidationError(f"Invalid URL format: {url}")

    return normalized


def validate_manga_url(url: str, *, require_supported: bool = True) -> str:
    """
    Validate a manga site URL.

    Args:
        url: URL to validate
        require_supported: If True, URL must be from a supported site

    Returns:
        Normalized URL

    Raises:
        ValidationError: If URL is invalid or unsupported
    """
    normalized = validate_url(url)

    if require_supported:
        is_bato = _BATO_PATTERN.match(normalized)
        is_mangadex = _MANGADEX_PATTERN.match(normalized)

        if not (is_bato or is_mangadex):
            raise ValidationError(
                f"URL must be from a supported manga site (Bato.to or MangaDex): {url}"
            )

    return normalized


def sanitize_filename(name: str, *, max_length: int = 255, replacement: str = "_") -> str:
    """
    Sanitize a string for safe use as a filename.

    Args:
        name: String to sanitize
        max_length: Maximum length for the result
        replacement: Character to replace invalid characters with

    Returns:
        Sanitized filename

    Raises:
        ValidationError: If name is empty after sanitization
    """
    if not name or not name.strip():
        raise ValidationError("Filename cannot be empty")

    # Remove dangerous characters
    sanitized = _DANGEROUS_PATH_CHARS.sub(replacement, name.strip())

    # Remove path traversal attempts
    sanitized = _PATH_TRAVERSAL_PATTERN.sub(replacement, sanitized)

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")

    # Ensure it's not a reserved name on Windows
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
    name_upper = sanitized.split(".")[0].upper()
    if name_upper in reserved_names:
        sanitized = f"{replacement}{sanitized}"

    # Truncate to max length
    if len(sanitized) > max_length:
        # Try to preserve extension if present
        parts = sanitized.rsplit(".", 1)
        if len(parts) == 2 and len(parts[1]) <= 10:  # Reasonable extension length
            ext = parts[1]
            base_max = max_length - len(ext) - 1
            sanitized = f"{parts[0][:base_max]}.{ext}"
        else:
            sanitized = sanitized[:max_length]

    if not sanitized:
        raise ValidationError(f"Filename is empty after sanitization: {name}")

    return sanitized


def validate_directory_path(path: str) -> str:
    """
    Validate a directory path for safety.

    Args:
        path: Path to validate

    Returns:
        Normalized path

    Raises:
        ValidationError: If path is invalid or unsafe
    """
    if not path or not path.strip():
        raise ValidationError("Directory path cannot be empty")

    normalized = path.strip()

    # Check for path traversal attempts
    if _PATH_TRAVERSAL_PATTERN.search(normalized):
        raise ValidationError(f"Path contains invalid traversal sequences: {path}")

    # Don't allow paths starting with ~ that aren't expanded
    if normalized.startswith("~") and "~" in normalized[1:]:
        raise ValidationError(f"Invalid path with tilde: {path}")

    return normalized


def sanitize_query_string(query: str, *, max_length: int = 500) -> str:
    """
    Sanitize a search query string.

    Args:
        query: Query to sanitize
        max_length: Maximum length

    Returns:
        Sanitized query

    Raises:
        ValidationError: If query is empty after sanitization
    """
    if not query or not query.strip():
        raise ValidationError("Query cannot be empty")

    # Remove control characters and excessive whitespace
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", query.strip())
    sanitized = re.sub(r"\s+", " ", sanitized)

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()

    if not sanitized:
        raise ValidationError(f"Query is empty after sanitization: {query}")

    return sanitized

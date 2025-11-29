"""Utilities for parsing remote plugin metadata blocks."""

from __future__ import annotations

import hashlib
import re
from typing import TypedDict

DOCSTRING_PATTERN = re.compile(r'^"""(.*?)"""', re.DOTALL | re.MULTILINE)
NAME_PATTERN = re.compile(r"Name:\s*(.+)", re.IGNORECASE)
AUTHOR_PATTERN = re.compile(r"Author:\s*(.+)", re.IGNORECASE)
VERSION_PATTERN = re.compile(r"Version:\s*(.+)", re.IGNORECASE)
DESCRIPTION_PATTERN = re.compile(r"Description:\s*(.+)", re.IGNORECASE)
REPOSITORY_PATTERN = re.compile(r"Repository:\s*(.+)", re.IGNORECASE)
LICENSE_PATTERN = re.compile(r"License:\s*(.+)", re.IGNORECASE)
DEPENDENCIES_PATTERN = re.compile(r"Dependencies:\s*(.+?)(?:\n\s*\n|\Z)", re.DOTALL | re.IGNORECASE)


class PluginMetadata(TypedDict, total=False):
    """Strongly typed representation of parsed metadata."""

    name: str
    author: str
    version: str
    description: str
    repository: str
    license: str
    dependencies: list[str]


def parse_plugin_metadata(code: str) -> PluginMetadata:
    """Extract metadata from the module-level docstring."""

    metadata: PluginMetadata = {"dependencies": []}
    doc_match = DOCSTRING_PATTERN.search(code)
    if not doc_match:
        return metadata
    block = doc_match.group(1)

    name_match = NAME_PATTERN.search(block)
    if name_match:
        metadata["name"] = name_match.group(1).strip()

    author_match = AUTHOR_PATTERN.search(block)
    if author_match:
        metadata["author"] = author_match.group(1).strip()

    version_match = VERSION_PATTERN.search(block)
    if version_match:
        metadata["version"] = version_match.group(1).strip()

    description_match = DESCRIPTION_PATTERN.search(block)
    if description_match:
        metadata["description"] = description_match.group(1).strip()

    repo_match = REPOSITORY_PATTERN.search(block)
    if repo_match:
        metadata["repository"] = repo_match.group(1).strip()

    license_match = LICENSE_PATTERN.search(block)
    if license_match:
        metadata["license"] = license_match.group(1).strip()

    deps_match = DEPENDENCIES_PATTERN.search(block)
    if deps_match:
        deps_str = deps_match.group(1)
        deps = [item.strip() for item in re.split(r"[,\n]", deps_str) if item.strip()]
        metadata["dependencies"] = deps
    elif "dependencies" not in metadata:
        metadata["dependencies"] = []
    return metadata


def calculate_checksum(code: str) -> str:
    """Return the SHA-256 checksum of the plugin code."""

    return hashlib.sha256(code.encode("utf-8")).hexdigest()


__all__ = ["PluginMetadata", "parse_plugin_metadata", "calculate_checksum"]

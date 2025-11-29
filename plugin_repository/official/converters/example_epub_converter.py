"""
Universal Manga Downloader Plugin

Name: Example EPUB Converter
Author: UMD Community
Version: 0.1.0
Description: Demonstrates converter metadata for remote repository entries.
Repository: https://github.com/umd-plugins/official
License: MIT
Dependencies: ebooklib>=0.18
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from plugins.base import BaseConverter, ChapterMetadata


class ExampleEpubConverter(BaseConverter):
    """Example converter that would emit EPUB files."""

    def get_name(self) -> str:
        return "Example EPUB Converter"

    def get_output_extension(self) -> str:
        return ".epub"

    def convert(
        self,
        image_files: Sequence[Path],
        output_dir: Path,
        metadata: ChapterMetadata,
    ) -> Path | None:
        # Placeholder implementation: just write a manifest text file.
        output_dir.mkdir(parents=True, exist_ok=True)
        artifact = output_dir / f"{metadata['title']}.txt"
        artifact.write_text(
            "\n".join(str(path) for path in image_files),
            encoding="utf-8",
        )
        return artifact

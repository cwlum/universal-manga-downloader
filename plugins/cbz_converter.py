"""CBZ converter plugin."""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Sequence
from pathlib import Path

from .base import BaseConverter, ChapterMetadata, compose_chapter_name

logger = logging.getLogger(__name__)


class CBZConverter(BaseConverter):
    """Package downloaded images into a CBZ archive."""

    def get_name(self) -> str:
        return "CBZ"

    def get_output_extension(self) -> str:
        return ".cbz"

    def convert(
        self,
        image_files: Sequence[Path],
        output_dir: Path,
        metadata: ChapterMetadata,
    ) -> Path | None:
        if not image_files:
            logger.warning("CBZ converter received no images for %s", metadata.get("title", "chapter"))
            return None

        base_name = compose_chapter_name(metadata.get("title"), metadata.get("chapter"))
        archive_path = output_dir / f"{base_name}{self.get_output_extension()}"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, file_path in enumerate(image_files, start=1):
                arcname = f"{index:03d}{file_path.suffix.lower()}"
                archive.write(file_path, arcname)
        logger.info("Created CBZ %s", archive_path)
        return archive_path

    def on_load(self) -> None:
        logger.debug("CBZ converter ready")

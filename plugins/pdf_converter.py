"""PDF converter plugin."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from PIL import Image

from .base import BaseConverter, ChapterMetadata, compose_chapter_name

logger = logging.getLogger(__name__)


class PDFConverter(BaseConverter):
    """Persist downloaded images into a single PDF document."""

    def get_name(self) -> str:
        return "PDF"

    def get_output_extension(self) -> str:
        return ".pdf"

    def convert(
        self,
        image_files: Sequence[Path],
        output_dir: Path,
        metadata: ChapterMetadata,
    ) -> Path | None:
        if not image_files:
            logger.warning("PDF converter received no images for %s", metadata.get("title", "chapter"))
            return None

        base_name = compose_chapter_name(metadata.get("title"), metadata.get("chapter"))
        pdf_path = output_dir / f"{base_name}{self.get_output_extension()}"
        images: list[Image.Image] = []
        try:
            for file_path in image_files:
                images.append(Image.open(file_path).convert("RGB"))

            if not images:
                return None

            primary, *rest = images
            primary.save(
                pdf_path,
                "PDF",
                resolution=100.0,
                save_all=True,
                append_images=rest,
            )
            logger.info("Created PDF %s", pdf_path)
            return pdf_path
        finally:
            for image in images:
                image.close()

    def on_load(self) -> None:
        logger.debug("PDF converter ready")

"""PDF conversion utilities for manga chapters.

.. deprecated:: 1.1.0
    This module is deprecated and will be removed in version 2.0.0.
    Use the plugin system instead: plugins/pdf_converter.py

    The PDF converter has been migrated to the plugin architecture for better
    modularity and extensibility. All new converter implementations should use
    the BaseConverter interface from plugins/base.py.
"""

from __future__ import annotations

import logging
import os
import warnings
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from pathlib import Path

from config import CONFIG

logger = logging.getLogger(__name__)

# Issue deprecation warning when this module is imported
warnings.warn(
    "core.pdf_converter is deprecated and will be removed in version 2.0.0. "
    "Use plugins.pdf_converter.PDFConverter instead.",
    DeprecationWarning,
    stacklevel=2,
)


class PDFConverter:
    """Handles conversion of downloaded images to PDF format.

    .. deprecated:: 1.1.0
        Use plugins.pdf_converter.PDFConverter instead. This class will be
        removed in version 2.0.0.
    """

    def __init__(self) -> None:
        self.supported_formats = CONFIG.pdf.supported_formats
        self.resolution = CONFIG.pdf.resolution

    def create_pdf(
        self,
        download_dir: str | Path,
        title: str,
        chapter: str,
    ) -> tuple[bool, str | None]:
        """
        Convert images in download directory to a single PDF.

        Args:
            download_dir: Directory containing downloaded images
            title: Manga title
            chapter: Chapter identifier

        Returns:
            Tuple of (success: bool, pdf_path: str | None)
        """
        download_dir = str(download_dir)
        image_files = self._get_sorted_images(download_dir)

        if not image_files:
            logger.warning("No images found in %s to create PDF", download_dir)
            return False, None

        pdf_path = os.path.join(download_dir, f"{title}_{chapter}.pdf")
        images: list[Image.Image] = []

        try:
            for path in image_files:
                try:
                    img = Image.open(path).convert("RGB")
                    images.append(img)
                except Exception as exc:
                    logger.warning("Failed to open image %s: %s", path, exc)
                    continue

            if not images:
                logger.error("No valid images to create PDF")
                return False, None

            primary, *rest = images
            primary.save(
                pdf_path,
                "PDF",
                resolution=self.resolution,
                save_all=True,
                append_images=rest,
            )

            logger.info("Created PDF: %s", pdf_path)
            return True, pdf_path

        except Exception:
            logger.exception("Failed to create PDF for %s_%s", title, chapter)
            return False, None

        finally:
            # Clean up image objects
            for image in images:
                try:
                    image.close()
                except Exception:
                    pass

    def _get_sorted_images(self, directory: str) -> list[str]:
        """Get sorted list of image file paths from directory."""
        try:
            all_files = os.listdir(directory)
        except OSError as exc:
            logger.error("Cannot read directory %s: %s", directory, exc)
            return []

        image_files = [
            os.path.join(directory, f)
            for f in all_files
            if f.lower().endswith(self.supported_formats)
        ]

        return sorted(image_files)

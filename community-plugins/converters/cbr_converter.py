"""
Universal Manga Downloader Plugin

Name: CBR Converter
Author: UMD Community
Version: 1.0.0
Description: Convert manga chapters to CBR (Comic Book RAR) format for comic book readers
Repository: https://github.com/cwlum/universal-manga-downloader
License: CC BY-NC-SA 4.0
Dependencies: rarfile>=4.0
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from plugins.base import BaseConverter, ChapterMetadata, compose_chapter_name

logger = logging.getLogger(__name__)


class CBRConverter(BaseConverter):
    """Package downloaded images into a CBR (Comic Book RAR) archive."""

    def __init__(self) -> None:
        super().__init__()
        self._rar_available = self._check_rar_command()

    def _check_rar_command(self) -> bool:
        """Check if 'rar' command is available in the system."""
        return shutil.which("rar") is not None

    def get_name(self) -> str:
        return "CBR"

    def get_output_extension(self) -> str:
        return ".cbr"

    def convert(
        self,
        image_files: Sequence[Path],
        output_dir: Path,
        metadata: ChapterMetadata,
    ) -> Path | None:
        """Convert image files to CBR format using RAR compression."""
        if not image_files:
            logger.warning("CBR converter received no images for %s", metadata.get("title", "chapter"))
            return None

        # Check if RAR command is available
        if not self._rar_available:
            logger.error(
                "RAR command-line tool not found. Please install WinRAR or RAR CLI:\n"
                "  - Windows: Download from https://www.rarlab.com/download.htm\n"
                "  - macOS: brew install rar\n"
                "  - Linux: sudo apt-get install rar (Debian/Ubuntu) or check your distro's package manager"
            )
            return None

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Compose output file name
        base_name = compose_chapter_name(metadata.get("title"), metadata.get("chapter"))
        archive_path = output_dir / f"{base_name}{self.get_output_extension()}"

        # Create a temporary directory for renamed files
        temp_dir = output_dir / f".cbr_temp_{base_name}"
        try:
            temp_dir.mkdir(exist_ok=True)

            # Copy and rename files with sequential numbering
            temp_files = []
            for index, file_path in enumerate(image_files, start=1):
                new_name = f"{index:03d}{file_path.suffix.lower()}"
                temp_file = temp_dir / new_name
                shutil.copy2(file_path, temp_file)
                temp_files.append(temp_file)

            # Create RAR archive using command line
            # rar a -ep -m0 -inul archive.cbr file1.jpg file2.jpg ...
            # -ep: exclude base directory from paths
            # -m0: store (no compression) - images are already compressed
            # -inul: disable all messages
            cmd = ["rar", "a", "-ep", "-m0", "-inul", str(archive_path)]
            cmd.extend(str(f) for f in temp_files)

            result = subprocess.run(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error("RAR command failed with code %d: %s", result.returncode, result.stderr)
                return None

            logger.info("Created CBR archive: %s", archive_path)
            return archive_path

        except Exception as e:
            logger.error("Failed to create CBR archive: %s", e)
            return None

        finally:
            # Clean up temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def on_load(self) -> None:
        """Hook executed when the converter becomes active."""
        if self._rar_available:
            logger.debug("CBR converter ready (RAR command found)")
        else:
            logger.warning(
                "CBR converter loaded but RAR command not found. "
                "Install RAR to use this converter."
            )

    def on_unload(self) -> None:
        """Hook executed when the converter is disabled."""
        logger.debug("CBR converter unloaded")

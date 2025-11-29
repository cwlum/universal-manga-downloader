"""
Universal Manga Downloader Plugin

Name: Remote EPUB Converter
Author: UMD Community
Version: 0.2.0
Description: Converts downloaded chapter images into a lightweight EPUB book.
Repository: https://github.com/umd-plugins/official
License: MIT
Dependencies: ebooklib>=0.18
"""

from __future__ import annotations

import mimetypes
from collections.abc import Sequence
from pathlib import Path

from plugins.base import BaseConverter, ChapterMetadata

try:
    from ebooklib import epub
except ImportError as exc:  # pragma: no cover - dependency error surfaced at runtime
    raise RuntimeError(
        "Remote EPUB Converter requires 'ebooklib'. Install via 'pip install ebooklib'"
    ) from exc


class RemoteEpubConverter(BaseConverter):
    """Create an EPUB book from downloaded page images."""

    def get_name(self) -> str:
        return "Remote EPUB Converter"

    def get_output_extension(self) -> str:
        return ".epub"

    def convert(
        self,
        image_files: Sequence[Path],
        output_dir: Path,
        metadata: ChapterMetadata,
    ) -> Path | None:
        if not image_files:
            return None
        output_dir.mkdir(parents=True, exist_ok=True)

        book = epub.EpubBook()
        identifier = metadata.get("source_url", "remote-epub")
        title = f"{metadata.get('title', 'Chapter')} - {metadata.get('chapter', '')}".strip(" -")
        book.set_identifier(identifier)
        book.set_title(title)
        book.set_language("en")
        book.add_author("UMD Remote Plugin")

        spine: list[epub.EpubItem] = ["nav"]
        chapters: list[epub.EpubHtml] = []

        for index, image_path in enumerate(image_files, start=1):
            image_file_name = f"images/{index:04d}_{image_path.name}"
            mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"

            image_item = epub.EpubItem(
                uid=f"img-{index}",
                file_name=image_file_name,
                media_type=mime_type,
                content=image_path.read_bytes(),
            )
            book.add_item(image_item)

            page = epub.EpubHtml(
                title=f"Page {index}",
                file_name=f"page_{index:04d}.xhtml",
            )
            page.content = (
                "<html><body><div style=\"text-align:center;\">"
                f"<img src=\"{image_file_name}\" alt=\"Page {index}\" style=\"max-width:100%;\"/>"
                "</div></body></html>"
            )
            book.add_item(page)
            chapters.append(page)
            spine.append(page)

        book.spine = spine
        book.toc = chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        output_name = f"{title or 'chapter'}.epub"
        output_path = output_dir / output_name
        epub.write_epub(str(output_path), book)
        return output_path

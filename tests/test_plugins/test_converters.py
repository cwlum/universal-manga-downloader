"""Tests for converter plugins and helpers."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from PIL import Image

from plugins.base import ChapterMetadata, compose_chapter_name
from plugins.cbz_converter import CBZConverter
from plugins.pdf_converter import PDFConverter


def _create_images(directory: Path, count: int) -> list[Path]:
    paths: list[Path] = []
    for index in range(count):
        path = directory / f"img{index}.png"
        image = Image.new("RGB", (10, 10), color="white")
        image.save(path)
        image.close()
        paths.append(path)
    return paths


def _build_metadata(title: str = "Series", chapter: str = "1") -> ChapterMetadata:
    return {"title": title, "chapter": chapter, "source_url": "https://example.com"}


def test_compose_chapter_name_variants() -> None:
    assert compose_chapter_name(None, None) == "Chapter"
    assert compose_chapter_name("Title", None) == "Title"
    assert compose_chapter_name(" Title ", " 001 ") == "Title - 001"
    assert compose_chapter_name("", "  ") == "Chapter"


def test_cbz_converter_creates_archive(tmp_path: Path) -> None:
    converter = CBZConverter()
    images = _create_images(tmp_path, 3)
    archive = converter.convert(images, tmp_path, _build_metadata())

    assert archive is not None
    assert archive.exists()

    with ZipFile(archive) as zf:
        entries = zf.namelist()
        assert entries == ["001.png", "002.png", "003.png"]


def test_cbz_converter_returns_none_when_empty(tmp_path: Path) -> None:
    converter = CBZConverter()
    result = converter.convert([], tmp_path, _build_metadata())
    assert result is None


def test_pdf_converter_builds_document(tmp_path: Path) -> None:
    converter = PDFConverter()
    images = _create_images(tmp_path, 2)
    pdf_path = converter.convert(images, tmp_path, _build_metadata("My Series", "5"))

    assert pdf_path is not None
    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"

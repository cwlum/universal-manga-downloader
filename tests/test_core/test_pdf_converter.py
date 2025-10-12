"""Tests for PDFConverter."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from core.pdf_converter import PDFConverter


class TestPDFConverter:
    """Test cases for PDFConverter."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def sample_images(self, temp_dir):
        """Create sample images for testing."""
        image_paths = []
        for i in range(3):
            img = Image.new('RGB', (100, 100), color=(255, 0, 0))
            path = os.path.join(temp_dir, f"{i+1:03d}.jpg")
            img.save(path)
            img.close()
            image_paths.append(path)
        return image_paths

    def test_create_pdf_success(self, temp_dir, sample_images):
        """Test successful PDF creation."""
        converter = PDFConverter()
        success, pdf_path = converter.create_pdf(temp_dir, "TestManga", "Chapter1")

        assert success is True
        assert pdf_path is not None
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith("TestManga_Chapter1.pdf")

    def test_create_pdf_no_images(self, temp_dir):
        """Test PDF creation with no images."""
        converter = PDFConverter()
        success, pdf_path = converter.create_pdf(temp_dir, "TestManga", "Chapter1")

        assert success is False
        assert pdf_path is None

    def test_get_sorted_images(self, temp_dir, sample_images):
        """Test getting sorted images."""
        converter = PDFConverter()
        images = converter._get_sorted_images(temp_dir)

        assert len(images) == 3
        # Check they're sorted
        assert "001.jpg" in images[0]
        assert "002.jpg" in images[1]
        assert "003.jpg" in images[2]

    def test_supported_formats(self, temp_dir):
        """Test that various image formats are supported."""
        converter = PDFConverter()

        # Create images in different formats
        formats = ["png", "jpg", "jpeg", "gif", "bmp", "webp"]
        for fmt in formats:
            if fmt == "webp":
                # Skip webp if not supported
                try:
                    img = Image.new('RGB', (100, 100), color=(255, 0, 0))
                    path = os.path.join(temp_dir, f"test.{fmt}")
                    img.save(path, format=fmt.upper())
                    img.close()
                except Exception:
                    continue
            else:
                img = Image.new('RGB', (100, 100), color=(255, 0, 0))
                path = os.path.join(temp_dir, f"test.{fmt}")
                img.save(path)
                img.close()

        images = converter._get_sorted_images(temp_dir)
        assert len(images) > 0

    def test_create_pdf_with_pathlib(self, temp_dir, sample_images):
        """Test PDF creation with Path object."""
        converter = PDFConverter()
        path_obj = Path(temp_dir)
        success, pdf_path = converter.create_pdf(path_obj, "TestManga", "Chapter1")

        assert success is True
        assert pdf_path is not None
        assert os.path.exists(pdf_path)

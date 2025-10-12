"""Tests for BaseParser."""

from __future__ import annotations

import pytest

from parsers.base_parser import BaseParser


class TestBaseParser:
    """Test cases for BaseParser."""

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test normal text
        assert BaseParser.sanitize_filename("Chapter 1") == "Chapter_1"

        # Test special characters
        assert BaseParser.sanitize_filename("Chapter: 1 / Part 2") == "Chapter__1___Part_2"

        # Test multiple underscores
        result = BaseParser.sanitize_filename("Test___Multiple___Underscores")
        assert "___" not in result

        # Test leading/trailing underscores
        assert not BaseParser.sanitize_filename("___test___").startswith("_")
        assert not BaseParser.sanitize_filename("___test___").endswith("_")

        # Test already valid filename
        assert BaseParser.sanitize_filename("Valid_Filename-123.txt") == "Valid_Filename-123.txt"

    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            BaseParser.get_name()

        with pytest.raises(NotImplementedError):
            BaseParser.can_parse(None, "")

        with pytest.raises(NotImplementedError):
            BaseParser.parse(None, "")

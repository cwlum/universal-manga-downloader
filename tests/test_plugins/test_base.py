"""Tests for plugin base classes and manager."""

from __future__ import annotations

from pathlib import Path

from plugins.base import BasePlugin, PluginManager, PluginType


def test_sanitize_filename() -> None:
    """BasePlugin provides reusable filename sanitization."""

    assert BasePlugin.sanitize_filename("Chapter 1") == "Chapter_1"
    assert BasePlugin.sanitize_filename("Chapter: 1 / Part 2") == "Chapter__1__Part_2"
    assert BasePlugin.sanitize_filename("___Leading___") == "Leading"
    assert BasePlugin.sanitize_filename("Valid_Filename-123.txt") == "Valid_Filename-123.txt"


def test_plugin_manager_discovers_plugins() -> None:
    """The plugin manager loads parser and converter plugins."""

    manager = PluginManager(Path(__file__).resolve().parents[2] / "plugins")
    manager.load_plugins()

    parser_names = {plugin.get_name() for plugin in manager.iter_enabled_parsers()}
    converter_names = {converter.get_name() for converter in manager.iter_enabled_converters()}

    assert "Bato" in parser_names
    assert {"PDF", "CBZ"}.issubset(converter_names)

    manager.set_enabled(PluginType.CONVERTER, "PDF", False)
    converter_names = {converter.get_name() for converter in manager.iter_enabled_converters()}
    assert "PDF" not in converter_names

    manager.set_enabled(PluginType.CONVERTER, "PDF", True)
    converter_names = {converter.get_name() for converter in manager.iter_enabled_converters()}
    assert "PDF" in converter_names

    manager.shutdown()

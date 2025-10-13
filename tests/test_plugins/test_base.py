"""Tests for plugin base classes and manager."""

from __future__ import annotations

from pathlib import Path

from plugins.base import BasePlugin, PluginLoader, PluginManager, PluginType


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


def test_plugin_loader_discovers_sources() -> None:
    """PluginLoader enumerates available parser and converter classes."""

    plugin_dir = Path(__file__).resolve().parents[2] / "plugins"
    loader = PluginLoader(plugin_dir)
    sources = list(loader.discover())

    parser_classes = {source.class_name for source in sources if source.plugin_type is PluginType.PARSER}
    converter_classes = {source.class_name for source in sources if source.plugin_type is PluginType.CONVERTER}

    assert "BatoParser" in parser_classes
    assert {"PDFConverter", "CBZConverter"}.issubset(converter_classes)

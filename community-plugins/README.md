# Community Plugins

This directory contains community-contributed plugins for Universal Manga Downloader.

## Installation

Copy the raw URL of any plugin and install via UMD:

1. Settings → Remote Plugins
2. Paste the raw URL: `https://raw.githubusercontent.com/lum-muu/universal-manga-downloader/main/community-plugins/parsers/your_plugin.py`
3. Click Install

## Available Plugins

See the [Plugin Wiki](https://github.com/lum-muu/universal-manga-downloader/wiki) for a complete list of available plugins.

## Contributing

See [Plugin Submission Guide](https://github.com/lum-muu/universal-manga-downloader/wiki/Plugin-Submission-Guide) in our wiki.

## Directory Structure

```
community-plugins/
├── parsers/          # Site-specific manga parsers
├── converters/       # Output format converters
└── index.json        # Plugin index (auto-generated)
```

## Validation

Before submitting, validate your plugin:

```bash
python scripts/validate_community_plugin.py community-plugins/parsers/your_plugin.py
```

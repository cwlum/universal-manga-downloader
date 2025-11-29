# Universal Manga Downloader - Official Plugin Repository

[![Plugin Market](https://img.shields.io/badge/market-view-blue)](https://umd-plugins.github.io/official/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Centralized repository for Universal Manga Downloader (UMD) community plugins. Use this repo as the canonical "wiki" for sharing parser/converter implementations, documentation, and screenshots.

## 🔌 Browse Plugins

- [Plugin Market (GitHub Pages)](https://umd-plugins.github.io/official/) – searchable gallery
- [`parsers/`](parsers) – raw parser modules
- [`converters/`](converters) – converter modules

Each plugin exposes the same API as built-in modules (`BasePlugin` or `BaseConverter`).

## 🚀 Install from UMD (v1.3.7+)

1. Open **Settings → Remote Plugins**.
2. Paste the raw GitHub URL from this repository (e.g., `https://raw.githubusercontent.com/umd-plugins/official/main/parsers/example_remote_parser.py`).
3. Click **Install** to load instantly.

## 📦 Sample Plugins

| Name | Type | Description | Install |
| --- | --- | --- | --- |
| Example Remote Parser | Parser | Demonstrates metadata + sanitize helpers | [📋 Copy](https://raw.githubusercontent.com/umd-plugins/official/main/parsers/example_remote_parser.py) |
| Example EPUB Converter | Converter | Sketch for exporting CBZ to EPUB | [📋 Copy](https://raw.githubusercontent.com/umd-plugins/official/main/converters/example_epub_converter.py) |

## 🧪 Validation

Pull requests run automated checks:

- `scripts/validate_plugin.py` – style & metadata
- `scripts/generate_index.py` – updates `index.json`
- `.github/workflows/validate-plugin.yml` – CI gate

## 📝 Submission Flow

1. Fork this repo.
2. Drop your plugin under `parsers/` or `converters/` with metadata docstring.
3. Run `python scripts/validate_plugin.py path/to/plugin.py`.
4. Submit a PR using the `[Plugin] Add <Name>` template.

See [`docs/submission-guide.md`](docs/submission-guide.md) for full details.

## 🔒 Security

- Reviewers check for dangerous calls (`exec`, `os.system`, etc.).
- Contributors must document dependencies explicitly.
- Users should **always** read code before installing.

## 📊 Metadata

`index.json` captures plugin metadata (name, version, checksum, downloads). The website reads this file to power search/filter/sort.

## 📜 License

Unless otherwise noted, contributions default to MIT.

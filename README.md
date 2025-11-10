# Universal Manga Downloader

![Version](https://img.shields.io/badge/version-1.2.1-orange)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-yellow)
![Last Updated](https://img.shields.io/badge/last%20updated-2025--01--10-informational)
[![GitLab](https://img.shields.io/badge/GitLab-Repository-orange?logo=gitlab)](https://gitlab.com/lummuu/universal-manga-downloader)
[![Pipeline](https://gitlab.com/lummuu/universal-manga-downloader/badges/main/pipeline.svg)](https://gitlab.com/lummuu/universal-manga-downloader/-/pipelines)

An extensible, user-friendly GUI tool to download manga chapters from various websites and automatically convert them into rich digital archives.

**🔗 Repository:** [https://gitlab.com/lummuu/universal-manga-downloader](https://gitlab.com/lummuu/universal-manga-downloader)

This tool is built on a **modular plugin engine**, making it adaptable to future website changes and expandable to support new sites or output formats without touching the core codebase.

---

## 🎉 What's New in Version 1.2.1

This release focuses on **stability, performance, and user experience improvements**:

### Performance & Reliability
- **🔄 Automatic Retry Logic**: Network errors are now automatically retried with exponential backoff (1s → 2s → 4s), making downloads more resilient
- **⏱️ Rate Limiting**: Built-in request throttling prevents triggering anti-bot measures and IP bans
- **💾 Disk Space Checking**: Pre-download validation ensures sufficient space is available (with safety margin)
- **🔧 Enhanced Thread Management**: Graceful shutdown prevents orphaned threads and ensures clean application exit

### User Experience
- **🖱️ Silky Smooth Scrolling**: Completely redesigned mouse wheel handling with:
  - Separate optimization for trackpad vs. mouse wheel on macOS
  - Pixel-based Canvas scrolling for buttery-smooth feel
  - Prevention of duplicate event bindings
- **🚀 Optimized ScraperPool**: Intelligent waiting instead of creating excessive temporary scrapers
- **📊 Enhanced CLI**: New `--config-info` flag and improved `--doctor` diagnostics with disk space checks

### Code Quality
- **✨ Consistent Filename Sanitization**: Unified implementation across all modules with Windows reserved name handling
- **🎯 Better Error Messages**: More specific exception handling with actionable user feedback
- **⚙️ Centralized Configuration**: All hardcoded values moved to CONFIG for easier customization

---

## A Brand New Tabbed Interface

Version 1.0.0 introduces a tabbed workspace that cleanly separates searching, monitoring your download queue, and configuration.

### Browser
The Browser tab is where you can search for manga, review series info, and easily select chapters for download.

![Browser Tab](assets/Browser.png)

### Downloads
A live queue dashboard! Every queued chapter gets its own status line and progress bar so you can watch fetching, downloading, and conversion stages in real time.

![Downloads Tab](assets/Downloads.png)

### Settings
The download directory, chapter workers, and image workers live together under the Settings tab for quick tweaks.

![Settings Tab](assets/Settings.png)

---

## Key Features

-   ✅ **Plugin System**: Automatically discovers parser and converter plugins, so contributors can add new sites or formats by dropping a file into the `plugins/` directory.
-   ✅ **Zero-Setup Installation**: Automatically installs all required libraries on first run.
-   ✅ **Tabbed UI**: Navigate between `Browser`, `Downloads`, and `Settings` tabs to keep searching, monitoring, and configuring separate and tidy.
-   ✅ **Batch Queue & Range Control**: Queue entire series, highlight ranges with one click, press `Ctrl+A` to select everything, or fine-tune chapter spans via the new range helpers.
-   ✅ **Per-Chapter Progress**: Watch each chapter advance from fetch to PDF conversion with a dedicated queue entry and live status updates.
-   ✅ **Multi-Threaded Downloads**: Adjust chapter and image worker counts to shorten download times on fast connections.
-   ✅ **Custom Download Folder**: Save chapters anywhere—no more being locked to your system Downloads directory.
-   ✅ **Bato.to Search & Chapter Explorer**: Search the catalog, review series info, and select chapters to pre-fill the downloader with a single click.
-   ✅ **Dual Search Providers**: Enable Bato.to or MangaDex in Settings → Plugins, then swap between them in the Browser tab to keep searching even if one site goes down.
-   ✅ **MangaDex Chapter Support**: Paste any MangaDex chapter URL and let the built-in plugin pull images directly from the official API.
-   ✅ **Plugin Output Formats**: Ships with PDF and CBZ converters and makes it trivial to ship your own (EPUB, plain images, etc.).
-   ✅ **Smart Folder Organization**: Creates folders named after the manga title and chapter.
-   ✅ **Advanced Web Scraping**: Uses `cloudscraper` to bypass anti-bot protections like Cloudflare.
-   ✅ **Cross-Platform Support**: Works flawlessly on Windows, macOS, and Linux.

---

## Before You Start: The Only Prerequisite

The **only** thing you need is **Python 3**.

#### How to check if Python 3 is installed?

Open your "Terminal" or "Command Prompt" and type `python3 --version` (or `python --version`). If you see a version number, you're ready. If not, download it from the [official Python website](https://www.python.org/downloads/), ensuring you check **"Add Python to PATH"** during installation.

---

## How to Use: Quick Start

#### Step 1: Install the Tool
Pick the workflow that fits your setup:

- **Option A (recommended)** – install with **pipx** from the local repository so `umd` is available system-wide but still isolated:

  First, clone this repository to your local machine. Then, navigate your terminal into the repository's directory and run:
  ```bash
  pipx install .
  ```

  Alternatively, you can point pipx to the full path of the repository from any directory:
  ```bash
  pipx install /path/to/universal-manga-downloader
  ```

- **Option B** – create a virtual environment for development and install in editable mode:

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e .
  ```

  (On Windows, replace the `source` line with `.venv\Scripts\activate`.)

If your system Python is “externally managed” (PEP 668) and rejects direct installs, use pipx or a virtual environment instead of `pip install` at the global level.

#### Step 2: Launch the Application
Once the installation is complete, you can run the application from any directory by simply typing:

```bash
umd
```

Need a quick health check before launching? Try:

```bash
umd --doctor
```

For verbose logging, append `--log-level debug`.

To upgrade to the latest release on demand, run:

```bash
umd --auto-update
```

The GUI window will appear, and you can start downloading manga.

### Handy CLI options
- `umd --version` — print the currently installed release.
- `umd --doctor` — verify Python, Tkinter, and required libraries.
- `umd --auto-update` — upgrade to the latest published package before launching.
- `umd --log-level debug` — surface verbose logs (useful when debugging).
- `umd --no-gui` — run validation only; ideal for CI or scripted checks.

#### Step 3: Using the Application
1.  In the **Browser** tab, type a title into **Search Manga** and press `Enter`, or double-click a result to load its synopsis and chapter list automatically.
2.  Multi-select chapters with Shift/Ctrl, press **Highlight Range** to preselect a span, or paste a chapter URL into **Quick Queue**—then choose **Queue Selected**, **Queue Range**, **Queue All**, or **Queue Download** to add them to the queue.
3.  Switch to the **Downloads** tab to watch each chapter's progress, and use the **Settings** tab to adjust the download folder or worker counts whenever you need.

---

## For Developers: Extend with Plugins

**New to the project?** Start with **[ONBOARDING.md](ONBOARDING.md)** for a quick 5-minute setup guide!

See **[DEVELOPMENT.md](DEVELOPMENT.md)** for environment setup, linting, and type-checking instructions before contributing changes. Refer to **[PLUGINS.md](PLUGINS.md)** for the full plugin specification, discovery rules, and example implementations. Check out **[ARCHITECTURE.md](ARCHITECTURE.md)** to understand the system design.

Universal Manga Downloader features a dedicated plugin system that allows you to add new site parsers or export formats without editing `manga_downloader.py`.

### Adding a Parser Plugin

1.  Create a new file inside `plugins/` (for example, `my_site.py`).
2.  Subclass `BasePlugin` from `plugins.base`.
3.  Implement the required methods:
    -   `get_name(self) -> str`
    -   `can_handle(self, url: str) -> bool`
    -   `parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None`
4.  (Optional) Override `on_load`/`on_unload` for setup or cleanup work.
5.  Save the file—no manual registration needed. The manager loads every plugin at startup.

### Adding a Converter Plugin

1.  Create a file in `plugins/` (for example, `epub_converter.py`).
2.  Subclass `BaseConverter` and implement:
    -   `get_name(self) -> str`
    -   `get_output_extension(self) -> str`
    -   `convert(self, image_files, output_dir, metadata)` returning the created file path.
3.  Use the supplied `ChapterMetadata` to populate filenames or metadata.
4.  Respect the project's non-commercial license—plugins must not include monetization or tracking code.

Once enabled from the Settings tab, your plugin will appear in the GUI and participate in downloads automatically. You can also exercise the standalone `PluginLoader` in unit tests to ensure new modules are discoverable before wiring them into the GUI.

### Future Extensions

-   Explore exposing plugin entry points so third-party packages installed via `pip` can register automatically.

---

## Troubleshooting & Common Pitfalls

- **`ERROR: externally-managed-environment` when installing** – macOS Homebrew Python enforces PEP 668. Install with `pipx install universal-manga-downloader`, or create a venv and run `pip install -e .` inside it.
- **`pip: command not found`** – call pip through Python: `python3 -m pip install -e .` (or use pipx).
- **`umd` still shows an old version** – you likely have an outdated symlink. If you used pipx, run `pipx uninstall universal-manga-downloader` followed by `pipx install /path/to/universal-manga-downloader`, or delete `~/.local/bin/umd` before reinstalling.
- **GUI fails to open / crashes immediately** – run `umd --doctor` to confirm Tkinter is installed and accessible; on Linux ensure the system has an X server running.
- **"No suitable parser found" in the queue** – the URL is either unsupported or the site changed its layout. Enable the correct parser plugin in Settings → Plugins and try again.
- **Download errors** – double-check network connectivity, confirm the site is reachable in a browser, and look at the terminal for detailed logs (use `--log-level debug` if needed).

## Disclaimer

Please read the full [Disclaimer](DISCLAIMER.md) before using this software. Users are solely responsible for their actions and must comply with all applicable copyright laws.

---

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

In short, you are free to:
-   **Share** — copy and redistribute the material in any medium or format.
-   **Adapt** — remix, transform, and build upon the material.

Under the following terms:
-   **Attribution** — You must give appropriate credit.
-   **NonCommercial** — You may not use the material for commercial purposes.
-   **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.

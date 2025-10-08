# Universal Manga Downloader (v3.4)

![Version](https://img.shields.io/badge/version-3.4.0-purple)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)

An extensible, user-friendly GUI tool to download manga chapters from various websites and automatically convert them into a single PDF file.

This tool is built on a **modular parser engine**, making it adaptable to future website changes and expandable to support new sites.

---

## What's New

-   **Custom download location & queue progress** – pick any destination folder and watch a dedicated queue progress bar track overall completion.
-   **Batch downloads & range control** – multi-select chapters, queue entire series, or target custom chapter ranges without reloading the UI.
-   **Configurable multi-threading** – dial in chapter and image worker counts to accelerate downloads with parallel fetches.
-   **Integrated Bato.to search & chapter browser** – look up series by title, inspect descriptions and metadata, then queue any chapter without leaving the app.
-   **Bato.si compatibility restored** – the `Bato_V3` parser now understands the latest Qwik-powered page format (it decodes the embedded base36 token map to recover image URLs), so tricky chapters such as [OMORI Official ch. 10](https://bato.si/title/160779-en-omori-official/3735107-ch_10) download again without manual work.
-   **Parser modules runnable as scripts** – every parser still loads dynamically inside the app, but you can now execute `python3 parsers/bato_v3_parser.py` directly while developing to debug its output.

---

## Key Features

-   ✅ **Modular Parser Engine**: Intelligently cycles through available parsers to find one that works for the given URL. Highly extensible for future websites.
-   ✅ **Zero-Setup Installation**: Automatically installs all required libraries on first run.
-   ✅ **Batch Queue & Range Control**: Queue entire series, multi-select chapters, or target custom chapter ranges in one click.
-   ✅ **Multi-Threaded Downloads**: Adjust chapter and image worker counts to shorten download times on fast connections.
-   ✅ **Custom Download Folder**: Save chapters anywhere—no more being locked to your system Downloads directory.
-   ✅ **Bato.to Search & Chapter Explorer**: Search the catalog, review series info, and select chapters to pre-fill the downloader with a single click.
-   ✅ **One-Click PDF Conversion**: Instantly merges all downloaded images into a single, high-quality PDF.
-   ✅ **Smart Folder Organization**: Creates folders named after the manga title and chapter.
-   ✅ **Advanced Web Scraping**: Uses `cloudscraper` to bypass anti-bot protections like Cloudflare.
-   ✅ **Cross-Platform Support**: Works flawlessly on Windows, macOS, and Linux.

---

## Before You Start: The Only Prerequisite

The **only** thing you need is **Python 3**.

#### How to check if Python 3 is installed?

Open your "Terminal" or "Command Prompt" and type `python3 --version` (or `python --version`). If you see a version number, you're ready. If not, download it from the [official Python website](https://www.python.org/downloads/), ensuring you check **"Add Python to PATH"** during installation.

---

## How to Use: Quick Start in 3 Steps

#### Step 1: Download The Tool
1.  Go to the project's GitHub page.
2.  Click the green **`< > Code`** button -> **`Download ZIP`**.
3.  Unzip the downloaded file.

#### Step 2: Find and Run the Script
1.  Open the unzipped folder.
2.  **Open a terminal in this folder**:
    -   **Windows**: Type `cmd` in the folder's address bar and press Enter.
    -   **macOS**: Right-click the folder's title in the Finder window and choose "New Terminal at Folder".
3.  In the terminal, type `python3 manga_downloader.py` and press Enter.

#### Step 3: Copy, Paste, and Download
1.  The GUI window will appear. (It may pause on first run to auto-install libraries).
2.  Use the **Search Manga** box to find a Bato.to series by title, then double-click a result to load its synopsis and chapter list.
3.  Select one or many chapters (use Shift/Ctrl for multi-select or the range fields) to queue them, or paste a chapter link manually, then click **Download**.
4.  Set your preferred save folder and adjust the chapter/image worker spinboxes if you need extra parallelism; the app will fetch images, show per-chapter and overall queue progress, and save the final PDF in your chosen directory.

---

## For Developers: How to Add a New Parser

This tool's strength is its modularity. To support a new website, you don't need to touch the main application.

1.  **Create a new parser file** in the `/parsers` directory (e.g., `my_site_parser.py`).
2.  **Create a parser class** that inherits from `BaseParser`.
3.  **Implement the `can_parse` and `parse` methods**:
    -   `can_parse(soup, url)`: A quick check to see if your parser can handle the page (e.g., check for a unique HTML tag or URL pattern).
    -   `parse(soup, url)`: The core logic to extract the `title`, `chapter`, and a list of `image_urls`. It should return a dictionary with these keys.
4.  **Done!** The main script will automatically detect and use your new parser.

---

## Troubleshooting

-   **"No suitable parser found"**: This means the URL is from a website or a page layout that is not yet supported.
-   **Window flashes and disappears**: Check the terminal for error messages.
-   **Download fails**: Check your internet connection and the URL.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

In short, you are free to:
-   **Share** — copy and redistribute the material in any medium or format.
-   **Adapt** — remix, transform, and build upon the material.

Under the following terms:
-   **Attribution** — You must give appropriate credit.
-   **NonCommercial** — You may not use the material for commercial purposes.
-   **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.

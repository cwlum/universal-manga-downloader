# Bato Downloader
![Version](https://img.shields.io/badge/version-2.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Last Updated](https://img.shields.io/badge/last%20updated-2025-07-13-informational)

A simple, user-friendly GUI application to download manga chapters from Bato.to and automatically convert them into a single PDF file.

## Features

-   **Zero-Setup Installation**: The script automatically installs any missing required libraries on first run.
-   **Automatic PDF Conversion**: Downloads all chapter images and instantly merges them into a single, convenient PDF file.
-   **Easy-to-use GUI**: Just paste the chapter URL and click download.
-   **Organized Downloads**: Automatically creates a named folder for each chapter in your "Downloads" directory.
-   **Cross-platform**: Works on macOS, Windows, and Linux.

## Requirements

-   [Python 3](https://www.python.org/downloads/)

That's it! The script handles the installation of all other dependencies.

## Usage

1.  Run the application from your terminal:
    ```bash
    python3 manga_downloader.py
    ```
2.  On the first run, the script may take a moment to download and install necessary libraries. You will see progress messages in the terminal.
3.  Once the window appears, paste the full URL of a Bato.to manga chapter into the input box.
    -   Example URL: `https://bato.to/chapter/123456`
4.  Click the "Download" button.
5.  The application will show the download progress. Once finished, the images and the final PDF will be saved in a new folder inside your system's "Downloads" directory.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

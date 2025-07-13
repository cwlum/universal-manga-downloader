# Bato Downloader
![Version](https://img.shields.io/badge/version-1.0.0-orange)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Last Updated](https://img.shields.io/badge/last%20updated-2025--07--13-informational)

A simple GUI application to download manga chapters from the Bato.to website.

## Features

-   Easy-to-use graphical user interface.
-   Just paste the chapter URL and click download.
-   Automatically creates a named folder for each chapter.
-   Saves images in sequential order for easy reading.
-   Cross-platform (should work on macOS, Windows, and Linux).

## Installation

This application requires Python 3. Before running, you need to install a few dependencies.

1.  **Install required Python libraries:**

    Open your terminal or command prompt and run:
    ```bash
    pip install requests beautifulsoup4
    ```

2.  **(macOS Only) Install Tkinter:**

    If you are on macOS and encounter a `ModuleNotFoundError: No module named '_tkinter'` error, it means your Python installation is missing the necessary GUI toolkit. You can install it with Homebrew by running:
    ```bash
    brew install python-tk
    ```

## Usage

1.  Run the application from your terminal:
    ```bash
    python3 manga_downloader.py
    ```
2.  A window will appear. Paste the full URL of a Bato.to manga chapter into the input box.
    -   Example URL: `https://zbato.org/title/160779/2901842`
3.  Click the "Download" button.
4.  The application will show the download progress. Once finished, the images will be saved in a new folder inside your system's "Downloads" directory.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

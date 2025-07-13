# Bato Manga Downloader (v2.1)

![Version](https://img.shields.io/badge/version-2.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Last Updated](https://img.shields.io/badge/last%20updated-2025-07-13-informational)

A simple GUI tool designed for manga enthusiasts to easily download chapters from Bato.to and automatically convert them into a single PDF file, perfect for offline reading and archiving.

This tool is built with **extreme simplicity** in mind. Even if you have no programming knowledge, you can easily get started by following these instructions.

---

## Key Features

-   ✅ **Zero-Setup Installation**: The script automatically handles all technical dependencies on its first run. You don't need to install anything manually.
-   ✅ **One-Click PDF Conversion**: After downloading, all images are instantly merged into a high-quality PDF file.
-   ✅ **Graphical User Interface**: Intuitive to use—just copy and paste a URL, then click a button.
-   ✅ **Smart Folder Organization**: Automatically creates folders named after the manga title and chapter number for easy management.
-   ✅ **Cross-Platform Support**: Works flawlessly on Windows, macOS, and Linux.

---

## Before You Start: The Only Prerequisite

The **only** thing you need to have installed on your computer beforehand is **Python 3**.

#### How to check if Python 3 is installed?

Open your computer's "Terminal" or "Command Prompt":
-   **Windows**: Press `Win` + `R`, type `cmd`, and press Enter.
-   **macOS**: Go to "Applications" -> "Utilities" -> "Terminal".

Then, type the following command and press Enter:
```bash
python3 --version
```
If you see a version number like `Python 3.x.x`, congratulations, you're ready to go!

> **What if it says `command not found`?**
> - Try the alternative command: `python --version`.
> - If both fail, you need to install Python 3. Go to the [official Python website](https://www.python.org/downloads/), download the latest version, and run the installer. **Be sure to check the box that says "Add Python to PATH" during installation!**

---

## How to Use: Quick Start in 3 Steps

#### Step 1: Download The Tool

1.  Go to the project's GitHub page.
2.  Click the green **`< > Code`** button in the top-right corner.
3.  Select **`Download ZIP`** from the dropdown menu.
4.  Once downloaded, unzip the file to a location you prefer (like your Desktop).

#### Step 2: Find and Run the Script

1.  Open the folder you just unzipped.
2.  **Open a terminal in the current folder**:
    -   **Windows**: In the folder's address bar, type `cmd` and press Enter. Or, hold `Shift` and right-click in the empty space, then select "Open PowerShell window here".
    -   **macOS**: Right-click the folder's name in the title bar at the top of the window and choose "New Terminal at Folder". Alternatively, you can drag the folder icon directly into an open Terminal window.
3.  In the terminal window that opens, type the following command and press Enter:
    ```bash
    python3 manga_downloader.py
    ```
    > **Note**: If the `python3` command doesn't work, try `python manga_downloader.py`.

#### Step 3: Copy, Paste, and Download

1.  After running the command, a GUI window will pop up.
    > **On First Run**: The script might take a moment to install necessary libraries. You'll see progress messages in the terminal—this is normal and part of the automatic setup.
2.  From your web browser, copy the full URL of the Bato.to manga **chapter** you want to download.
3.  Paste the URL into the input box in the application window.
4.  Click the "Download" button.
5.  The progress bar will show the download status. Once complete, you will find a new folder named after the manga in your system's "Downloads" directory, containing all the images and the final, merged PDF.

---

## Troubleshooting: What to Do If You Have Problems?

-   **Problem: The window flashes and disappears immediately after running the script.**
    -   **Cause**: This usually means an error occurred.
    -   **Solution**: Check the terminal window for any error messages. This information is crucial for figuring out the problem.

-   **Problem: The download fails or the progress bar gets stuck.**
    -   **Cause**: This could be a network issue or an invalid Bato.to URL.
    -   **Solution**: Ensure you have a stable internet connection and that the URL you pasted is a valid manga **chapter** page, not the main series page.

-   **Problem: On macOS, a message says the app "cannot be verified".**
    -   **Cause**: This is a standard macOS security feature.
    -   **Solution**: Go to "System Settings" -> "Privacy & Security". Scroll down, and you will see a message about the app being blocked. Click the "Open Anyway" button.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

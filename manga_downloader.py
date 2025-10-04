import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import os
import threading
import re
from urllib.parse import urlparse

# --- Auto-install required packages ---
def install_and_import(package, import_name=None):
    if import_name is None:
        import_name = package
    try:
        __import__(import_name)
    except ImportError:
        print(f"{package} not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--break-system-packages"])
            print(f"{package} installed successfully.")
            __import__(import_name)
        except Exception as e:
            print(f"Failed to install {package}. Please install it manually using: python -m pip install {package}")
            print(f"Error: {e}")
            sys.exit(1)

# Check and install packages
install_and_import("requests")
install_and_import("beautifulsoup4", "bs4")
install_and_import("Pillow", "PIL")
install_and_import("cloudscraper")

# --- Now import everything else ---
import requests
import cloudscraper
from bs4 import BeautifulSoup
from PIL import Image
from parsers import ALL_PARSERS


class MangaDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Universal Manga Downloader")
        self.geometry("500x250")

        self.url_label = ttk.Label(self, text="Manga Chapter URL:")
        self.url_label.pack(pady=5)

        self.url_entry = ttk.Entry(self, width=60)
        self.url_entry.pack(pady=5, padx=10)

        self.download_button = ttk.Button(self, text="Download", command=self.start_download_thread)
        self.download_button.pack(pady=10)

        self.progress = ttk.Progressbar(self, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)

        self.status_label = ttk.Label(self, text="Status: Ready")
        self.status_label.pack(pady=5)

    def start_download_thread(self):
        self.download_button.config(state="disabled")
        self.status_label.config(text="Status: Starting download...")
        self.progress["value"] = 0
        thread = threading.Thread(target=self.download_manga)
        thread.start()

    def download_manga(self):
        url = self.url_entry.get()
        if not url:
            self.status_label.config(text="Status: Error - URL is empty")
            self.download_button.config(state="normal")
            return

        try:
            scraper = cloudscraper.create_scraper()
            print(f"Fetching URL: {url}")
            response = scraper.get(url)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            # --- Modular Parsing Engine ---
            parsed_data = None
            for parser in ALL_PARSERS:
                self.status_label.config(text=f"Status: Trying parser {parser.get_name()}...")
                self.update_idletasks()
                if parser.can_parse(soup, url):
                    parsed_data = parser.parse(soup, url)
                    if parsed_data:
                        self.status_label.config(text=f"Status: Parsed successfully with {parser.get_name()}!")
                        self.update_idletasks()
                        break
            
            if not parsed_data:
                self.status_label.config(text="Status: Error - No suitable parser found for this URL.")
                self.download_button.config(state="normal")
                return

            title = parsed_data['title']
            chapter = parsed_data['chapter']
            image_urls = parsed_data['image_urls']

            # --- Create Directory ---
            download_dir = os.path.join(os.path.expanduser("~"), "Downloads", f"{title}_{chapter}")
            os.makedirs(download_dir, exist_ok=True)

            # --- Download Images ---
            total_images = len(image_urls)
            self.progress["maximum"] = total_images
            for i, img_url in enumerate(image_urls):
                try:
                    img_response = scraper.get(img_url)
                    img_response.raise_for_status()
                    
                    parsed_url = urlparse(img_url)
                    filename, file_ext = os.path.splitext(os.path.basename(parsed_url.path))
                    if not file_ext:
                        content_type = img_response.headers.get('content-type')
                        ext_match = re.search(r'image/(\w+)', content_type) if content_type else None
                        file_ext = f".{ext_match.group(1)}" if ext_match else ".jpg"

                    file_path = os.path.join(download_dir, f"{i+1:03d}{file_ext}")
                    with open(file_path, 'wb') as f:
                        f.write(img_response.content)

                    self.status_label.config(text=f"Status: Downloading {i+1}/{total_images}")
                    self.progress["value"] = i + 1
                    self.update_idletasks()

                except requests.RequestException as e:
                    print(f"Failed to download {img_url}: {e}")
                    continue

            self.status_label.config(text="Status: Download complete. Now creating PDF...")
            self.update_idletasks()

            # --- Create PDF ---
            supported_formats = ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp')
            image_files = sorted([
                os.path.join(download_dir, f) 
                for f in os.listdir(download_dir) 
                if f.lower().endswith(supported_formats)
            ])

            if image_files:
                pdf_path = os.path.join(download_dir, f"{title}_{chapter}.pdf")
                
                images_to_save = [Image.open(f).convert('RGB') for f in image_files]
                
                if images_to_save:
                    images_to_save[0].save(
                        pdf_path, "PDF", resolution=100.0, save_all=True, 
                        append_images=images_to_save[1:]
                    )
                    self.status_label.config(text=f"Status: PDF created! Saved to {pdf_path}")
                else:
                    self.status_label.config(text="Status: No valid images found to create PDF.")
            else:
                self.status_label.config(text="Status: No images found to create PDF.")

        except requests.RequestException as e:
            self.status_label.config(text=f"Status: Error - Failed to fetch URL: {e}")
        except Exception as e:
            self.status_label.config(text=f"Status: Error - An unexpected error occurred: {e}")

        self.download_button.config(state="normal")

if __name__ == "__main__":
    app = MangaDownloader()
    app.mainloop()


import tkinter as tk
from tkinter import ttk, filedialog
import subprocess
import sys
import os

# --- Auto-install required packages ---
def install_and_import(package, import_name=None):
    if import_name is None:
        import_name = package
    try:
        __import__(import_name)
    except ImportError:
        print(f"{package} not found. Installing...")
        try:
            # Add --break-system-packages to handle PEP 668 externally managed environments
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
import re
import json
import threading
from urllib.parse import urlparse
from PIL import Image


class MangaDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bato.to Manga Downloader")
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
            # Use cloudscraper to bypass Cloudflare
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url)
            response.raise_for_status()
            html_content = response.text

            soup = BeautifulSoup(html_content, 'html.parser')

            # --- Extract Title and Chapter ---
            title_tag = soup.find('a', href=re.compile(r'/title/\d+'))
            title = title_tag.text.strip() if title_tag else "Manga"
            title = re.sub(r'[^a-zA-Z0-9_.-]', '_', title) # Sanitize title

            chapter_info = soup.find('h6', class_='text-lg')
            chapter = chapter_info.text.strip() if chapter_info else "Chapter"
            chapter = re.sub(r'[^a-zA-Z0-9_.-]', '_', chapter) # Sanitize chapter

            # --- Create Directory ---
            download_dir = os.path.join(os.path.expanduser("~"), "Downloads", f"{title}_{chapter}")
            os.makedirs(download_dir, exist_ok=True)

            # --- Extract Image URLs ---
            image_urls = []
            
            # Method 1: Try the 'astro-island' method first (for older page structures)
            astro_island = soup.find('astro-island', {'component-url': re.compile(r'ImageList')})
            if astro_island:
                props_str = astro_island.get('props', '{}')
                props_json = json.loads(props_str.replace('"', '"'))
                image_files_str = props_json.get('imageFiles', [0, '[]'])[1]
                image_urls = [img[1] for img in json.loads(image_files_str)]

            # Method 2: Fallback to script tag parsing (for newer page structures like zbato.org)
            if not image_urls:
                script_tag = soup.find('script', string=re.compile(r'const imgHttps ='))
                if script_tag:
                    script_content = script_tag.string
                    match = re.search(r'const imgHttps = (\[.*?\]);', script_content)
                    if match:
                        json_str = match.group(1)
                        image_urls = json.loads(json_str)

            if not image_urls:
                self.status_label.config(text="Status: Error - Could not find image list.")
                self.download_button.config(state="normal")
                return

            # --- Download Images ---
            total_images = len(image_urls)
            self.progress["maximum"] = total_images
            for i, img_url in enumerate(image_urls):
                try:
                    # Use the same scraper session to download images
                    img_response = scraper.get(img_url)
                    img_response.raise_for_status()

                    # Get file extension
                    parsed_url = urlparse(img_url)
                    filename, file_ext = os.path.splitext(os.path.basename(parsed_url.path))
                    if not file_ext:
                        # Guess extension from content type
                        content_type = img_response.headers.get('content-type')
                        if content_type:
                            ext_match = re.search(r'image/(\w+)', content_type)
                            if ext_match:
                                file_ext = f".{ext_match.group(1)}"
                            else:
                                file_ext = ".jpg" # Default
                        else:
                            file_ext = ".jpg"

                    # Save file
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
            # Add 'webp' to the list of supported image formats
            supported_formats = ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp')
            image_files = sorted([
                os.path.join(download_dir, f) 
                for f in os.listdir(download_dir) 
                if f.lower().endswith(supported_formats)
            ])

            if image_files:
                try:
                    pdf_path = os.path.join(download_dir, f"{title}_{chapter}.pdf")
                    
                    # Open the first image
                    img1 = Image.open(image_files[0]).convert('RGB')
                    
                    # Create a list of other images
                    other_images = []
                    if len(image_files) > 1:
                        for img_path in image_files[1:]:
                            img = Image.open(img_path).convert('RGB')
                            other_images.append(img)

                    # Save as PDF
                    img1.save(pdf_path, "PDF" ,resolution=100.0, save_all=True, append_images=other_images)

                    self.status_label.config(text=f"Status: PDF created successfully! Saved to {pdf_path}")
                except Exception as e:
                    self.status_label.config(text=f"Status: Error creating PDF: {e}")
            else:
                self.status_label.config(text="Status: No images found to create PDF.")


        except requests.RequestException as e:
            self.status_label.config(text=f"Status: Error - Failed to fetch URL: {e}")
        except Exception as e:
            self.status_label.config(text=f"Status: Error - An unexpected error occurred: {e}")

        self.download_button.config(state="normal")

if __name__ == "__main__":
    # The package check happens right after the initial imports
    # so by the time we get here, all dependencies should be ready.
    app = MangaDownloader()
    app.mainloop()

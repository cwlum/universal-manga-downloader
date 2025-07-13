
import tkinter as tk
from tkinter import ttk, filedialog
import requests
from bs4 import BeautifulSoup
import re
import json
import os
import threading
from urllib.parse import urlparse

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
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
            response = requests.get(url, headers=headers)
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
            astro_island = soup.find('astro-island', {'component-url': re.compile(r'ImageList')})
            if not astro_island:
                self.status_label.config(text="Status: Error - Could not find image list.")
                self.download_button.config(state="normal")
                return

            props_str = astro_island.get('props', '{}')
            props_json = json.loads(props_str.replace('&quot;', '"'))
            image_files_str = props_json.get('imageFiles', [0, '[]'])[1]
            image_urls = [img[1] for img in json.loads(image_files_str)]

            if not image_urls:
                self.status_label.config(text="Status: Error - No images found on the page.")
                self.download_button.config(state="normal")
                return

            # --- Download Images ---
            total_images = len(image_urls)
            self.progress["maximum"] = total_images
            for i, img_url in enumerate(image_urls):
                try:
                    img_response = requests.get(img_url, headers=headers)
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

            self.status_label.config(text=f"Status: Download complete! Saved to {download_dir}")

        except requests.RequestException as e:
            self.status_label.config(text=f"Status: Error - Failed to fetch URL: {e}")
        except Exception as e:
            self.status_label.config(text=f"Status: Error - An unexpected error occurred: {e}")

        self.download_button.config(state="normal")

if __name__ == "__main__":
    app = MangaDownloader()
    app.mainloop()

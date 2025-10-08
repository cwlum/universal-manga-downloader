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
from services import BatoService


class MangaDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Universal Manga Downloader")
        self.geometry("900x650")
        self.minsize(820, 600)

        self.bato_service = BatoService()
        self.search_results = []
        self.series_data = None
        self.series_chapters = []

        self._build_ui()

    def _build_ui(self):
        self.configure(padx=10, pady=10)

        # --- Search Section ---
        search_frame = ttk.LabelFrame(self, text="Search Manga")
        search_frame.pack(fill="both", expand=False, pady=(0, 10))

        search_entry_frame = ttk.Frame(search_frame)
        search_entry_frame.pack(fill="x", padx=10, pady=5)

        self.search_entry = ttk.Entry(search_entry_frame)
        self.search_entry.pack(side="left", fill="x", expand=True)

        self.search_button = ttk.Button(search_entry_frame, text="Search", command=self.start_search_thread)
        self.search_button.pack(side="left", padx=(5, 0))

        results_frame = ttk.Frame(search_frame)
        results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.search_results_listbox = tk.Listbox(results_frame, height=6)
        self.search_results_listbox.pack(side="left", fill="both", expand=True)

        search_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.search_results_listbox.yview)
        search_scrollbar.pack(side="right", fill="y")
        self.search_results_listbox.configure(yscrollcommand=search_scrollbar.set)

        self.search_results_listbox.bind("<<ListboxSelect>>", self.on_search_select)
        self.search_results_listbox.bind("<Double-1>", self.on_search_double_click)

        # --- Series Section ---
        series_frame = ttk.LabelFrame(self, text="Series Details")
        series_frame.pack(fill="both", expand=True)

        controls_frame = ttk.Frame(series_frame)
        controls_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(controls_frame, text="Series URL:").pack(side="left")
        self.series_url_var = tk.StringVar()
        self.series_url_entry = ttk.Entry(controls_frame, textvariable=self.series_url_var)
        self.series_url_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.load_series_button = ttk.Button(controls_frame, text="Load Series", command=self.start_series_info_thread)
        self.load_series_button.pack(side="left")

        self.series_title_var = tk.StringVar(value="Series title will appear here")
        ttk.Label(series_frame, textvariable=self.series_title_var, font=("TkDefaultFont", 12, "bold")).pack(anchor="w", padx=10)

        info_and_chapters_frame = ttk.Frame(series_frame)
        info_and_chapters_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        info_frame = ttk.Frame(info_and_chapters_frame)
        info_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(info_frame, text="Summary & Info:").pack(anchor="w")

        info_text_container = ttk.Frame(info_frame)
        info_text_container.pack(fill="both", expand=True)

        self.series_info_text = tk.Text(info_text_container, height=12, wrap="word", state="disabled")
        self.series_info_text.pack(side="left", fill="both", expand=True)

        info_scrollbar = ttk.Scrollbar(info_text_container, orient="vertical", command=self.series_info_text.yview)
        info_scrollbar.pack(side="right", fill="y")
        self.series_info_text.configure(yscrollcommand=info_scrollbar.set)

        chapters_frame = ttk.Frame(info_and_chapters_frame)
        chapters_frame.pack(side="left", fill="both", expand=False, padx=(10, 0))

        ttk.Label(chapters_frame, text="Chapters:").pack(anchor="w")

        chapters_list_container = ttk.Frame(chapters_frame)
        chapters_list_container.pack(fill="both", expand=True)

        self.chapters_listbox = tk.Listbox(chapters_list_container, height=12)
        self.chapters_listbox.pack(side="left", fill="both", expand=True)

        chapters_scrollbar = ttk.Scrollbar(chapters_list_container, orient="vertical", command=self.chapters_listbox.yview)
        chapters_scrollbar.pack(side="right", fill="y")
        self.chapters_listbox.configure(yscrollcommand=chapters_scrollbar.set)

        self.chapters_listbox.bind("<<ListboxSelect>>", self.on_chapter_select)
        self.chapters_listbox.bind("<Double-1>", self.on_chapter_double_click)

        ttk.Button(chapters_frame, text="Download Selected", command=self.download_selected_chapter).pack(fill="x", pady=(5, 0))

        # --- Download Section ---
        download_frame = ttk.LabelFrame(self, text="Chapter Download")
        download_frame.pack(fill="x", pady=(10, 0))

        download_entry_frame = ttk.Frame(download_frame)
        download_entry_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(download_entry_frame, text="Chapter URL:").pack(side="left")
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(download_entry_frame, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.download_button = ttk.Button(download_entry_frame, text="Download", command=self.start_download_thread)
        self.download_button.pack(side="left")

        progress_frame = ttk.Frame(download_frame)
        progress_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x")

        self.status_label = ttk.Label(download_frame, text="Status: Ready")
        self.status_label.pack(anchor="w", padx=10, pady=(0, 10))

    # --- Search Handlers ---
    def start_search_thread(self):
        query = self.search_entry.get().strip()
        if not query:
            self.status_label.config(text="Status: Enter a search query.")
            return

        self.search_button.config(state="disabled")
        self.status_label.config(text=f'Status: Searching for "{query}"...')
        thread = threading.Thread(target=self._perform_search, args=(query,), daemon=True)
        thread.start()

    def _perform_search(self, query):
        try:
            results = self.bato_service.search_manga(query)
        except requests.RequestException as exc:
            message = f"Status: Search failed - {exc}"
            self.after(0, lambda: self._on_search_failure(message))
        except Exception as exc:
            self.after(0, lambda: self._on_search_failure(f"Status: Search error - {exc}"))
        else:
            self.after(0, lambda: self._on_search_success(results, query))

    def _on_search_success(self, results, query):
        self.search_results = results
        self.search_results_listbox.delete(0, tk.END)
        for result in results:
            title = result.get("title", "Unknown")
            subtitle = result.get("subtitle")
            display = f"{title} — {subtitle}" if subtitle else title
            self.search_results_listbox.insert(tk.END, display)

        if results:
            self.status_label.config(text=f'Status: Found {len(results)} result(s) for "{query}".')
        else:
            self.status_label.config(text=f'Status: No results for "{query}".')

        self.search_button.config(state="normal")

    def _on_search_failure(self, message):
        self.search_button.config(state="normal")
        self.status_label.config(text=message)

    def on_search_select(self, event):
        selection = event.widget.curselection()
        if not selection:
            return
        index = selection[0]
        if 0 <= index < len(self.search_results):
            series_url = self.search_results[index].get("url", "")
            if series_url:
                self.series_url_var.set(series_url)

    def on_search_double_click(self, event):
        self.on_search_select(event)
        self.start_series_info_thread()

    def _get_selected_search_url(self):
        selection = self.search_results_listbox.curselection()
        if not selection:
            return ""
        index = selection[0]
        if 0 <= index < len(self.search_results):
            return self.search_results[index].get("url", "")
        return ""

    # --- Series Handlers ---
    def start_series_info_thread(self):
        series_url = self.series_url_var.get().strip()
        if not series_url:
            series_url = self._get_selected_search_url()
            if not series_url:
                self.status_label.config(text="Status: Select a series or paste its URL.")
                return
            self.series_url_var.set(series_url)

        self.load_series_button.config(state="disabled")
        self.status_label.config(text="Status: Fetching series info...")
        thread = threading.Thread(target=self._perform_series_fetch, args=(series_url,), daemon=True)
        thread.start()

    def _perform_series_fetch(self, series_url):
        try:
            data = self.bato_service.get_series_info(series_url)
        except requests.RequestException as exc:
            message = f"Status: Failed to fetch series info - {exc}"
            self.after(0, lambda: self._on_series_failure(message))
        except Exception as exc:
            self.after(0, lambda: self._on_series_failure(f"Status: Series parsing error - {exc}"))
        else:
            self.after(0, lambda: self._on_series_success(data))

    def _on_series_success(self, data):
        self.series_data = data
        self.series_chapters = data.get("chapters", []) or []

        title = data.get("title") or "Unknown Title"
        self.series_title_var.set(title)

        info_lines = []
        description = data.get("description")
        if description:
            info_lines.append(description)

        attributes = data.get("attributes") or {}
        for label, value in attributes.items():
            if isinstance(value, (list, tuple, set)):
                value_text = ", ".join(str(item) for item in value)
            else:
                value_text = str(value)
            info_lines.append(f"{label}: {value_text}")

        info_content = "\n\n".join(info_lines) if info_lines else "No additional information available."
        self._update_text_widget(self.series_info_text, info_content)

        self.chapters_listbox.delete(0, tk.END)
        for idx, chapter in enumerate(self.series_chapters, start=1):
            chapter_title = chapter.get("title") or chapter.get("label") or f"Chapter {idx}"
            self.chapters_listbox.insert(tk.END, f"{idx:03d} • {chapter_title}")

        if self.series_chapters:
            first_url = self.series_chapters[0].get("url", "")
            if first_url:
                self.url_var.set(first_url)

        self.status_label.config(text=f"Status: Loaded {len(self.series_chapters)} chapter(s).")
        self.load_series_button.config(state="normal")

    def _on_series_failure(self, message):
        self.load_series_button.config(state="normal")
        self.status_label.config(text=message)

    def _update_text_widget(self, widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state="disabled")

    def on_chapter_select(self, event):
        selection = event.widget.curselection()
        if not selection:
            return
        index = selection[0]
        if 0 <= index < len(self.series_chapters):
            chapter = self.series_chapters[index]
            chapter_url = chapter.get("url", "")
            if chapter_url:
                self.url_var.set(chapter_url)
            chapter_title = chapter.get("title") or chapter.get("label") or f"Chapter {index + 1}"
            self.status_label.config(text=f"Status: Selected {chapter_title}")

    def on_chapter_double_click(self, event):
        self.download_selected_chapter()

    def download_selected_chapter(self):
        selection = self.chapters_listbox.curselection()
        if not selection:
            self.status_label.config(text="Status: Select a chapter to download.")
            return
        index = selection[0]
        if 0 <= index < len(self.series_chapters):
            chapter = self.series_chapters[index]
            chapter_url = chapter.get("url", "")
            if chapter_url:
                self.url_var.set(chapter_url)
            self.start_download_thread()

    # --- Download Handlers ---
    def start_download_thread(self):
        url = self.url_var.get().strip()
        if not url:
            self.status_label.config(text="Status: Error - URL is empty")
            return

        self.download_button.config(state="disabled")
        self.status_label.config(text="Status: Starting download...")
        self.progress["value"] = 0
        thread = threading.Thread(target=self.download_manga, args=(url,), daemon=True)
        thread.start()

    def download_manga(self, url):
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

import tkinter as tk
from tkinter import ttk, filedialog
import subprocess
import sys
import os
import threading
import re
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        self.queue_lock = threading.Lock()
        self.chapter_executor_lock = threading.Lock()
        self.pending_downloads = 0
        self.active_downloads = 0
        self.chapter_executor = None
        self._chapter_executor_workers = None

        self.chapter_workers_var = tk.IntVar(value=1)
        self.image_workers_var = tk.IntVar(value=4)
        self.range_start_var = tk.StringVar()
        self.range_end_var = tk.StringVar()
        self.queue_status_var = tk.StringVar(value="Queue: idle")
        self.download_dir_var = tk.StringVar(value=self._get_default_download_root())
        self.download_dir_path = self.download_dir_var.get()
        self.download_dir_var.trace_add("write", self._on_download_dir_var_write)
        self._chapter_workers_value = self._clamp_value(self.chapter_workers_var.get(), 1, 10, 1)
        self.chapter_workers_var.set(self._chapter_workers_value)
        self._image_workers_value = self._clamp_value(self.image_workers_var.get(), 1, 32, 4)
        self.image_workers_var.set(self._image_workers_value)
        self.total_downloads = 0
        self.completed_downloads = 0

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._ensure_chapter_executor(force_reset=True)
        self._update_queue_status()
        self._update_queue_progress()

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

        self.chapters_listbox = tk.Listbox(chapters_list_container, height=12, selectmode="extended")
        self.chapters_listbox.pack(side="left", fill="both", expand=True)

        chapters_scrollbar = ttk.Scrollbar(chapters_list_container, orient="vertical", command=self.chapters_listbox.yview)
        chapters_scrollbar.pack(side="right", fill="y")
        self.chapters_listbox.configure(yscrollcommand=chapters_scrollbar.set)

        self.chapters_listbox.bind("<<ListboxSelect>>", self.on_chapter_select)
        self.chapters_listbox.bind("<Double-1>", self.on_chapter_double_click)

        range_frame = ttk.Frame(chapters_frame)
        range_frame.pack(fill="x", pady=(5, 0))
        ttk.Label(range_frame, text="Range:").pack(side="left")
        range_start_entry = ttk.Entry(range_frame, width=5, textvariable=self.range_start_var)
        range_start_entry.pack(side="left", padx=(5, 2))
        ttk.Label(range_frame, text="to").pack(side="left")
        range_end_entry = ttk.Entry(range_frame, width=5, textvariable=self.range_end_var)
        range_end_entry.pack(side="left", padx=(2, 5))

        ttk.Button(chapters_frame, text="Download Selected", command=self.download_selected_chapter).pack(fill="x", pady=(5, 0))
        ttk.Button(chapters_frame, text="Download Range", command=self.download_range).pack(fill="x", pady=(2, 0))
        ttk.Button(chapters_frame, text="Download All", command=self.download_all_chapters).pack(fill="x", pady=(2, 0))

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

        directory_frame = ttk.Frame(download_frame)
        directory_frame.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Label(directory_frame, text="Save to:").pack(side="left")
        self.download_dir_entry = ttk.Entry(directory_frame, textvariable=self.download_dir_var)
        self.download_dir_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        ttk.Button(directory_frame, text="Browse…", command=self._browse_download_dir).pack(side="left")

        concurrency_frame = ttk.Frame(download_frame)
        concurrency_frame.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Label(concurrency_frame, text="Chapter workers:").pack(side="left")
        self.chapter_workers_spinbox = ttk.Spinbox(
            concurrency_frame,
            from_=1,
            to=10,
            width=4,
            textvariable=self.chapter_workers_var,
            command=self._on_chapter_workers_change,
        )
        self.chapter_workers_spinbox.pack(side="left", padx=(5, 15))
        self.chapter_workers_spinbox.bind("<FocusOut>", self._on_chapter_workers_change)

        ttk.Label(concurrency_frame, text="Image workers:").pack(side="left")
        self.image_workers_spinbox = ttk.Spinbox(
            concurrency_frame,
            from_=1,
            to=32,
            width=4,
            textvariable=self.image_workers_var,
            command=self._on_image_workers_change,
        )
        self.image_workers_spinbox.pack(side="left", padx=(5, 0))
        self.image_workers_spinbox.bind("<FocusOut>", self._on_image_workers_change)

        progress_frame = ttk.Frame(download_frame)
        progress_frame.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Label(progress_frame, text="Image progress:").pack(anchor="w")
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x")

        queue_progress_frame = ttk.Frame(download_frame)
        queue_progress_frame.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Label(queue_progress_frame, text="Queue progress:").pack(anchor="w")
        self.queue_progress = ttk.Progressbar(queue_progress_frame, orient="horizontal", mode="determinate")
        self.queue_progress.pack(fill="x")

        self.queue_label = ttk.Label(download_frame, textvariable=self.queue_status_var)
        self.queue_label.pack(anchor="w", padx=10, pady=(0, 5))

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
            self.range_start_var.set(str(index + 1))
            self.range_end_var.set(str(index + 1))

    def on_chapter_double_click(self, event):
        self.download_selected_chapter()

    def download_selected_chapter(self):
        selection = self.chapters_listbox.curselection()
        if not selection:
            self._set_status("Status: Select one or more chapters to download.")
            return
        indices = sorted({idx for idx in selection if 0 <= idx < len(self.series_chapters)})
        chapter_items = []
        for index in indices:
            chapter = self.series_chapters[index]
            chapter_url = chapter.get("url", "")
            if not chapter_url:
                continue
            label = self._format_chapter_label(index, chapter)
            chapter_items.append((chapter_url, label))

        if not chapter_items:
            self._set_status("Status: Selected chapters are missing download URLs.")
            return

        self.url_var.set(chapter_items[0][0])
        self._enqueue_chapter_downloads(chapter_items)

    def download_range(self):
        if not self.series_chapters:
            self._set_status("Status: Load a series before downloading a range.")
            return

        try:
            start = int(self.range_start_var.get())
            end = int(self.range_end_var.get())
        except (TypeError, ValueError):
            self._set_status("Status: Invalid range. Use numeric values like 1 and 5.")
            return

        if start <= 0 or end <= 0:
            self._set_status("Status: Range values must be positive integers.")
            return

        if start > end:
            start, end = end, start

        max_index = len(self.series_chapters)
        start_index = max(1, start)
        end_index = min(max_index, end)
        if start_index > end_index:
            self._set_status("Status: Range does not match any chapters.")
            return

        chapter_items = []
        for idx in range(start_index - 1, end_index):
            chapter = self.series_chapters[idx]
            chapter_url = chapter.get("url", "")
            if not chapter_url:
                continue
            label = self._format_chapter_label(idx, chapter)
            chapter_items.append((chapter_url, label))

        if not chapter_items:
            self._set_status("Status: No downloadable chapters in the requested range.")
            return

        self.url_var.set(chapter_items[0][0])
        self._enqueue_chapter_downloads(chapter_items)

    def download_all_chapters(self):
        if not self.series_chapters:
            self._set_status("Status: No chapters available to download.")
            return

        chapter_items = []
        for idx, chapter in enumerate(self.series_chapters):
            chapter_url = chapter.get("url", "")
            if not chapter_url:
                continue
            label = self._format_chapter_label(idx, chapter)
            chapter_items.append((chapter_url, label))

        if not chapter_items:
            self._set_status("Status: Unable to queue downloads because no chapter URLs were found.")
            return

        self.url_var.set(chapter_items[0][0])
        self._enqueue_chapter_downloads(chapter_items)

    # --- Download Handlers ---
    def start_download_thread(self):
        url = self.url_var.get().strip()
        if not url:
            self._set_status("Status: Error - URL is empty")
            return

        self._enqueue_chapter_downloads([(url, None)])

    def _enqueue_chapter_downloads(self, chapter_items):
        queued = 0
        for url, label in chapter_items:
            if not url:
                continue
            self._submit_download_task(url, label)
            queued += 1

        if queued:
            label = "chapter" if queued == 1 else "chapters"
            self._set_status(f"Status: Queued {queued} {label} for download.")
        else:
            self._set_status("Status: No chapters were queued for download.")

    def _submit_download_task(self, url, initial_label):
        self._ensure_chapter_executor()
        with self.queue_lock:
            self.pending_downloads += 1
            self.total_downloads += 1
        self._update_queue_status()
        self._update_queue_progress()
        future = self.chapter_executor.submit(self._download_chapter_worker, url, initial_label)
        future.add_done_callback(self._on_download_task_done)

    def _ensure_chapter_executor(self, force_reset=False):
        desired_workers = self._clamp_value(self._chapter_workers_value, 1, 10, 1)
        if desired_workers != self._chapter_workers_value:
            self._chapter_workers_value = desired_workers
            self.chapter_workers_var.set(desired_workers)
        with self.chapter_executor_lock:
            if (
                force_reset
                or self.chapter_executor is None
                or self._chapter_executor_workers != desired_workers
            ):
                if self.chapter_executor is not None:
                    self.chapter_executor.shutdown(wait=False)
                self.chapter_executor = ThreadPoolExecutor(
                    max_workers=desired_workers,
                    thread_name_prefix="chapter-download",
                )
                self._chapter_executor_workers = desired_workers

    def _on_chapter_workers_change(self, event=None):
        value = self._clamp_value(self.chapter_workers_var.get(), 1, 10, self._chapter_workers_value or 1)
        if value != self.chapter_workers_var.get():
            self.chapter_workers_var.set(value)
        if value != self._chapter_workers_value or event is None:
            self._chapter_workers_value = value
            self._ensure_chapter_executor(force_reset=True)

    def _on_image_workers_change(self, event=None):
        value = self._clamp_value(self.image_workers_var.get(), 1, 32, self._image_workers_value or 4)
        if value != self.image_workers_var.get():
            self.image_workers_var.set(value)
        if value != self._image_workers_value or event is None:
            self._image_workers_value = value

    def _on_download_start(self, label):
        nice_label = label or "chapter"
        with self.queue_lock:
            if self.pending_downloads > 0:
                self.pending_downloads -= 1
            self.active_downloads += 1
        self._update_queue_status()
        self._update_queue_progress()
        self._set_status(f"Status: Downloading {nice_label}...")
        self._set_progress(maximum=1, value=0)

    def _on_download_end(self, label):
        with self.queue_lock:
            if self.active_downloads > 0:
                self.active_downloads -= 1
            if self.total_downloads > 0:
                self.completed_downloads = min(self.completed_downloads + 1, self.total_downloads)
            active = self.active_downloads
            pending = self.pending_downloads
            done_all = active == 0 and pending == 0
        self._update_queue_status()
        self._update_queue_progress()
        if done_all:
            with self.queue_lock:
                if self.active_downloads == 0 and self.pending_downloads == 0:
                    self.total_downloads = 0
                    self.completed_downloads = 0
            self._update_queue_progress()
            self._set_progress(maximum=1, value=0)
            self._set_status("Status: Ready")

    def _update_queue_status(self):
        with self.queue_lock:
            active = self.active_downloads
            pending = self.pending_downloads

        queue_text = f"Queue • Active: {active} | Pending: {pending}"
        self.after(0, lambda: self.queue_status_var.set(queue_text))

    def _update_queue_progress(self):
        with self.queue_lock:
            total = self.total_downloads
            completed = min(self.completed_downloads, total)

        def update():
            if total > 0:
                self.queue_progress["maximum"] = max(1, total)
                self.queue_progress["value"] = completed
            else:
                self.queue_progress["maximum"] = 1
                self.queue_progress["value"] = 0

        self.after(0, update)

    def _set_status(self, message):
        self.after(0, lambda: self.status_label.config(text=message))

    def _set_progress(self, maximum=None, value=None):
        def update():
            if maximum is not None:
                max_value = max(1, maximum)
                self.progress["maximum"] = max_value
                if value is None and self.progress["value"] > max_value:
                    self.progress["value"] = max_value
            if value is not None:
                self.progress["value"] = min(self.progress["maximum"], value)

        self.after(0, update)

    def _clamp_value(self, value, minimum, maximum, default):
        try:
            int_value = int(value)
        except (TypeError, ValueError, tk.TclError):
            int_value = default
        if minimum is not None:
            int_value = max(minimum, int_value)
        if maximum is not None:
            int_value = min(maximum, int_value)
        return int_value

    def _browse_download_dir(self):
        initial_dir = self.download_dir_path or self._get_default_download_root()
        directory = filedialog.askdirectory(initialdir=initial_dir)
        if directory:
            self.download_dir_var.set(directory)

    def _on_download_dir_var_write(self, *_):
        value = self.download_dir_var.get()
        self.download_dir_path = value.strip() if isinstance(value, str) else ""

    def _resolve_download_base_dir(self):
        base = self.download_dir_path or self._get_default_download_root()
        base = os.path.abspath(os.path.expanduser(base))
        try:
            os.makedirs(base, exist_ok=True)
        except OSError as exc:
            self._set_status(f"Status: Error - Cannot access download directory: {exc}")
            return None
        return base

    def _get_default_download_root(self):
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.isdir(downloads):
            return downloads
        return os.path.expanduser("~")

    def _format_chapter_label(self, index, chapter):
        chapter_title = chapter.get("title") or chapter.get("label") or f"Chapter {index + 1}"
        return f"{index + 1:03d} • {chapter_title}"

    def _download_chapter_worker(self, url, initial_label):
        display_label = initial_label or url
        self._on_download_start(display_label)
        scraper = cloudscraper.create_scraper()
        chapter_display = display_label
        try:
            self._set_status(f"Status: Fetching {display_label}...")
            response = scraper.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            parsed_data = None
            for parser in ALL_PARSERS:
                self._set_status(f"Status: {display_label} • trying parser {parser.get_name()}...")
                if parser.can_parse(soup, url):
                    parsed_data = parser.parse(soup, url)
                    if parsed_data:
                        break

            if not parsed_data:
                self._set_status("Status: Error - No suitable parser found for this URL.")
                return

            title = parsed_data["title"]
            chapter = parsed_data["chapter"]
            chapter_display = f"{title} — {chapter}"
            image_urls = parsed_data["image_urls"]

            base_dir = self._resolve_download_base_dir()
            if not base_dir:
                return
            download_dir = os.path.join(base_dir, f"{title}_{chapter}")
            os.makedirs(download_dir, exist_ok=True)

            failed_downloads = self._download_images_concurrently(
                scraper, image_urls, download_dir, chapter_display
            )

            if failed_downloads and len(failed_downloads) == len(image_urls):
                self._set_status(f"Status: Failed to download images for {chapter_display}.")
                return

            self._create_pdf(download_dir, title, chapter, chapter_display)
            if failed_downloads:
                self._set_status(
                    f"Status: Completed {chapter_display} with {len(failed_downloads)} failed image(s)."
                )
            else:
                self._set_status(f"Status: Completed {chapter_display}.")
        except requests.RequestException as exc:
            self._set_status(f"Status: Error - Failed to fetch {display_label}: {exc}")
            raise
        except Exception as exc:
            self._set_status(f"Status: Error - Download failed for {chapter_display}: {exc}")
            raise
        finally:
            self._on_download_end(display_label)

    def _download_images_concurrently(self, scraper, image_urls, download_dir, chapter_display):
        total_images = len(image_urls)
        if total_images == 0:
            self._set_status(f"Status: {chapter_display} • No images found to download.")
            self._set_progress(maximum=1, value=0)
            return []

        workers = self._clamp_value(self._image_workers_value or 4, 1, 32, 4)
        self._set_progress(maximum=total_images, value=0)
        self._set_status(f"Status: {chapter_display} • Downloading images...")

        failed = []
        progress_lock = threading.Lock()
        completed = 0

        def fetch_image(index, img_url):
            try:
                img_response = scraper.get(img_url, timeout=30)
                img_response.raise_for_status()
                file_ext = self._determine_file_extension(img_url, img_response)
                file_path = os.path.join(download_dir, f"{index + 1:03d}{file_ext}")
                with open(file_path, "wb") as f:
                    f.write(img_response.content)
                return index, True, None
            except Exception as exc:  # noqa: BLE001
                print(f"Failed to download {img_url}: {exc}")
                return index, False, img_url

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="image-download") as executor:
            futures = [
                executor.submit(fetch_image, index, img_url) for index, img_url in enumerate(image_urls)
            ]
            for future in as_completed(futures):
                index, success, error_url = future.result()
                with progress_lock:
                    completed += 1
                    current_completed = completed
                self._set_progress(value=current_completed)
                self._set_status(
                    f"Status: {chapter_display} • {current_completed}/{total_images} image(s) downloaded"
                )
                if not success and error_url:
                    failed.append(error_url)

        return failed

    def _determine_file_extension(self, img_url, response):
        parsed_url = urlparse(img_url)
        _, file_ext = os.path.splitext(os.path.basename(parsed_url.path))
        if not file_ext:
            content_type = response.headers.get("content-type")
            ext_match = re.search(r"image/(\w+)", content_type) if content_type else None
            file_ext = f".{ext_match.group(1)}" if ext_match else ".jpg"
        return file_ext

    def _create_pdf(self, download_dir, title, chapter, chapter_display):
        supported_formats = ("png", "jpg", "jpeg", "gif", "bmp", "webp")
        image_files = sorted(
            [
                os.path.join(download_dir, f)
                for f in os.listdir(download_dir)
                if f.lower().endswith(supported_formats)
            ]
        )

        if not image_files:
            self._set_status(f"Status: {chapter_display} • No images found to create PDF.")
            return

        pdf_path = os.path.join(download_dir, f"{title}_{chapter}.pdf")
        images = []
        try:
            for path in image_files:
                images.append(Image.open(path).convert("RGB"))
            if images:
                primary, *rest = images
                primary.save(
                    pdf_path,
                    "PDF",
                    resolution=100.0,
                    save_all=True,
                    append_images=rest,
                )
                self._set_status(f"Status: {chapter_display} • PDF saved to {pdf_path}")
        finally:
            for image in images:
                image.close()

    def _on_download_task_done(self, future):
        try:
            future.result()
        except Exception as exc:  # noqa: BLE001
            print(f"Download task failed: {exc}")

    def on_close(self):
        with self.chapter_executor_lock:
            if self.chapter_executor is not None:
                self.chapter_executor.shutdown(wait=False)
                self.chapter_executor = None
        self.destroy()

if __name__ == "__main__":
    app = MangaDownloader()
    app.mainloop()

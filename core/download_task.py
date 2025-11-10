"""Encapsulated chapter download workflow with UI callback hooks."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import cloudscraper
import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from config import CONFIG
from core.queue_manager import QueueState
from plugins.base import ChapterMetadata, ParsedChapter, PluginManager, compose_chapter_name
from utils.file_utils import (
    check_disk_space_sufficient,
    collect_image_files,
    determine_file_extension,
    ensure_directory,
    estimate_chapter_size,
)
from utils.http_client import ScraperPool

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DownloadUIHooks:
    """Callable hooks used to push download progress back to the UI layer."""

    on_start: Callable[[str | None, int], None]
    on_end: Callable[[str | None, int], None]
    queue_set_status: Callable[[int, str, QueueState | None], None]
    queue_mark_finished: Callable[[int, bool, str | None], None]
    queue_update_title: Callable[[int, str], None]
    queue_reset_progress: Callable[[int, int], None]
    queue_update_progress: Callable[[int, int, int | None], None]
    set_status: Callable[[str], None]


class DownloadTask:
    """Execute a chapter download, emitting updates through ``DownloadUIHooks``."""

    def __init__(
        self,
        queue_id: int,
        url: str,
        initial_label: str | None,
        *,
        plugin_manager: PluginManager,
        scraper_pool: ScraperPool,
        image_semaphore: threading.Semaphore,
        image_worker_count: int,
        resolve_download_dir: Callable[[], str | None],
        ui_hooks: DownloadUIHooks,
    ) -> None:
        self.queue_id = queue_id
        self.url = url
        self.initial_label = initial_label
        self.plugin_manager = plugin_manager
        self.scraper_pool = scraper_pool
        self.image_semaphore = image_semaphore
        self.image_worker_count = max(1, image_worker_count)
        self.resolve_download_dir = resolve_download_dir
        self.ui = ui_hooks

    def run(self) -> None:
        """Execute the download workflow."""

        display_label = self.initial_label or self.url
        self.ui.on_start(display_label, self.queue_id)
        chapter_display = display_label

        try:
            with self.scraper_pool.session() as scraper:
                soup = self._fetch_chapter_page(scraper, display_label)
                if soup is None:
                    return

                parsed_chapter = self._parse_chapter(soup, chapter_display)
                if not parsed_chapter:
                    return

                title = parsed_chapter["title"]
                chapter = parsed_chapter["chapter"]
                chapter_display = f"{title} — {chapter}"
                self.ui.queue_update_title(self.queue_id, chapter_display)
                self.ui.queue_set_status(self.queue_id, "Preparing download…", QueueState.RUNNING)

                image_urls = parsed_chapter["image_urls"]
                if not image_urls:
                    self._mark_failure(
                        "No images found.",
                        chapter_display,
                        status_message=f"Status: {chapter_display} • No images found to download.",
                    )
                    return

                download_dir = self._prepare_download_dir(title, chapter)
                if not download_dir:
                    self._mark_failure(
                        "Unable to prepare download directory.",
                        chapter_display,
                        status_message="Status: Error - Cannot access download directory.",
                    )
                    return

                failed = self._download_images(
                    scraper,
                    image_urls,
                    download_dir,
                    chapter_display,
                )

                if failed and len(failed) == len(image_urls):
                    self._mark_failure(
                        "All image downloads failed.",
                        chapter_display,
                        status_message=f"Status: Failed to download images for {chapter_display}.",
                    )
                    return

                metadata: ChapterMetadata = {
                    "title": title,
                    "chapter": chapter,
                    "source_url": self.url,
                }
                conversions_ok = self._run_converters(download_dir, metadata, chapter_display)
                if not conversions_ok:
                    self._mark_failure("Conversion failed.", chapter_display)
                    return

                if failed:
                    failures = len(failed)
                    message = f"Completed with {failures} failed image(s)."
                    self.ui.queue_mark_finished(self.queue_id, True, message)
                    self.ui.set_status(
                        f"Status: Completed {chapter_display} with {failures} failed image(s)."
                    )
                else:
                    self.ui.queue_mark_finished(self.queue_id, True, "Completed")
                    self.ui.set_status(f"Status: Completed {chapter_display}.")
        except requests.RequestException as exc:
            self.ui.queue_mark_finished(self.queue_id, False, f"Network error: {exc}")
            self.ui.set_status(f"Status: Error - Failed to fetch {chapter_display}: {exc}")
            logger.exception("Network error while downloading %s", chapter_display)
            raise
        except Exception as exc:  # noqa: BLE001 - propagate unexpected failures
            self.ui.queue_mark_finished(self.queue_id, False, f"Error: {exc}")
            self.ui.set_status(f"Status: Error - Download failed for {chapter_display}: {exc}")
            logger.exception("Unhandled error while processing %s", chapter_display)
            raise
        finally:
            self.ui.on_end(display_label, self.queue_id)

    def _fetch_chapter_page(
        self,
        scraper: cloudscraper.CloudScraper,
        display_label: str,
    ) -> BeautifulSoup | None:
        self.ui.queue_set_status(self.queue_id, "Fetching chapter page…", QueueState.RUNNING)
        self.ui.set_status(f"Status: Fetching {display_label}...")

        max_retries = CONFIG.download.max_retries
        retry_delay = CONFIG.download.retry_delay

        for attempt in range(max_retries + 1):
            try:
                response = scraper.get(self.url, timeout=CONFIG.download.request_timeout)
                response.raise_for_status()
                return BeautifulSoup(response.text, "html.parser")
            except requests.RequestException as exc:
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(
                        "Retry %d/%d for chapter page after %.1fs: %s",
                        attempt + 1, max_retries, wait_time, exc
                    )
                    self.ui.queue_set_status(
                        self.queue_id,
                        f"Retrying ({attempt + 1}/{max_retries})…",
                        QueueState.RUNNING
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("Failed to fetch chapter page after %d attempts", max_retries + 1)
                    self._mark_failure(
                        f"Network error after {max_retries + 1} attempts: {exc}",
                        display_label,
                        status_message=f"Status: Failed to fetch {display_label} - {exc}"
                    )
                    raise

        return None

    def _parse_chapter(
        self,
        soup: BeautifulSoup,
        chapter_display: str,
    ) -> ParsedChapter | None:
        parser_plugins = list(self.plugin_manager.iter_enabled_parsers())
        if not parser_plugins:
            self._mark_failure(
                "No parser plugins enabled.",
                chapter_display,
                status_message="Status: Error - No parser plugins enabled.",
            )
            return None

        parsed_data: ParsedChapter | None = None
        for parser in parser_plugins:
            parser_name = parser.get_name()
            self.ui.queue_set_status(
                self.queue_id,
                f"Parsing with {parser_name}…",
                QueueState.RUNNING,
            )
            self.ui.set_status(
                f"Status: {chapter_display} • trying parser {parser_name}..."
            )
            if not parser.can_handle(self.url):
                continue
            parsed_result = parser.parse(soup, self.url)
            if parsed_result:
                parsed_data = parsed_result
                break

        if not parsed_data:
            self._mark_failure(
                "No suitable parser found.",
                chapter_display,
                status_message="Status: Error - No suitable parser found for this URL.",
            )
            return None

        return parsed_data

    def _prepare_download_dir(self, title: str, chapter: str) -> str | None:
        base_dir = self.resolve_download_dir()
        if not base_dir:
            return None
        folder_name = compose_chapter_name(title, chapter)
        download_candidate = os.path.join(base_dir, folder_name)
        return ensure_directory(download_candidate)

    def _download_images(
        self,
        scraper: cloudscraper.CloudScraper,
        image_urls: Sequence[str],
        download_dir: str,
        chapter_display: str,
    ) -> list[str]:
        total_images = len(image_urls)
        if total_images == 0:
            self._mark_failure(
                "No images found.",
                chapter_display,
                status_message=f"Status: {chapter_display} • No images found to download.",
            )
            return []

        # Check disk space before starting download
        estimated_size = estimate_chapter_size(total_images)
        is_sufficient, free_bytes, required_bytes = check_disk_space_sufficient(
            download_dir, estimated_size
        )

        if not is_sufficient and free_bytes >= 0:
            # Format sizes for user-friendly display
            free_mb = free_bytes / (1024 * 1024)
            required_mb = required_bytes / (1024 * 1024)
            logger.warning(
                "Insufficient disk space for %s: %.1f MB free, %.1f MB required",
                chapter_display,
                free_mb,
                required_mb,
            )
            self._mark_failure(
                f"Insufficient disk space: {free_mb:.1f} MB free, {required_mb:.1f} MB required.",
                chapter_display,
                status_message=f"Status: Not enough disk space for {chapter_display}.",
            )
            return []

        workers = min(self.image_worker_count, CONFIG.download.max_total_image_workers)
        self.ui.queue_reset_progress(self.queue_id, total_images)
        self.ui.queue_set_status(
            self.queue_id,
            f"Downloading images (0/{total_images})…",
            QueueState.RUNNING,
        )
        self.ui.set_status(f"Status: {chapter_display} • Downloading images...")

        failed: list[str] = []
        progress_lock = threading.Lock()
        completed = 0
        base_headers = dict(scraper.headers)
        if self.url:
            base_headers["Referer"] = self.url
        base_cookies = scraper.cookies.get_dict()
        request_timeout = CONFIG.download.request_timeout
        progress_interval = max(0.05, CONFIG.ui.progress_update_interval_ms / 1000)
        last_ui_update = 0.0

        def emit_progress(completed_count: int, *, force: bool = False) -> None:
            nonlocal last_ui_update
            now = time.monotonic()
            if not force and (now - last_ui_update) < progress_interval:
                return
            last_ui_update = now
            self.ui.queue_update_progress(self.queue_id, completed_count, None)
            self.ui.queue_set_status(
                self.queue_id,
                f"Downloading images ({completed_count}/{total_images})…",
                QueueState.RUNNING,
            )
            self.ui.set_status(
                f"Status: {chapter_display} • {completed_count}/{total_images} image(s) downloaded"
            )

        def fetch_image(index: int, img_url: str) -> tuple[int, bool, str | None]:
            self.image_semaphore.acquire()
            session = self.scraper_pool.acquire()

            max_retries = CONFIG.download.max_retries
            retry_delay = CONFIG.download.retry_delay

            try:
                last_error = None
                for attempt in range(max_retries + 1):
                    try:
                        with session.get(
                            img_url,
                            timeout=request_timeout,
                            stream=True,
                            headers=base_headers,
                            cookies=base_cookies,
                        ) as img_response:
                            img_response.raise_for_status()
                            file_ext = determine_file_extension(img_url, img_response)
                            file_path = os.path.join(download_dir, f"{index + 1:03d}{file_ext}")
                            with open(file_path, "wb") as file_handler:
                                for chunk in img_response.iter_content(chunk_size=65536):
                                    if not chunk:
                                        continue
                                    file_handler.write(chunk)
                        return index, True, None
                    except (requests.RequestException, OSError, IOError) as exc:
                        last_error = exc
                        if attempt < max_retries:
                            # Exponential backoff: 1s, 2s, 4s, ...
                            wait_time = retry_delay * (2 ** attempt)
                            logger.debug(
                                "Retry %d/%d for image %d after %.1fs: %s",
                                attempt + 1, max_retries, index + 1, wait_time, exc
                            )
                            time.sleep(wait_time)
                        else:
                            logger.warning(
                                "Failed to download image %d from %s after %d attempts: %s",
                                index + 1, img_url, max_retries + 1, exc
                            )

                # All retries exhausted
                return index, False, img_url
            except Exception as exc:  # noqa: BLE001 - protect thread from unexpected failures
                logger.exception("Unexpected error downloading image %d from %s", index + 1, img_url)
                return index, False, img_url
            finally:
                self.scraper_pool.release(session)
                self.image_semaphore.release()

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="image-download") as executor:
            futures = [
                executor.submit(fetch_image, index, img_url)
                for index, img_url in enumerate(image_urls)
            ]
            for future in as_completed(futures):
                _index, success, error_url = future.result()
                with progress_lock:
                    completed += 1
                    current_completed = completed
                emit_progress(current_completed, force=current_completed == total_images)
                if not success and error_url:
                    failed.append(error_url)

        if failed:
            self.ui.queue_set_status(
                self.queue_id,
                f"Images downloaded with {len(failed)} failure(s).",
                QueueState.RUNNING,
            )
        else:
            self.ui.queue_set_status(self.queue_id, "Images downloaded.", QueueState.RUNNING)

        return failed

    def _run_converters(
        self,
        download_dir: str,
        metadata: ChapterMetadata,
        chapter_display: str,
    ) -> bool:
        image_files = collect_image_files(download_dir)
        if not image_files:
            self.ui.set_status(f"Status: {chapter_display} • No images available for conversion.")
            return False

        converters = list(self.plugin_manager.iter_enabled_converters())
        if not converters:
            self.ui.queue_set_status(
                self.queue_id,
                "Images downloaded (no converters enabled).",
                QueueState.RUNNING,
            )
            self.ui.set_status(f"Status: {chapter_display} • Skipped conversion (no converters enabled).")
            return True

        success = False
        output_dir = Path(download_dir)
        for converter in converters:
            converter_name = converter.get_name()
            self.ui.queue_set_status(
                self.queue_id,
                f"Converting with {converter_name}…",
                QueueState.RUNNING,
            )
            self.ui.set_status(f"Status: {chapter_display} • Converting with {converter_name}...")
            try:
                result_path = converter.convert(image_files, output_dir, metadata)
            except Exception as exc:  # noqa: BLE001 - plugin failure should be visible
                logger.exception("Converter %s failed", converter_name)
                self.ui.queue_set_status(
                    self.queue_id,
                    f"{converter_name} failed: {exc}",
                    QueueState.RUNNING,
                )
                continue

            if result_path is None:
                self.ui.queue_set_status(
                    self.queue_id,
                    f"{converter_name} produced no output.",
                    QueueState.RUNNING,
                )
                continue

            success = True
            self.ui.queue_set_status(
                self.queue_id,
                f"{converter_name} created {result_path.name}",
                QueueState.RUNNING,
            )
            self.ui.set_status(
                f"Status: {chapter_display} • {converter_name} created {result_path.name}"
            )

        return success

    def _mark_failure(
        self,
        message: str,
        chapter_display: str,
        *,
        status_message: str | None = None,
    ) -> None:
        self.ui.queue_mark_finished(self.queue_id, False, message)
        if status_message is not None:
            self.ui.set_status(status_message)
        else:
            self.ui.set_status(f"Status: {chapter_display} • {message}")


__all__ = ["DownloadTask", "DownloadUIHooks"]

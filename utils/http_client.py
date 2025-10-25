"""HTTP client utilities for managing reusable CloudScraper sessions."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from queue import Empty, Full, LifoQueue

import cloudscraper

logger = logging.getLogger(__name__)


class ScraperPool:
    """Bounded pool that hands out reusable ``cloudscraper`` sessions."""

    def __init__(self, max_size: int = 8) -> None:
        self._max_size = max_size if max_size > 0 else 0
        self._pool: LifoQueue[cloudscraper.CloudScraper] = LifoQueue(maxsize=self._max_size)
        self._created = 0
        self._lock = threading.Lock()
        self._closed = False

    def acquire(self) -> cloudscraper.CloudScraper:
        """Return a scraper instance, creating one if necessary."""

        if self._closed:
            raise RuntimeError("ScraperPool has been closed.")

        try:
            return self._pool.get_nowait()
        except Empty:
            return self._create_scraper()

    def release(self, scraper: cloudscraper.CloudScraper) -> None:
        """Return a scraper to the pool or close it when the pool is saturated."""

        if self._closed:
            self._close_scraper(scraper)
            return

        try:
            self._pool.put_nowait(scraper)
        except Full:
            self._close_scraper(scraper)

    @contextmanager
    def session(self) -> Iterator[cloudscraper.CloudScraper]:
        """Context manager that automatically releases the scraper back to the pool."""

        scraper = self.acquire()
        try:
            yield scraper
        finally:
            self.release(scraper)

    def close(self) -> None:
        """Close all pooled scrapers and prevent further acquisition."""

        if self._closed:
            return
        self._closed = True

        while True:
            try:
                scraper = self._pool.get_nowait()
            except Empty:
                break
            self._close_scraper(scraper)

    def _create_scraper(self) -> cloudscraper.CloudScraper:
        with self._lock:
            if self._max_size == 0 or self._created < self._max_size:
                self._created += 1
                return cloudscraper.create_scraper()

        # Pool is saturated; create an ad-hoc scraper that won't be retained.
        logger.debug("Scraper pool saturated; creating a transient scraper.")
        return cloudscraper.create_scraper()

    def _close_scraper(self, scraper: cloudscraper.CloudScraper) -> None:
        try:
            scraper.close()
        except Exception:  # noqa: BLE001 - closing failures are non-fatal
            logger.debug("Failed to close scraper cleanly", exc_info=True)


__all__ = ["ScraperPool"]

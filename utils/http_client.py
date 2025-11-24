"""HTTP client utilities for managing reusable CloudScraper sessions."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from queue import Empty, Full, LifoQueue

import cloudscraper

logger = logging.getLogger(__name__)


class ScraperPool:
    """Bounded pool that hands out reusable ``cloudscraper`` sessions.

    Features:
    - Bounded pool prevents resource exhaustion
    - Waits for available scrapers when pool is saturated
    - Thread-safe acquisition and release
    - Automatic cleanup on close
    """

    def __init__(self, max_size: int = 8, wait_timeout: float = 30.0) -> None:
        self._max_size = max_size if max_size > 0 else 0
        self._pool: LifoQueue[cloudscraper.CloudScraper] = LifoQueue(maxsize=self._max_size)
        self._created = 0
        self._lock = threading.Lock()
        self._closed = False
        self._wait_timeout = wait_timeout
        self._wait_count = 0  # Track how many threads are waiting

    def acquire(self, timeout: float | None = None) -> cloudscraper.CloudScraper:
        """Return a scraper instance, creating one or waiting if necessary.

        Args:
            timeout: Maximum time to wait for an available scraper (uses default if None)

        Returns:
            CloudScraper instance

        Raises:
            RuntimeError: If pool is closed or timeout expires
        """

        if self._closed:
            raise RuntimeError("ScraperPool has been closed.") from None

        wait_time = timeout if timeout is not None else self._wait_timeout

        # Try to get from pool immediately
        try:
            return self._pool.get_nowait()
        except Empty:
            pass

        # Try to create a new scraper if under limit
        scraper = self._try_create_scraper()
        if scraper is not None:
            return scraper

        # Pool is saturated - wait for one to become available
        logger.debug("Scraper pool saturated, waiting up to %.1fs for available scraper", wait_time)
        with self._lock:
            self._wait_count += 1

        try:
            start_time = time.time()
            while time.time() - start_time < wait_time:
                try:
                    # Try to get with short timeout to allow checking _closed
                    scraper = self._pool.get(timeout=0.5)
                    return scraper
                except Empty:
                    if self._closed:
                        raise RuntimeError("ScraperPool was closed while waiting") from None
                    continue

            # Timeout expired - create transient scraper as fallback
            logger.warning("Scraper pool wait timeout after %.1fs, creating transient scraper", wait_time)
            return cloudscraper.create_scraper()

        finally:
            with self._lock:
                self._wait_count -= 1

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

    def _try_create_scraper(self) -> cloudscraper.CloudScraper | None:
        """Attempt to create a new scraper if under the pool limit.

        Returns:
            New scraper if created, None if pool is at max capacity

        Raises:
            RuntimeError: If pool is closed
        """
        with self._lock:
            if self._closed:
                raise RuntimeError("ScraperPool has been closed.") from None
            if self._max_size == 0 or self._created < self._max_size:
                self._created += 1
                logger.debug("Creating scraper %d/%d", self._created, self._max_size)
                return cloudscraper.create_scraper()
        return None

    def get_stats(self) -> dict[str, int]:
        """Return pool statistics for monitoring.

        Returns:
            Dictionary with keys: created, max_size, waiting
        """
        with self._lock:
            return {
                "created": self._created,
                "max_size": self._max_size,
                "waiting": self._wait_count,
            }

    def _close_scraper(self, scraper: cloudscraper.CloudScraper) -> None:
        try:
            scraper.close()
        except Exception:  # noqa: BLE001 - closing failures are non-fatal
            logger.debug("Failed to close scraper cleanly", exc_info=True)


__all__ = ["ScraperPool"]

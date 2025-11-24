"""Rate limiting and circuit breaker utilities for external API calls."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimiter:
    """Token bucket rate limiter with thread-safe implementation."""

    def __init__(self, rate: float, capacity: int = 1) -> None:
        """
        Initialize rate limiter.

        Args:
            rate: Minimum seconds between requests (e.g., 0.5 = 2 req/sec)
            capacity: Burst capacity (number of tokens that can accumulate)
        """
        self._rate = max(0.001, rate)
        self._capacity = max(1, capacity)
        self._tokens = float(capacity)
        self._last_update = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, block: bool = True) -> bool:
        """
        Acquire permission to make a request.

        Args:
            block: If True, wait until a token is available. If False, return immediately.

        Returns:
            True if permission granted, False if block=False and no tokens available.
        """
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_update
                self._last_update = now

                # Refill tokens based on elapsed time
                self._tokens = min(self._capacity, self._tokens + elapsed / self._rate)

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True

                if not block:
                    return False

                # Calculate sleep time needed
                sleep_time = (1.0 - self._tokens) * self._rate

            # Sleep outside the lock to avoid blocking other threads
            if block and sleep_time > 0:
                logger.debug("Rate limiter: sleeping %.3fs", sleep_time)
                time.sleep(min(sleep_time, 1.0))  # Cap sleep at 1 second per iteration
            else:
                break

        return False


class CircuitState(str, Enum):
    """States for the circuit breaker pattern."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Too many failures, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 60.0  # Seconds to wait before trying half-open
    window_size: int = 10  # Number of recent calls to track


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and blocks a call."""


class CircuitBreaker:
    """Circuit breaker pattern implementation for fault tolerance."""

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._recent_calls: deque[bool] = deque(maxlen=self._config.window_size)
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception raised by func
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN (failed {self._failure_count} times)"
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self._recent_calls.append(True)

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info("Circuit breaker CLOSED after successful recovery")

    def _on_failure(self) -> None:
        """Handle failed call."""
        with self._lock:
            self._recent_calls.append(False)
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning("Circuit breaker reopened after failure in HALF_OPEN state")
            elif self._state == CircuitState.CLOSED:
                # Check if we've exceeded failure threshold
                recent_failures = sum(1 for success in self._recent_calls if not success)
                if recent_failures >= self._config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.error(
                        "Circuit breaker OPENED after %d failures in recent %d calls",
                        recent_failures,
                        len(self._recent_calls),
                    )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open state."""
        if self._last_failure_time is None:
            return True
        elapsed = time.monotonic() - self._last_failure_time
        return elapsed >= self._config.timeout

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._recent_calls.clear()
            logger.info("Circuit breaker manually reset to CLOSED")

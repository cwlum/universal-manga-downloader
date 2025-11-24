"""Edge case tests for error handling and validation."""

from __future__ import annotations

import pytest

from utils.rate_limit import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError, RateLimiter
from utils.validation import (
    ValidationError,
    sanitize_filename,
    sanitize_query_string,
    validate_directory_path,
    validate_manga_url,
    validate_url,
)


class TestURLValidation:
    """Test URL validation edge cases."""

    def test_validate_url_empty(self):
        """Test that empty URLs are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_url("")

        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_url("   ")

    def test_validate_url_allow_empty(self):
        """Test that empty URLs can be allowed."""
        assert validate_url("", allow_empty=True) == ""
        assert validate_url("   ", allow_empty=True) == ""

    def test_validate_url_invalid_scheme(self):
        """Test that non-http(s) schemes are rejected."""
        with pytest.raises(ValidationError, match="scheme"):
            validate_url("ftp://example.com")

        with pytest.raises(ValidationError, match="scheme"):
            validate_url("javascript:alert(1)")

    def test_validate_url_no_domain(self):
        """Test that URLs without domain are rejected."""
        with pytest.raises(ValidationError):
            validate_url("http://")

    def test_validate_url_valid(self):
        """Test that valid URLs are accepted."""
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://example.com/path") == "http://example.com/path"
        assert validate_url("  https://example.com  ") == "https://example.com"

    def test_validate_manga_url_bato(self):
        """Test Bato URL validation."""
        valid_urls = [
            "https://bato.to/series/123",
            "http://www.bato.to/series/123",
            "https://batoto.com/chapter/456",
        ]
        for url in valid_urls:
            assert validate_manga_url(url) == url

    def test_validate_manga_url_mangadex(self):
        """Test MangaDex URL validation."""
        valid_urls = [
            "https://mangadex.org/title/abc123",
            "http://www.mangadex.org/chapter/def456",
        ]
        for url in valid_urls:
            assert validate_manga_url(url) == url

    def test_validate_manga_url_unsupported(self):
        """Test that unsupported manga sites are rejected."""
        with pytest.raises(ValidationError, match="supported manga site"):
            validate_manga_url("https://unsupported-site.com/manga/123")

    def test_validate_manga_url_allow_unsupported(self):
        """Test that unsupported sites can be allowed."""
        url = "https://example.com/manga/123"
        assert validate_manga_url(url, require_supported=False) == url


class TestFilenameValidation:
    """Test filename sanitization edge cases."""

    def test_sanitize_filename_empty(self):
        """Test that empty filenames are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            sanitize_filename("")

        with pytest.raises(ValidationError, match="cannot be empty"):
            sanitize_filename("   ")

    def test_sanitize_filename_dangerous_chars(self):
        """Test that dangerous characters are removed."""
        # Validation's sanitize_filename replaces with underscores
        result = sanitize_filename('file<>:"|?*name')
        assert "_" in result
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_filename_path_traversal(self):
        """Test that path traversal attempts are sanitized."""
        result = sanitize_filename("../../../etc/passwd")
        # Should not contain ".." patterns
        assert ".." not in result
        assert "etc" in result or "passwd" in result

    def test_sanitize_filename_reserved_windows_names(self):
        """Test that Windows reserved names are handled."""
        assert sanitize_filename("CON") == "_CON"
        assert sanitize_filename("con.txt") == "_con.txt"
        assert sanitize_filename("PRN") == "_PRN"
        assert sanitize_filename("AUX") == "_AUX"
        assert sanitize_filename("NUL") == "_NUL"

    def test_sanitize_filename_max_length(self):
        """Test filename length truncation."""
        long_name = "a" * 300
        sanitized = sanitize_filename(long_name, max_length=255)
        assert len(sanitized) == 255

    def test_sanitize_filename_preserve_extension(self):
        """Test that file extensions are preserved when truncating."""
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name, max_length=255)
        assert sanitized.endswith(".txt")
        assert len(sanitized) == 255

    def test_sanitize_filename_valid(self):
        """Test that valid filenames pass through."""
        assert sanitize_filename("valid_filename.txt") == "valid_filename.txt"
        assert sanitize_filename("  spaces  ") == "spaces"


class TestDirectoryValidation:
    """Test directory path validation edge cases."""

    def test_validate_directory_empty(self):
        """Test that empty paths are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_directory_path("")

    def test_validate_directory_path_traversal(self):
        """Test that path traversal is detected."""
        with pytest.raises(ValidationError, match="traversal"):
            validate_directory_path("../../../etc")

        with pytest.raises(ValidationError, match="traversal"):
            validate_directory_path("path/../../../escape")

    def test_validate_directory_valid(self):
        """Test that valid paths are accepted."""
        assert validate_directory_path("/home/user/downloads") == "/home/user/downloads"
        assert validate_directory_path("  /path/to/dir  ") == "/path/to/dir"


class TestQueryValidation:
    """Test query string sanitization edge cases."""

    def test_sanitize_query_empty(self):
        """Test that empty queries are rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            sanitize_query_string("")

    def test_sanitize_query_control_chars(self):
        """Test that control characters are removed."""
        assert sanitize_query_string("query\x00\x1ftext") == "querytext"

    def test_sanitize_query_excessive_whitespace(self):
        """Test that excessive whitespace is normalized."""
        assert sanitize_query_string("query   with    spaces") == "query with spaces"
        assert sanitize_query_string("  query  ") == "query"

    def test_sanitize_query_max_length(self):
        """Test query length truncation."""
        long_query = "a" * 600
        sanitized = sanitize_query_string(long_query, max_length=500)
        assert len(sanitized) == 500

    def test_sanitize_query_valid(self):
        """Test that valid queries pass through."""
        assert sanitize_query_string("valid query") == "valid query"


class TestRateLimiter:
    """Test rate limiter edge cases."""

    def test_rate_limiter_single_request(self):
        """Test single request acquisition."""
        limiter = RateLimiter(rate=0.1, capacity=1)
        assert limiter.acquire(block=False) is True

    def test_rate_limiter_immediate_second_request(self):
        """Test that second immediate request fails when no tokens."""
        limiter = RateLimiter(rate=0.1, capacity=1)
        limiter.acquire(block=False)
        assert limiter.acquire(block=False) is False

    def test_rate_limiter_burst_capacity(self):
        """Test burst capacity allows multiple requests."""
        limiter = RateLimiter(rate=0.1, capacity=3)
        assert limiter.acquire(block=False) is True
        assert limiter.acquire(block=False) is True
        assert limiter.acquire(block=False) is True
        assert limiter.acquire(block=False) is False  # 4th should fail

    def test_rate_limiter_token_refill(self):
        """Test that tokens refill over time."""
        import time

        limiter = RateLimiter(rate=0.05, capacity=1)  # 0.05s = 50ms between requests
        limiter.acquire(block=False)
        time.sleep(0.06)  # Wait longer than rate
        assert limiter.acquire(block=False) is True


class TestCircuitBreaker:
    """Test circuit breaker edge cases."""

    def test_circuit_breaker_initial_state(self):
        """Test that circuit breaker starts closed."""
        from utils.rate_limit import CircuitState

        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_successful_calls(self):
        """Test that successful calls keep circuit closed."""
        breaker = CircuitBreaker()

        def success_func():
            return "success"

        for _ in range(10):
            result = breaker.call(success_func)
            assert result == "success"

        from utils.rate_limit import CircuitState

        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_opens_on_failures(self):
        """Test that circuit opens after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3, window_size=5)
        breaker = CircuitBreaker(config)

        def fail_func():
            raise RuntimeError("fail")

        # Cause failures
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        # Circuit should now be open
        from utils.rate_limit import CircuitState

        assert breaker.state == CircuitState.OPEN

        # Further calls should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            breaker.call(fail_func)

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker half-open state and recovery."""
        import time

        config = CircuitBreakerConfig(
            failure_threshold=2, success_threshold=2, timeout=0.1, window_size=5
        )
        breaker = CircuitBreaker(config)

        def fail_func():
            raise RuntimeError("fail")

        def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        from utils.rate_limit import CircuitState

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Next call should transition to half-open
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

        # Another success should close it
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_manual_reset(self):
        """Test manual circuit breaker reset."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)

        def fail_func():
            raise RuntimeError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        from utils.rate_limit import CircuitState

        assert breaker.state == CircuitState.OPEN

        # Manual reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED

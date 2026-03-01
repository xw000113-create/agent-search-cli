"""
Tests for retry handler module.
"""

import unittest
from unittest.mock import Mock
import time

from agent_search.retry_handler import (
    RetryConfig,
    RetryHandler,
    CircuitBreaker,
    CircuitBreakerOpen,
    retry,
)


class TestRetryConfig(unittest.TestCase):
    """Test RetryConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = RetryConfig()

        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.base_delay, 1.0)
        self.assertEqual(config.max_delay, 60.0)
        self.assertEqual(config.exponential_base, 2.0)
        self.assertTrue(config.jitter)

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetryConfig(max_retries=5, base_delay=0.5, max_delay=30.0)

        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.base_delay, 0.5)
        self.assertEqual(config.max_delay, 30.0)

    def test_status_code_lists(self):
        """Test status code configuration."""
        config = RetryConfig()

        # Should retry on these
        self.assertIn(429, config.retry_on_status_codes)
        self.assertIn(503, config.retry_on_status_codes)

        # Should give up on these
        self.assertIn(400, config.giveup_on_status_codes)
        self.assertIn(404, config.giveup_on_status_codes)


class TestRetryHandler(unittest.TestCase):
    """Test RetryHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = RetryConfig(max_retries=3, base_delay=0.1)
        self.handler = RetryHandler(self.config)

    def test_success_no_retry(self):
        """Test successful execution without retry."""
        func = Mock(return_value="success")

        result = self.handler.execute(func)

        self.assertEqual(result, "success")
        self.assertEqual(func.call_count, 1)

    def test_retry_on_failure(self):
        """Test retry on failure."""
        func = Mock(side_effect=[Exception("Fail"), Exception("Fail"), "success"])

        result = self.handler.execute(func)

        self.assertEqual(result, "success")
        self.assertEqual(func.call_count, 3)

    def test_exhaust_retries(self):
        """Test exhausting all retries."""
        func = Mock(side_effect=Exception("Always fails"))

        with self.assertRaises(Exception) as context:
            self.handler.execute(func)

        self.assertEqual(func.call_count, 4)  # Initial + 3 retries
        self.assertIn("Always fails", str(context.exception))

    def test_calculate_delay(self):
        """Test delay calculation."""
        delay0 = self.handler.calculate_delay(0)
        delay1 = self.handler.calculate_delay(1)
        delay2 = self.handler.calculate_delay(2)

        # Delays should increase
        self.assertLess(delay0, delay1)
        self.assertLess(delay1, delay2)

        # Delays should be within bounds
        self.assertGreaterEqual(delay0, 0)
        self.assertLessEqual(delay2, self.config.max_delay)

    def test_should_retry_on_status_code(self):
        """Test should_retry for status codes."""
        # Should retry on 429
        self.assertTrue(self.handler.should_retry(None, 429))

        # Should give up on 404
        self.assertFalse(self.handler.should_retry(None, 404))

        # Should retry on 500
        self.assertTrue(self.handler.should_retry(None, 500))

    def test_should_retry_on_exception(self):
        """Test should_retry for exceptions."""
        # Should retry on generic Exception
        self.assertTrue(self.handler.should_retry(Exception("Test")))

        # Should not retry on KeyboardInterrupt
        self.assertFalse(self.handler.should_retry(KeyboardInterrupt()))


class TestCircuitBreaker(unittest.TestCase):
    """Test CircuitBreaker."""

    def setUp(self):
        """Set up test fixtures."""
        self.cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

    def test_initial_state(self):
        """Test initial state."""
        self.assertFalse(self.cb.is_open)

    def test_open_after_failures(self):
        """Test circuit opens after failures."""
        # Record failures
        for _ in range(3):
            self.cb.record_failure()

        self.assertTrue(self.cb.is_open)

    def test_record_success_closes(self):
        """Test success closes circuit."""
        # Open circuit
        for _ in range(3):
            self.cb.record_failure()

        # Simulate recovery timeout by moving last_failure_time back
        self.cb._last_failure_time = time.time() - 0.2  # 0.2s ago > 0.1s timeout

        # Circuit should be half-open
        self.assertFalse(self.cb.is_open)

        # Record successes
        for _ in range(3):
            self.cb.record_success()

        # Circuit should be closed
        self.assertFalse(self.cb.is_open)

    def test_context_manager_success(self):
        """Test context manager with success."""
        with self.cb:
            pass  # Success

        self.assertFalse(self.cb.is_open)

    def test_context_manager_failure(self):
        """Test context manager with failure."""
        try:
            with self.cb:
                raise Exception("Test error")
        except Exception:
            pass

        self.assertEqual(self.cb._failures, 1)

    def test_context_manager_raises_when_open(self):
        """Test context manager raises when open."""
        # Open circuit
        for _ in range(3):
            self.cb.record_failure()

        with self.assertRaises(CircuitBreakerOpen):
            with self.cb:
                pass


class TestRetryDecorator(unittest.TestCase):
    """Test retry decorator."""

    def test_retry_decorator(self):
        """Test retry decorator."""
        call_count = [0]

        @retry(max_retries=2, base_delay=0.01)
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Fail")
            return "success"

        result = flaky_function()

        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 2)


class TestRetryContext(unittest.TestCase):
    """Test RetryContext."""

    def test_context_usage(self):
        """Test using retry context."""
        config = RetryConfig(max_retries=2)
        handler = RetryHandler(config)

        with handler.attempt() as attempt:
            # Create a mock response
            response = Mock()
            response.status_code = 200

            # Should not raise
            attempt.check_response(response)

        self.assertTrue(attempt._completed)


if __name__ == "__main__":
    unittest.main()

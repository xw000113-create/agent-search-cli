"""
Tests for rate limiting and retry modules.
"""

import unittest
import time
from unittest.mock import Mock, patch

from agent_search.rate_limiter import (
    RateLimiter,
    AdaptiveRateLimiter,
    RequestThrottler,
    get_rate_limiter,
)


class TestRateLimiter(unittest.TestCase):
    """Test RateLimiter."""

    def setUp(self):
        """Set up test fixtures."""
        self.limiter = RateLimiter(
            min_delay=0.1, max_delay=0.2, burst_size=2, burst_window=1.0
        )

    def test_wait_basic(self):
        """Test basic wait functionality."""
        delay = self.limiter.wait()

        # wait() returns the intended delay value (actual sleep may be mocked)
        self.assertGreater(delay, 0)
        self.assertIsInstance(delay, float)

    def test_burst_handling(self):
        """Test burst handling."""
        # Within burst: small delay (0.1-0.5). Beyond burst: rate-limited delay (min_delay-max_delay).
        delays = []
        for _ in range(3):
            delay = self.limiter.wait()
            delays.append(delay)

        # First 2 should use burst delay (0.1-0.5 range)
        self.assertLess(delays[0], 0.6)
        self.assertLess(delays[1], 0.6)

        # Third exceeds burst_size=2, so it uses rate-limited delay
        self.assertGreater(delays[2], 0.05)

    def test_get_current_rate(self):
        """Test getting current rate."""
        rate = self.limiter.get_current_rate()

        self.assertIsInstance(rate, (int, float))
        self.assertGreaterEqual(rate, 0)

    def test_is_rate_limited(self):
        """Test rate limit detection."""
        # Initially not rate limited
        self.assertFalse(self.limiter.is_rate_limited())

        # Exhaust burst
        for _ in range(3):
            self.limiter.wait()

        # Should be rate limited
        self.assertTrue(self.limiter.is_rate_limited())


class TestAdaptiveRateLimiter(unittest.TestCase):
    """Test AdaptiveRateLimiter."""

    def setUp(self):
        """Set up test fixtures."""
        self.limiter = AdaptiveRateLimiter(
            min_delay=0.1, max_delay=0.5, backoff_factor=1.5, recovery_factor=0.9
        )

    def test_record_success(self):
        """Test recording success."""
        self.limiter.record_success()

        self.assertEqual(self.limiter._consecutive_successes, 1)
        self.assertEqual(self.limiter._consecutive_failures, 0)

    def test_record_rate_limit(self):
        """Test recording rate limit."""
        initial_delay = self.limiter._current_delay

        self.limiter.record_rate_limit()

        self.assertEqual(self.limiter._consecutive_failures, 1)
        self.assertEqual(self.limiter._consecutive_successes, 0)
        # Delay should increase
        self.assertGreater(self.limiter._current_delay, initial_delay)

    def test_adaptive_delay(self):
        """Test adaptive delay adjustment."""
        # Record multiple failures
        for _ in range(5):
            self.limiter.record_rate_limit()

        delay = self.limiter.wait()

        # Delay should be higher than minimum
        self.assertGreater(delay, self.limiter.min_delay)

        # Record successes to recover
        for _ in range(6):
            self.limiter.record_success()

        # Should reduce delay
        self.assertLess(self.limiter._current_delay, delay)


class TestRequestThrottler(unittest.TestCase):
    """Test RequestThrottler."""

    def setUp(self):
        """Set up test fixtures."""
        self.limiter = RateLimiter(min_delay=0.1)
        self.callback_called = [False]

        def callback(delay, success):
            self.callback_called[0] = True

        self.callback = callback

    def test_context_manager(self):
        """Test context manager usage."""
        with RequestThrottler(self.limiter) as throttler:
            pass

        self.assertGreater(throttler.delay, 0)

    def test_callback_execution(self):
        """Test callback is called on exit."""
        with RequestThrottler(self.limiter, callback=self.callback):
            pass

        self.assertTrue(self.callback_called[0])

    def test_exception_handling(self):
        """Test exception handling in context."""
        try:
            with RequestThrottler(self.limiter, callback=self.callback):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Callback should still be called
        self.assertTrue(self.callback_called[0])


class TestGetRateLimiter(unittest.TestCase):
    """Test get_rate_limiter function."""

    def test_singleton(self):
        """Test singleton behavior."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        self.assertIs(limiter1, limiter2)

    def test_default_parameters(self):
        """Test default parameters."""
        limiter = get_rate_limiter()

        self.assertEqual(limiter.min_delay, 1.0)
        self.assertEqual(limiter.max_delay, 3.0)
        self.assertEqual(limiter.burst_size, 1)


if __name__ == "__main__":
    unittest.main()

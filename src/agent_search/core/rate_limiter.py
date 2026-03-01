"""
Rate Limiter with Jitter

Provides rate limiting functionality with configurable delays and jitter
to avoid detection patterns.
"""

import time
import random
import threading
from typing import Optional, Callable
from datetime import datetime, timedelta


class RateLimiter:
    """
    Rate limiter with jitter to simulate human-like request patterns.
    
    Usage:
        limiter = RateLimiter(min_delay=1.0, max_delay=3.0)
        
        # Before each request
        limiter.wait()
        response = requests.get(url)
    """
    
    def __init__(
        self,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        burst_size: int = 1,
        burst_window: float = 60.0,
    ):
        """
        Initialize rate limiter.
        
        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            burst_size: Number of requests allowed in burst window
            burst_window: Time window for burst in seconds
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.burst_size = burst_size
        self.burst_window = timedelta(seconds=burst_window)
        
        self._last_request_time: Optional[datetime] = None
        self._request_times: list = []
        self._lock = threading.Lock()
        
    def wait(self) -> float:
        """
        Wait for the appropriate delay before making next request.
        
        Returns:
            The actual delay time in seconds
        """
        with self._lock:
            now = datetime.now()
            
            # Clean up old request times outside burst window
            cutoff = now - self.burst_window
            self._request_times = [t for t in self._request_times if t > cutoff]
            
            # Check if we're within burst limit
            if len(self._request_times) < self.burst_size:
                # Can proceed immediately, but still add small delay
                delay = random.uniform(0.1, 0.5)
            else:
                # Need to wait based on rate limiting
                if self._last_request_time:
                    elapsed = (now - self._last_request_time).total_seconds()
                    base_delay = random.uniform(self.min_delay, self.max_delay)
                    delay = max(0, base_delay - elapsed)
                else:
                    delay = random.uniform(self.min_delay, self.max_delay)
            
            if delay > 0:
                time.sleep(delay)
            
            # Record this request
            self._last_request_time = datetime.now()
            self._request_times.append(self._last_request_time)
            
            return delay
    
    def wait_with_jitter(self, base_delay: Optional[float] = None) -> float:
        """
        Wait with additional jitter for more human-like behavior.
        
        Args:
            base_delay: Base delay (uses min/max if not provided)
            
        Returns:
            The actual delay time in seconds
        """
        if base_delay is None:
            delay = random.uniform(self.min_delay, self.max_delay)
        else:
            # Add ±20% jitter
            jitter = base_delay * 0.2
            delay = random.uniform(base_delay - jitter, base_delay + jitter)
        
        delay = max(0, delay)  # Ensure non-negative
        time.sleep(delay)
        
        with self._lock:
            self._last_request_time = datetime.now()
            self._request_times.append(self._last_request_time)
        
        return delay
    
    def get_current_rate(self) -> float:
        """
        Get current requests per minute rate.
        
        Returns:
            Requests per minute
        """
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=1)
            recent_requests = [t for t in self._request_times if t > cutoff]
            return len(recent_requests)
    
    def is_rate_limited(self) -> bool:
        """
        Check if currently rate limited.
        
        Returns:
            True if within burst window and exceeded burst size
        """
        with self._lock:
            now = datetime.now()
            cutoff = now - self.burst_window
            recent_requests = [t for t in self._request_times if t > cutoff]
            return len(recent_requests) >= self.burst_size


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts based on response codes.
    Slows down on rate limit responses, speeds up on success.
    """
    
    def __init__(
        self,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        burst_size: int = 1,
        burst_window: float = 60.0,
        backoff_factor: float = 1.5,
        recovery_factor: float = 0.95,
    ):
        super().__init__(min_delay, max_delay, burst_size, burst_window)
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        self._current_delay = min_delay
        self._consecutive_successes = 0
        self._consecutive_failures = 0
        
    def record_success(self):
        """Record a successful request."""
        self._consecutive_successes += 1
        self._consecutive_failures = 0
        
        # Gradually reduce delay after consecutive successes
        if self._consecutive_successes >= 5:
            self._current_delay = max(
                self.min_delay,
                self._current_delay * self.recovery_factor
            )
            self._consecutive_successes = 0
    
    def record_rate_limit(self):
        """Record a rate limit (429) response."""
        self._consecutive_failures += 1
        self._consecutive_successes = 0
        
        # Increase delay
        self._current_delay = min(
            self.max_delay * 2,  # Allow exceeding max_delay temporarily
            self._current_delay * self.backoff_factor
        )
    
    def wait(self) -> float:
        """Wait with adaptive delay."""
        delay = random.uniform(self._current_delay, self._current_delay * 1.2)
        time.sleep(delay)
        
        with self._lock:
            self._last_request_time = datetime.now()
            self._request_times.append(self._last_request_time)
        
        return delay


class RequestThrottler:
    """
    Context manager for throttling requests.
    
    Usage:
        with RequestThrottler(limiter):
            response = requests.get(url)
    """
    
    def __init__(self, limiter: RateLimiter, callback: Optional[Callable] = None):
        self.limiter = limiter
        self.callback = callback
        self.delay = 0.0
        
    def __enter__(self):
        self.delay = self.limiter.wait()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.callback:
            self.callback(self.delay, exc_type is None)
        return False


# Global rate limiter singleton
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    min_delay: float = 1.0,
    max_delay: float = 3.0,
    burst_size: int = 1,
) -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter(min_delay, max_delay, burst_size)
    return _global_limiter


def set_global_rate_limiter(limiter: RateLimiter):
    """Set the global rate limiter instance."""
    global _global_limiter
    _global_limiter = limiter

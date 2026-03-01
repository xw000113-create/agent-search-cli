"""
Retry Logic with Exponential Backoff

Provides retry functionality with configurable backoff strategies
for handling transient failures.
"""

import time
import random
from typing import Optional, Callable, Any, Type, Union, List
from functools import wraps


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on: Optional[List[Type[Exception]]] = None,
        retry_on_status_codes: Optional[List[int]] = None,
        giveup_on_status_codes: Optional[List[int]] = None,
        jitter: bool = True,
        on_retry: Optional[Callable[[Exception, int, float], None]] = None,
        on_giveup: Optional[Callable[[Exception, int], None]] = None,
    ):
        """
        Configure retry behavior.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay cap in seconds
            exponential_base: Base for exponential backoff (default: 2.0)
            retry_on: Exception types to retry on (default: all exceptions)
            retry_on_status_codes: HTTP status codes to retry (default: [429, 503, 504])
            giveup_on_status_codes: HTTP status codes to never retry (default: [400, 401, 403, 404])
            jitter: Add randomness to delays
            on_retry: Callback when retry occurs (exception, attempt_number, delay)
            on_giveup: Callback when giving up (exception, attempt_number)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on = retry_on or [Exception]
        self.retry_on_status_codes = retry_on_status_codes or [429, 503, 504, 502, 500]
        self.giveup_on_status_codes = giveup_on_status_codes or [400, 401, 403, 404, 405]
        self.jitter = jitter
        self.on_retry = on_retry
        self.on_giveup = on_giveup


class RetryHandler:
    """
    Handles retry logic with exponential backoff.
    
    Usage:
        retry = RetryHandler(RetryConfig(max_retries=5))
        
        # With context manager
        with retry.attempt() as attempt:
            response = requests.get(url)
            attempt.check_response(response)
            return response
        
        # With decorator
        @retry.retry_with_backoff()
        def fetch_data(url):
            return requests.get(url)
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._attempt_count = 0
        
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt using exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add ±25% jitter
            jitter = delay * 0.25
            delay = random.uniform(delay - jitter, delay + jitter)
        
        return max(0, delay)
    
    def should_retry(self, exception: Optional[Exception], status_code: Optional[int] = None) -> bool:
        """
        Determine if we should retry based on exception and status code.
        
        Args:
            exception: The exception that occurred
            status_code: HTTP status code if applicable
            
        Returns:
            True if should retry
        """
        # Check status codes first
        if status_code is not None:
            if status_code in self.config.giveup_on_status_codes:
                return False
            if status_code in self.config.retry_on_status_codes:
                return True
            # Retry on 5xx errors
            if status_code >= 500:
                return True
            # Don't retry on other 4xx errors
            if status_code >= 400:
                return False
        
        # Check exception type
        return any(isinstance(exception, exc_type) for exc_type in self.config.retry_on)
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            self._attempt_count = attempt
            
            try:
                result = func(*args, **kwargs)
                
                # Check if result has status_code (like requests.Response)
                status_code = getattr(result, 'status_code', None)
                
                if status_code is not None and not self.should_retry(None, status_code):
                    return result
                
                if status_code is not None and status_code >= 400:
                    # Treat as failure
                    raise Exception(f"HTTP {status_code}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Get status code if available
                status_code = getattr(e, 'status_code', None)
                
                # Check if we should retry
                if not self.should_retry(e, status_code):
                    raise
                
                # Check if we've exhausted retries
                if attempt >= self.config.max_retries:
                    if self.config.on_giveup:
                        self.config.on_giveup(e, attempt + 1)
                    raise e

                # Calculate and wait
                delay = self.calculate_delay(attempt)

                if self.config.on_retry:
                    self.config.on_retry(e, attempt + 1, delay)

                time.sleep(delay)

        if last_exception:
            raise last_exception
        raise Exception("All retries exhausted")
    
    def retry_with_backoff(self, func: Optional[Callable] = None):
        """
        Decorator to add retry logic to a function.
        
        Usage:
            @retry.retry_with_backoff()
            def fetch_url(url):
                return requests.get(url)
        """
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return self.execute(f, *args, **kwargs)
            return wrapper
        
        if func:
            return decorator(func)
        return decorator
    
    def attempt(self) -> 'RetryContext':
        """
        Create a retry context for use with context managers.

        Usage:
            with handler.attempt() as attempt:
                response = requests.get(url)
                attempt.check_response(response)

        Returns:
            RetryContext instance
        """
        return RetryContext(self)

    def get_attempt_count(self) -> int:
        """Get the number of attempts made in the last execution."""
        return self._attempt_count


class RetryContext:
    """
    Context manager for retry attempts.
    
    Usage:
        handler = RetryHandler(RetryConfig())
        
        with handler.attempt() as attempt:
            response = requests.get(url)
            attempt.check_response(response)
    """
    
    def __init__(self, handler: RetryHandler):
        self.handler = handler
        self.attempt = 0
        self._completed = False
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred
            return False
        self._completed = True
        return True
    
    def check_response(self, response):
        """
        Check if response indicates success or needs retry.
        
        Args:
            response: Response object with status_code attribute
            
        Raises:
            Exception: If should retry (to trigger retry logic)
        """
        status_code = getattr(response, 'status_code', None)
        
        if status_code is None:
            return
        
        if self.handler.should_retry(None, status_code):
            response.raise_for_status()


class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascading failures.
    
    Usage:
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        
        try:
            with cb:
                response = requests.get(url)
        except CircuitBreakerOpen:
            print("Circuit is open, request not attempted")
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._half_open_calls = 0
        
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        if self._state == 'OPEN':
            if self._last_failure_time and \
               (time.time() - self._last_failure_time) > self.recovery_timeout:
                self._state = 'HALF_OPEN'
                self._half_open_calls = 0
                return False
            return True
        return False
    
    def record_success(self):
        """Record a successful call."""
        if self._state == 'HALF_OPEN':
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = 'CLOSED'
                self._failures = 0
        elif self._state == 'CLOSED':
            self._failures = max(0, self._failures - 1)
    
    def record_failure(self):
        """Record a failed call."""
        self._failures += 1
        self._last_failure_time = time.time()
        
        if self._state == 'HALF_OPEN':
            self._state = 'OPEN'
        elif self._state == 'CLOSED' and self._failures >= self.failure_threshold:
            self._state = 'OPEN'
    
    def __enter__(self):
        if self.is_open:
            raise CircuitBreakerOpen("Circuit breaker is open")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.record_success()
        else:
            self.record_failure()
        return False


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


# Convenience functions

def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: Optional[List[Type[Exception]]] = None,
):
    """
    Simple retry decorator.
    
    Usage:
        @retry(max_retries=5)
        def fetch_data():
            return requests.get(url)
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on=retry_on,
    )
    handler = RetryHandler(config)
    return handler.retry_with_backoff

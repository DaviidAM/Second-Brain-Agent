"""
Rate Limiting and Backoff - Phase 7: Observability and Performance
Rate limiting, token bucket, exponential backoff, circuit breaker.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import time
import threading


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")


class CircuitOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class BackoffType(Enum):
    """Types of backoff strategies."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_second: float = 120.0
    burst_size: int = 150
    per_endpoint_limits: dict = None

    def __post_init__(self):
        if self.per_endpoint_limits is None:
            self.per_endpoint_limits = {}


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens."""
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def get_wait_time(self) -> float:
        """Get time to wait for tokens to be available."""
        with self.lock:
            self._refill()
            if self.tokens >= 1:
                return 0.0
            return (1 - self.tokens) / self.rate


class BackoffStrategy:
    """Exponential backoff strategy."""

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        backoff_type: BackoffType = BackoffType.EXPONENTIAL
    ):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.backoff_type = backoff_type

    def get_delay(self, attempt: int) -> float:
        """Get delay for given attempt number."""
        if self.backoff_type == BackoffType.EXPONENTIAL:
            delay = self.initial_delay * (self.multiplier ** attempt)
        elif self.backoff_type == BackoffType.LINEAR:
            delay = self.initial_delay * attempt
        else:
            delay = self.initial_delay

        return min(delay, self.max_delay)


class CircuitBreaker:
    """Circuit breaker for external dependencies."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"
        self.lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker."""
        with self.lock:
            if self.state == "open":
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half-open"
                else:
                    raise CircuitOpen("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            self.failure_count = 0
            if self.state == "half-open":
                self.state = "closed"

    def _on_failure(self):
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"

    def get_state(self) -> str:
        """Get current circuit state."""
        return self.state


class RateLimiter:
    """
    Main rate limiter with token bucket and per-endpoint limits.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.global_bucket = TokenBucket(
            self.config.requests_per_second,
            self.config.burst_size
        )
        self.endpoint_buckets: dict[str, TokenBucket] = {}
        self.backoff = BackoffStrategy()
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.lock = threading.Lock()

    def check_limit(self, endpoint: str = "default") -> bool:
        """Check if request is within rate limit."""
        with self.lock:
            if not self._check_endpoint_limit(endpoint):
                return False

            return self.global_bucket.consume()

    def _check_endpoint_limit(self, endpoint: str) -> bool:
        """Check endpoint-specific rate limit."""
        limit = self.config.per_endpoint_limits.get(endpoint)
        if not limit:
            return True

        if endpoint not in self.endpoint_buckets:
            self.endpoint_buckets[endpoint] = TokenBucket(limit, int(limit * 1.5))

        return self.endpoint_buckets[endpoint].consume()

    def acquire(self, endpoint: str = "default") -> float:
        """Acquire permission to make request, returns wait time."""
        if self.check_limit(endpoint):
            return 0.0

        return max(
            self.global_bucket.get_wait_time(),
            self.endpoint_buckets.get(endpoint, self.global_bucket).get_wait_time()
        )

    def wait_and_retry(self, endpoint: str = "default") -> float:
        """Wait until request can be made."""
        wait_time = self.acquire(endpoint)

        if wait_time > 0:
            time.sleep(wait_time)

        return wait_time

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker for a service."""
        with self.lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreaker()
            return self.circuit_breakers[name]

    def get_status(self) -> dict:
        """Get rate limiter status."""
        return {
            "global": {
                "rate": self.config.requests_per_second,
                "available_tokens": self.global_bucket.tokens
            },
            "endpoints": {
                name: {"rate": bucket.rate, "tokens": bucket.tokens}
                for name, bucket in self.endpoint_buckets.items()
            },
            "circuit_breakers": {
                name: cb.get_state()
                for name, cb in self.circuit_breakers.items()
            }
        }

    def reset(self):
        """Reset rate limiter state."""
        with self.lock:
            self.global_bucket.tokens = float(self.config.burst_size)
            self.endpoint_buckets.clear()
            self.circuit_breakers.clear()

"""
Concurrency Protection - Phase 7: Observability and Performance
Semaphore-based concurrency limits, request queuing, timeout enforcement.
"""

import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class ConcurrencyConfig:
    """Configuration for concurrency control."""

    max_concurrent_requests: int = 50
    max_concurrent_enrichments: int = 5
    queue_size: int = 100
    default_timeout: float = 30.0


class SemaphorePool:
    """Pool of semaphores for different operation types."""

    def __init__(self):
        self._semaphores: dict[str, threading.Semaphore] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._counters: dict[str, int] = {}
        self._lock = threading.Lock()

    def acquire(self, name: str, limit: int, timeout: Optional[float] = None) -> bool:
        """Acquire semaphore for operation type."""
        with self._lock:
            if name not in self._semaphores:
                self._semaphores[name] = threading.Semaphore(limit)
                self._locks[name] = threading.Lock()
                self._counters[name] = 0

        semaphore = self._semaphores[name]
        return semaphore.acquire(timeout=timeout)

    def release(self, name: str):
        """Release semaphore for operation type."""
        if name in self._semaphores:
            self._semaphores[name].release()

    def get_current_count(self, name: str) -> int:
        """Get current count for operation type."""
        with self._lock:
            return self._counters.get(name, 0)

    def increment(self, name: str):
        """Increment counter for operation type."""
        with self._lock:
            if name in self._counters:
                self._counters[name] += 1

    def decrement(self, name: str):
        """Decrement counter for operation type."""
        with self._lock:
            if name in self._counters:
                self._counters[name] -= 1


class RequestQueue:
    """Queue for handling burst requests."""

    def __init__(self, max_size: int = 100):
        self._queue: queue.Queue = queue.Queue(maxsize=max_size)
        self._workers: list[threading.Thread] = []
        self._running = False

    def enqueue(self, func: Callable, *args, **kwargs) -> bool:
        """Add request to queue."""
        try:
            self._queue.put((func, args, kwargs), block=False)
            return True
        except queue.Full:
            return False

    def dequeue(self, timeout: Optional[float] = None) -> Optional[tuple]:
        """Remove request from queue."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def is_full(self) -> bool:
        """Check if queue is full."""
        return self._queue.full()

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()


class ConcurrencyManager:
    """
    Main concurrency manager with semaphore and queue control.
    """

    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        self.config = config or ConcurrencyConfig()
        self.semaphore_pool = SemaphorePool()
        self.request_queue = RequestQueue(self.config.queue_size)
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.max_concurrent_requests
        )

    def execute_with_limit(
        self,
        operation_type: str,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Any:
        """Execute function with concurrency limits."""
        timeout = timeout or self.config.default_timeout

        acquired = self.semaphore_pool.acquire(
            operation_type, self._get_limit(operation_type), timeout
        )

        if not acquired:
            raise TimeoutError(f"Could not acquire semaphore for {operation_type}")

        try:
            self.semaphore_pool.increment(operation_type)
            future = self.executor.submit(func, *args, **kwargs)
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            raise TimeoutError(f"Operation {operation_type} timed out")
        finally:
            self.semaphore_pool.decrement(operation_type)
            self.semaphore_pool.release(operation_type)

    def _get_limit(self, operation_type: str) -> int:
        """Get limit for operation type."""
        limits = {
            "query": self.config.max_concurrent_requests,
            "enrichment": self.config.max_concurrent_enrichments,
        }
        return limits.get(operation_type, 10)

    def enqueue_request(self, func: Callable, *args, **kwargs) -> bool:
        """Enqueue request for async processing."""
        return self.request_queue.enqueue(func, *args, **kwargs)

    def process_queue(self, worker_func: Callable):
        """Process queued requests with worker function."""
        while self.request_queue.size() > 0:
            item = self.request_queue.dequeue(timeout=1.0)
            if item:
                func, args, kwargs = item
                try:
                    worker_func(func, *args, **kwargs)
                except Exception:
                    pass

    def get_status(self) -> dict:
        """Get concurrency status."""
        return {
            "max_concurrent_requests": self.config.max_concurrent_requests,
            "max_concurrent_enrichments": self.config.max_concurrent_enrichments,
            "queue_size": self.request_queue.size(),
            "queue_capacity": self.config.queue_size,
            "active_workers": len([w for w in self.executor._threads if w.is_alive()]),
        }

    def shutdown(self, wait: bool = True):
        """Shutdown executor and cleanup."""
        self.executor.shutdown(wait=wait)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

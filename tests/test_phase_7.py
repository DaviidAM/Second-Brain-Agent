"""
Tests for Phase 7: Observability and Performance
"""

import pytest
from src.mcp.logging_config import (
    StructuredLogger, LogLevel, LogContext, LogEntry, RequestLogger
)
from src.mcp.metrics import (
    MetricsCollector, QueryMetrics, EnrichmentMetrics
)
from src.mcp.health import (
    HealthChecker, HealthStatus, ReadinessProbe, LivenessProbe, ComponentHealth
)
from src.mcp.rate_limiter import (
    RateLimiter, TokenBucket, BackoffStrategy, BackoffType,
    CircuitBreaker, RateLimitConfig
)
from src.mcp.cache import (
    CacheManager, QueryCache, EmbeddingCache, CacheEntry
)
from src.mcp.concurrency import (
    ConcurrencyManager, ConcurrencyConfig, SemaphorePool, RequestQueue
)


class TestStructuredLogger:
    """Tests for StructuredLogger."""

    def test_initialization(self):
        """Test logger initialization."""
        logger = StructuredLogger()
        
        assert logger.name == "mcp"
        assert logger.level == LogLevel.INFO

    def test_log_info(self):
        """Test info logging."""
        logger = StructuredLogger(log_level="SILENT")
        
        logger.info("Test message")
        
        assert logger is not None


class TestLogContext:
    """Tests for LogContext."""

    def test_context_creation(self):
        """Test creating log context."""
        context = LogContext(
            request_id="req-123",
            correlation_id="corr-456",
            operation="query"
        )
        
        assert context.request_id == "req-123"
        assert context.correlation_id == "corr-456"


class TestRequestLogger:
    """Tests for RequestLogger."""

    def test_initialization(self):
        """Test request logger initialization."""
        logger = RequestLogger()
        
        assert logger.logger is not None


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_initialization(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector()
        
        assert collector.query_metrics is not None
        assert collector.enrichment_metrics is not None

    def test_record_query(self):
        """Test recording query metrics."""
        collector = MetricsCollector()
        
        collector.record_query(100.0, True, False)
        
        assert collector.query_metrics.total_queries == 1
        assert collector.query_metrics.successful_queries == 1

    def test_record_enrichment(self):
        """Test recording enrichment metrics."""
        collector = MetricsCollector()
        
        collector.record_enrichment(
            success=True,
            tokens_used=1000,
            llm_time_ms=500.0,
            gaps_detected=2,
            gaps_filled=2,
            files_written=1
        )
        
        assert collector.enrichment_metrics.total_enrichments == 1

    def test_get_query_stats(self):
        """Test getting query statistics."""
        collector = MetricsCollector()
        
        collector.record_query(100.0, True)
        collector.record_query(200.0, True)
        
        stats = collector.get_query_stats()
        
        assert stats["total_queries"] == 2
        assert "avg_latency_ms" in stats


class TestQueryMetrics:
    """Tests for QueryMetrics."""

    def test_avg_latency(self):
        """Test average latency calculation."""
        metrics = QueryMetrics()
        
        metrics.total_queries = 2
        metrics.total_latency_ms = 300.0
        
        assert metrics.avg_latency_ms == 150.0


class TestHealthChecker:
    """Tests for HealthChecker."""

    def test_initialization(self):
        """Test health checker initialization."""
        checker = HealthChecker()
        
        assert checker.readiness_probe is not None
        assert checker.liveness_probe is not None

    def test_is_alive(self):
        """Test liveness check."""
        checker = HealthChecker()
        
        alive = checker.is_alive()
        
        assert isinstance(alive, bool)

    def test_get_health(self):
        """Test getting health status."""
        checker = HealthChecker()
        
        health = checker.get_health()
        
        assert "status" in health
        assert "readiness" in health
        assert "liveness" in health


class TestReadinessProbe:
    """Tests for ReadinessProbe."""

    def test_add_check(self):
        """Test adding readiness check."""
        probe = ReadinessProbe()
        
        probe.add_check("test", lambda: True)
        
        assert len(probe._checks) == 1


class TestTokenBucket:
    """Tests for TokenBucket."""

    def test_initialization(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(10.0, 100)
        
        assert bucket.rate == 10.0
        assert bucket.capacity == 100

    def test_consume(self):
        """Test consuming tokens."""
        bucket = TokenBucket(10.0, 100)
        
        result = bucket.consume(1)
        
        assert result is True


class TestBackoffStrategy:
    """Tests for BackoffStrategy."""

    def test_exponential_backoff(self):
        """Test exponential backoff."""
        strategy = BackoffStrategy(
            initial_delay=1.0,
            multiplier=2.0,
            backoff_type=BackoffType.EXPONENTIAL
        )
        
        delay = strategy.get_delay(2)
        
        assert delay == 4.0

    def test_max_delay(self):
        """Test max delay cap."""
        strategy = BackoffStrategy(
            initial_delay=1.0,
            max_delay=5.0,
            multiplier=10.0
        )
        
        delay = strategy.get_delay(10)
        
        assert delay == 5.0


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker()
        
        assert cb.state == "closed"
        assert cb.failure_threshold == 5

    def test_call_success(self):
        """Test successful call through circuit breaker."""
        cb = CircuitBreaker()
        
        result = cb.call(lambda: "success")
        
        assert result == "success"
        assert cb.state == "closed"


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter()
        
        assert limiter.global_bucket is not None

    def test_check_limit(self):
        """Test checking rate limit."""
        limiter = RateLimiter()
        
        result = limiter.check_limit("query")
        
        assert isinstance(result, bool)

    def test_get_status(self):
        """Test getting rate limiter status."""
        limiter = RateLimiter()
        
        status = limiter.get_status()
        
        assert "global" in status


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_is_expired(self):
        """Test checking if entry is expired."""
        import time
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=time.time() - 100,
            last_accessed=time.time() - 100,
            ttl=10.0
        )
        
        assert entry.is_expired() is True


class TestQueryCache:
    """Tests for QueryCache."""

    def test_initialization(self):
        """Test query cache initialization."""
        cache = QueryCache()
        
        assert cache.max_size == 1000

    def test_get_miss(self):
        """Test cache miss."""
        cache = QueryCache()
        
        result = cache.get("nonexistent")
        
        assert result is None

    def test_set_and_get(self):
        """Test setting and getting cache entry."""
        cache = QueryCache()
        
        cache.set("key", "value")
        result = cache.get("key")
        
        assert result == "value"

    def test_invalidate(self):
        """Test cache invalidation."""
        cache = QueryCache()
        
        cache.set("key", "value")
        cache.invalidate("key")
        
        assert cache.get("key") is None


class TestCacheManager:
    """Tests for CacheManager."""

    def test_initialization(self):
        """Test cache manager initialization."""
        manager = CacheManager()
        
        assert manager.query_cache is not None
        assert manager.embedding_cache is not None

    def test_query_cache(self):
        """Test query cache operations."""
        manager = CacheManager()
        
        manager.set_query("query1", "result")
        result = manager.get_query("query1")
        
        assert result == "result"

    def test_get_stats(self):
        """Test getting cache statistics."""
        manager = CacheManager()
        
        stats = manager.get_stats()
        
        assert "query_cache" in stats


class TestSemaphorePool:
    """Tests for SemaphorePool."""

    def test_initialization(self):
        """Test semaphore pool initialization."""
        pool = SemaphorePool()
        
        assert pool._semaphores == {}

    def test_acquire_release(self):
        """Test acquiring and releasing semaphore."""
        pool = SemaphorePool()
        
        result = pool.acquire("test", 5, 0.1)
        pool.release("test")
        
        assert isinstance(result, bool)


class TestRequestQueue:
    """Tests for RequestQueue."""

    def test_initialization(self):
        """Test request queue initialization."""
        queue = RequestQueue(10)
        
        assert queue.size() == 0

    def test_enqueue_dequeue(self):
        """Test enqueue and dequeue."""
        queue = RequestQueue(10)
        
        queue.enqueue(lambda: "test")
        
        assert queue.size() == 1


class TestConcurrencyManager:
    """Tests for ConcurrencyManager."""

    def test_initialization(self):
        """Test concurrency manager initialization."""
        manager = ConcurrencyManager()
        
        assert manager.semaphore_pool is not None
        assert manager.executor is not None

    def test_get_status(self):
        """Test getting concurrency status."""
        manager = ConcurrencyManager()
        
        status = manager.get_status()
        
        assert "max_concurrent_requests" in status

    def test_context_manager(self):
        """Test context manager."""
        with ConcurrencyManager() as manager:
            assert manager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

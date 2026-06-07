"""
Metrics Collection - Phase 7: Observability and Performance
Query latency histograms, enrichment metrics, token usage tracking.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class QueryMetrics:
    """Metrics for query operations."""

    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_latency_ms: float = 0.0
    latencies: list[float] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def avg_latency_ms(self) -> float:
        return (
            self.total_latency_ms / self.total_queries
            if self.total_queries > 0
            else 0.0
        )

    def get_percentile(self, percentile: float) -> float:
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]


@dataclass
class EnrichmentMetrics:
    """Metrics for enrichment operations."""

    total_enrichments: int = 0
    successful_enrichments: int = 0
    failed_enrichments: int = 0
    total_tokens_used: int = 0
    gaps_detected: int = 0
    gaps_filled: int = 0
    files_written: int = 0
    total_llm_time_ms: float = 0.0


class MetricsCollector:
    """
    Main metrics collector class.
    """

    def __init__(self):
        self.query_metrics = QueryMetrics()
        self.enrichment_metrics = EnrichmentMetrics()
        self._custom_metrics: dict[str, float] = {}
        self._counter_metrics: dict[str, int] = defaultdict(int)
        self._start_time = time.time()

    def record_query(
        self, latency_ms: float, success: bool = True, cached: bool = False
    ):
        """Record query metrics."""
        self.query_metrics.total_queries += 1

        if success:
            self.query_metrics.successful_queries += 1
        else:
            self.query_metrics.failed_queries += 1

        self.query_metrics.total_latency_ms += latency_ms
        self.query_metrics.latencies.append(latency_ms)

        if cached:
            self.query_metrics.cache_hits += 1
        else:
            self.query_metrics.cache_misses += 1

    def record_enrichment(
        self,
        success: bool,
        tokens_used: int = 0,
        llm_time_ms: float = 0.0,
        gaps_detected: int = 0,
        gaps_filled: int = 0,
        files_written: int = 0,
    ):
        """Record enrichment metrics."""
        self.enrichment_metrics.total_enrichments += 1

        if success:
            self.enrichment_metrics.successful_enrichments += 1
        else:
            self.enrichment_metrics.failed_enrichments += 1

        self.enrichment_metrics.total_tokens_used += tokens_used
        self.enrichment_metrics.total_llm_time_ms += llm_time_ms
        self.enrichment_metrics.gaps_detected += gaps_detected
        self.enrichment_metrics.gaps_filled += gaps_filled
        self.enrichment_metrics.files_written += files_written

    def record_custom(self, name: str, value: float):
        """Record custom metric."""
        self._custom_metrics[name] = value

    def increment_counter(self, name: str, value: int = 1):
        """Increment counter metric."""
        self._counter_metrics[name] += value

    def get_query_stats(self) -> dict:
        """Get query statistics."""
        return {
            "total_queries": self.query_metrics.total_queries,
            "successful_queries": self.query_metrics.successful_queries,
            "failed_queries": self.query_metrics.failed_queries,
            "avg_latency_ms": round(self.query_metrics.avg_latency_ms, 2),
            "p50_latency_ms": round(self.query_metrics.get_percentile(50), 2),
            "p95_latency_ms": round(self.query_metrics.get_percentile(95), 2),
            "p99_latency_ms": round(self.query_metrics.get_percentile(99), 2),
            "cache_hits": self.query_metrics.cache_hits,
            "cache_misses": self.query_metrics.cache_misses,
            "cache_hit_rate": round(
                self.query_metrics.cache_hits
                / max(self.query_metrics.total_queries, 1)
                * 100,
                2,
            ),
        }

    def get_enrichment_stats(self) -> dict:
        """Get enrichment statistics."""
        return {
            "total_enrichments": self.enrichment_metrics.total_enrichments,
            "successful_enrichments": self.enrichment_metrics.successful_enrichments,
            "failed_enrichments": self.enrichment_metrics.failed_enrichments,
            "total_tokens_used": self.enrichment_metrics.total_tokens_used,
            "avg_llm_time_ms": round(
                self.enrichment_metrics.total_llm_time_ms
                / max(self.enrichment_metrics.total_enrichments, 1),
                2,
            ),
            "gaps_detected": self.enrichment_metrics.gaps_detected,
            "gaps_filled": self.enrichment_metrics.gaps_filled,
            "files_written": self.enrichment_metrics.files_written,
        }

    def get_all_stats(self) -> dict:
        """Get all statistics."""
        return {
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "timestamp": datetime.utcnow().isoformat(),
            "query": self.get_query_stats(),
            "enrichment": self.get_enrichment_stats(),
            "custom": self._custom_metrics.copy(),
            "counters": dict(self._counter_metrics),
        }

    def reset(self):
        """Reset all metrics."""
        self.query_metrics = QueryMetrics()
        self.enrichment_metrics = EnrichmentMetrics()
        self._custom_metrics.clear()
        self._counter_metrics.clear()
        self._start_time = time.time()

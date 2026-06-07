# SLO Definitions - Phase 7: Observability and Performance

## Query Path SLOs

| Metric | Target | Description |
|--------|--------|-------------|
| p95 Latency (cached) | < 500ms | Query latency when result is cached |
| p95 Latency (full) | < 2000ms | Query latency for full retrieval |
| p99 Latency | < 5000ms | Maximum expected latency |
| Availability | 99.9% | Uptime percentage |
| Error Rate | < 1% | Failed query percentage |

## Enrichment Path SLOs

| Metric | Target | Description |
|--------|--------|-------------|
| p95 Latency | < 10s | Including LLM call |
| p99 Latency | < 30s | Maximum enrichment time |
| Success Rate | > 95% | Successful enrichment percentage |
| Error Rate | < 5% | Failed enrichment percentage |

## General SLOs

| Metric | Target | Description |
|--------|--------|-------------|
| Cache Hit Rate | > 60% | Query cache effectiveness |
| Rate Limit Rejections | < 1% | Percentage of rate-limited requests |
| Health Check Pass Rate | 100% | Readiness probe success |

## Alerting Thresholds

- **Warning**: p95 latency > 80% of target for 5 minutes
- **Critical**: p95 latency > target for 5 minutes
- **Warning**: Error rate > 0.5% for 5 minutes
- **Critical**: Error rate > 1% for 5 minutes
- **Warning**: Cache hit rate < 40% for 10 minutes

## Monitoring Dashboards

Key metrics to display:
1. Query latency histogram (p50, p95, p99)
2. Request rate over time
3. Error rate by type
4. Cache hit/miss ratio
5. Active concurrent requests
6. Enrichment queue depth
7. LLM token usage

## Runbook Actions

### High Latency
1. Check cache hit rate
2. Review index size and freshness
3. Check for slow queries
4. Review concurrent request load

### High Error Rate
1. Check LLM API status
2. Review rate limiter state
3. Check circuit breaker status
4. Review error logs

### Low Cache Hit Rate
1. Check cache TTL settings
2. Review query patterns
3. Check for cache invalidation storms

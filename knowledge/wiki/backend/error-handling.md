---
title: "Error Handling and Logging: Building Robust Error Management and Observability Systems"
author: david-alba
created_at: "2026-05-25T14:15:00Z"
last_modified: "2026-06-02T12:30:00Z"
tags:
  - monitoring
  - testing
  - best-practices
  - backend
source_type: manual
confidence_score: 0.89
---

# Error Handling & Logging

## Importance

Proper error handling and logging are essential for:
- Debugging production issues
- Monitoring application health
- Understanding user experience
- Security and compliance
- Performance optimization

## Error Handling Principles

### 1. Be Specific
```python
# ❌ Bad
except Exception:
    pass

# ✓ Good
except ValueError as e:
    logger.error(f"Invalid input: {e}", exc_info=True)
    raise ValueError("Input must be valid JSON") from e
```

### 2. Fail Fast
Catch and handle errors as soon as possible.

```python
# Validate input immediately
if not is_valid_email(email):
    raise ValueError("Invalid email format")
```

### 3. Provide Context
Include relevant information in error messages.

```python
error_context = {
    "user_id": user_id,
    "action": "update_profile",
    "timestamp": datetime.now(),
    "environment": os.getenv("ENV"),
}
```

### 4. Recover Gracefully
Implement fallback strategies.

```python
try:
    data = fetch_from_primary()
except ConnectionError:
    logger.warning("Primary service failed, using cache")
    data = fetch_from_cache()
```

## Logging Levels

| Level | Use Case | Example |
|-------|----------|---------|
| DEBUG | Development, detailed info | "User clicked button X" |
| INFO | General informational | "User logged in successfully" |
| WARNING | Something unexpected | "Cache miss rate high" |
| ERROR | Error occurred, action failed | "Database connection failed" |
| CRITICAL | System failure | "Out of memory" |

## Structured Logging

```python
# ❌ Unstructured
logger.info("User login successful")

# ✓ Structured
logger.info("user_login", extra={
    "user_id": 123,
    "email": "user@example.com",
    "ip_address": "192.168.1.1",
    "duration_ms": 245
})
```

## Python Logging Configuration

```python
import logging
import json

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Example usage
logger.info("Processing request", extra={
    "request_id": "abc123",
    "method": "POST",
    "path": "/api/users"
})
```

## Error Response Format

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Email is required and must be valid",
    "details": {
      "field": "email",
      "received": "invalid-email",
      "expected": "valid email format"
    },
    "timestamp": "2026-06-02T12:30:45Z",
    "request_id": "req-abc123"
  }
}
```

## Exception Hierarchy

```python
class APIError(Exception):
    """Base exception for API errors"""
    pass

class ValidationError(APIError):
    """Validation failed"""
    pass

class NotFoundError(APIError):
    """Resource not found"""
    pass

class UnauthorizedError(APIError):
    """Authentication failed"""
    pass
```

## Monitoring & Alerting

### Key Metrics
- Error rate (errors per minute)
- Error distribution (by type)
- Response time percentiles (p50, p95, p99)
- Stack trace frequency

### Alert Conditions
```
IF error_rate > 100/min THEN alert "High error rate"
IF response_time_p99 > 2s THEN alert "Slow performance"
IF critical_error_count > 0 THEN alert "Critical error"
```

## Tools

- **Logging**: Python logging, structlog, pythonjson-logger
- **Monitoring**: Sentry, New Relic, DataDog
- **Visualization**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger, Zipkin

## Best Practices

✓ Log security events (logins, failures)  
✓ Never log sensitive data (passwords, tokens, PII)  
✓ Use correlation IDs for request tracing  
✓ Set appropriate log retention policies  
✓ Monitor log levels in production  
✓ Test error paths  
✓ Document error codes  
✓ Use consistent error formats  

## Related Topics

- [[wiki/backend/rest-api-design.md|API Design & Error Responses]]
- [[wiki/patterns/circuit-breaker.md|Resilience Patterns]]
- [[wiki/backend/microservices.md|Distributed Systems Debugging]]

---

**Importance**: High  
**Learning Curve**: Easy to Medium

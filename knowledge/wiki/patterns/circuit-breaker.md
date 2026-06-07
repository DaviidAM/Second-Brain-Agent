---
title: "Circuit Breaker Pattern: Preventing Cascading Failures in Distributed Systems"
author: david-alba
created_at: "2026-05-01T10:00:00Z"
last_modified: "2026-06-01T14:30:00Z"
tags:
  - patterns
  - resilience
  - microservices
  - distributed-systems
source_type: manual
confidence_score: 0.95
---

# Circuit Breaker Pattern

## Overview

The Circuit Breaker pattern is a critical resilience pattern for preventing cascading failures in distributed systems. It acts as a proxy that monitors for failures and can prevent further requests from being sent to a failing service.

## Problem

In distributed systems, services depend on remote calls to other services. When a service fails or becomes slow, it can cause:
- Cascading failures throughout the system
- Resource exhaustion (threads, connections)
- Poor user experience
- System-wide outages

## Solution

The Circuit Breaker pattern implements a state machine with three states:

### States

1. **Closed** (Normal Operation)
   - Requests pass through normally
   - Failures are counted
   - When failure threshold is reached, trips to Open

2. **Open** (Failing)
   - Requests fail immediately without calling the service
   - No requests are sent to the failing service
   - After a timeout, transitions to Half-Open

3. **Half-Open** (Recovery Testing)
   - Limited number of requests allowed
   - If requests succeed, transitions to Closed
   - If requests fail, transitions back to Open

## Implementation Details

### Key Configuration

```python
class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Exception = Exception
    ):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = "CLOSED"
```

### State Transitions

```
[CLOSED] --failure_threshold_reached--> [OPEN]
[OPEN] --timeout_expired--> [HALF_OPEN]
[HALF_OPEN] --success--> [CLOSED]
[HALF_OPEN] --failure--> [OPEN]
```

## Related Patterns

- [[wiki/patterns/retry-logic.md|Retry Logic Pattern]]
- [[wiki/patterns/timeout-pattern.md|Timeout Pattern]]
- [[wiki/backend/service-degradation.md|Service Degradation]]
- [[wiki/patterns/bulkhead.md|Bulkhead Pattern]]

## Benefits

✓ Prevents cascading failures  
✓ Fails fast and gracefully  
✓ Allows recovery time for failing services  
✓ Reduces resource exhaustion  
✓ Improves system resilience

## Drawbacks

✗ Added complexity  
✗ Requires careful configuration  
✗ Can mask underlying issues if not monitored

## Real-World Examples

1. **Hystrix** - Netflix's Java implementation
2. **Polly** - .NET resilience library
3. **resilience4j** - Java library
4. **Ocelot** - .NET API Gateway

## Monitoring

Always monitor:
- Circuit state transitions
- Failure rates
- Recovery attempts
- Mean time to recovery (MTTR)

---

**Last Updated**: 2026-06-01  
**Confidence**: High (0.95)

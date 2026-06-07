---
title: "Asynchronous Programming in Python: Async/Await, Coroutines, and Event Loops"
author: david-alba
created_at: "2026-04-20T14:30:00Z"
last_modified: "2026-06-02T09:15:00Z"
tags:
  - python
  - performance
  - implementation
  - best-practices
source_type: manual
confidence_score: 0.93
---

# Async/Await in Python

## What is Asynchronous Programming?

Asynchronous programming allows programs to perform multiple operations concurrently without blocking on I/O operations. It's essential for building performant web applications and handling multiple concurrent requests.

## Key Concepts

### Coroutines
Functions defined with `async def` that can be paused and resumed.

```python
async def fetch_data(url):
    response = await http_client.get(url)
    return response.json()
```

### Await
Pauses execution until a coroutine completes and returns its result.

```python
result = await fetch_data("https://api.example.com/data")
```

### Event Loop
The core of async programming - manages and executes coroutines.

```python
asyncio.run(main())  # Runs the coroutine
```

## Async I/O Patterns

### Concurrent Requests
```python
async def main():
    results = await asyncio.gather(
        fetch_data(url1),
        fetch_data(url2),
        fetch_data(url3)
    )
    return results
```

### Timeouts
```python
try:
    result = await asyncio.wait_for(fetch_data(url), timeout=5.0)
except asyncio.TimeoutError:
    print("Request timed out")
```

### Task Creation
```python
task = asyncio.create_task(fetch_data(url))
result = await task
```

## Libraries

- **asyncio** - Standard library async framework
- **aiohttp** - Async HTTP client
- **httpx** - Modern HTTP client with async support
- **FastAPI** - Web framework with async support
- **SQLAlchemy** - With async engine support

## Best Practices

1. **Avoid blocking operations** in async code
2. **Use asyncio primitives** for synchronization (Lock, Event, Semaphore)
3. **Handle exceptions** properly with try/except
4. **Monitor event loops** for deadlocks
5. **Use context managers** (async with)

## Performance Comparison

```
Sync (Sequential):    ████████████████████████ ~30s for 1000 requests
Async (Concurrent):   ██ ~1s for 1000 requests
```

## Common Pitfalls

❌ Blocking operations in async functions  
❌ Missing await keyword  
❌ Not using gather() for concurrent tasks  
❌ Improper exception handling  
❌ Thread safety issues in async context

## Related Topics

- [[wiki/python/context-managers.md|Context Managers in Python]]
- [[wiki/backend/microservices.md|Microservices with Python]]
- [[wiki/backend/rest-api-design.md|Building REST APIs]]

---

**Difficulty**: Intermediate  
**Python Version**: 3.7+

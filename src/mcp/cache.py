"""
Cache Strategy - Phase 7: Observability and Performance
LRU cache for queries, cache invalidation, TTL-based expiration.
"""

from dataclasses import dataclass
from typing import Optional, Any
import time
import threading
from collections import OrderedDict


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    ttl: Optional[float] = None
    hit_count: int = 0

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl


class QueryCache:
    """LRU cache for query results."""

    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            entry.last_accessed = time.time()
            entry.hit_count += 1
            self._cache.move_to_end(key)

            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set value in cache."""
        with self.lock:
            if key in self._cache:
                del self._cache[key]

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl or self.default_ttl
            )

            self._cache[key] = entry
            self._cache.move_to_end(key)

            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def invalidate(self, key: str):
        """Invalidate a cache entry."""
        with self.lock:
            self._cache.pop(key, None)

    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self.lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate * 100, 2)
            }


class EmbeddingCache:
    """Cache for embedding vectors."""

    def __init__(self, max_size: int = 5000, default_ttl: float = 86400):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get embedding from cache."""
        with self.lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            if entry.is_expired():
                del self._cache[key]
                return None

            entry.last_accessed = time.time()
            self._cache.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set embedding in cache."""
        with self.lock:
            if key in self._cache:
                del self._cache[key]

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl or self.default_ttl
            )

            self._cache[key] = entry
            self._cache.move_to_end(key)

            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def clear(self):
        """Clear embedding cache."""
        with self.lock:
            self._cache.clear()


class CacheManager:
    """
    Main cache manager with query and embedding caches.
    """

    def __init__(
        self,
        query_cache_size: int = 1000,
        embedding_cache_size: int = 5000,
        query_ttl: float = 3600,
        embedding_ttl: float = 86400
    ):
        self.query_cache = QueryCache(query_cache_size, query_ttl)
        self.embedding_cache = EmbeddingCache(embedding_cache_size, embedding_ttl)

    def get_query(self, key: str) -> Optional[Any]:
        """Get query result from cache."""
        return self.query_cache.get(key)

    def set_query(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set query result in cache."""
        self.query_cache.set(key, value, ttl)

    def invalidate_query(self, key: str):
        """Invalidate query cache entry."""
        self.query_cache.invalidate(key)

    def get_embedding(self, key: str) -> Optional[Any]:
        """Get embedding from cache."""
        return self.embedding_cache.get(key)

    def set_embedding(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set embedding in cache."""
        self.embedding_cache.set(key, value, ttl)

    def invalidate_all(self):
        """Invalidate all caches."""
        self.query_cache.clear()
        self.embedding_cache.clear()

    def get_stats(self) -> dict:
        """Get all cache statistics."""
        return {
            "query_cache": self.query_cache.get_stats(),
            "embedding_cache": {
                "size": len(self.embedding_cache._cache),
                "max_size": self.embedding_cache.max_size
            }
        }

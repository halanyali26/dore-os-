"""
Dore OS v2.0 — Platform Cache
In-memory TTL cache for platform data (YouTube, Spotify).
Reduces external API calls by caching results for a configurable duration.
"""
import time
import threading
from typing import Any, Dict, Optional


class TTLCache:
    """Simple in-memory TTL (Time-To-Live) cache with thread-safe access."""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        """
        Args:
            ttl_seconds: Default TTL in seconds (default: 300 = 5 minutes)
            max_size: Maximum number of entries before eviction
        """
        self._store: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache. Returns None if missing or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None

            if time.monotonic() > entry["expires_at"]:
                del self._store[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a value with optional per-key TTL override."""
        expires_at = time.monotonic() + (ttl if ttl is not None else self._ttl)

        with self._lock:
            # Evict oldest if at capacity
            if len(self._store) >= self._max_size:
                oldest_key = min(self._store, key=lambda k: self._store[k]["expires_at"])
                del self._store[oldest_key]

            self._store[key] = {
                "value": value,
                "expires_at": expires_at,
            }

    def delete(self, key: str):
        """Remove a key from cache."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def get_or_set(self, key: str, factory, ttl: Optional[int] = None) -> Any:
        """
        Get from cache if available, otherwise call factory() to produce value,
        cache it, and return.
        """
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value, ttl)
        return value

    @property
    def stats(self) -> Dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "entries": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": round(hit_rate, 1),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
        }

    @property
    def keys(self) -> list:
        """Return a copy of all non-expired keys."""
        with self._lock:
            now = time.monotonic()
            return [k for k, v in self._store.items() if v["expires_at"] > now]


# ─── Module-level caches ────────────────────────────────────
# Platform data (YouTube stats, Spotify data) — 5 min TTL
platform_cache = TTLCache(ttl_seconds=300)

# Composable bridge results — 10 min TTL
composio_cache = TTLCache(ttl_seconds=600)

# General-purpose cache — 2 min TTL
short_cache = TTLCache(ttl_seconds=120)


def get_platform_cache() -> TTLCache:
    """Get the platform data cache instance."""
    return platform_cache


def get_composio_cache() -> TTLCache:
    """Get the Composio bridge cache instance."""
    return composio_cache

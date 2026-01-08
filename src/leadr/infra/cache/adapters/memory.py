"""In-memory cache implementation."""

import threading
import time
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass
class CacheEntry:
    """A cache entry with value and expiration time."""

    value: Any
    expires_at: float


class InMemoryCache:
    """Thread-safe in-memory cache with TTL support.

    This implementation uses a simple dict with expiration checking on read.
    Suitable for single-process applications. For multi-process or distributed
    deployments, replace with a Redis-backed implementation.

    Usage:
        # Create a new instance
        cache = InMemoryCache()
        cache.set("key", "value", ttl_seconds=60)
        value = cache.get("key")

        # Or use the singleton for application-wide caching
        cache = InMemoryCache.get_instance()
    """

    _instance: ClassVar["InMemoryCache | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        """Initialize the cache."""
        self._data: dict[str, CacheEntry] = {}
        self._data_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "InMemoryCache":
        """Get the singleton instance.

        Thread-safe singleton pattern for application-wide caching.

        Returns:
            The singleton InMemoryCache instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance.

        Primarily useful for testing to ensure a clean state.
        """
        with cls._lock:
            cls._instance = None

    def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: The cache key to retrieve.

        Returns:
            The cached value, or None if not found or expired.
        """
        with self._data_lock:
            entry = self._data.get(key)
            if entry is None:
                return None

            # Check expiration
            if time.time() > entry.expires_at:
                # Expired - remove and return None
                del self._data[key]
                return None

            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a value in the cache with a TTL.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl_seconds: Time-to-live in seconds.
        """
        expires_at = time.time() + ttl_seconds
        with self._data_lock:
            self._data[key] = CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        """Delete a key from the cache.

        Args:
            key: The cache key to delete.
        """
        with self._data_lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._data_lock:
            self._data.clear()

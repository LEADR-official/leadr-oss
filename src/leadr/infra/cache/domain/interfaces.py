"""Cache backend protocol definition."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CacheBackend(Protocol):
    """Protocol for cache backends.

    Defines the interface for cache implementations.
    This abstraction allows swapping cache backends (e.g., in-memory to Redis)
    without changing the consuming code.
    """

    def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: The cache key to retrieve.

        Returns:
            The cached value, or None if not found or expired.
        """
        ...

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a value in the cache with a TTL.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl_seconds: Time-to-live in seconds.
        """
        ...

    def delete(self, key: str) -> None:
        """Delete a key from the cache.

        Args:
            key: The cache key to delete.
        """
        ...

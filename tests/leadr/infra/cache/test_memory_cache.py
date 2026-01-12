"""Tests for in-memory cache implementation."""

import time
from unittest.mock import patch

from leadr.infra.cache.adapters.memory import InMemoryCache
from leadr.infra.cache.domain.interfaces import CacheBackend


class TestInMemoryCache:
    """Test InMemoryCache implementation."""

    def test_implements_cache_backend_protocol(self) -> None:
        """InMemoryCache should implement CacheBackend protocol."""
        cache = InMemoryCache()
        assert isinstance(cache, CacheBackend)

    def test_get_returns_none_for_missing_key(self) -> None:
        """get() should return None for keys that don't exist."""
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None

    def test_set_and_get_string_value(self) -> None:
        """set() and get() should work with string values."""
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl_seconds=60)
        assert cache.get("key1") == "value1"

    def test_set_and_get_dict_value(self) -> None:
        """set() and get() should work with dict values."""
        cache = InMemoryCache()
        data = {"name": "test", "count": 42}
        cache.set("key1", data, ttl_seconds=60)
        assert cache.get("key1") == data

    def test_set_and_get_list_value(self) -> None:
        """set() and get() should work with list values."""
        cache = InMemoryCache()
        data = [1, 2, 3, "four"]
        cache.set("key1", data, ttl_seconds=60)
        assert cache.get("key1") == data

    def test_set_overwrites_existing_value(self) -> None:
        """set() should overwrite existing values."""
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl_seconds=60)
        cache.set("key1", "value2", ttl_seconds=60)
        assert cache.get("key1") == "value2"

    def test_delete_removes_key(self) -> None:
        """delete() should remove a key from the cache."""
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl_seconds=60)
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_delete_nonexistent_key_does_not_raise(self) -> None:
        """delete() should not raise for nonexistent keys."""
        cache = InMemoryCache()
        cache.delete("nonexistent")  # Should not raise

    def test_ttl_expiration(self) -> None:
        """Values should expire after TTL seconds."""
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl_seconds=1)

        # Value should exist immediately
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)

        # Value should be expired
        assert cache.get("key1") is None

    def test_ttl_expiration_with_mock_time(self) -> None:
        """Values should expire after TTL using mocked time."""
        cache = InMemoryCache()

        with patch("time.time") as mock_time:
            # Set at time 1000
            mock_time.return_value = 1000.0
            cache.set("key1", "value1", ttl_seconds=60)

            # Still valid at time 1059
            mock_time.return_value = 1059.0
            assert cache.get("key1") == "value1"

            # Expired at time 1061
            mock_time.return_value = 1061.0
            assert cache.get("key1") is None

    def test_clear_removes_all_keys(self) -> None:
        """clear() should remove all keys from the cache."""
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl_seconds=60)
        cache.set("key2", "value2", ttl_seconds=60)
        cache.set("key3", "value3", ttl_seconds=60)

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_multiple_caches_are_independent(self) -> None:
        """Different cache instances should be independent."""
        cache1 = InMemoryCache()
        cache2 = InMemoryCache()

        cache1.set("key1", "value1", ttl_seconds=60)

        assert cache1.get("key1") == "value1"
        assert cache2.get("key1") is None


class TestInMemoryCacheSingleton:
    """Test singleton pattern for InMemoryCache."""

    def test_get_instance_returns_same_instance(self) -> None:
        """get_instance() should return the same instance."""
        instance1 = InMemoryCache.get_instance()
        instance2 = InMemoryCache.get_instance()
        assert instance1 is instance2

    def test_get_instance_data_persists(self) -> None:
        """Data should persist across get_instance() calls."""
        instance1 = InMemoryCache.get_instance()
        instance1.set("singleton_key", "singleton_value", ttl_seconds=60)

        instance2 = InMemoryCache.get_instance()
        assert instance2.get("singleton_key") == "singleton_value"

    def test_reset_instance_creates_new_instance(self) -> None:
        """reset_instance() should clear the singleton."""
        instance1 = InMemoryCache.get_instance()
        instance1.set("key", "value", ttl_seconds=60)

        InMemoryCache.reset_instance()

        instance2 = InMemoryCache.get_instance()
        assert instance1 is not instance2
        assert instance2.get("key") is None


class TestCacheBackendProtocol:
    """Test CacheBackend protocol definition."""

    def test_protocol_defines_get_method(self) -> None:
        """CacheBackend should define get method."""
        assert hasattr(CacheBackend, "get")

    def test_protocol_defines_set_method(self) -> None:
        """CacheBackend should define set method."""
        assert hasattr(CacheBackend, "set")

    def test_protocol_defines_delete_method(self) -> None:
        """CacheBackend should define delete method."""
        assert hasattr(CacheBackend, "delete")

    def test_protocol_is_runtime_checkable(self) -> None:
        """CacheBackend should be runtime_checkable."""
        # Classes implementing the protocol should pass isinstance check
        cache = InMemoryCache()
        assert isinstance(cache, CacheBackend)

        # Classes not implementing the protocol should fail
        class NotACache:
            pass

        assert not isinstance(NotACache(), CacheBackend)

    def test_protocol_method_stubs_are_callable(self) -> None:
        """Protocol method stubs should be callable (for coverage of ... bodies)."""

        # Create a minimal class that satisfies the protocol structurally
        # but delegates to the protocol's method stubs to cover the ... lines
        class MinimalCache:
            def get(self, key: str) -> None:
                # Call protocol method stub to cover line 24
                return CacheBackend.get(self, key)  # type: ignore[reportAbstractUsage]

            def set(self, key: str, value: object, ttl_seconds: int) -> None:
                # Call protocol method stub to cover line 34
                return CacheBackend.set(self, key, value, ttl_seconds)  # type: ignore[reportAbstractUsage]

            def delete(self, key: str) -> None:
                # Call protocol method stub to cover line 42
                return CacheBackend.delete(self, key)  # type: ignore[reportAbstractUsage]

        cache = MinimalCache()
        # These calls exercise the protocol's ... stub bodies
        assert cache.get("key") is None
        assert cache.set("key", "value", 60) is None
        assert cache.delete("key") is None

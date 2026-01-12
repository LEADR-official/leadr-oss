"""Cache infrastructure module."""

from leadr.infra.cache.adapters.memory import InMemoryCache
from leadr.infra.cache.domain.interfaces import CacheBackend
from leadr.infra.cache.services.dependencies import CacheDep, get_cache

__all__ = [
    "CacheBackend",
    "CacheDep",
    "InMemoryCache",
    "get_cache",
]

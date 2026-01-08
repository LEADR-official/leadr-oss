"""FastAPI dependencies for cache infrastructure."""

from typing import Annotated

from fastapi import Depends

from leadr.infra.cache.adapters.memory import InMemoryCache
from leadr.infra.cache.domain.interfaces import CacheBackend


def get_cache() -> CacheBackend:
    """Get the cache backend singleton.

    Returns:
        The application-wide cache backend instance.
    """
    return InMemoryCache.get_instance()


CacheDep = Annotated[CacheBackend, Depends(get_cache)]

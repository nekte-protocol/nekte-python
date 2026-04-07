"""CacheStore Port — backing store for capability cache."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable


@dataclass
class CacheStoreEntry:
    data: object
    cached_at: float
    ttl_ms: float
    access_count: int = 0
    token_cost: int = 8


@dataclass
class CacheGetResult:
    entry: CacheStoreEntry
    freshness: Literal["fresh", "stale"]


@runtime_checkable
class CacheStore(Protocol):
    """Port: cache backing store. Adapters: InMemoryCacheStore, RedisCacheStore."""

    def get(self, key: str) -> CacheGetResult | None: ...
    def set(self, key: str, entry: CacheStoreEntry) -> None: ...
    def delete(self, key: str) -> bool: ...
    def keys(self) -> Iterator[str]: ...
    @property
    def size(self) -> int: ...
    def clear(self) -> None: ...

"""InMemoryCacheStore Adapter — SIEVE + GDSF + TTL jitter + SWR."""

from __future__ import annotations

import random
import time
from collections.abc import Iterator

from ..domain.cache.sieve_policy import SievePolicy
from ..ports.cache_store import CacheGetResult, CacheStoreEntry


class InMemoryCacheStore:
    """Default cache store with SIEVE eviction, GDSF weighting, TTL jitter."""

    def __init__(
        self,
        max_entries: int = 1000,
        jitter_factor: float = 0.1,
        grace_factor: float = 2.0,
    ) -> None:
        self._entries: dict[str, CacheStoreEntry] = {}
        self._sieve: SievePolicy[str] = SievePolicy()
        self._max_entries = max_entries
        self._jitter_factor = jitter_factor
        self._grace_factor = grace_factor

    def get(self, key: str) -> CacheGetResult | None:
        entry = self._entries.get(key)
        if entry is None:
            return None

        now = time.time() * 1000
        age = now - entry.cached_at
        ttl = entry.ttl_ms
        grace_limit = ttl + ttl * self._grace_factor

        if age <= ttl:
            entry.access_count += 1
            self._sieve.access(key)
            return CacheGetResult(entry=entry, freshness="fresh")

        if age <= grace_limit:
            entry.access_count += 1
            self._sieve.access(key)
            return CacheGetResult(entry=entry, freshness="stale")

        # Expired
        del self._entries[key]
        self._sieve.delete(key)
        return None

    def set(self, key: str, entry: CacheStoreEntry) -> None:
        stored = CacheStoreEntry(
            data=entry.data,
            cached_at=entry.cached_at,
            ttl_ms=self._apply_jitter(entry.ttl_ms),
            access_count=entry.access_count,
            token_cost=entry.token_cost,
        )

        if key in self._entries:
            self._entries[key] = stored
            self._sieve.access(key)
            return

        while len(self._entries) >= self._max_entries:
            self._evict()

        self._entries[key] = stored
        self._sieve.insert(key)

    def delete(self, key: str) -> bool:
        self._sieve.delete(key)
        return self._entries.pop(key, None) is not None

    def keys(self) -> Iterator[str]:
        return iter(list(self._entries.keys()))

    @property
    def size(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
        self._sieve.clear()

    def _evict(self) -> None:
        """GDSF-weighted SIEVE eviction."""
        best_key: str | None = None
        best_priority = float("inf")
        candidates: list[str] = []

        for _ in range(3):
            key = self._sieve.evict()
            if key is None:
                break
            candidates.append(key)
            entry = self._entries.get(key)
            priority = entry.access_count * entry.token_cost if entry else 0
            if priority < best_priority:
                best_key = key
                best_priority = priority

        for key in candidates:
            if key != best_key:
                self._sieve.insert(key)

        if best_key is not None:
            self._entries.pop(best_key, None)

    def _apply_jitter(self, ttl_ms: float) -> float:
        factor = 1 - self._jitter_factor + random.random() * 2 * self._jitter_factor
        return round(ttl_ms * factor)

"""CapabilityCache — Application Service.

Orchestrates CacheStore (port) with negative caching,
stale-while-revalidate, and token-cost awareness.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from ..domain.cache.token_cost import token_cost_for_level
from ..domain.types import Capability, DiscoveryLevel
from ..ports.cache_store import CacheGetResult, CacheStore, CacheStoreEntry

CacheEntryData = dict[str, Any]  # { levels, hash, max_level }
RevalidationFn = Callable[[str, str], None]


class CapabilityCache:
    """Client-side cache with SIEVE, GDSF, SWR, and negative caching."""

    def __init__(
        self,
        store: CacheStore,
        default_ttl_ms: float = 5 * 60 * 1000,
        namespace: str = "",
        negative_ttl_ms: float = 60_000,
    ) -> None:
        self._store = store
        self._default_ttl_ms = default_ttl_ms
        self._namespace = f"{namespace}:" if namespace else ""
        self._negative_ttl_ms = negative_ttl_ms
        self._negatives: dict[str, float] = {}
        self._revalidating: set[str] = set()
        self._revalidation_fn: RevalidationFn | None = None

    def on_revalidate(self, fn: RevalidationFn) -> None:
        self._revalidation_fn = fn

    def set(
        self,
        agent_id: str,
        cap: Capability,
        level: DiscoveryLevel,
        ttl_ms: float | None = None,
    ) -> None:
        key = self._key(agent_id, cap.id)  # type: ignore[union-attr]
        self._negatives.pop(key, None)

        existing = self._store.get(key)
        existing_data: CacheEntryData | None = (
            existing.entry.data if existing else None  # type: ignore[union-attr]
        )
        max_level = max(existing_data.get("max_level", 0), level) if existing_data else level

        data: CacheEntryData = existing_data.copy() if existing_data else {"levels": {}, "hash": "", "max_level": 0}
        data["hash"] = cap.h  # type: ignore[union-attr]
        data["max_level"] = max_level
        data["levels"][str(level)] = cap.model_dump() if hasattr(cap, "model_dump") else dict(cap)  # type: ignore[union-attr]

        self._store.set(key, CacheStoreEntry(
            data=data,
            cached_at=time.time() * 1000,
            ttl_ms=ttl_ms or self._default_ttl_ms,
            access_count=existing.entry.access_count if existing else 0,
            token_cost=token_cost_for_level(max_level),
        ))

    def get_hash(self, agent_id: str, cap_id: str) -> str | None:
        entry = self._get_entry(agent_id, cap_id)
        return entry.get("hash") if entry else None

    def get(self, agent_id: str, cap_id: str, level: DiscoveryLevel) -> dict[str, Any] | None:
        entry = self._get_entry(agent_id, cap_id)
        if entry is None:
            return None
        return entry.get("levels", {}).get(str(level))

    def is_valid(self, agent_id: str, cap_id: str, h: str) -> bool:
        return self.get_hash(agent_id, cap_id) == h

    # -- Negative caching --

    def set_negative(self, agent_id: str, cap_id: str) -> None:
        self._negatives[self._key(agent_id, cap_id)] = time.time() * 1000 + self._negative_ttl_ms

    def is_negative(self, agent_id: str, cap_id: str) -> bool:
        key = self._key(agent_id, cap_id)
        expiry = self._negatives.get(key)
        if expiry is None:
            return False
        if time.time() * 1000 > expiry:
            del self._negatives[key]
            return False
        return True

    # -- Invalidation --

    def invalidate(self, agent_id: str, cap_id: str) -> None:
        self._store.delete(self._key(agent_id, cap_id))

    def invalidate_agent(self, agent_id: str) -> None:
        prefix = f"{self._namespace}{agent_id}:"
        for key in list(self._store.keys()):
            if key.startswith(prefix):
                self._store.delete(key)
        for key in list(self._negatives):
            if key.startswith(prefix):
                del self._negatives[key]

    def clear(self) -> None:
        self._store.clear()
        self._negatives.clear()
        self._revalidating.clear()

    def stats(self) -> dict[str, int]:
        agents: set[str] = set()
        for key in self._store.keys():
            without_ns = key[len(self._namespace):] if key.startswith(self._namespace) else key
            agents.add(without_ns.split(":")[0])
        return {"size": self._store.size, "agents": len(agents), "negatives": len(self._negatives)}

    # -- Internal --

    def _key(self, agent_id: str, cap_id: str) -> str:
        return f"{self._namespace}{agent_id}:{cap_id}"

    def _get_entry(self, agent_id: str, cap_id: str) -> CacheEntryData | None:
        if self.is_negative(agent_id, cap_id):
            return None
        key = self._key(agent_id, cap_id)
        result = self._store.get(key)
        if result is None:
            return None
        data = result.entry.data
        if not isinstance(data, dict) or "hash" not in data:
            return None
        if result.freshness == "stale":
            self._trigger_revalidation(agent_id, cap_id, key)
        return data  # type: ignore[return-value]

    def _trigger_revalidation(self, agent_id: str, cap_id: str, key: str) -> None:
        if not self._revalidation_fn or key in self._revalidating:
            return
        self._revalidating.add(key)
        self._revalidation_fn(agent_id, cap_id)

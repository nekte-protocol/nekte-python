"""Test InMemoryCacheStore — SIEVE + GDSF + TTL jitter + SWR."""

import time

from nekte.adapters.memory_cache_store import InMemoryCacheStore
from nekte.ports.cache_store import CacheStoreEntry


def make_entry(**kwargs) -> CacheStoreEntry:
    return CacheStoreEntry(
        data=kwargs.get("data", {"test": True}),
        cached_at=kwargs.get("cached_at", time.time() * 1000),
        ttl_ms=kwargs.get("ttl_ms", 60_000),
        access_count=kwargs.get("access_count", 0),
        token_cost=kwargs.get("token_cost", 8),
    )


def test_set_and_get():
    s = InMemoryCacheStore(jitter_factor=0)
    s.set("k", make_entry())
    r = s.get("k")
    assert r is not None
    assert r.freshness == "fresh"


def test_missing_returns_none():
    s = InMemoryCacheStore()
    assert s.get("missing") is None


def test_delete():
    s = InMemoryCacheStore(jitter_factor=0)
    s.set("k", make_entry())
    assert s.delete("k")
    assert s.get("k") is None


def test_clear():
    s = InMemoryCacheStore(jitter_factor=0)
    s.set("a", make_entry())
    s.set("b", make_entry())
    s.clear()
    assert s.size == 0


def test_stale_within_grace():
    s = InMemoryCacheStore(jitter_factor=0, grace_factor=10)
    # TTL=10ms, grace=10*10=100ms → total lifetime 110ms
    s.set("k", make_entry(ttl_ms=10, cached_at=time.time() * 1000))
    time.sleep(0.02)  # 20ms: past 10ms TTL, within 110ms grace
    r = s.get("k")
    assert r is not None
    assert r.freshness == "stale"


def test_expired_past_grace():
    s = InMemoryCacheStore(jitter_factor=0, grace_factor=0)
    s.set("k", make_entry(ttl_ms=1, cached_at=time.time() * 1000))
    time.sleep(0.01)
    assert s.get("k") is None
    assert s.size == 0


def test_access_count_increments():
    s = InMemoryCacheStore(jitter_factor=0)
    s.set("k", make_entry(access_count=0))
    s.get("k")
    s.get("k")
    r = s.get("k")
    assert r is not None
    assert r.entry.access_count == 3


def test_eviction_at_capacity():
    s = InMemoryCacheStore(max_entries=3, jitter_factor=0)
    s.set("a", make_entry())
    s.set("b", make_entry())
    s.set("c", make_entry())
    s.set("d", make_entry())  # triggers eviction
    assert s.size == 3


def test_sieve_scan_resistance():
    s = InMemoryCacheStore(max_entries=5, jitter_factor=0)
    s.set("hot1", make_entry())
    s.set("hot2", make_entry())
    s.get("hot1")
    s.get("hot2")

    s.set("scan1", make_entry())
    s.set("scan2", make_entry())
    s.set("scan3", make_entry())

    # Overflow
    s.set("new1", make_entry())
    s.set("new2", make_entry())

    assert s.get("hot1") is not None
    assert s.get("hot2") is not None


def test_gdsf_prefers_evicting_cheap():
    s = InMemoryCacheStore(max_entries=3, jitter_factor=0)

    # Expensive entry, accessed
    s.set("expensive", make_entry(token_cost=120, access_count=5))
    s.get("expensive")

    # Cheap entries
    s.set("cheap1", make_entry(token_cost=8, access_count=0))
    s.set("cheap2", make_entry(token_cost=8, access_count=0))

    # Overflow
    s.set("new", make_entry(token_cost=8))

    assert s.get("expensive") is not None


def test_jitter_does_not_mutate_input():
    s = InMemoryCacheStore(jitter_factor=0.5)
    entry = make_entry(ttl_ms=1000)
    s.set("k", entry)
    assert entry.ttl_ms == 1000  # original unchanged


def test_jitter_zero_exact():
    s = InMemoryCacheStore(jitter_factor=0)
    s.set("k", make_entry(ttl_ms=5000))
    r = s.get("k")
    assert r is not None
    assert r.entry.ttl_ms == 5000


def test_update_existing():
    s = InMemoryCacheStore(max_entries=3, jitter_factor=0)
    s.set("a", make_entry(data="v1"))
    s.set("b", make_entry())
    s.set("c", make_entry())
    s.set("a", make_entry(data="v2"))  # update, not new insert
    assert s.size == 3
    assert s.get("a").entry.data == "v2"


def test_capacity_one():
    s = InMemoryCacheStore(max_entries=1, jitter_factor=0)
    s.set("a", make_entry(data="first"))
    s.set("b", make_entry(data="second"))
    assert s.size == 1
    assert s.get("a") is None
    assert s.get("b").entry.data == "second"

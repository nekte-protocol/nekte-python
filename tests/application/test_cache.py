"""Test CapabilityCache — negative caching, SWR, stats."""

from nekte.adapters.memory_cache_store import InMemoryCacheStore
from nekte.application.cache import CapabilityCache
from nekte.domain.types import CapabilityRef

ref = CapabilityRef(id="sentiment", cat="nlp", h="abc12345")


def make_cache(**kwargs):
    return CapabilityCache(
        store=InMemoryCacheStore(
            max_entries=kwargs.pop("max_entries", 100),
            jitter_factor=0,
            grace_factor=kwargs.pop("grace_factor", 2),
        ),
        **kwargs,
    )


def test_set_and_get_hash():
    c = make_cache()
    c.set("agent1", ref, 0)
    assert c.get_hash("agent1", "sentiment") == "abc12345"


def test_get_at_level():
    c = make_cache()
    c.set("agent1", ref, 0)
    result = c.get("agent1", "sentiment", 0)
    assert result is not None
    assert result["id"] == "sentiment"


def test_missing_returns_none():
    c = make_cache()
    assert c.get_hash("x", "y") is None
    assert c.get("x", "y", 0) is None


def test_is_valid():
    c = make_cache()
    c.set("a", ref, 0)
    assert c.is_valid("a", "sentiment", "abc12345")
    assert not c.is_valid("a", "sentiment", "wrong")


def test_invalidate():
    c = make_cache()
    c.set("a", ref, 0)
    c.invalidate("a", "sentiment")
    assert c.get_hash("a", "sentiment") is None


def test_invalidate_agent():
    c = make_cache()
    c.set("a", ref, 0)
    c.set("a", CapabilityRef(id="other", cat="x", h="h2"), 0)
    c.invalidate_agent("a")
    assert c.stats()["size"] == 0


def test_negative_caching():
    c = make_cache(negative_ttl_ms=60_000)
    c.set_negative("a", "missing")
    assert c.is_negative("a", "missing")
    assert c.get_hash("a", "missing") is None  # blocked by negative


def test_positive_clears_negative():
    c = make_cache(negative_ttl_ms=60_000)
    c.set_negative("a", "sentiment")
    c.set("a", ref, 0)
    assert not c.is_negative("a", "sentiment")
    assert c.get_hash("a", "sentiment") == "abc12345"


def test_stats():
    c = make_cache()
    c.set("agent1", ref, 0)
    c.set("agent2", CapabilityRef(id="x", cat="y", h="z"), 0)
    c.set_negative("agent3", "missing")
    s = c.stats()
    assert s["size"] == 2
    assert s["agents"] == 2
    assert s["negatives"] == 1


def test_clear():
    c = make_cache()
    c.set("a", ref, 0)
    c.set_negative("b", "x")
    c.clear()
    assert c.stats() == {"size": 0, "agents": 0, "negatives": 0}


def test_stale_triggers_revalidation():
    """SWR: accessing stale entry calls revalidation fn."""
    import time

    store = InMemoryCacheStore(max_entries=100, jitter_factor=0, grace_factor=10)
    c = CapabilityCache(store=store, default_ttl_ms=10)  # 10ms TTL, 110ms total

    calls: list[tuple[str, str]] = []
    c.on_revalidate(lambda a, cap: calls.append((a, cap)))

    c.set("a", ref, 0)
    time.sleep(0.02)  # 20ms: past 10ms TTL, within 110ms grace

    c.get_hash("a", "sentiment")  # should trigger revalidation
    assert len(calls) == 1
    assert calls[0] == ("a", "sentiment")


def test_revalidation_dedup():
    """SWR: multiple stale accesses trigger only one revalidation."""
    import time

    store = InMemoryCacheStore(max_entries=100, jitter_factor=0, grace_factor=10)
    c = CapabilityCache(store=store, default_ttl_ms=10)

    calls: list[tuple[str, str]] = []
    c.on_revalidate(lambda a, cap: calls.append((a, cap)))

    c.set("a", ref, 0)
    time.sleep(0.02)

    c.get_hash("a", "sentiment")
    c.get_hash("a", "sentiment")
    c.get_hash("a", "sentiment")

    assert len(calls) == 1

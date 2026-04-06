"""Test SIEVE eviction policy — scan resistance, second chance, edge cases."""

from nekte.domain.cache.sieve_policy import SievePolicy


def test_fifo_order_when_unvisited():
    s = SievePolicy[str]()
    s.insert("a")
    s.insert("b")
    s.insert("c")
    assert s.evict() == "a"
    assert s.evict() == "b"
    assert s.evict() == "c"


def test_second_chance_for_visited():
    s = SievePolicy[str]()
    s.insert("a")
    s.insert("b")
    s.insert("c")
    s.access("a")
    assert s.evict() == "b"  # a skipped (visited)


def test_scan_resistance():
    s = SievePolicy[str]()
    s.insert("hot1")
    s.insert("hot2")
    s.access("hot1")
    s.access("hot2")

    for i in range(10):
        s.insert(f"scan-{i}")

    evicted = [s.evict() for _ in range(10)]
    assert all(k is not None and k.startswith("scan-") for k in evicted)
    assert s.has("hot1")
    assert s.has("hot2")


def test_all_visited_terminates():
    s = SievePolicy[str]()
    for i in range(100):
        s.insert(f"k-{i}")
        s.access(f"k-{i}")
    result = s.evict()
    assert result is not None
    assert s.size == 99


def test_delete_head():
    s = SievePolicy[str]()
    s.insert("a")
    s.insert("b")
    s.delete("a")
    assert s.evict() == "b"


def test_delete_tail():
    s = SievePolicy[str]()
    s.insert("a")
    s.insert("b")
    s.delete("b")
    assert s.evict() == "a"


def test_delete_only():
    s = SievePolicy[str]()
    s.insert("x")
    s.delete("x")
    assert s.evict() is None


def test_empty_evict():
    s = SievePolicy[str]()
    assert s.evict() is None


def test_reinsert_acts_as_access():
    s = SievePolicy[str]()
    s.insert("a")
    s.insert("b")
    s.insert("a")  # should mark visited
    assert s.size == 2
    assert s.evict() == "b"


def test_clear():
    s = SievePolicy[str]()
    s.insert("a")
    s.insert("b")
    s.clear()
    assert s.size == 0
    assert s.evict() is None

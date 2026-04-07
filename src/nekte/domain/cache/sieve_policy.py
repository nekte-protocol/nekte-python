"""SIEVE Eviction Policy — Pure domain algorithm.

NSDI 2024: "SIEVE is Simpler than LRU"
A FIFO queue + hand pointer + visited bit. Scan-resistant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

K = TypeVar("K")


@dataclass
class _SieveNode(Generic[K]):
    key: K
    visited: bool = False
    prev: _SieveNode[K] | None = None
    next: _SieveNode[K] | None = None


class SievePolicy(Generic[K]):
    """SIEVE eviction policy with O(1) amortized eviction."""

    def __init__(self) -> None:
        self._head: _SieveNode[K] | None = None
        self._tail: _SieveNode[K] | None = None
        self._hand: _SieveNode[K] | None = None
        self._nodes: dict[K, _SieveNode[K]] = {}

    @property
    def size(self) -> int:
        return len(self._nodes)

    def has(self, key: K) -> bool:
        return key in self._nodes

    def access(self, key: K) -> None:
        """Mark an entry as visited (no reordering)."""
        node = self._nodes.get(key)
        if node is not None:
            node.visited = True

    def insert(self, key: K) -> None:
        """Insert at tail. Re-insert acts as access."""
        if key in self._nodes:
            self.access(key)
            return

        node = _SieveNode(key=key, prev=self._tail)
        if self._tail is not None:
            self._tail.next = node
        else:
            self._head = node
        self._tail = node
        self._nodes[key] = node

    def evict(self) -> K | None:
        """Evict one entry using the hand pointer. Returns evicted key or None."""
        if not self._nodes:
            return None

        if self._hand is None:
            self._hand = self._head

        max_iter = len(self._nodes) * 2
        for _ in range(max_iter):
            if self._hand is None:
                break
            if not self._hand.visited:
                victim = self._hand
                self._remove(victim)
                return victim.key
            self._hand.visited = False
            self._hand = self._hand.next or self._head

        # All were visited and cleared — evict current hand
        if self._hand is not None:
            victim = self._hand
            self._remove(victim)
            return victim.key

        return None

    def delete(self, key: K) -> None:
        """Remove a specific key."""
        node = self._nodes.get(key)
        if node is not None:
            self._remove(node)

    def clear(self) -> None:
        """Reset all state."""
        self._head = None
        self._tail = None
        self._hand = None
        self._nodes.clear()

    def _remove(self, node: _SieveNode[K]) -> None:
        if self._hand is node:
            self._hand = node.next or self._head
            if self._hand is node:
                self._hand = None

        if node.prev is not None:
            node.prev.next = node.next
        else:
            self._head = node.next

        if node.next is not None:
            node.next.prev = node.prev
        else:
            self._tail = node.prev

        node.prev = None
        node.next = None
        self._nodes.pop(node.key, None)

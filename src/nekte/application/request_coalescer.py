"""Request Coalescer — prevents thundering herd on concurrent requests."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


class RequestCoalescer:
    """Deduplicates concurrent async calls for the same key."""

    def __init__(self) -> None:
        self._inflight: dict[str, asyncio.Task[Any]] = {}

    async def coalesce(self, key: str, fn: Callable[[], Awaitable[T]]) -> T:
        """Execute fn for key, or join an in-flight request if one exists."""
        existing = self._inflight.get(key)
        if existing is not None:
            return await existing

        task = asyncio.create_task(self._run(key, fn))
        self._inflight[key] = task
        return await task

    async def _run(self, key: str, fn: Callable[[], Awaitable[Any]]) -> Any:
        try:
            return await fn()
        finally:
            self._inflight.pop(key, None)

    @property
    def pending(self) -> int:
        return len(self._inflight)

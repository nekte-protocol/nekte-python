"""DelegateStream — streaming delegate with cancel support."""

from __future__ import annotations

from typing import AsyncIterator

from ..domain.sse import SseEvent


class DelegateStream:
    """Streaming delegate with lifecycle control. Use as async iterator."""

    def __init__(
        self,
        task_id: str,
        events: AsyncIterator[SseEvent],
        cancel_fn: object,  # Callable[[str | None], Awaitable[None]]
    ) -> None:
        self._task_id = task_id
        self._events = events
        self._cancel_fn = cancel_fn

    @property
    def task_id(self) -> str:
        return self._task_id

    @property
    def events(self) -> AsyncIterator[SseEvent]:
        return self._events

    async def cancel(self, reason: str | None = None) -> None:
        """Cancel the task server-side."""
        await self._cancel_fn(reason)  # type: ignore[misc]

    def __aiter__(self) -> AsyncIterator[SseEvent]:
        return self._events

    async def __anext__(self) -> SseEvent:
        return await self._events.__anext__()

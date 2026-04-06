"""CancellationToken — Pythonic replacement for AbortController/AbortSignal."""

from __future__ import annotations

import asyncio


class CancellationToken:
    """Cooperative cancellation for async tasks. Thread-safe via asyncio.Event."""

    def __init__(self) -> None:
        self._event = asyncio.Event()
        self._reason: str | None = None

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str | None:
        return self._reason

    def cancel(self, reason: str | None = None) -> None:
        """Signal cancellation."""
        self._reason = reason
        self._event.set()

    async def wait_cancelled(self) -> None:
        """Await until cancellation is signalled."""
        await self._event.wait()

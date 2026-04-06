"""DelegateHandler Port — inbound task delegation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..application.cancellation import CancellationToken
    from ..domain.types import ContextEnvelope, Task
    from .stream_writer import StreamWriter


@runtime_checkable
class DelegateHandler(Protocol):
    """Port: handles delegated tasks. signal is required (CancellationToken)."""

    async def __call__(
        self,
        task: Task,
        stream: StreamWriter,
        context: ContextEnvelope | None,
        signal: CancellationToken,
    ) -> None: ...

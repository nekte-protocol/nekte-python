"""StreamWriter Port — streaming output (SSE, gRPC)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..domain.types import MultiLevelResult, TaskStatus


@runtime_checkable
class StreamWriter(Protocol):
    """Port: streaming output. Adapters: SseStreamWriter, GrpcStreamWriter."""

    def progress(self, processed: int, total: int, message: str | None = None) -> None: ...
    def partial(self, out: dict[str, Any], resolved_level: str | None = None) -> None: ...
    def complete(
        self, task_id: str, out: MultiLevelResult | dict[str, Any], meta: dict[str, Any] | None = None
    ) -> None: ...
    def error(self, code: int, message: str, task_id: str | None = None) -> None: ...
    def cancelled(
        self, task_id: str, previous_status: TaskStatus, reason: str | None = None
    ) -> None: ...
    def close(self) -> None: ...
    @property
    def is_closed(self) -> bool: ...

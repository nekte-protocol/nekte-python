"""Transport Port — outbound protocol communication."""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from ..domain.sse import SseEvent
from ..domain.types import NekteMethod, NekteResponse


@runtime_checkable
class Transport(Protocol):
    """Port: outbound transport. Adapters: HttpTransport, GrpcTransport."""

    async def rpc(self, method: NekteMethod, params: Any) -> NekteResponse: ...
    def stream(self, method: NekteMethod, params: Any) -> AsyncIterator[SseEvent]: ...
    async def get(self, url: str) -> Any: ...
    async def close(self) -> None: ...

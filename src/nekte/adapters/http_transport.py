"""HTTP Transport Adapter — implements Transport port using httpx."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..domain.sse import SseEvent, parse_sse_event
from ..domain.types import NekteMethod, NekteRequest, NekteResponse


class HttpTransport:
    """Transport adapter using httpx for HTTP + SSE."""

    def __init__(
        self,
        endpoint: str,
        *,
        headers: dict[str, str] | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._client = httpx.AsyncClient(timeout=timeout_s, headers=self._headers)
        self._request_id = 0

    async def rpc(self, method: NekteMethod, params: Any) -> NekteResponse:
        self._request_id += 1
        request = NekteRequest(method=method, id=self._request_id, params=params)
        resp = await self._client.post(self._endpoint, content=request.model_dump_json())
        resp.raise_for_status()
        return NekteResponse.model_validate(resp.json())

    async def stream(self, method: NekteMethod, params: Any) -> AsyncIterator[SseEvent]:
        self._request_id += 1
        request = NekteRequest(method=method, id=self._request_id, params=params)
        async with self._client.stream(
            "POST", self._endpoint, content=request.model_dump_json()
        ) as resp:
            resp.raise_for_status()
            buffer = ""
            async for chunk in resp.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    block, buffer = buffer.split("\n\n", 1)
                    block = block.strip()
                    if block:
                        event = parse_sse_event(block)
                        if event is not None:
                            yield event
            if buffer.strip():
                event = parse_sse_event(buffer.strip())
                if event is not None:
                    yield event

    async def get(self, url: str) -> Any:
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()

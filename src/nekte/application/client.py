"""NekteClient — Application Service (Hexagonal Architecture).

Orchestrates Transport (port) + CapabilityCache + RequestCoalescer.
Does NOT know about HTTP, gRPC, or any transport specifics.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Literal

from ..domain.budget import create_budget
from ..domain.errors import NekteProtocolError
from ..domain.sse import SseEvent
from ..domain.types import (
    AgentCard,
    ContextEnvelope,
    DiscoverParams,
    DiscoverResult,
    InvokeResult,
    NekteMethod,
    Task,
    TaskCancelParams,
    TaskLifecycleResult,
    TaskResumeParams,
    TaskStatusParams,
    TaskStatusResult,
    TokenBudget,
    NEKTE_ERRORS,
    WELL_KNOWN_PATH,
)
from ..ports.transport import Transport
from .cache import CapabilityCache
from .delegate_stream import DelegateStream
from .request_coalescer import RequestCoalescer


class NekteClient:
    """NEKTE protocol client with progressive discovery and zero-schema invocation."""

    def __init__(
        self,
        endpoint: str,
        *,
        transport: Transport,
        cache: CapabilityCache,
        default_budget: TokenBudget | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._transport = transport
        self._cache = cache
        self._default_budget = default_budget
        self._agent_id: str | None = None
        self._coalescer = RequestCoalescer()

        # Wire stale-while-revalidate
        self._cache.on_revalidate(self._on_revalidate)

    async def __aenter__(self) -> NekteClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    @property
    def cache(self) -> CapabilityCache:
        return self._cache

    # -- Agent Card --

    async def agent_card(self) -> AgentCard:
        data = await self._transport.get(f"{self._endpoint}{WELL_KNOWN_PATH}")
        card = AgentCard.model_validate(data)
        self._agent_id = card.agent
        return card

    # -- Discovery --

    async def discover(self, params: DiscoverParams) -> DiscoverResult:
        result = await self._rpc("nekte.discover", params.model_dump())
        dr = DiscoverResult.model_validate(result)

        if self._agent_id:
            for cap in dr.caps:
                if "id" in cap and "h" in cap:
                    from ..domain.types import CapabilityRef
                    self._cache.set(self._agent_id, CapabilityRef(**cap), params.level)

        if not self._agent_id:
            self._agent_id = dr.agent

        return dr

    async def catalog(self, filter: dict[str, Any] | None = None) -> DiscoverResult:
        return await self.discover(DiscoverParams(level=0, filter=filter))

    async def describe(self, cap_id: str) -> DiscoverResult:
        return await self.discover(DiscoverParams(level=1, filter={"id": cap_id}))

    async def schema(self, cap_id: str) -> DiscoverResult:
        return await self.discover(DiscoverParams(level=2, filter={"id": cap_id}))

    # -- Invoke --

    async def invoke(
        self,
        cap_id: str,
        *,
        input: dict[str, Any],
        budget: TokenBudget | None = None,
    ) -> InvokeResult:
        agent_id = self._agent_id or "unknown"
        cached_hash = self._cache.get_hash(agent_id, cap_id)
        b = budget or self._default_budget or create_budget()

        params: dict[str, Any] = {"cap": cap_id, "in": input, "budget": b.model_dump()}
        if cached_hash:
            params["h"] = cached_hash

        try:
            result = await self._rpc("nekte.invoke", params)
            return InvokeResult.model_validate(result)
        except NekteProtocolError as err:
            if err.is_version_mismatch and isinstance(err.data, dict):
                schema = err.data.get("schema")
                if schema and isinstance(schema, dict) and "id" in schema:
                    from ..domain.types import CapabilityRef
                    self._cache.set(agent_id, CapabilityRef(**schema), 2)
                # Retry without hash
                retry_params = {"cap": cap_id, "in": input, "budget": b.model_dump()}
                result = await self._rpc("nekte.invoke", retry_params)
                return InvokeResult.model_validate(result)
            raise

    # -- Delegate --

    def delegate_stream(
        self,
        task: Task,
        context: ContextEnvelope | None = None,
    ) -> DelegateStream:
        params = {"task": task.model_dump(), "context": context.model_dump() if context else None}
        events = self._transport.stream("nekte.delegate", params)

        async def cancel(reason: str | None = None) -> None:
            await self.cancel_task(task.id, reason)

        return DelegateStream(task_id=task.id, events=events, cancel_fn=cancel)

    # -- Task Lifecycle --

    async def cancel_task(self, task_id: str, reason: str | None = None) -> TaskLifecycleResult:
        result = await self._rpc("nekte.task.cancel", {"task_id": task_id, "reason": reason})
        return TaskLifecycleResult.model_validate(result)

    async def resume_task(
        self, task_id: str, budget: TokenBudget | None = None
    ) -> TaskLifecycleResult:
        params: dict[str, Any] = {"task_id": task_id}
        if budget:
            params["budget"] = budget.model_dump()
        result = await self._rpc("nekte.task.resume", params)
        return TaskLifecycleResult.model_validate(result)

    async def task_status(self, task_id: str) -> TaskStatusResult:
        result = await self._rpc("nekte.task.status", {"task_id": task_id})
        return TaskStatusResult.model_validate(result)

    # -- Verify --

    async def verify(
        self,
        task_id: str,
        checks: list[Literal["hash", "sample", "source"]] | None = None,
        budget: TokenBudget | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "task_id": task_id,
            "checks": checks or ["hash", "sample", "source"],
        }
        if budget:
            params["budget"] = budget.model_dump()
        return await self._rpc("nekte.verify", params)

    async def close(self) -> None:
        await self._transport.close()

    # -- Transport --

    async def _rpc(self, method: NekteMethod, params: Any) -> Any:
        response = await self._transport.rpc(method, params)
        if response.error:
            raise NekteProtocolError(
                response.error.code, response.error.message, response.error.data
            )
        return response.result

    def _on_revalidate(self, agent_id: str, cap_id: str) -> None:
        """Stale-while-revalidate callback — runs discover in background."""
        import asyncio

        key = f"revalidate:{agent_id}:{cap_id}"

        async def refresh() -> None:
            try:
                level = 2 if self._cache.get(agent_id, cap_id, 2) else (
                    1 if self._cache.get(agent_id, cap_id, 1) else 0
                )
                await self.discover(DiscoverParams(level=level, filter={"id": cap_id}))
            except Exception:
                pass  # Best-effort background refresh

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._coalescer.coalesce(key, refresh))
        except RuntimeError:
            pass  # No event loop — skip revalidation

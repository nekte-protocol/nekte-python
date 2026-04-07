"""NekteServer — Application Service (Hexagonal Architecture).

Orchestrates CapabilityRegistry + TaskRegistry.
Does NOT know about HTTP, Starlette, or any transport specifics.
The server is transport-agnostic — adapters handle wire format.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from ..domain.budget import create_budget, resolve_budget
from ..domain.errors import NekteProtocolError
from ..domain.types import (
    NEKTE_ERRORS,
    NEKTE_VERSION,
    AgentCard,
    ContextParams,
    DelegateParams,
    DiscoverParams,
    InvokeParams,
    NekteError,
    NekteMethod,
    NekteRequest,
    NekteResponse,
    TaskCancelParams,
    TaskResumeParams,
    TaskStatusParams,
    VerifyParams,
)
from .cancellation import CancellationToken
from .capability_registry import CapabilityConfig, CapabilityRegistry, HandlerContext
from .task_registry import (
    TaskNotCancellableError,
    TaskNotFoundError,
    TaskNotResumableError,
    TaskRegistry,
)

DelegateHandler = Callable[..., Awaitable[None]]


class NekteServer:
    """NEKTE protocol server — register capabilities, handle requests."""

    def __init__(self, agent: str, *, version: str | None = None) -> None:
        self.agent = agent
        self.version = version
        self.registry = CapabilityRegistry()
        self.tasks = TaskRegistry()
        self._delegate_handler: DelegateHandler | None = None
        self._contexts: dict[str, Any] = {}
        self._context_timestamps: dict[str, float] = {}

    def capability(
        self,
        cap_id: str,
        *,
        input_model: type,
        output_model: type,
        category: str,
        description: str,
        handler: Callable[..., Any],
        to_minimal: Callable[[Any], str] | None = None,
        to_compact: Callable[[Any], dict[str, Any]] | None = None,
        cost: dict[str, float] | None = None,
    ) -> None:
        """Register a capability."""
        self.registry.register(
            cap_id,
            CapabilityConfig(
                input_model=input_model,
                output_model=output_model,
                category=category,
                description=description,
                handler=handler,
                to_minimal=to_minimal,
                to_compact=to_compact,
                cost=cost,
            ),
        )

    def on_delegate(self, handler: DelegateHandler) -> None:
        """Register the streaming delegate handler."""
        self._delegate_handler = handler

    def agent_card(self, endpoint: str) -> AgentCard:
        return AgentCard(
            nekte=NEKTE_VERSION,
            agent=self.agent,
            endpoint=endpoint,
            caps=[c.id for c in self.registry.all()],
            auth="none",
            budget_support=True,
        )

    async def handle_request(self, request: NekteRequest) -> NekteResponse:
        """Main dispatch — transport-agnostic."""
        method = request.method
        params = request.params
        rid = request.id

        try:
            if method == "nekte.discover":
                return self._ok(rid, await self._handle_discover(params))
            elif method == "nekte.invoke":
                return self._ok(rid, await self._handle_invoke(params))
            elif method == "nekte.delegate":
                return self._ok(rid, await self._handle_delegate(params))
            elif method == "nekte.context":
                return self._ok(rid, self._handle_context(params))
            elif method == "nekte.verify":
                return self._ok(rid, await self._handle_verify(params))
            elif method == "nekte.task.cancel":
                return self._ok(rid, self._handle_task_cancel(params))
            elif method == "nekte.task.resume":
                return self._ok(rid, self._handle_task_resume(params))
            elif method == "nekte.task.status":
                return self._ok(rid, self._handle_task_status(params))
            else:
                return self._error(rid, -32601, f"Method not found: {method}")
        except NekteProtocolError as e:
            return NekteResponse(
                id=rid, error=NekteError(code=e.code, message=e.message, data=e.data)
            )
        except Exception as e:
            return self._error(rid, -32000, str(e))

    # -- Handlers --

    async def _handle_discover(self, params: Any) -> dict[str, Any]:
        p = DiscoverParams.model_validate(params) if isinstance(params, dict) else params
        caps = self.registry.filter(
            category=p.filter.get("category") if p.filter else None,
            query=p.filter.get("query") if p.filter else None,
            cap_id=p.filter.get("id") if p.filter else None,
        )
        return {
            "agent": self.agent,
            "v": self.version,
            "caps": [self.registry.project(c.schema, p.level) for c in caps],
        }

    async def _handle_invoke(self, params: Any) -> dict[str, Any]:
        p = InvokeParams.model_validate(params) if isinstance(params, dict) else params
        cap = self.registry.get(p.cap)
        if not cap:
            raise NekteProtocolError(NEKTE_ERRORS["CAPABILITY_NOT_FOUND"], "CAPABILITY_NOT_FOUND")

        if p.h and p.h != cap.version_hash:
            raise NekteProtocolError(
                NEKTE_ERRORS["VERSION_MISMATCH"],
                "VERSION_MISMATCH",
                {"current_hash": cap.version_hash, "schema": cap.schema.model_dump()},
            )

        budget = p.budget or create_budget()
        ctx = HandlerContext(budget=budget, signal=CancellationToken())
        result = await self.registry.invoke(p.cap, p.input, ctx)
        resolved_data, resolved_level = resolve_budget(result, budget)

        return {
            "out": resolved_data,
            "resolved_level": resolved_level.value
            if hasattr(resolved_level, "value")
            else resolved_level,
        }

    async def _handle_delegate(self, params: Any) -> dict[str, Any]:
        p = DelegateParams.model_validate(params) if isinstance(params, dict) else params
        if p.context:
            self._contexts[p.context.id] = p.context

        caps = self.registry.all()
        if not caps:
            raise ValueError("No capabilities registered to handle delegation")

        words = p.task.desc.lower().split()
        match = next(
            (
                c
                for c in caps
                if any(w in c.id.lower() or w in c.schema.desc.lower() for w in words)
            ),
            None,
        )
        if not match:
            return {
                "task_id": p.task.id,
                "status": "failed",
                "error": {"code": "NO_MATCHING_CAPABILITY"},
            }

        ctx = HandlerContext(
            budget=p.task.budget, signal=CancellationToken(), context=p.context, task_id=p.task.id
        )
        result = await self.registry.invoke(match.id, p.task.model_dump(), ctx)
        return {"task_id": p.task.id, "status": "completed", "out": result.model_dump()}

    def _handle_context(self, params: Any) -> dict[str, Any]:
        import time

        p = ContextParams.model_validate(params) if isinstance(params, dict) else params

        if p.action == "share":
            self._contexts[p.envelope.id] = p.envelope
            self._context_timestamps[p.envelope.id] = time.time()
            return {"id": p.envelope.id, "status": "stored"}
        elif p.action == "request":
            ctx = self._contexts.get(p.envelope.id)
            if not ctx:
                return {"id": p.envelope.id, "status": "not_found"}
            stored_at = self._context_timestamps.get(p.envelope.id, 0)
            age_s = time.time() - stored_at
            if age_s > ctx.ttl_s:
                del self._contexts[p.envelope.id]
                raise NekteProtocolError(NEKTE_ERRORS["CONTEXT_EXPIRED"], "CONTEXT_EXPIRED")
            return ctx.model_dump() if hasattr(ctx, "model_dump") else dict(ctx)
        elif p.action == "revoke":
            self._contexts.pop(p.envelope.id, None)
            self._context_timestamps.pop(p.envelope.id, None)
            return {"id": p.envelope.id, "status": "revoked"}
        else:
            raise ValueError(f"Unknown context action: {p.action}")

    async def _handle_verify(self, params: Any) -> dict[str, Any]:
        import hashlib, json

        p = VerifyParams.model_validate(params) if isinstance(params, dict) else params
        task_entry = self.tasks.get(p.task_id)
        result: dict[str, Any] = {"task_id": p.task_id, "checks": p.checks, "status": "verified"}

        for check in p.checks:
            if check == "hash":
                if task_entry:
                    hash_input = json.dumps({"task_id": p.task_id, "status": task_entry.status})
                    result["hash"] = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
                    result["hash_valid"] = True
                else:
                    result["hash_valid"] = False
            elif check == "sample":
                result["sample"] = {"task_found": task_entry is not None} if task_entry else None
            elif check == "source":
                result["source"] = {"agent": self.agent, "version": self.version}
        return result

    def _handle_task_cancel(self, params: Any) -> dict[str, Any]:
        p = TaskCancelParams.model_validate(params) if isinstance(params, dict) else params
        entry = self.tasks.get_or_raise(p.task_id)
        previous = entry.status
        self.tasks.cancel(p.task_id, p.reason)
        return self.tasks.to_lifecycle_result(
            self.tasks.get_or_raise(p.task_id), previous
        ).model_dump()

    def _handle_task_resume(self, params: Any) -> dict[str, Any]:
        p = TaskResumeParams.model_validate(params) if isinstance(params, dict) else params
        entry = self.tasks.get_or_raise(p.task_id)
        previous = entry.status
        self.tasks.resume(p.task_id)
        return self.tasks.to_lifecycle_result(
            self.tasks.get_or_raise(p.task_id), previous
        ).model_dump()

    def _handle_task_status(self, params: Any) -> dict[str, Any]:
        p = TaskStatusParams.model_validate(params) if isinstance(params, dict) else params
        return self.tasks.to_status_result(p.task_id).model_dump()

    # -- Helpers --

    @staticmethod
    def _ok(rid: str | int, result: Any) -> NekteResponse:
        return NekteResponse(id=rid, result=result)

    @staticmethod
    def _error(rid: str | int, code: int, message: str) -> NekteResponse:
        return NekteResponse(id=rid, error=NekteError(code=code, message=message))

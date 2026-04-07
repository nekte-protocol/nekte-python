"""CapabilityRegistry — Domain Service.

Registers capabilities with Pydantic models, auto-generates version hashes,
and produces multi-level projections (L0/L1/L2).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

from ..domain.budget import resolve_budget
from ..domain.hash import compute_version_hash
from ..domain.types import (
    CapabilityRef,
    CapabilitySchema,
    CapabilitySummary,
    DetailLevel,
    MultiLevelResult,
    TokenBudget,
)
from .cancellation import CancellationToken


@dataclass(frozen=True)
class HandlerContext:
    """Context passed to capability handlers."""

    budget: TokenBudget
    signal: CancellationToken
    context: Any | None = None
    task_id: str | None = None
    checkpoint: dict[str, Any] | None = None


CapabilityHandler = Callable[..., Any | Awaitable[Any]]


@dataclass(frozen=True)
class CapabilityConfig:
    """Configuration for a registered capability."""

    input_model: type[BaseModel]
    output_model: type[BaseModel]
    category: str
    description: str
    handler: CapabilityHandler
    to_minimal: Callable[[Any], str] | None = None
    to_compact: Callable[[Any], dict[str, Any]] | None = None
    cost: dict[str, float] | None = None
    examples: list[dict[str, Any]] | None = None


@dataclass
class RegisteredCapability:
    """A capability registered in the registry."""

    id: str
    config: CapabilityConfig
    schema: CapabilitySchema
    version_hash: str


class CapabilityRegistry:
    """Domain Service: register, discover, and invoke capabilities."""

    def __init__(self) -> None:
        self._capabilities: dict[str, RegisteredCapability] = {}

    def register(self, cap_id: str, config: CapabilityConfig) -> RegisteredCapability:
        """Register a capability with auto-generated version hash."""
        input_schema = self._model_to_json_schema(config.input_model)
        output_schema = self._model_to_json_schema(config.output_model)
        version_hash = compute_version_hash(input_schema, output_schema)

        schema = CapabilitySchema(
            id=cap_id,
            cat=config.category,
            h=version_hash,
            desc=config.description,
            cost=config.cost,
            input=input_schema,
            output=output_schema,
            examples=config.examples,
        )

        registered = RegisteredCapability(
            id=cap_id,
            config=config,
            schema=schema,
            version_hash=version_hash,
        )
        self._capabilities[cap_id] = registered
        return registered

    def get(self, cap_id: str) -> RegisteredCapability | None:
        return self._capabilities.get(cap_id)

    def all(self) -> list[RegisteredCapability]:
        return list(self._capabilities.values())

    def filter(
        self, category: str | None = None, query: str | None = None, cap_id: str | None = None
    ) -> list[RegisteredCapability]:
        caps = self.all()
        if cap_id:
            found = self.get(cap_id)
            return [found] if found else []
        if category:
            caps = [c for c in caps if c.schema.cat == category]
        if query:
            q = query.lower()
            caps = [c for c in caps if q in c.id.lower() or q in c.schema.desc.lower()]
        return caps

    async def invoke(self, cap_id: str, input_data: Any, ctx: HandlerContext) -> MultiLevelResult:
        """Validate input, execute handler, build multi-level result."""
        cap = self._capabilities.get(cap_id)
        if not cap:
            raise ValueError(f"Capability not found: {cap_id}")

        # Validate input with Pydantic model
        parsed = cap.config.input_model.model_validate(input_data)

        # Execute handler
        start = time.monotonic()
        result = cap.config.handler(parsed, ctx)
        if hasattr(result, "__await__"):
            result = await result
        ms = round((time.monotonic() - start) * 1000)

        # Build multi-level result
        full: dict[str, Any]
        if isinstance(result, BaseModel):
            full = result.model_dump()
        elif isinstance(result, dict):
            full = dict(result)
        else:
            full = {"value": result}
        full["_meta"] = {"ms": ms}

        return MultiLevelResult(
            minimal=cap.config.to_minimal(result) if cap.config.to_minimal else None,
            compact=cap.config.to_compact(result) if cap.config.to_compact else full,
            full=full,
        )

    def project(self, schema: CapabilitySchema, level: int) -> dict[str, Any]:
        """Project a capability to the requested discovery level."""
        if level == 0:
            return CapabilityRef(id=schema.id, cat=schema.cat, h=schema.h).model_dump()
        if level == 1:
            return CapabilitySummary(
                id=schema.id, cat=schema.cat, h=schema.h, desc=schema.desc, cost=schema.cost
            ).model_dump()
        return schema.model_dump()

    @staticmethod
    def _model_to_json_schema(model: type[BaseModel]) -> dict[str, Any]:
        """Convert Pydantic model to JSON Schema dict."""
        return model.model_json_schema()

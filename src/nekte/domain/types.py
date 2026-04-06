"""NEKTE Protocol Types — Value Objects (Pydantic models).

Every type mirrors the TypeScript SDK exactly. Field names match the wire format.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Token Budget
# ---------------------------------------------------------------------------

class DetailLevel(str, Enum):
    MINIMAL = "minimal"
    COMPACT = "compact"
    FULL = "full"


class TokenBudget(BaseModel):
    max_tokens: int = Field(gt=0)
    detail_level: DetailLevel


# ---------------------------------------------------------------------------
# Discovery levels
# ---------------------------------------------------------------------------

DiscoveryLevel = Literal[0, 1, 2]


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

class CapabilityRef(BaseModel):
    id: str
    cat: str
    h: str


class CapabilitySummary(CapabilityRef):
    desc: str
    cost: dict[str, Any] | None = None


class CapabilitySchema(CapabilitySummary):
    input: dict[str, Any]
    output: dict[str, Any]
    examples: list[dict[str, Any]] | None = None


Capability = Union[CapabilityRef, CapabilitySummary, CapabilitySchema]


# ---------------------------------------------------------------------------
# Agent Card
# ---------------------------------------------------------------------------

class AgentCard(BaseModel):
    nekte: str = "0.2"
    agent: str
    endpoint: str
    caps: list[str]
    auth: Literal["bearer", "apikey", "none"] | None = None
    budget_support: bool | None = None


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

ContextCompression = Literal["none", "semantic", "reference"]


class ContextPermissions(BaseModel):
    forward: bool
    persist: bool
    derive: bool


class ContextEnvelope(BaseModel):
    id: str
    data: dict[str, Any]
    compression: ContextCompression
    permissions: ContextPermissions
    ttl_s: float = Field(gt=0)
    budget_hint: float | None = None


# ---------------------------------------------------------------------------
# Multi-level result
# ---------------------------------------------------------------------------

class MultiLevelResult(BaseModel):
    minimal: Any | None = None
    compact: dict[str, Any] | None = None
    full: dict[str, Any] | None = None


class InvokeResult(BaseModel):
    out: dict[str, Any] | MultiLevelResult
    resolved_level: DetailLevel | None = None
    meta: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

class VerificationProof(BaseModel):
    hash: str | None = None
    samples: int | None = None
    evidence: list[dict[str, Any]] | None = None
    source: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

TaskStatus = Literal[
    "pending", "accepted", "running",
    "completed", "failed", "cancelled", "suspended",
]

TerminalTaskStatus = Literal["completed", "failed", "cancelled"]
ActiveTaskStatus = Literal["pending", "accepted", "running", "suspended"]


class Task(BaseModel):
    id: str
    desc: str
    timeout_ms: int = Field(gt=0)
    budget: TokenBudget


class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    out: MultiLevelResult | None = None
    proof: VerificationProof | None = None
    error: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# JSON-RPC
# ---------------------------------------------------------------------------

NekteMethod = Literal[
    "nekte.discover",
    "nekte.invoke",
    "nekte.delegate",
    "nekte.context",
    "nekte.verify",
    "nekte.task.cancel",
    "nekte.task.resume",
    "nekte.task.status",
]


class NekteRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    method: NekteMethod
    id: str | int
    params: Any = None


class NekteError(BaseModel):
    code: int
    message: str
    data: Any = None


class NekteResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    result: Any = None
    error: NekteError | None = None


# ---------------------------------------------------------------------------
# Method params
# ---------------------------------------------------------------------------

class DiscoverParams(BaseModel):
    level: DiscoveryLevel
    filter: dict[str, Any] | None = None


class DiscoverResult(BaseModel):
    agent: str
    v: str | None = None
    caps: list[dict[str, Any]]


class InvokeParams(BaseModel):
    cap: str
    h: str | None = None
    input: dict[str, Any] = Field(alias="in")
    budget: TokenBudget | None = None

    model_config = {"populate_by_name": True}


class DelegateParams(BaseModel):
    task: Task
    context: ContextEnvelope | None = None


class ContextParams(BaseModel):
    action: Literal["share", "request", "revoke"]
    envelope: ContextEnvelope


class VerifyParams(BaseModel):
    task_id: str
    checks: list[Literal["hash", "sample", "source"]]
    budget: TokenBudget | None = None


class TaskCancelParams(BaseModel):
    task_id: str
    reason: str | None = None


class TaskResumeParams(BaseModel):
    task_id: str
    budget: TokenBudget | None = None


class TaskStatusParams(BaseModel):
    task_id: str


class TaskStatusResult(BaseModel):
    task_id: str
    status: TaskStatus
    progress: dict[str, int] | None = None
    checkpoint_available: bool
    created_at: float
    updated_at: float


class TaskLifecycleResult(BaseModel):
    task_id: str
    status: TaskStatus
    previous_status: TaskStatus


# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

NEKTE_ERRORS: dict[str, int] = {
    "VERSION_MISMATCH": -32001,
    "CAPABILITY_NOT_FOUND": -32002,
    "BUDGET_EXCEEDED": -32003,
    "CONTEXT_EXPIRED": -32004,
    "CONTEXT_PERMISSION_DENIED": -32005,
    "TASK_TIMEOUT": -32006,
    "TASK_FAILED": -32007,
    "VERIFICATION_FAILED": -32008,
    "TASK_NOT_FOUND": -32009,
    "TASK_NOT_CANCELLABLE": -32010,
    "TASK_NOT_RESUMABLE": -32011,
}

WELL_KNOWN_PATH = "/.well-known/nekte.json"
NEKTE_VERSION = "0.3.0"

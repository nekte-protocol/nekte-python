"""NEKTE Protocol — Token-efficient agent-to-agent coordination.

Usage:
    from nekte import NekteClient
    # ... or import from specific layers:
    from nekte.domain import TokenBudget, Task
    from nekte.ports import Transport, CacheStore
    from nekte.application import NekteClient, CapabilityCache
    from nekte.adapters import HttpTransport, InMemoryCacheStore
"""

from .adapters import HttpTransport, InMemoryCacheStore
from .application.cache import CapabilityCache
from .application.cancellation import CancellationToken
from .application.client import NekteClient
from .application.delegate_stream import DelegateStream
from .domain.errors import NekteProtocolError, TaskTransitionError
from .domain.types import (
    NEKTE_ERRORS,
    NEKTE_VERSION,
    AgentCard,
    Capability,
    CapabilityRef,
    CapabilitySchema,
    CapabilitySummary,
    ContextEnvelope,
    ContextPermissions,
    DelegateParams,
    DetailLevel,
    DiscoverParams,
    DiscoverResult,
    InvokeParams,
    InvokeResult,
    MultiLevelResult,
    NekteMethod,
    NekteRequest,
    NekteResponse,
    Task,
    TaskCancelParams,
    TaskLifecycleResult,
    TaskResult,
    TaskResumeParams,
    TaskStatus,
    TaskStatusParams,
    TaskStatusResult,
    TokenBudget,
    VerifyParams,
)

__version__ = NEKTE_VERSION
__all__ = [
    "NEKTE_ERRORS",
    "NEKTE_VERSION",
    "AgentCard",
    "CancellationToken",
    "Capability",
    "CapabilityCache",
    "CapabilityRef",
    "CapabilitySchema",
    "CapabilitySummary",
    "ContextEnvelope",
    "ContextPermissions",
    "DelegateParams",
    "DelegateStream",
    "DetailLevel",
    "DiscoverParams",
    "DiscoverResult",
    "HttpTransport",
    "InMemoryCacheStore",
    "InvokeParams",
    "InvokeResult",
    "MultiLevelResult",
    "NekteClient",
    "NekteMethod",
    "NekteProtocolError",
    "NekteRequest",
    "NekteResponse",
    "Task",
    "TaskCancelParams",
    "TaskLifecycleResult",
    "TaskResult",
    "TaskResumeParams",
    "TaskStatus",
    "TaskStatusParams",
    "TaskStatusResult",
    "TaskTransitionError",
    "TokenBudget",
    "VerifyParams",
]

"""NEKTE Protocol — Token-efficient agent-to-agent coordination.

Usage:
    from nekte import NekteClient
    # ... or import from specific layers:
    from nekte.domain import TokenBudget, Task
    from nekte.ports import Transport, CacheStore
    from nekte.application import NekteClient, CapabilityCache
    from nekte.adapters import HttpTransport, InMemoryCacheStore
"""

from .domain.types import (
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
    TaskResumeParams,
    TaskResult,
    TaskStatus,
    TaskStatusParams,
    TaskStatusResult,
    TokenBudget,
    VerifyParams,
    NEKTE_ERRORS,
    NEKTE_VERSION,
)
from .domain.errors import NekteProtocolError, TaskTransitionError
from .application.client import NekteClient
from .application.cache import CapabilityCache
from .application.delegate_stream import DelegateStream
from .application.cancellation import CancellationToken
from .adapters import HttpTransport, InMemoryCacheStore

__version__ = NEKTE_VERSION
__all__ = [
    "NekteClient",
    "NekteProtocolError",
    "TaskTransitionError",
    "CapabilityCache",
    "DelegateStream",
    "CancellationToken",
    "HttpTransport",
    "InMemoryCacheStore",
    "AgentCard",
    "TokenBudget",
    "Task",
    "DiscoverParams",
    "DiscoverResult",
    "InvokeResult",
    "MultiLevelResult",
    "DetailLevel",
    "TaskStatus",
    "NEKTE_ERRORS",
    "NEKTE_VERSION",
]

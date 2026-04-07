"""NEKTE Task Domain Model — Aggregate Root with state machine.

State Machine:
  pending -> accepted -> running -> completed
                      -> suspended -> running (resume)
  (any non-terminal) -> cancelled | failed

All domain objects are IMMUTABLE. State transitions return new instances.
This enforces DDD invariants: you cannot bypass the state machine.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .errors import TaskTransitionError
from .types import ContextEnvelope, Task, TaskStatus

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

TASK_TRANSITIONS: dict[TaskStatus, tuple[TaskStatus, ...]] = {
    "pending": ("accepted", "cancelled", "failed"),
    "accepted": ("running", "cancelled", "failed"),
    "running": ("completed", "failed", "cancelled", "suspended"),
    "completed": (),
    "failed": (),
    "cancelled": (),
    "suspended": ("running", "cancelled", "failed"),
}

CANCELLABLE_STATES: tuple[TaskStatus, ...] = ("pending", "accepted", "running", "suspended")
RESUMABLE_STATES: tuple[TaskStatus, ...] = ("suspended",)
TERMINAL_STATES: tuple[TaskStatus, ...] = ("completed", "failed", "cancelled")


def is_valid_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    return to_status in TASK_TRANSITIONS.get(from_status, ())


def is_terminal(status: TaskStatus) -> bool:
    return status in TERMINAL_STATES


def is_active(status: TaskStatus) -> bool:
    return not is_terminal(status)


def is_cancellable(status: TaskStatus) -> bool:
    return status in CANCELLABLE_STATES


def is_resumable(status: TaskStatus) -> bool:
    return status in RESUMABLE_STATES


# ---------------------------------------------------------------------------
# Value Objects (frozen — immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskCheckpoint:
    """Immutable checkpoint snapshot."""

    data: dict[str, Any]
    created_at: float


@dataclass(frozen=True)
class TaskTransition:
    """Immutable record of a single state transition."""

    from_status: TaskStatus
    to_status: TaskStatus
    timestamp: float
    reason: str | None = None


# ---------------------------------------------------------------------------
# Aggregate Root (frozen — state changes return NEW instances)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskEntry:
    """Immutable Aggregate Root for task lifecycle.

    All state changes go through transition() or with_checkpoint(),
    which return new TaskEntry instances. Direct mutation is impossible
    because this dataclass is frozen.
    """

    task: Task
    status: TaskStatus
    context: ContextEnvelope | None
    checkpoint: TaskCheckpoint | None
    transitions: tuple[TaskTransition, ...]
    created_at: float
    updated_at: float

    def transition(self, to: TaskStatus, reason: str | None = None) -> TaskEntry:
        """Return a new TaskEntry with the transitioned status.

        Raises TaskTransitionError if the transition is invalid.
        """
        if not is_valid_transition(self.status, to):
            raise TaskTransitionError(self.task.id, self.status, to)

        now = time.time()
        new_transition = TaskTransition(
            from_status=self.status,
            to_status=to,
            timestamp=now,
            reason=reason,
        )

        return TaskEntry(
            task=self.task,
            status=to,
            context=self.context,
            checkpoint=self.checkpoint,
            transitions=(*self.transitions, new_transition),
            created_at=self.created_at,
            updated_at=now,
        )

    def with_checkpoint(self, data: dict[str, Any]) -> TaskEntry:
        """Return a new TaskEntry with checkpoint data saved.

        Only valid in 'running' or 'suspended' state.
        """
        if self.status not in ("running", "suspended"):
            raise ValueError(f"Cannot checkpoint task in '{self.status}' state")

        now = time.time()
        return TaskEntry(
            task=self.task,
            status=self.status,
            context=self.context,
            checkpoint=TaskCheckpoint(data=data, created_at=now),
            transitions=self.transitions,
            created_at=self.created_at,
            updated_at=now,
        )


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_task_entry(task: Task, context: ContextEnvelope | None = None) -> TaskEntry:
    """Factory: create a new TaskEntry in 'pending' state."""
    now = time.time()
    return TaskEntry(
        task=task,
        status="pending",
        context=context,
        checkpoint=None,
        transitions=(),
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Backwards-compatible free functions (delegate to methods)
# ---------------------------------------------------------------------------


def transition_task(entry: TaskEntry, to: TaskStatus, reason: str | None = None) -> TaskEntry:
    """Transition a task. Returns a NEW TaskEntry (old one is unchanged)."""
    return entry.transition(to, reason)


def save_checkpoint(entry: TaskEntry, data: dict[str, Any]) -> TaskEntry:
    """Save checkpoint. Returns a NEW TaskEntry (old one is unchanged)."""
    return entry.with_checkpoint(data)

"""NEKTE Task Domain Model — Aggregate Root with state machine.

State Machine:
  pending -> accepted -> running -> completed
                      -> suspended -> running (resume)
  (any non-terminal) -> cancelled | failed
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
# Value Objects
# ---------------------------------------------------------------------------


@dataclass
class TaskCheckpoint:
    data: dict[str, Any]
    created_at: float


@dataclass
class TaskTransition:
    from_status: TaskStatus
    to_status: TaskStatus
    timestamp: float
    reason: str | None = None


# ---------------------------------------------------------------------------
# Aggregate Root
# ---------------------------------------------------------------------------


@dataclass
class TaskEntry:
    task: Task
    status: TaskStatus
    context: ContextEnvelope | None
    checkpoint: TaskCheckpoint | None
    transitions: list[TaskTransition]
    created_at: float
    updated_at: float


def create_task_entry(task: Task, context: ContextEnvelope | None = None) -> TaskEntry:
    """Factory: create a new TaskEntry in 'pending' state."""
    now = time.time()
    return TaskEntry(
        task=task,
        status="pending",
        context=context,
        checkpoint=None,
        transitions=[],
        created_at=now,
        updated_at=now,
    )


def transition_task(entry: TaskEntry, to: TaskStatus, reason: str | None = None) -> TaskEntry:
    """Transition a task to a new status. Raises TaskTransitionError if invalid."""
    if not is_valid_transition(entry.status, to):
        raise TaskTransitionError(entry.task.id, entry.status, to)

    now = time.time()
    entry.transitions.append(
        TaskTransition(
            from_status=entry.status,
            to_status=to,
            timestamp=now,
            reason=reason,
        )
    )
    entry.status = to
    entry.updated_at = now
    return entry


def save_checkpoint(entry: TaskEntry, data: dict[str, Any]) -> TaskEntry:
    """Save a checkpoint on a running/suspended task."""
    if entry.status not in ("running", "suspended"):
        raise ValueError(f"Cannot checkpoint task in '{entry.status}' state")
    entry.checkpoint = TaskCheckpoint(data=data, created_at=time.time())
    entry.updated_at = time.time()
    return entry

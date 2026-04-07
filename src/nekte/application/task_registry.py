"""TaskRegistry — Domain Service + Repository.

Manages the lifecycle of delegated tasks: registration, state transitions,
cancellation via CancellationToken, checkpointing, and cleanup.
"""

from __future__ import annotations

from typing import Any

from ..domain.errors import NekteProtocolError
from ..domain.task import (
    TaskEntry,
    create_task_entry,
    is_cancellable,
    is_resumable,
    is_terminal,
)
from ..domain.types import (
    NEKTE_ERRORS,
    ContextEnvelope,
    Task,
    TaskLifecycleResult,
    TaskStatus,
    TaskStatusResult,
)
from .cancellation import CancellationToken


class TaskNotFoundError(NekteProtocolError):
    def __init__(self, task_id: str) -> None:
        super().__init__(NEKTE_ERRORS["TASK_NOT_FOUND"], f"Task not found: {task_id}")
        self.task_id = task_id


class TaskNotCancellableError(NekteProtocolError):
    def __init__(self, task_id: str, status: TaskStatus) -> None:
        super().__init__(
            NEKTE_ERRORS["TASK_NOT_CANCELLABLE"],
            f"Task '{task_id}' in '{status}' state cannot be cancelled",
        )


class TaskNotResumableError(NekteProtocolError):
    def __init__(self, task_id: str, status: TaskStatus) -> None:
        super().__init__(
            NEKTE_ERRORS["TASK_NOT_RESUMABLE"],
            f"Task '{task_id}' in '{status}' state cannot be resumed",
        )


class TaskRegistry:
    """Domain Service + Repository for task lifecycle management."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskEntry] = {}
        self._tokens: dict[str, CancellationToken] = {}

    def register(self, task: Task, context: ContextEnvelope | None = None) -> TaskEntry:
        """Register a new task. Returns entry + creates CancellationToken."""
        if task.id in self._tasks:
            raise ValueError(f"Task already registered: {task.id}")

        entry = create_task_entry(task, context)
        self._tasks[task.id] = entry
        self._tokens[task.id] = CancellationToken()
        return entry

    def get(self, task_id: str) -> TaskEntry | None:
        return self._tasks.get(task_id)

    def get_or_raise(self, task_id: str) -> TaskEntry:
        entry = self._tasks.get(task_id)
        if not entry:
            raise TaskNotFoundError(task_id)
        return entry

    def token(self, task_id: str) -> CancellationToken:
        """Get the CancellationToken for a task."""
        t = self._tokens.get(task_id)
        if not t:
            raise TaskNotFoundError(task_id)
        return t

    def transition(self, task_id: str, to: TaskStatus, reason: str | None = None) -> TaskEntry:
        """Transition a task. Updates the stored entry."""
        entry = self.get_or_raise(task_id)
        new_entry = entry.transition(to, reason)
        self._tasks[task_id] = new_entry
        return new_entry

    def cancel(self, task_id: str, reason: str | None = None) -> TaskEntry:
        """Cancel a task and fire the CancellationToken."""
        entry = self.get_or_raise(task_id)
        if not is_cancellable(entry.status):
            raise TaskNotCancellableError(task_id, entry.status)

        new_entry = entry.transition("cancelled", reason)
        self._tasks[task_id] = new_entry
        self._tokens[task_id].cancel(reason)
        return new_entry

    def suspend(self, task_id: str, checkpoint_data: dict[str, Any] | None = None) -> TaskEntry:
        entry = self.get_or_raise(task_id)
        new_entry = entry.transition("suspended")
        if checkpoint_data:
            new_entry = new_entry.with_checkpoint(checkpoint_data)
        self._tasks[task_id] = new_entry
        return new_entry

    def resume(self, task_id: str) -> TaskEntry:
        entry = self.get_or_raise(task_id)
        if not is_resumable(entry.status):
            raise TaskNotResumableError(task_id, entry.status)
        new_entry = entry.transition("running", "Resumed")
        self._tasks[task_id] = new_entry
        return new_entry

    def save_checkpoint(self, task_id: str, data: dict[str, Any]) -> TaskEntry:
        entry = self.get_or_raise(task_id)
        new_entry = entry.with_checkpoint(data)
        self._tasks[task_id] = new_entry
        return new_entry

    def to_status_result(self, task_id: str) -> TaskStatusResult:
        entry = self.get_or_raise(task_id)
        return TaskStatusResult(
            task_id=entry.task.id,
            status=entry.status,
            checkpoint_available=entry.checkpoint is not None,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    def to_lifecycle_result(
        self, entry: TaskEntry, previous_status: TaskStatus
    ) -> TaskLifecycleResult:
        return TaskLifecycleResult(
            task_id=entry.task.id,
            status=entry.status,
            previous_status=previous_status,
        )

    def active(self) -> list[TaskEntry]:
        return [e for e in self._tasks.values() if not is_terminal(e.status)]

    def all(self) -> list[TaskEntry]:
        return list(self._tasks.values())

    @property
    def size(self) -> int:
        return len(self._tasks)

    def cleanup(self, max_age_s: float = 300) -> int:
        """Remove terminal tasks older than max_age_s. Returns count removed."""
        import time

        threshold = time.time() - max_age_s
        to_remove = [
            tid
            for tid, entry in self._tasks.items()
            if is_terminal(entry.status) and entry.updated_at < threshold
        ]
        for tid in to_remove:
            del self._tasks[tid]
            self._tokens.pop(tid, None)
        return len(to_remove)

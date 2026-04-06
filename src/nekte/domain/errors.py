"""NEKTE Domain Errors."""

from __future__ import annotations

from .types import NEKTE_ERRORS, TaskStatus


class NekteProtocolError(Exception):
    """Raised when a NEKTE protocol operation fails."""

    def __init__(self, code: int, message: str, data: object = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    @property
    def is_version_mismatch(self) -> bool:
        return self.code == NEKTE_ERRORS["VERSION_MISMATCH"]

    @property
    def is_capability_not_found(self) -> bool:
        return self.code == NEKTE_ERRORS["CAPABILITY_NOT_FOUND"]

    @property
    def is_budget_exceeded(self) -> bool:
        return self.code == NEKTE_ERRORS["BUDGET_EXCEEDED"]

    @property
    def is_context_expired(self) -> bool:
        return self.code == NEKTE_ERRORS["CONTEXT_EXPIRED"]

    @property
    def is_task_timeout(self) -> bool:
        return self.code == NEKTE_ERRORS["TASK_TIMEOUT"]

    @property
    def is_task_failed(self) -> bool:
        return self.code == NEKTE_ERRORS["TASK_FAILED"]

    @property
    def is_task_not_found(self) -> bool:
        return self.code == NEKTE_ERRORS["TASK_NOT_FOUND"]

    @property
    def is_task_not_cancellable(self) -> bool:
        return self.code == NEKTE_ERRORS["TASK_NOT_CANCELLABLE"]

    @property
    def is_task_not_resumable(self) -> bool:
        return self.code == NEKTE_ERRORS["TASK_NOT_RESUMABLE"]


class TaskTransitionError(Exception):
    """Raised when an invalid task state transition is attempted."""

    def __init__(self, task_id: str, from_status: TaskStatus, to_status: TaskStatus) -> None:
        super().__init__(
            f"Invalid task transition: '{from_status}' -> '{to_status}' for task '{task_id}'"
        )
        self.task_id = task_id
        self.from_status = from_status
        self.to_status = to_status

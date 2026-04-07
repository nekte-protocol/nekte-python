"""Test domain error types."""

from nekte.domain.errors import NekteProtocolError, TaskTransitionError
from nekte.domain.types import NEKTE_ERRORS


def test_protocol_error_properties():
    err = NekteProtocolError(NEKTE_ERRORS["VERSION_MISMATCH"], "VERSION_MISMATCH")
    assert err.is_version_mismatch
    assert not err.is_capability_not_found
    assert str(err) == "VERSION_MISMATCH"


def test_protocol_error_all_properties():
    checks = {
        "VERSION_MISMATCH": "is_version_mismatch",
        "CAPABILITY_NOT_FOUND": "is_capability_not_found",
        "BUDGET_EXCEEDED": "is_budget_exceeded",
        "CONTEXT_EXPIRED": "is_context_expired",
        "TASK_TIMEOUT": "is_task_timeout",
        "TASK_FAILED": "is_task_failed",
        "TASK_NOT_FOUND": "is_task_not_found",
        "TASK_NOT_CANCELLABLE": "is_task_not_cancellable",
        "TASK_NOT_RESUMABLE": "is_task_not_resumable",
    }
    for error_name, prop_name in checks.items():
        err = NekteProtocolError(NEKTE_ERRORS[error_name], error_name)
        assert getattr(err, prop_name) is True, f"{prop_name} should be True for {error_name}"


def test_protocol_error_data():
    err = NekteProtocolError(-32001, "test", data={"schema": {"id": "x"}})
    assert err.data == {"schema": {"id": "x"}}


def test_task_transition_error():
    err = TaskTransitionError("t-1", "pending", "completed")
    assert err.task_id == "t-1"
    assert err.from_status == "pending"
    assert err.to_status == "completed"
    assert "pending" in str(err)
    assert "completed" in str(err)

"""Test task state machine — transitions, terminal states, checkpoint, immutability."""

import pytest

from nekte.domain.errors import TaskTransitionError
from nekte.domain.task import (
    create_task_entry,
    is_active,
    is_cancellable,
    is_resumable,
    is_terminal,
    is_valid_transition,
    save_checkpoint,
    transition_task,
)
from nekte.domain.types import Task, TokenBudget


def make_task(task_id: str = "t-001") -> Task:
    return Task(
        id=task_id,
        desc="test",
        timeout_ms=5000,
        budget=TokenBudget(max_tokens=100, detail_level="compact"),
    )


def test_valid_transitions():
    assert is_valid_transition("pending", "accepted")
    assert is_valid_transition("running", "completed")
    assert is_valid_transition("running", "suspended")
    assert is_valid_transition("suspended", "running")


def test_invalid_transitions():
    assert not is_valid_transition("completed", "running")
    assert not is_valid_transition("pending", "completed")
    assert not is_valid_transition("cancelled", "running")


def test_terminal_states():
    assert is_terminal("completed")
    assert is_terminal("failed")
    assert is_terminal("cancelled")
    assert not is_terminal("running")
    assert not is_terminal("suspended")


def test_active_states():
    assert is_active("pending")
    assert is_active("running")
    assert is_active("suspended")
    assert not is_active("completed")


def test_cancellable():
    assert is_cancellable("pending")
    assert is_cancellable("running")
    assert is_cancellable("suspended")
    assert not is_cancellable("completed")


def test_resumable():
    assert is_resumable("suspended")
    assert not is_resumable("running")
    assert not is_resumable("pending")


def test_create_entry():
    entry = create_task_entry(make_task())
    assert entry.status == "pending"
    assert len(entry.transitions) == 0


def test_transition_returns_new_entry():
    original = create_task_entry(make_task())
    transitioned = transition_task(original, "accepted")

    # Original is unchanged (immutable)
    assert original.status == "pending"
    assert len(original.transitions) == 0

    # New entry has the transition
    assert transitioned.status == "accepted"
    assert len(transitioned.transitions) == 1
    assert transitioned.transitions[0].from_status == "pending"
    assert transitioned.transitions[0].to_status == "accepted"


def test_invalid_transition_raises():
    entry = create_task_entry(make_task())
    with pytest.raises(TaskTransitionError):
        transition_task(entry, "completed")


def test_full_lifecycle():
    entry = create_task_entry(make_task())
    entry = transition_task(entry, "accepted")
    entry = transition_task(entry, "running")
    entry = transition_task(entry, "completed")
    assert entry.status == "completed"
    assert len(entry.transitions) == 3


def test_suspend_resume():
    entry = create_task_entry(make_task())
    entry = transition_task(entry, "accepted")
    entry = transition_task(entry, "running")
    entry = transition_task(entry, "suspended")
    assert entry.status == "suspended"
    entry = transition_task(entry, "running")
    assert entry.status == "running"


def test_checkpoint_returns_new_entry():
    entry = create_task_entry(make_task())
    entry = transition_task(entry, "accepted")
    entry = transition_task(entry, "running")

    original = entry
    checkpointed = save_checkpoint(entry, {"batch": 50})

    assert original.checkpoint is None
    assert checkpointed.checkpoint is not None
    assert checkpointed.checkpoint.data == {"batch": 50}


def test_checkpoint_invalid_state():
    entry = create_task_entry(make_task())
    with pytest.raises(ValueError):
        save_checkpoint(entry, {"x": 1})


# ---------------------------------------------------------------------------
# Immutability tests (DDD invariant enforcement)
# ---------------------------------------------------------------------------


def test_entry_is_frozen():
    """TaskEntry is immutable — direct mutation raises."""
    entry = create_task_entry(make_task())
    with pytest.raises(AttributeError):
        entry.status = "accepted"  # type: ignore[misc]


def test_checkpoint_is_frozen():
    """TaskCheckpoint is immutable."""
    entry = create_task_entry(make_task())
    entry = transition_task(entry, "accepted")
    entry = transition_task(entry, "running")
    entry = save_checkpoint(entry, {"x": 1})
    with pytest.raises(AttributeError):
        entry.checkpoint.data = {}  # type: ignore[misc]


def test_transition_record_is_frozen():
    """TaskTransition is immutable."""
    entry = create_task_entry(make_task())
    entry = transition_task(entry, "accepted")
    with pytest.raises(AttributeError):
        entry.transitions[0].from_status = "running"  # type: ignore[misc]


def test_method_transition():
    """Test the method-based API (entry.transition())."""
    entry = create_task_entry(make_task())
    entry2 = entry.transition("accepted")
    assert entry.status == "pending"
    assert entry2.status == "accepted"


def test_method_with_checkpoint():
    """Test the method-based API (entry.with_checkpoint())."""
    entry = create_task_entry(make_task())
    entry = entry.transition("accepted").transition("running")
    entry2 = entry.with_checkpoint({"progress": 50})
    assert entry.checkpoint is None
    assert entry2.checkpoint is not None

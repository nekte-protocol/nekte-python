"""Test Pydantic type serialization round-trips."""

from nekte.domain.types import (
    NEKTE_ERRORS,
    AgentCard,
    CapabilityRef,
    CapabilitySummary,
    ContextEnvelope,
    ContextPermissions,
    DetailLevel,
    DiscoverParams,
    InvokeResult,
    MultiLevelResult,
    NekteRequest,
    NekteResponse,
    Task,
    TaskLifecycleResult,
    TaskStatusResult,
    TokenBudget,
)


def test_token_budget_round_trip():
    b = TokenBudget(max_tokens=500, detail_level=DetailLevel.COMPACT)
    d = b.model_dump()
    assert d["max_tokens"] == 500
    assert d["detail_level"] == "compact"
    b2 = TokenBudget.model_validate(d)
    assert b2 == b


def test_capability_ref():
    r = CapabilityRef(id="sentiment", cat="nlp", h="abc12345")
    assert r.id == "sentiment"
    d = r.model_dump()
    assert d == {"id": "sentiment", "cat": "nlp", "h": "abc12345"}


def test_capability_summary_extends_ref():
    s = CapabilitySummary(id="x", cat="y", h="z", desc="Test", cost={"avg_ms": 100})
    assert s.desc == "Test"
    assert s.id == "x"


def test_agent_card():
    card = AgentCard(agent="test", endpoint="http://localhost:4001", caps=["a", "b"])
    assert card.nekte == "0.2"
    assert card.auth is None


def test_context_envelope():
    env = ContextEnvelope(
        id="ctx-1",
        data={"key": "value"},
        compression="none",
        permissions=ContextPermissions(forward=False, persist=False, derive=True),
        ttl_s=3600,
    )
    d = env.model_dump()
    assert d["ttl_s"] == 3600
    assert d["permissions"]["derive"] is True


def test_task():
    t = Task(
        id="t-1",
        desc="test task",
        timeout_ms=5000,
        budget=TokenBudget(max_tokens=100, detail_level="compact"),
    )
    assert t.budget.max_tokens == 100


def test_multi_level_result():
    r = MultiLevelResult(minimal="hello", compact={"x": 1})
    assert r.full is None


def test_invoke_result():
    r = InvokeResult(out={"score": 0.9}, resolved_level=DetailLevel.COMPACT)
    assert r.resolved_level == DetailLevel.COMPACT


def test_nekte_request():
    req = NekteRequest(method="nekte.discover", id=1, params={"level": 0})
    assert req.jsonrpc == "2.0"


def test_nekte_response_with_error():
    resp = NekteResponse.model_validate(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32001, "message": "VERSION_MISMATCH"},
        }
    )
    assert resp.error is not None
    assert resp.error.code == -32001


def test_discover_params():
    p = DiscoverParams(level=0, filter={"category": "nlp"})
    assert p.level == 0


def test_task_status_result():
    r = TaskStatusResult(
        task_id="t-1",
        status="running",
        checkpoint_available=False,
        created_at=1000.0,
        updated_at=2000.0,
    )
    assert r.status == "running"


def test_task_lifecycle_result():
    r = TaskLifecycleResult(task_id="t-1", status="cancelled", previous_status="running")
    assert r.previous_status == "running"


def test_nekte_errors_complete():
    assert len(NEKTE_ERRORS) == 11
    assert NEKTE_ERRORS["VERSION_MISMATCH"] == -32001
    assert NEKTE_ERRORS["TASK_NOT_RESUMABLE"] == -32011

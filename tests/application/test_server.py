"""Test NekteServer — capability registration, request dispatch, task lifecycle."""

import pytest

from pydantic import BaseModel

from nekte.application.server import NekteServer
from nekte.domain.types import NekteRequest


class TextInput(BaseModel):
    text: str


class ScoreOutput(BaseModel):
    score: float
    label: str


def make_server() -> NekteServer:
    server = NekteServer("test-agent", version="1.0.0")
    server.capability(
        "sentiment",
        input_model=TextInput,
        output_model=ScoreOutput,
        category="nlp",
        description="Analyze text sentiment",
        handler=lambda inp, ctx: ScoreOutput(score=0.9, label="positive"),
        to_minimal=lambda out: f"{out.label} {out.score}",
        to_compact=lambda out: {"label": out.label, "score": out.score},
    )
    return server


# -- Agent Card --


def test_agent_card():
    server = make_server()
    card = server.agent_card("http://localhost:4001")
    assert card.agent == "test-agent"
    assert "sentiment" in card.caps


# -- Discover --


@pytest.mark.asyncio
async def test_discover_l0():
    server = make_server()
    req = NekteRequest(method="nekte.discover", id=1, params={"level": 0})
    resp = await server.handle_request(req)
    assert resp.error is None
    assert resp.result["agent"] == "test-agent"
    assert len(resp.result["caps"]) == 1
    assert "id" in resp.result["caps"][0]


@pytest.mark.asyncio
async def test_discover_l1():
    server = make_server()
    req = NekteRequest(
        method="nekte.discover", id=1, params={"level": 1, "filter": {"id": "sentiment"}}
    )
    resp = await server.handle_request(req)
    assert resp.result["caps"][0]["desc"] == "Analyze text sentiment"


# -- Invoke --


@pytest.mark.asyncio
async def test_invoke():
    server = make_server()
    req = NekteRequest(
        method="nekte.invoke", id=2, params={"cap": "sentiment", "in": {"text": "great"}}
    )
    resp = await server.handle_request(req)
    assert resp.error is None
    assert "out" in resp.result


@pytest.mark.asyncio
async def test_invoke_capability_not_found():
    server = make_server()
    req = NekteRequest(method="nekte.invoke", id=2, params={"cap": "nonexistent", "in": {}})
    resp = await server.handle_request(req)
    assert resp.error is not None
    assert resp.error.code == -32002


@pytest.mark.asyncio
async def test_invoke_version_mismatch():
    server = make_server()
    req = NekteRequest(
        method="nekte.invoke", id=2, params={"cap": "sentiment", "h": "wrong", "in": {"text": "hi"}}
    )
    resp = await server.handle_request(req)
    assert resp.error is not None
    assert resp.error.code == -32001
    assert "current_hash" in resp.error.data


# -- Context --


@pytest.mark.asyncio
async def test_context_share_and_request():
    server = make_server()

    # Share
    share_req = NekteRequest(
        method="nekte.context",
        id=3,
        params={
            "action": "share",
            "envelope": {
                "id": "ctx-1",
                "data": {"key": "val"},
                "compression": "none",
                "permissions": {"forward": False, "persist": False, "derive": True},
                "ttl_s": 3600,
            },
        },
    )
    resp = await server.handle_request(share_req)
    assert resp.result["status"] == "stored"

    # Request
    req_req = NekteRequest(
        method="nekte.context",
        id=4,
        params={
            "action": "request",
            "envelope": {
                "id": "ctx-1",
                "data": {},
                "compression": "none",
                "permissions": {"forward": False, "persist": False, "derive": True},
                "ttl_s": 3600,
            },
        },
    )
    resp = await server.handle_request(req_req)
    assert resp.error is None


@pytest.mark.asyncio
async def test_context_revoke():
    server = make_server()
    req = NekteRequest(
        method="nekte.context",
        id=5,
        params={
            "action": "revoke",
            "envelope": {
                "id": "ctx-1",
                "data": {},
                "compression": "none",
                "permissions": {"forward": False, "persist": False, "derive": True},
                "ttl_s": 3600,
            },
        },
    )
    resp = await server.handle_request(req)
    assert resp.result["status"] == "revoked"


# -- Verify --


@pytest.mark.asyncio
async def test_verify():
    server = make_server()
    req = NekteRequest(
        method="nekte.verify",
        id=6,
        params={
            "task_id": "t-1",
            "checks": ["hash", "source"],
        },
    )
    resp = await server.handle_request(req)
    assert resp.result["status"] == "verified"
    assert resp.result["source"]["agent"] == "test-agent"


# -- Task Lifecycle --


@pytest.mark.asyncio
async def test_task_cancel():
    server = make_server()
    # Register a task first
    from nekte.domain.types import Task, TokenBudget

    task = Task(
        id="t-cancel",
        desc="test",
        timeout_ms=5000,
        budget=TokenBudget(max_tokens=100, detail_level="compact"),
    )
    server.tasks.register(task)
    server.tasks.transition("t-cancel", "accepted")
    server.tasks.transition("t-cancel", "running")

    req = NekteRequest(
        method="nekte.task.cancel", id=7, params={"task_id": "t-cancel", "reason": "test"}
    )
    resp = await server.handle_request(req)
    assert resp.error is None
    assert resp.result["status"] == "cancelled"
    assert resp.result["previous_status"] == "running"


@pytest.mark.asyncio
async def test_task_status():
    server = make_server()
    from nekte.domain.types import Task, TokenBudget

    task = Task(
        id="t-status",
        desc="test",
        timeout_ms=5000,
        budget=TokenBudget(max_tokens=100, detail_level="compact"),
    )
    server.tasks.register(task)
    server.tasks.transition("t-status", "accepted")

    req = NekteRequest(method="nekte.task.status", id=8, params={"task_id": "t-status"})
    resp = await server.handle_request(req)
    assert resp.result["status"] == "accepted"


@pytest.mark.asyncio
async def test_unknown_method():
    server = make_server()
    # Bypass Pydantic validation to test server dispatch with invalid method
    req = NekteRequest.model_construct(jsonrpc="2.0", method="nekte.unknown", id=9, params=None)
    resp = await server.handle_request(req)
    assert resp.error is not None
    assert resp.error.code == -32601

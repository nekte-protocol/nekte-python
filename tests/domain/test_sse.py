"""Test SSE event encode/parse round-trips."""

from nekte.domain.sse import (
    SseCancelledEvent,
    SseCompleteEvent,
    SseErrorEvent,
    SseProgressEvent,
    encode_sse_event,
    parse_sse_event,
    parse_sse_stream,
)


def test_encode_progress():
    event = SseProgressEvent(data={"processed": 5, "total": 10, "message": "Step 5"})
    encoded = encode_sse_event(event)
    assert encoded.startswith("event: progress\n")
    assert '"processed": 5' in encoded
    assert encoded.endswith("\n\n")


def test_parse_progress():
    block = 'event: progress\ndata: {"processed":5,"total":10}'
    event = parse_sse_event(block)
    assert event is not None
    assert event.event == "progress"
    assert event.data["processed"] == 5


def test_round_trip_complete():
    original = SseCompleteEvent(
        data={"task_id": "t-1", "status": "completed", "out": {"minimal": "done"}}
    )
    encoded = encode_sse_event(original)
    parsed = parse_sse_event(encoded.strip())
    assert parsed is not None
    assert parsed.event == "complete"
    assert parsed.data["task_id"] == "t-1"


def test_round_trip_error():
    original = SseErrorEvent(data={"code": -32007, "message": "TASK_FAILED"})
    encoded = encode_sse_event(original)
    parsed = parse_sse_event(encoded.strip())
    assert parsed is not None
    assert parsed.data["code"] == -32007


def test_round_trip_cancelled():
    original = SseCancelledEvent(
        data={"task_id": "t-1", "reason": "user", "previous_status": "running"}
    )
    encoded = encode_sse_event(original)
    parsed = parse_sse_event(encoded.strip())
    assert parsed is not None
    assert parsed.event == "cancelled"


def test_parse_incomplete_returns_none():
    assert parse_sse_event("event: progress") is None
    assert parse_sse_event("data: {}") is None
    assert parse_sse_event("") is None


def test_parse_invalid_json_returns_none():
    assert parse_sse_event("event: progress\ndata: {invalid}") is None


def test_parse_unknown_event_returns_none():
    assert parse_sse_event("event: unknown_type\ndata: {}") is None


def test_parse_stream():
    stream = (
        'event: progress\ndata: {"processed":1,"total":3}\n\n'
        'event: progress\ndata: {"processed":2,"total":3}\n\n'
        'event: complete\ndata: {"task_id":"t-1","status":"completed","out":{}}\n\n'
    )
    events = parse_sse_stream(stream)
    assert len(events) == 3
    assert events[0].event == "progress"
    assert events[2].event == "complete"


def test_parse_stream_with_empty_blocks():
    stream = '\n\nevent: progress\ndata: {"processed":1,"total":1}\n\n\n\n'
    events = parse_sse_stream(stream)
    assert len(events) == 1

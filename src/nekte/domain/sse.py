"""NEKTE SSE (Server-Sent Events) — types + encode/parse (pure)."""

from __future__ import annotations

import json
from typing import Any, Literal, Union

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class SseProgressEvent(BaseModel):
    event: Literal["progress"] = "progress"
    data: dict[str, Any]  # { processed, total, message? }


class SsePartialEvent(BaseModel):
    event: Literal["partial"] = "partial"
    data: dict[str, Any]  # { out, resolved_level? }


class SseCompleteEvent(BaseModel):
    event: Literal["complete"] = "complete"
    data: dict[str, Any]  # { task_id, status, out, meta? }


class SseErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    data: dict[str, Any]  # { task_id?, code, message }


class SseCancelledEvent(BaseModel):
    event: Literal["cancelled"] = "cancelled"
    data: dict[str, Any]  # { task_id, reason?, previous_status }


class SseSuspendedEvent(BaseModel):
    event: Literal["suspended"] = "suspended"
    data: dict[str, Any]  # { task_id, checkpoint_available }


class SseResumedEvent(BaseModel):
    event: Literal["resumed"] = "resumed"
    data: dict[str, Any]  # { task_id, from_checkpoint }


class SseStatusChangeEvent(BaseModel):
    event: Literal["status_change"] = "status_change"
    data: dict[str, Any]  # { task_id, from, to, reason? }


SseEvent = Union[
    SseProgressEvent,
    SsePartialEvent,
    SseCompleteEvent,
    SseErrorEvent,
    SseCancelledEvent,
    SseSuspendedEvent,
    SseResumedEvent,
    SseStatusChangeEvent,
]

SSE_CONTENT_TYPE = "text/event-stream"


# ---------------------------------------------------------------------------
# Encode / Parse
# ---------------------------------------------------------------------------


def encode_sse_event(event: SseEvent) -> str:
    """Encode a NEKTE SSE event to text/event-stream format."""
    return f"event: {event.event}\ndata: {json.dumps(event.data)}\n\n"


def parse_sse_event(block: str) -> SseEvent | None:
    """Parse a single SSE event block. Returns None if incomplete."""
    event_type: str | None = None
    data_str: str | None = None

    for line in block.split("\n"):
        if line.startswith("event: "):
            event_type = line[7:].strip()
        elif line.startswith("data: "):
            data_str = line[6:]

    if not event_type or not data_str:
        return None

    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        return None

    event_map: dict[str, type[SseEvent]] = {
        "progress": SseProgressEvent,
        "partial": SsePartialEvent,
        "complete": SseCompleteEvent,
        "error": SseErrorEvent,
        "cancelled": SseCancelledEvent,
        "suspended": SseSuspendedEvent,
        "resumed": SseResumedEvent,
        "status_change": SseStatusChangeEvent,
    }

    cls = event_map.get(event_type)
    if cls is None:
        return None

    return cls(event=event_type, data=data)  # type: ignore[arg-type]


def parse_sse_stream(text: str) -> list[SseEvent]:
    """Parse a full SSE stream into events."""
    events: list[SseEvent] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if block:
            event = parse_sse_event(block)
            if event is not None:
                events.append(event)
    return events

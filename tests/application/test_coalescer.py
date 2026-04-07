"""Test RequestCoalescer — concurrent deduplication."""

import asyncio

import pytest

from nekte.application.request_coalescer import RequestCoalescer


@pytest.mark.asyncio
async def test_executes_fn():
    c = RequestCoalescer()

    async def fn() -> str:
        return "hello"

    result = await c.coalesce("k", fn)
    assert result == "hello"


@pytest.mark.asyncio
async def test_coalesces_concurrent():
    c = RequestCoalescer()
    call_count = 0

    async def slow():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return "result"

    results = await asyncio.gather(
        c.coalesce("k", slow),
        c.coalesce("k", slow),
        c.coalesce("k", slow),
    )

    assert call_count == 1
    assert all(r == "result" for r in results)


@pytest.mark.asyncio
async def test_different_keys_independent():
    c = RequestCoalescer()
    counts = {"a": 0, "b": 0}

    async def fn_a():
        counts["a"] += 1
        return "a"

    async def fn_b():
        counts["b"] += 1
        return "b"

    ra, rb = await asyncio.gather(c.coalesce("a", fn_a), c.coalesce("b", fn_b))
    assert ra == "a"
    assert rb == "b"
    assert counts == {"a": 1, "b": 1}


@pytest.mark.asyncio
async def test_allows_retry_after_completion():
    c = RequestCoalescer()
    n = 0

    async def fn():
        nonlocal n
        n += 1
        return n

    r1 = await c.coalesce("k", fn)
    r2 = await c.coalesce("k", fn)
    assert r1 == 1
    assert r2 == 2


@pytest.mark.asyncio
async def test_cleans_up_on_error():
    c = RequestCoalescer()

    async def failing():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await c.coalesce("k", failing)

    assert c.pending == 0

    async def ok():
        return "recovered"

    result = await c.coalesce("k", ok)
    assert result == "recovered"

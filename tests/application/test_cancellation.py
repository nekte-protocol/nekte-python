"""Test CancellationToken."""

import asyncio

import pytest

from nekte.application.cancellation import CancellationToken


def test_initial_state():
    token = CancellationToken()
    assert not token.is_cancelled
    assert token.reason is None


def test_cancel():
    token = CancellationToken()
    token.cancel("user requested")
    assert token.is_cancelled
    assert token.reason == "user requested"


def test_cancel_no_reason():
    token = CancellationToken()
    token.cancel()
    assert token.is_cancelled
    assert token.reason is None


@pytest.mark.asyncio
async def test_wait_cancelled():
    token = CancellationToken()

    async def cancel_later():
        await asyncio.sleep(0.01)
        token.cancel("timeout")

    _task = asyncio.create_task(cancel_later())  # noqa: RUF006
    await token.wait_cancelled()
    assert token.is_cancelled
    assert token.reason == "timeout"

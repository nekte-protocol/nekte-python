"""Test budget resolution and token estimation."""

from nekte.domain.budget import create_budget, estimate_tokens, resolve_budget
from nekte.domain.types import DetailLevel, MultiLevelResult, TokenBudget


def test_estimate_tokens_string():
    assert estimate_tokens("hello world") == 3  # 11 chars / 4 = 2.75 → 3


def test_estimate_tokens_dict():
    tokens = estimate_tokens({"key": "value"})
    assert tokens > 0


def test_create_budget_defaults():
    b = create_budget()
    assert b.max_tokens == 500
    assert b.detail_level == DetailLevel.COMPACT


def test_create_budget_overrides():
    b = create_budget(max_tokens=100, detail_level="minimal")
    assert b.max_tokens == 100
    assert b.detail_level == DetailLevel.MINIMAL


def test_resolve_budget_full():
    result = MultiLevelResult(
        minimal="short",
        compact={"score": 0.9},
        full={"score": 0.9, "details": "very long explanation " * 50},
    )
    budget = TokenBudget(max_tokens=4096, detail_level=DetailLevel.FULL)
    _data, level = resolve_budget(result, budget)
    assert level == DetailLevel.FULL


def test_resolve_budget_compact():
    result = MultiLevelResult(minimal="short", compact={"score": 0.9})
    budget = TokenBudget(max_tokens=50, detail_level=DetailLevel.COMPACT)
    _data, level = resolve_budget(result, budget)
    assert level == DetailLevel.COMPACT


def test_resolve_budget_minimal_fallback():
    result = MultiLevelResult(minimal="ok", compact={"x": "y" * 10000})
    budget = TokenBudget(max_tokens=10, detail_level=DetailLevel.COMPACT)
    _data, level = resolve_budget(result, budget)
    assert level == DetailLevel.MINIMAL


def test_resolve_budget_no_budget():
    result = MultiLevelResult(compact={"x": 1})
    _data, level = resolve_budget(result, None)
    assert level == DetailLevel.COMPACT

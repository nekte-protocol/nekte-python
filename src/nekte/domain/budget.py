"""NEKTE Token Budget — resolution and estimation (pure logic)."""

from __future__ import annotations

import json
import math
from typing import Any

from .types import DetailLevel, MultiLevelResult, TokenBudget

DEFAULT_BUDGETS: dict[DetailLevel, TokenBudget] = {
    DetailLevel.MINIMAL: TokenBudget(max_tokens=50, detail_level=DetailLevel.MINIMAL),
    DetailLevel.COMPACT: TokenBudget(max_tokens=500, detail_level=DetailLevel.COMPACT),
    DetailLevel.FULL: TokenBudget(max_tokens=4096, detail_level=DetailLevel.FULL),
}


def estimate_tokens(value: Any) -> int:
    """Rough token estimation: ~4 characters per token."""
    text = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"))
    return math.ceil(len(text) / 4)


def resolve_budget(
    result: MultiLevelResult, budget: TokenBudget | None = None
) -> tuple[Any, DetailLevel]:
    """Resolve which detail level to return based on budget. Returns (data, level)."""
    requested = budget.detail_level if budget else DetailLevel.COMPACT
    max_tokens = budget.max_tokens if budget else 500

    levels: list[DetailLevel]
    if requested == DetailLevel.FULL:
        levels = [DetailLevel.FULL, DetailLevel.COMPACT, DetailLevel.MINIMAL]
    elif requested == DetailLevel.COMPACT:
        levels = [DetailLevel.COMPACT, DetailLevel.MINIMAL]
    else:
        levels = [DetailLevel.MINIMAL]

    for level in levels:
        data = getattr(result, level.value, None)
        if data is not None and estimate_tokens(data) <= max_tokens:
            return data, level

    # Last resort: return minimal even if over budget
    if result.minimal is not None:
        return result.minimal, DetailLevel.MINIMAL
    if result.compact is not None:
        return result.compact, DetailLevel.COMPACT
    return result.full, DetailLevel.FULL


def create_budget(
    max_tokens: int = 500,
    detail_level: DetailLevel | str = DetailLevel.COMPACT,
) -> TokenBudget:
    """Create a token budget with sensible defaults."""
    dl = DetailLevel(detail_level) if isinstance(detail_level, str) else detail_level
    return TokenBudget(max_tokens=max_tokens, detail_level=dl)

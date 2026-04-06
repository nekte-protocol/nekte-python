"""Token Cost — Value Object mapping discovery levels to re-fetch cost."""

from __future__ import annotations

from ..types import DiscoveryLevel

TOKEN_COST: dict[DiscoveryLevel, int] = {
    0: 8,    # L0 catalog
    1: 40,   # L1 summary
    2: 120,  # L2 full schema
}


def token_cost_for_level(level: DiscoveryLevel) -> int:
    return TOKEN_COST[level]

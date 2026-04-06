"""NEKTE Version Hashing — deterministic, cross-SDK compatible.

MUST produce the same 8-char hex as the TypeScript SDK.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonicalize(value: Any) -> str:
    """Canonicalize a value for stable hashing. Object keys sorted recursively."""
    return json.dumps(_sort_recursive(value), separators=(",", ":"), sort_keys=True)


def compute_version_hash(input_schema: dict[str, Any], output_schema: dict[str, Any]) -> str:
    """Compute 8-char hex hash of input+output schemas. Cross-SDK deterministic."""
    canonical = canonicalize({"input": input_schema, "output": output_schema})
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]


def _sort_recursive(value: Any) -> Any:
    """Recursively sort dictionary keys for canonical form."""
    if isinstance(value, dict):
        return {k: _sort_recursive(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_sort_recursive(item) for item in value]
    return value

"""Cross-SDK Conformance Tests.

These hash vectors are shared with the TypeScript SDK at:
  packages/core/src/__tests__/conformance/hash_vectors.json

If any vector fails, both SDKs must be checked — a mismatch
means cross-SDK interoperability is broken.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nekte.domain.hash import compute_version_hash

VECTORS_PATH = Path(__file__).parent / "hash_vectors.json"


def load_vectors() -> list[dict]:
    return json.loads(VECTORS_PATH.read_text())


def test_all_vectors_match() -> None:
    """Every hash vector must produce the same hash as the TypeScript SDK."""
    vectors = load_vectors()
    for vector in vectors:
        result = compute_version_hash(vector["input"], vector["output"])
        assert result == vector["expected_hash"], (
            f"Hash mismatch for '{vector['name']}': "
            f"got {result}, expected {vector['expected_hash']}. "
            f"Cross-SDK interoperability is broken!"
        )


@pytest.mark.parametrize("vector", load_vectors(), ids=lambda v: v["name"])
def test_individual_vector(vector: dict) -> None:
    """Parameterized test — one assertion per vector for clear failure reporting."""
    result = compute_version_hash(vector["input"], vector["output"])
    assert result == vector["expected_hash"]

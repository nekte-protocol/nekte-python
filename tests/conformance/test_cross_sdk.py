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


@pytest.fixture(params=load_vectors(), ids=lambda v: v["name"])
def vector(request: pytest.FixtureRequest) -> dict:
    return request.param


def test_hash_conformance(vector: dict) -> None:
    """Each vector must produce the exact same hash as the TypeScript SDK."""
    h = compute_version_hash(vector["input"], vector["output"])
    assert h == vector["expected_hash"], (
        f"Hash mismatch for '{vector['name']}': "
        f"got {h}, expected {vector['expected_hash']}. "
        f"Cross-SDK interoperability is broken!"
    )

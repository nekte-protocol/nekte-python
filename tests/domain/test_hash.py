"""Test version hashing — must be deterministic and cross-SDK compatible."""

from nekte.domain.hash import canonicalize, compute_version_hash


def test_deterministic_hash():
    h1 = compute_version_hash({"type": "object"}, {"type": "number"})
    h2 = compute_version_hash({"type": "object"}, {"type": "number"})
    assert h1 == h2
    assert len(h1) == 8


def test_key_order_does_not_matter():
    h1 = compute_version_hash({"a": 1, "b": 2}, {"x": 1})
    h2 = compute_version_hash({"b": 2, "a": 1}, {"x": 1})
    assert h1 == h2


def test_different_schemas_produce_different_hashes():
    h1 = compute_version_hash({"type": "string"}, {"type": "number"})
    h2 = compute_version_hash({"type": "string"}, {"type": "string"})
    assert h1 != h2


def test_nested_key_sorting():
    h1 = compute_version_hash(
        {"props": {"z": 1, "a": 2}},
        {"props": {"z": 1, "a": 2}},
    )
    h2 = compute_version_hash(
        {"props": {"a": 2, "z": 1}},
        {"props": {"a": 2, "z": 1}},
    )
    assert h1 == h2


def test_canonicalize_sorts_keys():
    result = canonicalize({"b": 2, "a": 1})
    assert result.index('"a"') < result.index('"b"')


def test_canonicalize_handles_arrays():
    result = canonicalize([3, 1, 2])
    assert result == "[3,1,2]"  # Arrays maintain order


def test_canonicalize_handles_nulls():
    result = canonicalize({"a": None, "b": 1})
    assert '"a":null' in result

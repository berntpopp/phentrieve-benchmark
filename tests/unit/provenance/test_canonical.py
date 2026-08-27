import unicodedata

import pytest

from phentrieve_benchmark.provenance.canonical import (
    canonical_json_bytes,
    canonical_jsonl_bytes,
    canonical_text_bytes,
    normalize_value,
)


def test_canonical_text_normalizes_unicode_and_line_endings() -> None:
    decomposed = unicodedata.normalize("NFD", "Größe\r\n")
    assert canonical_text_bytes(decomposed) == "Größe\n".encode()


def test_canonical_json_is_independent_of_mapping_order() -> None:
    left = canonical_json_bytes({"b": 2, "a": "Größe"})
    right = canonical_json_bytes({"a": "Gro\u0308ße", "b": 2})
    assert left == right


def test_jsonl_uses_stable_record_order_and_final_newline() -> None:
    value = canonical_jsonl_bytes(
        [{"document_id": "b", "value": 2}, {"document_id": "a", "value": 1}],
        identity_key="document_id",
    )
    assert value.splitlines() == [
        b'{"document_id":"a","value":1}',
        b'{"document_id":"b","value":2}',
    ]
    assert value.endswith(b"\n")


@pytest.mark.parametrize(
    "value",
    [
        {"Gro\u0308ße": 1, "Größe": 2},
        {1: "integer", "1": "string"},
    ],
)
def test_normalize_value_rejects_normalized_mapping_key_collisions(
    value: dict[object, object],
) -> None:
    with pytest.raises(ValueError, match="normalized mapping key collision"):
        normalize_value(value)


def test_normalize_value_recursively_normalizes_nested_mappings_and_sequences() -> None:
    value = {"outer": ("Gro\u0308ße", {"ke\u0301y": ["Gro\u0308ße"]})}

    assert normalize_value(value) == {"outer": ["Größe", {"kéy": ["Größe"]}]}


def test_jsonl_rejects_duplicate_identities_regardless_of_input_order() -> None:
    records = [
        {"document_id": "same", "value": 1},
        {"document_id": "same", "value": 2},
    ]

    with pytest.raises(ValueError, match="duplicate canonical identity"):
        canonical_jsonl_bytes(records, identity_key="document_id")
    with pytest.raises(ValueError, match="duplicate canonical identity"):
        canonical_jsonl_bytes(list(reversed(records)), identity_key="document_id")


def test_jsonl_normalizes_decomposed_identity_key_before_lookup() -> None:
    value = canonical_jsonl_bytes(
        [{"do\u0301cument_id": "b"}, {"do\u0301cument_id": "a"}],
        identity_key="do\u0301cument_id",
    )

    assert value.splitlines() == [
        '{"dócument_id":"a"}'.encode(),
        '{"dócument_id":"b"}'.encode(),
    ]

import unicodedata

from phentrieve_benchmark.provenance.canonical import (
    canonical_json_bytes,
    canonical_jsonl_bytes,
    canonical_text_bytes,
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

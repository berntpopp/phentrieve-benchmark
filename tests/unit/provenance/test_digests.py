import pytest
from pydantic import ValidationError

from phentrieve_benchmark.provenance.digests import (
    ComponentDigest,
    aggregate_sha256,
    sha256_bytes,
)


def test_sha256_bytes_uses_lowercase_hex() -> None:
    assert sha256_bytes(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )


def test_aggregate_hash_is_order_independent_but_role_sensitive() -> None:
    source = ComponentDigest(role="source", stable_id="case-1", sha256="a" * 64)
    gold = ComponentDigest(role="gold", stable_id="case-1", sha256="b" * 64)

    assert aggregate_sha256("document-set/v1", [source, gold]) == aggregate_sha256(
        "document-set/v1", [gold, source]
    )
    assert aggregate_sha256(
        "document-set/v1",
        [source.model_copy(update={"role": "input"}), gold],
    ) != aggregate_sha256("document-set/v1", [source, gold])


def test_aggregate_normalizes_fields_before_sorting() -> None:
    decomposed = ComponentDigest(
        role="source", stable_id="a\u0308", sha256="a" * 64
    )
    composed = ComponentDigest(role="source", stable_id="ä", sha256="a" * 64)
    later_component = ComponentDigest(role="source", stable_id="b", sha256="b" * 64)

    assert aggregate_sha256("document-set/v1", [decomposed, later_component]) == (
        aggregate_sha256("document-set/v1", [later_component, composed])
    )


@pytest.mark.parametrize(
    "components",
    [
        [
            ComponentDigest(role="source", stable_id="case-1", sha256="a" * 64),
            ComponentDigest(role="source", stable_id="case-1", sha256="a" * 64),
        ],
        [
            ComponentDigest(role="source", stable_id="case-1", sha256="a" * 64),
            ComponentDigest(role="source", stable_id="case-1", sha256="b" * 64),
        ],
        [
            ComponentDigest(role="source", stable_id="café", sha256="a" * 64),
            ComponentDigest(role="source", stable_id="cafe\u0301", sha256="b" * 64),
        ],
    ],
)
def test_aggregate_rejects_duplicate_normalized_logical_identities(
    components: list[ComponentDigest],
) -> None:
    with pytest.raises(ValueError, match="duplicate component identity"):
        aggregate_sha256("document-set/v1", components)


@pytest.mark.parametrize("schema_version", ["", "   "])
def test_aggregate_rejects_blank_schema_version(schema_version: str) -> None:
    with pytest.raises(ValueError, match="schema version"):
        aggregate_sha256(schema_version, [])


def test_aggregate_schema_version_is_normalized_and_domain_separated() -> None:
    assert aggregate_sha256("document-set/v1", []) == aggregate_sha256(
        "document-set/v1", []
    )
    assert aggregate_sha256("document-set/v1", []) != aggregate_sha256(
        "document-set/v2", []
    )
    assert aggregate_sha256("document-se\u0301t/v1", []) == aggregate_sha256(
        "document-sét/v1", []
    )


@pytest.mark.parametrize("value", ["A" * 64, "a" * 63])
def test_component_digest_rejects_invalid_sha256(value: str) -> None:
    with pytest.raises(ValidationError):
        ComponentDigest(role="source", stable_id="case-1", sha256=value)


@pytest.mark.parametrize("field", ["role", "stable_id"])
def test_component_digest_rejects_empty_identity_fields(field: str) -> None:
    values = {"role": "source", "stable_id": "case-1", "sha256": "a" * 64}
    values[field] = ""

    with pytest.raises(ValidationError):
        ComponentDigest(**values)


def test_component_digest_forbids_extra_fields_and_mutation() -> None:
    with pytest.raises(ValidationError):
        ComponentDigest(
            role="source", stable_id="case-1", sha256="a" * 64, unexpected=True
        )

    component = ComponentDigest(role="source", stable_id="case-1", sha256="a" * 64)
    with pytest.raises(ValidationError):
        component.role = "input"

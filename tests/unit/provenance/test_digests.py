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

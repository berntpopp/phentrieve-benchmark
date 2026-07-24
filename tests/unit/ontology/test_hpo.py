from hashlib import sha256
from pathlib import Path

import pytest

from phentrieve_benchmark.ontology.hpo import (
    HpoIndexError,
    load_hpo_index,
    load_hpo_source_recipe,
)
from tests.fixtures.hpo import synthetic_hpo_obo


def test_official_hpo_source_recipe_is_exact() -> None:
    path = (
        Path(__file__).parents[3]
        / "configs/ontologies/hpo-v2026-06-23.yaml"
    )
    recipe = load_hpo_source_recipe(path).value
    assert recipe.release == "v2026-06-23"
    assert recipe.expected_byte_length == 11_222_341
    assert recipe.sha256 == (
        "a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b"
    )


def test_loads_strict_immutable_hpo_index() -> None:
    body = synthetic_hpo_obo()
    index = load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )
    assert index.terms["HP:0000002"].alternate_ids == (
        "HP:0000006",
        "HP:1000002",
    )
    assert index.terms["HP:0000003"].obsolete
    assert index.terms["HP:0000003"].replaced_by == ("HP:0000002",)
    assert index.terms["HP:0000004"].replaced_by == (
        "HP:0000001",
        "HP:0000002",
    )
    assert index.terms["HP:0000005"].consider == ("HP:0000001",)
    assert index.alternate_to_primary["HP:1000002"] == "HP:0000002"
    assert "HP:0000006" not in index.alternate_to_primary
    assert index.terms["HP:0000001"].umls_cuis == ("C0000001",)
    assert index.umls_to_hpo["C0000001"] == (
        "HP:0000001",
        "HP:0000002",
    )
    assert index.umls_to_hpo["C0000003"] == ("HP:0000003",)


@pytest.mark.parametrize(
    "xref_lines",
    [
        b"xref: UMLS:not-a-cui\n",
        b"xref: UMLS:C0000001\nxref: UMLS:C0000001\n",
    ],
)
def test_rejects_malformed_and_duplicate_umls_xrefs(
    xref_lines: bytes,
) -> None:
    body = (
        synthetic_hpo_obo()
        + b"\n[Term]\nid: HP:0000008\nname: Bad xref\n"
        + xref_lines
    )

    with pytest.raises(HpoIndexError, match="UMLS"):
        load_hpo_index(
            body,
            release="v2026-06-23",
            ontology_sha256=sha256(body).hexdigest(),
        )


@pytest.mark.parametrize(
    "addition",
    [
        b"\n[Term]\nid: BAD:1\nname: Bad\n",
        b"\n[Term]\nid: HP:0000008\nname: Missing\nreplaced_by: HP:9999999\n",
        (
            b"\n[Term]\nid: HP:0000008\nname: Cycle A\nis_obsolete: true\n"
            b"replaced_by: HP:0000009\n\n[Term]\nid: HP:0000009\n"
            b"name: Cycle B\nis_obsolete: true\nreplaced_by: HP:0000008\n"
        ),
    ],
)
def test_rejects_invalid_ids_missing_targets_and_cycles(addition: bytes) -> None:
    body = synthetic_hpo_obo() + addition
    with pytest.raises(HpoIndexError):
        load_hpo_index(
            body,
            release="v2026-06-23",
            ontology_sha256=sha256(body).hexdigest(),
        )

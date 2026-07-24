from hashlib import sha256

from phentrieve_benchmark.ontology.hpo import load_hpo_index
from phentrieve_benchmark.ontology.revision import (
    HpoRevisionStatus,
    audit_hpo_ids,
)
from tests.fixtures.hpo import synthetic_hpo_obo


def test_revision_policy_is_conservative_and_deterministic() -> None:
    body = synthetic_hpo_obo()
    index = load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )
    values = [
        ("a7", "bad"),
        ("a6", "HP:9999999"),
        ("a5", "HP:0000006"),
        ("a4", "HP:0000005"),
        ("a3", "HP:0000004"),
        ("a2", "HP:0000003"),
        ("a1", "HP:1000002"),
        ("a0", "HP:0000001"),
    ]
    decisions = audit_hpo_ids(reversed(values), index=index)
    by_id = {item.source_annotation_id: item for item in decisions}
    assert by_id["a0"].status is HpoRevisionStatus.ACTIVE
    assert by_id["a0"].canonical_hpo_id == "HP:0000001"
    assert by_id["a1"].status is HpoRevisionStatus.ALT_ID
    assert by_id["a1"].canonical_hpo_id == "HP:0000002"
    assert by_id["a2"].status is HpoRevisionStatus.OBSOLETE_REPLACED
    assert by_id["a2"].canonical_hpo_id is None
    assert by_id["a2"].proposed_hpo_ids == ("HP:0000002",)
    assert by_id["a2"].requires_manual_review
    assert by_id["a3"].status is HpoRevisionStatus.OBSOLETE_AMBIGUOUS
    assert by_id["a4"].status is HpoRevisionStatus.OBSOLETE_AMBIGUOUS
    assert by_id["a5"].status is HpoRevisionStatus.OBSOLETE_UNRESOLVED
    assert by_id["a6"].status is HpoRevisionStatus.UNKNOWN
    assert by_id["a7"].status is HpoRevisionStatus.INVALID_FORMAT
    assert decisions == audit_hpo_ids(values, index=index)

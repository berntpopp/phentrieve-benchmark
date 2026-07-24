import json
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_published_hpo_audit_is_text_free_and_internally_consistent() -> None:
    path = ROOT / "datasets/raghpo/hpo-audit-v2026-06-23.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["ontology_release"] == "v2026-06-23"
    assert payload["ontology_sha256"] == (
        "a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b"
    )
    targets = {target["target_id"]: target for target in payload["targets"]}
    assert targets["csc"]["source_annotations"] == 1795
    assert targets["csc"]["counts"] == {
        "active": 1779,
        "alt_id": 0,
        "obsolete_replaced": 15,
        "obsolete_ambiguous": 1,
        "obsolete_unresolved": 0,
        "unknown": 0,
        "invalid_format": 0,
    }
    assert len(targets["csc"]["manual_review"]) == 16
    assert targets["gsc"]["source_annotations"] == 1012
    assert targets["gsc"]["counts"]["active"] == 1012
    assert targets["gsc"]["manual_review"] == []
    serialized = path.read_text(encoding="utf-8").casefold()
    assert "clinical_note" not in serialized
    assert "hpo_description" not in serialized

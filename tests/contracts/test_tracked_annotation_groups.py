import json
from collections import Counter
from pathlib import Path

from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    assign_annotation_groups,
    load_e3c_inventory,
)

ROOT = Path(__file__).parents[2]
INVENTORY = ROOT / "datasets/e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json"
GROUPS = ROOT / "datasets/e3c-de/selections/e3c-annotation-groups-v1.json"
PROHIBITED = {"text", "text_snippet", "prompt", "credential", "timestamp"}


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value))
    return set()


def test_tracked_groups_are_reproducible_from_the_tracked_inventory() -> None:
    inventory_bytes = INVENTORY.read_bytes()
    groups_bytes = GROUPS.read_bytes()
    expected = assign_annotation_groups(load_e3c_inventory(inventory_bytes))
    assert groups_bytes == expected.canonical_bytes()
    manifest = AnnotationGroupManifest.model_validate_json(groups_bytes, strict=True)
    assert manifest.inventory_sha256 == sha256_bytes(inventory_bytes)


def test_tracked_groups_have_the_agreed_sizes_and_no_text() -> None:
    manifest = AnnotationGroupManifest.model_validate_json(
        GROUPS.read_bytes(), strict=True
    )
    assert len(manifest.records) == 246
    german = Counter(
        record.source_language
        for record in manifest.records
        if record.annotation_language == "de"
    )
    assert german["en"] == 21
    assert german["fr"] in {20, 21}
    assert german["es"] in {20, 21}
    assert not _keys(json.loads(GROUPS.read_bytes())) & PROHIBITED

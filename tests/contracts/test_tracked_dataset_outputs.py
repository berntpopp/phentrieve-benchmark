import json
from pathlib import Path

from phentrieve_benchmark.provenance.digests import sha256_bytes

ROOT = Path(__file__).parents[2]
INVENTORY = ROOT / "datasets/e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json"
MAPPING = (
    ROOT / "datasets/e3c-de/mappings/e3c-l1-umls-hpo-v2026-06-23-v1.json"
)
MAPPING_SUMMARY = (
    ROOT
    / "datasets/e3c-de/mappings/"
    "e3c-l1-umls-hpo-v2026-06-23-summary-v1.json"
)
PROHIBITED = {
    "text",
    "clinical_note",
    "hpo_description",
    "text_snippet",
    "prompt",
    "credential",
    "run_id",
    "timestamp",
    "host",
    "environment",
}


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value))
    return set()


def test_tracked_e3c_inventory_is_text_free_and_exact() -> None:
    inventory_bytes = INVENTORY.read_bytes()
    inventory = json.loads(inventory_bytes)

    assert sha256_bytes(inventory_bytes) == (
        "20070d0e425148ceab9f9828e1b55e2f9fce8ae7762419a6f7f908ec62111e1b"
    )
    assert len(inventory) == 246
    identities = {
        (item["language"], item["source_case_id"]) for item in inventory
    }
    assert len(identities) == 246
    assert not _keys(inventory) & PROHIBITED


def test_tracked_e3c_mapping_outputs_are_text_free_and_exact() -> None:
    mapping_bytes = MAPPING.read_bytes()
    summary_bytes = MAPPING_SUMMARY.read_bytes()
    mapping = json.loads(mapping_bytes)
    summary = json.loads(summary_bytes)

    assert sha256_bytes(mapping_bytes) == (
        "6a2498c2b16410b9c951263a49260df82f73d1cdffe32049788ad0fc077f13d5"
    )
    assert sha256_bytes(summary_bytes) == (
        "fea1cb5d74326f1f44542213cd81fb953c3dad5599978847ee30c2ddfdceda16"
    )
    assert len(mapping["population_case_ids"]) == 246
    assert len(mapping["records"]) == 3696
    classification_counts = {
        item["classification"]: item["count"]
        for item in summary["classifications"]
    }
    assert classification_counts == {
        "unique_active": 1321,
        "ambiguous": 58,
        "missing": 1925,
        "obsolete": 0,
        "invalid": 392,
    }
    assert not (_keys(mapping) | _keys(summary)) & PROHIBITED

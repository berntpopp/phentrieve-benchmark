import json
from collections import Counter
from pathlib import Path

from phentrieve_benchmark.provenance.digests import sha256_bytes

ROOT = Path(__file__).parents[2]
INVENTORY = ROOT / "datasets/e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json"
SELECTION = ROOT / "datasets/e3c-de/selections/e3c-de-feasibility-30-v1.json"
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


def test_tracked_e3c_outputs_are_text_free_and_exact() -> None:
    inventory_bytes = INVENTORY.read_bytes()
    selection_bytes = SELECTION.read_bytes()
    inventory = json.loads(inventory_bytes)
    selection = json.loads(selection_bytes)

    assert sha256_bytes(inventory_bytes) == (
        "20070d0e425148ceab9f9828e1b55e2f9fce8ae7762419a6f7f908ec62111e1b"
    )
    assert sha256_bytes(selection_bytes) == (
        "9500caf1503fef2560b32eec561c17291cce80dbf66e6250ae8067871df13bfc"
    )
    assert len(inventory) == 246
    identities = {
        (item["language"], item["source_case_id"]) for item in inventory
    }
    assert len(identities) == 246
    assert len(selection["records"]) == 30
    assert Counter(item["language"] for item in selection["records"]) == {
        "en": 10,
        "fr": 10,
        "es": 10,
    }
    assert selection["inventory_sha256"] == sha256_bytes(inventory_bytes)
    assert selection["selection_seed"] == "phentrieve-e3c-de-feasibility-30-v1"
    assert selection["algorithm_id"] == "e3c-diversity-maximin/v1"
    assert selection["overrides"] == []
    assert not (_keys(inventory) | _keys(selection)) & PROHIBITED

from pathlib import Path

from phentrieve_benchmark.selection.groups import load_e3c_inventory

ROOT = Path(__file__).parents[2]
INVENTORY = ROOT / "datasets/e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json"
ATTRIBUTION = ROOT / "datasets/e3c-de/ATTRIBUTION.md"


def test_attribution_lists_every_inventory_report_once() -> None:
    rows = [
        line
        for line in ATTRIBUTION.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `")
    ]
    case_ids = [row.split("`")[1] for row in rows]
    expected = {
        record.source_case_id
        for record in load_e3c_inventory(INVENTORY.read_bytes())
    }
    assert len(case_ids) == len(set(case_ids))
    assert set(case_ids) == expected

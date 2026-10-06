from collections import Counter
from pathlib import Path

from phentrieve_benchmark.selection.groups import load_e3c_inventory

ROOT = Path(__file__).parents[2]
INVENTORY = ROOT / "datasets/e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json"
ATTRIBUTION = ROOT / "datasets/e3c-de/ATTRIBUTION.md"
PUBLISHER_LICENSES = ROOT / "datasets/e3c-de/PUBLISHER-LICENSES.md"


def _rows() -> list[str]:
    return [
        line
        for line in ATTRIBUTION.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `")
    ]


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip("|").split(" | ")]


def test_attribution_rows_are_complete_and_licenses_are_pinned() -> None:
    cells = [_cells(row) for row in _rows()]
    assert all(len(row) == 6 and all(row) for row in cells)
    assert Counter(row[5].strip("`") for row in cells) == {
        "CC BY 4.0": 115,
        "CC-BY": 81,
        "CC BY": 43,
        "CC BY-NC": 7,
    }


def test_publisher_license_check_covers_every_report_once() -> None:
    rows = [
        _cells(line)
        for line in PUBLISHER_LICENSES.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `")
    ]
    case_ids = [row[0].strip("`") for row in rows]
    assert len(case_ids) == len(set(case_ids))
    assert set(case_ids) == {row.split("`")[1] for row in _rows()}
    assert all(len(row) == 5 and all(row) for row in rows)
    assert [row[0] for row in rows if "-SA" in row[3]] == [
        "`EN102305`",
        "`EN104179`",
        "`EN104184`",
        "`EN104263`",
        "`EN106233`",
    ]


def test_attribution_lists_every_inventory_report_once() -> None:
    case_ids = [row.split("`")[1] for row in _rows()]
    expected = {
        record.source_case_id
        for record in load_e3c_inventory(INVENTORY.read_bytes())
    }
    assert len(case_ids) == len(set(case_ids))
    assert set(case_ids) == expected

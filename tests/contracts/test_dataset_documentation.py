from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_target_documentation_records_commands_counts_and_limits() -> None:
    paths = (
        ROOT / "datasets/e3c-de/README.md",
        ROOT / "datasets/e3c-de/selection-policy.md",
        ROOT / "datasets/e3c-de/mappings/README.md",
        ROOT / "datasets/raghpo/README.md",
        ROOT / "datasets/raghpo/csc/README.md",
        ROOT / "datasets/raghpo/gsc/README.md",
    )
    combined = "\n".join(path.read_text("utf-8") for path in paths)
    for required in (
        "f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc",
        "080fc3a04c91ee45c8986076765f4d4b4f14ddd9",
        "prepare e3c",
        "prepare csc",
        "prepare gsc",
        "84",
        "81",
        "116",
        "1,795",
        "114",
        "1,012",
        "v2026-06-23",
        "UTF-16",
        "len(canonical_text.split())",
        "empty evidence spans",
        "local",
        "map-hpo e3c",
        "3,696",
    ):
        assert required in combined

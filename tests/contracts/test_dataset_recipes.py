from pathlib import Path

from phentrieve_benchmark.acquisition.recipes import (
    E3cAdapterContract,
    load_license_evidence,
    load_source_recipe,
    load_target_recipe,
)

ROOT = Path(__file__).parents[2]
E3C_COMMIT = "f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc"
RAGHPO_COMMIT = "080fc3a04c91ee45c8986076765f4d4b4f14ddd9"
TYPES = (
    "CLINENTITY",
    "EVENT",
    "ACTOR",
    "BODYPART",
    "TIMEX3",
    "RML",
    "TIMEX3TimexLinkLink",
    "RMLPERTAINSTOLink",
    "EVENTTLINKLink",
    "EVENTALINKLink",
)


def test_real_source_locks_and_license_hashes_are_exact() -> None:
    e3c = load_source_recipe(ROOT / "datasets/e3c-de/dataset.yaml")
    raghpo = load_source_recipe(ROOT / "datasets/raghpo/source.yaml")
    e3c_license = load_license_evidence(
        ROOT / "datasets/e3c-de/license-evidence.yaml"
    )
    raghpo_license = load_license_evidence(
        ROOT / "datasets/raghpo/license-evidence.yaml"
    )

    assert e3c.value.source_commit == E3C_COMMIT
    assert raghpo.value.source_commit == RAGHPO_COMMIT
    assert e3c.value.archive.url.endswith(f"/zip/{E3C_COMMIT}")
    assert raghpo.value.archive.url.endswith(f"/zip/{RAGHPO_COMMIT}")
    assert e3c.value.archive.expected_byte_length == 233_811_002
    assert raghpo.value.archive.expected_byte_length == 12_524_020
    assert e3c.value.archive.sha256 == (
        "04e06d0a153a8ea845b647459ab51eb2fed5007bdf450d441c1469f8719a2206"
    )
    assert raghpo.value.archive.sha256 == (
        "a2ece2b7b44e522a299dff02733dd1cad69d5ba11f7dc4da9c346c201662b52b"
    )
    assert e3c.value.license_evidence_sha256 == e3c_license.sha256
    assert raghpo.value.license_evidence_sha256 == raghpo_license.sha256


def test_e3c_inventory_and_official_counts_are_exact() -> None:
    source = load_source_recipe(ROOT / "datasets/e3c-de/dataset.yaml").value
    assert source.included_paths == (
        "README.md",
        "data_annotation/English/layer1/*.xml",
        "data_annotation/French/layer1/*.xml",
        "data_annotation/Spanish/layer1/*.xml",
    )
    assert source.ignored_path_prefixes
    contract = source.adapter_contract
    assert isinstance(contract, E3cAdapterContract)
    assert {
        item.language: item.expected_documents
        for item in contract.language_paths
    } == {"en": 84, "fr": 81, "es": 81}
    expected = {
        "en": (1024, 4885, 682, 968, 380, 480, 502, 541, 4350, 114),
        "fr": (1327, 4312, 427, 659, 333, 508, 236, 474, 3848, 71),
        "es": (1345, 4767, 319, 814, 383, 391, 604, 473, 4096, 92),
    }
    for language in contract.language_paths:
        assert tuple(item.name for item in language.expected_semantic_counts) == TYPES
        assert tuple(
            item.count for item in language.expected_semantic_counts
        ) == expected[language.language]


def test_raghpo_inventory_tables_and_hpo_release_are_exact() -> None:
    source = load_source_recipe(ROOT / "datasets/raghpo/source.yaml").value
    assert source.included_paths == (
        "LICENSE",
        "RAG-HPO Tests and Data Analysis copy.xlsx",
        "README.md",
        "Test_Cases.csv",
    )
    csc = load_target_recipe(ROOT / "datasets/raghpo/csc/dataset.yaml").value
    gsc = load_target_recipe(ROOT / "datasets/raghpo/gsc/dataset.yaml").value
    assert sorted(table.data_rows for table in csc.expected_tables) == [116, 1789]
    assert sorted(table.data_rows for table in gsc.expected_tables) == [114, 1012]
    assert str(csc.hpo_release) == str(gsc.hpo_release) == "v2026-06-23"
    assert csc.required_paths == (
        "RAG-HPO Tests and Data Analysis copy.xlsx",
    )

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.acquisition.recipes import (
    E3cAdapterContract,
    LicenseEvidence,
    NormalizationRecipe,
    RaghpoAdapterContract,
    SourceRecipe,
    load_license_evidence,
    load_source_recipe,
    load_target_recipe,
)

COMMIT = "f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc"
DIGEST = "a" * 64


def source_yaml(*, formatting: bool = False) -> str:
    if formatting:
        return f"""
# Semantically identical with different formatting.
source_commit: {COMMIT}
source_id: e3c
schema_version: source-recipe/v1
repository_url: https://github.com/hltfbk/E3C-Corpus
archive:
  maximum_compression_ratio: 100
  maximum_expanded_bytes: 500000000
  maximum_member_bytes: 20000000
  maximum_member_count: 100000
  expected_top_level_directory: E3C-Corpus-{COMMIT}
  sha256: {DIGEST}
  maximum_byte_length: 300000000
  expected_byte_length: 200000000
  format: zip
  url: https://codeload.github.com/hltfbk/E3C-Corpus/zip/{COMMIT}
included_paths:
  - data_annotation/English/layer1/*.xml
ignored_path_prefixes:
  - data_annotation/French
adapter_id: e3c-xmi/v1
source_schema_id: webanno-uima-xmi/v2
adapter_contract:
  kind: e3c-xmi/v1
  sofa_type: cas:Sofa
  structural_types: [Token, Sentence]
  language_paths:
    - language: en
      path_pattern: data_annotation/English/layer1/*.xml
      expected_documents: 84
  semantic_types:
    - name: CLINENTITY
      kind: annotation
      begin_attribute: begin
      end_attribute: end
      concept_attribute: cui
      argument_attributes: []
      allowed_attributes: [factuality]
license_evidence_sha256: {"b" * 64}
"""
    return f"""
schema_version: source-recipe/v1
source_id: e3c
repository_url: https://github.com/hltfbk/E3C-Corpus
source_commit: {COMMIT}
archive:
  url: https://codeload.github.com/hltfbk/E3C-Corpus/zip/{COMMIT}
  format: zip
  expected_byte_length: 200000000
  maximum_byte_length: 300000000
  sha256: {DIGEST}
  expected_top_level_directory: E3C-Corpus-{COMMIT}
  maximum_member_count: 100000
  maximum_member_bytes: 20000000
  maximum_expanded_bytes: 500000000
  maximum_compression_ratio: 100
included_paths:
  - data_annotation/English/layer1/*.xml
ignored_path_prefixes:
  - data_annotation/French
adapter_id: e3c-xmi/v1
source_schema_id: webanno-uima-xmi/v2
adapter_contract:
  kind: e3c-xmi/v1
  language_paths:
    - language: en
      path_pattern: data_annotation/English/layer1/*.xml
      expected_documents: 84
  sofa_type: cas:Sofa
  structural_types:
    - Token
    - Sentence
  semantic_types:
    - name: CLINENTITY
      kind: annotation
      begin_attribute: begin
      end_attribute: end
      concept_attribute: cui
      argument_attributes: []
      allowed_attributes:
        - factuality
license_evidence_sha256: {"b" * 64}
"""


def write(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    return path


def test_source_recipe_loads_strict_typed_e3c_contract(tmp_path: Path) -> None:
    loaded = load_source_recipe(write(tmp_path / "source.yaml", source_yaml()))

    assert loaded.value.source_id == "e3c"
    assert loaded.value.source_commit == COMMIT
    assert isinstance(loaded.value.adapter_contract, E3cAdapterContract)
    assert loaded.value.adapter_contract.language_paths[0].expected_documents == 84
    assert len(loaded.sha256) == 64


def test_semantic_recipe_hash_ignores_yaml_formatting_comments_and_order(
    tmp_path: Path,
) -> None:
    first = load_source_recipe(write(tmp_path / "first.yaml", source_yaml()))
    second = load_source_recipe(
        write(tmp_path / "second.yaml", source_yaml(formatting=True))
    )

    assert first.value == second.value
    assert first.sha256 == second.sha256


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("https://", "http://", "HTTPS"),
        ("codeload.github.com", "example.org", "codeload"),
        (f"/zip/{COMMIT}", "/zip/main", "commit"),
        (DIGEST, "0" * 64, "sha256"),
        ("expected_byte_length: 200000000", "expected_byte_length: true", "integer"),
        (
            "maximum_byte_length: 300000000",
            "maximum_byte_length: 100",
            "maximum_byte_length",
        ),
    ],
)
def test_source_recipe_rejects_unsafe_or_coercive_archive_identity(
    tmp_path: Path,
    old: str,
    new: str,
    message: str,
) -> None:
    path = write(tmp_path / "source.yaml", source_yaml().replace(old, new, 1))

    with pytest.raises((ValidationError, ValueError), match=message):
        load_source_recipe(path)


@pytest.mark.parametrize(
    "suffix",
    ["?download=1", "#fragment"],
)
def test_source_recipe_rejects_archive_query_or_fragment(
    tmp_path: Path, suffix: str
) -> None:
    value = source_yaml().replace(
        f"/zip/{COMMIT}",
        f"/zip/{COMMIT}{suffix}",
        1,
    )

    with pytest.raises(ValueError, match=r"query|fragment"):
        load_source_recipe(write(tmp_path / "source.yaml", value))


def test_source_recipe_rejects_overlapping_included_and_ignored_paths(
    tmp_path: Path,
) -> None:
    value = source_yaml().replace(
        "data_annotation/French",
        "data_annotation/English",
    )

    with pytest.raises(ValueError, match="overlap"):
        load_source_recipe(write(tmp_path / "source.yaml", value))


def test_source_recipe_rejects_adapter_contract_for_wrong_source(
    tmp_path: Path,
) -> None:
    value = source_yaml().replace("source_id: e3c", "source_id: raghpo")

    with pytest.raises(ValueError, match="adapter contract"):
        load_source_recipe(write(tmp_path / "source.yaml", value))


@pytest.mark.parametrize(
    "value",
    [
        "schema_version: source-recipe/v1\nsource_id: one\nsource_id: two\n",
        "schema_version: &schema source-recipe/v1\nsource_id: *schema\n",
        "schema_version: source-recipe/v1\n1: non-string-key\n",
        "schema_version: source-recipe/v1\n---\nsource_id: second\n",
    ],
)
def test_yaml_rejects_duplicates_aliases_nonstring_keys_and_multiple_documents(
    tmp_path: Path,
    value: str,
) -> None:
    with pytest.raises(ValueError):
        load_source_recipe(write(tmp_path / "source.yaml", value))


def test_raghpo_contract_is_discriminated_and_strict() -> None:
    payload = {
        **load_source_recipe_payload(source_yaml()),
        "source_id": "raghpo",
        "adapter_id": "raghpo-tabular/v1",
        "adapter_contract": {
            "kind": "raghpo-tabular/v1",
            "selected_files": [
                "Test_Cases.csv",
                "RAG-HPO Tests and Data Analysis copy.xlsx",
            ],
            "workbook_limits": {
                "maximum_member_count": 100,
                "maximum_member_bytes": 1_000_000,
                "maximum_expanded_bytes": 10_000_000,
                "maximum_compression_ratio": 100,
            },
        },
    }

    recipe = SourceRecipe.model_validate_json(json.dumps(payload))

    assert isinstance(recipe.adapter_contract, RaghpoAdapterContract)


def load_source_recipe_payload(value: str) -> dict[str, object]:
    import yaml

    payload = yaml.safe_load(value)
    assert isinstance(payload, dict)
    return payload


def test_target_recipe_and_license_evidence_are_hashed_semantically(
    tmp_path: Path,
) -> None:
    target_path = write(
        tmp_path / "target.yaml",
        """
schema_version: normalization-recipe/v1
target_id: csc
source_id: raghpo
adapter_id: raghpo-csc/v1
required_paths: [Test_Cases.csv]
expected_tables:
  - source_path: Test_Cases.csv
    columns: [Case, clinical_note]
    data_rows: 116
expected_counts:
  - name: documents
    count: 116
hpo_release: v2026-06-23
""",
    )
    evidence_path = write(
        tmp_path / "license-evidence.yaml",
        f"""
schema_version: license-evidence/v1
source_id: raghpo
repository_url: https://github.com/PoseyPod/RAG-HPO
source_commit: {"a" * 40}
license_id: MIT
license_url: https://github.com/PoseyPod/RAG-HPO/blob/{"a" * 40}/LICENSE
access_date: 2026-07-24
upstream_statement: MIT License
redistribution_decision: source_not_redistributed
derivative_work_notes: Text-free metadata only.
unresolved_questions: []
""",
    )

    target = load_target_recipe(target_path)
    evidence = load_license_evidence(evidence_path)

    assert isinstance(target.value, NormalizationRecipe)
    assert target.value.expected_tables[0].data_rows == 116
    assert isinstance(evidence.value, LicenseEvidence)
    assert evidence.value.license_id == "MIT"
    assert len(target.sha256) == len(evidence.sha256) == 64


def test_license_evidence_accepts_scientific_review_snapshot(
    tmp_path: Path,
) -> None:
    evidence_path = write(
        tmp_path / "license-evidence.yaml",
        f"""
schema_version: license-evidence/v1
source_id: e3c
repository_url: https://github.com/hltfbk/E3C-Corpus
source_commit: {"a" * 40}
license_id: LicenseRef-E3C-CC-BY-NC-version-unspecified
license_url: https://github.com/hltfbk/E3C-Corpus/blob/{"a" * 40}/README.md
access_date: 2026-07-24
upstream_statement: CC BY-NC without a version.
redistribution_decision: noncommercial_scientific_review_snapshot
derivative_work_notes: Selected review texts are redistributed.
unresolved_questions:
  - The CC BY-NC version remains unspecified.
""",
    )

    evidence = load_license_evidence(evidence_path)

    assert (
        evidence.value.redistribution_decision
        == "noncommercial_scientific_review_snapshot"
    )

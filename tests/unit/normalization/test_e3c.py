from pathlib import Path

import pytest

from phentrieve_benchmark.acquisition.recipes import (
    E3cLanguagePath,
    E3cSemanticCount,
    load_source_recipe,
)
from phentrieve_benchmark.normalization.e3c import (
    E3cNormalizationError,
    normalize_e3c_members,
)
from tests.fixtures.e3c import synthetic_e3c_xmi

ROOT = Path(__file__).parents[3]
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


def _source():
    source = load_source_recipe(ROOT / "datasets/e3c-de/dataset.yaml").value
    contract = source.adapter_contract
    language_path = E3cLanguagePath(
        language="en",
        path_pattern="data_annotation/English/layer1/*.xml",
        expected_documents=1,
        expected_semantic_counts=tuple(
            E3cSemanticCount(name=name, count=1) for name in TYPES
        ),
    )
    return source.model_copy(
        update={
            "adapter_contract": contract.model_copy(
                update={"language_paths": (language_path,)}
            )
        }
    )


def test_normalizes_registered_entities_relations_and_utf16_spans() -> None:
    result = normalize_e3c_members(
        {
            "data_annotation/English/layer1/EN000001.xml": (
                synthetic_e3c_xmi()
            )
        },
        source_recipe=_source(),
    )
    document = result.documents[0]
    source_set = result.source_annotation_sets[0]
    assert document.language == "en"
    assert document.source_case_id == "EN000001"
    assert document.document_id == "e3c:v2.0.0:en:EN000001:native"
    assert document.text == "A😀 Café\nfinal"
    assert {item.source_type for item in source_set.annotations} == set(TYPES[:6])
    assert {item.source_type for item in source_set.relations} == set(TYPES[6:])
    clinical = next(
        item for item in source_set.annotations if item.source_type == "CLINENTITY"
    )
    assert clinical.source_concept_id == "C1234567"
    assert clinical.evidence_spans[0].text_snippet == "Café"
    assert clinical.evidence_spans[0].start_char == 3
    assert {item.name for item in clinical.attributes} == {"discontinuous"}
    assert all(relation.arguments for relation in source_set.relations)
    assert result.source_structure_counts == (
        ("en", "EN000001", "sentences", 1),
    )


@pytest.mark.parametrize(
    "path",
    [
        "data_annotation/German/layer1/DE1.xml",
        "data_annotation/English/layer2/EN1.xml",
        "data_annotation/english/layer1/EN1.xml",
    ],
)
def test_rejects_language_paths_outside_exact_layer_one(path: str) -> None:
    with pytest.raises(E3cNormalizationError, match="path"):
        normalize_e3c_members(
            {path: synthetic_e3c_xmi()}, source_recipe=_source()
        )


def test_rejects_unknown_custom_type_and_wrong_counts() -> None:
    valid_path = "data_annotation/English/layer1/EN000001.xml"
    with pytest.raises(E3cNormalizationError, match="custom"):
        normalize_e3c_members(
            {valid_path: synthetic_e3c_xmi(unknown_custom_type=True)},
            source_recipe=_source(),
        )
    with pytest.raises(E3cNormalizationError, match="count"):
        normalize_e3c_members({}, source_recipe=_source())


@pytest.mark.parametrize(
    "payload",
    [
        b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e "x">]><x>&e;</x>',
        b"<not-xmi/>",
    ],
)
def test_rejects_unsafe_or_malformed_xml(payload: bytes) -> None:
    with pytest.raises(E3cNormalizationError):
        normalize_e3c_members(
            {"data_annotation/English/layer1/EN000001.xml": payload},
            source_recipe=_source(),
        )

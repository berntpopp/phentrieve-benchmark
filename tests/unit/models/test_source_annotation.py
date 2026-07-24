import json

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.annotation import EvidenceSpan
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.source_annotation import (
    SourceAnnotation,
    SourceAnnotationSet,
    SourceAttribute,
    SourceRelation,
    SourceRelationArgument,
    validate_source_annotation_set,
)


def document() -> Document:
    return Document.from_text(
        source_case_id="synthetic-1",
        case_group_id="synthetic-1",
        document_id="synthetic:en:1",
        language="en",
        translation_status=TranslationStatus.NATIVE,
        text="Synthetic phenotype.",
    )


def annotation_set(**updates: object) -> SourceAnnotationSet:
    source_document = document()
    values: dict[str, object] = {
        "annotation_set_id": "synthetic:source:v1",
        "document_sha256": source_document.document_sha256,
        "source_schema_id": "synthetic-xmi/v1",
        "annotations": (
            SourceAnnotation(
                source_annotation_id="entity-2",
                source_type="EVENT",
                attributes=(
                    SourceAttribute(
                        namespace="e3c",
                        name="factuality",
                        value="actual",
                    ),
                ),
            ),
            SourceAnnotation(
                source_annotation_id="entity-1",
                source_type="CLINENTITY",
                source_concept_id="C0000001",
                evidence_spans=(
                    EvidenceSpan(
                        start_char=0,
                        end_char=9,
                        text_snippet="Synthetic",
                    ),
                ),
            ),
        ),
        "relations": (
            SourceRelation(
                source_relation_id="relation-1",
                source_type="PERTAINS_TO",
                arguments=(
                    SourceRelationArgument(
                        role="target",
                        referenced_annotation_id="entity-2",
                    ),
                    SourceRelationArgument(
                        role="source",
                        referenced_annotation_id="entity-1",
                    ),
                ),
            ),
        ),
    }
    values.update(updates)
    return SourceAnnotationSet(**values)


def test_source_annotation_set_normalizes_and_sorts_set_like_values() -> None:
    first = annotation_set()
    second = SourceAnnotationSet(
        **{
            **first.model_dump(),
            "annotations": tuple(reversed(first.annotations)),
            "relations": tuple(reversed(first.relations)),
        }
    )

    assert first == second
    assert [item.source_annotation_id for item in first.annotations] == [
        "entity-1",
        "entity-2",
    ]
    assert [argument.role for argument in first.relations[0].arguments] == [
        "source",
        "target",
    ]


def test_source_annotation_set_normalizes_nfc_strings() -> None:
    item = SourceAnnotation(
        source_annotation_id="entite\u0301",
        source_type="CLINENTITY",
        attributes=(
            SourceAttribute(
                namespace="synthe\u0301tique",
                name="qualite\u0301",
                value="pre\u0301sent",
            ),
        ),
    )

    assert item.source_annotation_id == "entité"
    assert item.attributes[0].namespace == "synthétique"
    assert item.attributes[0].name == "qualité"
    assert item.attributes[0].value == "présent"


@pytest.mark.parametrize(
    "updates",
    [
        {
            "annotations": (
                SourceAnnotation(
                    source_annotation_id="café",
                    source_type="EVENT",
                ),
                SourceAnnotation(
                    source_annotation_id="cafe\u0301",
                    source_type="EVENT",
                ),
            )
        },
        {
            "relations": (
                SourceRelation(
                    source_relation_id="same",
                    source_type="RELATION",
                ),
            )
            * 2
        },
    ],
)
def test_source_annotation_set_rejects_duplicate_normalized_identities(
    updates: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        annotation_set(**updates)


def test_source_annotation_rejects_duplicate_attribute_identity() -> None:
    with pytest.raises(ValueError, match="duplicate attribute"):
        SourceAnnotation(
            source_annotation_id="entity-1",
            source_type="EVENT",
            attributes=(
                SourceAttribute(namespace="e3c", name="state", value="one"),
                SourceAttribute(namespace="e3c", name="state", value="two"),
            ),
        )


def test_source_relation_rejects_duplicate_argument_identity() -> None:
    argument = SourceRelationArgument(
        role="source",
        referenced_annotation_id="entity-1",
    )

    with pytest.raises(ValueError, match="duplicate argument"):
        SourceRelation(
            source_relation_id="relation-1",
            source_type="RELATION",
            arguments=(argument, argument),
        )


def test_source_annotation_set_rejects_dangling_relation_argument() -> None:
    relation = SourceRelation(
        source_relation_id="relation-1",
        source_type="RELATION",
        arguments=(
            SourceRelationArgument(
                role="source",
                referenced_annotation_id="missing",
            ),
        ),
    )

    with pytest.raises(ValueError, match="missing"):
        annotation_set(relations=(relation,))


def test_validate_source_annotation_set_checks_document_hash_and_spans() -> None:
    source_document = document()
    validate_source_annotation_set(source_document, annotation_set())

    wrong_document = Document.from_text(
        source_case_id="synthetic-2",
        case_group_id="synthetic-2",
        document_id="synthetic:en:2",
        language="en",
        translation_status=TranslationStatus.NATIVE,
        text="Different synthetic text.",
    )
    with pytest.raises(ValueError, match="document hash mismatch"):
        validate_source_annotation_set(wrong_document, annotation_set())


def test_validate_source_annotation_set_rejects_span_mismatch() -> None:
    invalid = SourceAnnotationSet(
        **{
            **annotation_set().model_dump(),
            "annotations": (
                SourceAnnotation(
                    source_annotation_id="entity-1",
                    source_type="CLINENTITY",
                    evidence_spans=(
                        EvidenceSpan(
                            start_char=0,
                            end_char=9,
                            text_snippet="Mismatch",
                        ),
                    ),
                ),
            ),
            "relations": (),
        }
    )

    with pytest.raises(ValueError, match="span text mismatch"):
        validate_source_annotation_set(document(), invalid)


def test_source_annotation_contract_is_strict_and_versioned() -> None:
    item = annotation_set()
    payload = item.model_dump(mode="json")

    assert payload["schema_version"] == "source-annotation-set/v1"
    assert SourceAnnotationSet.model_validate_json(json.dumps(payload)) == item

    payload["schema_version"] = "source-annotation-set/v2"
    with pytest.raises(ValidationError, match="schema_version"):
        SourceAnnotationSet.model_validate_json(json.dumps(payload))
    with pytest.raises(ValidationError):
        SourceAttribute(namespace=1, name="state", value="actual")

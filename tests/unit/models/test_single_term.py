import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.curated_annotation import (
    ActorKind,
    AnnotationReference,
    AssertionStatus,
    Experiencer,
    OntologyReference,
    Temporality,
)
from phentrieve_benchmark.models.single_term import (
    SingleTermRecord,
    SingleTermSelection,
    SingleTermSelectionRecord,
    SingleTermSet,
)


def _selection_record(suffix: str, span_index: int = 0) -> SingleTermSelectionRecord:
    return SingleTermSelectionRecord(
        annotation=AnnotationReference(
            annotation_set_sha256=suffix * 64,
            annotation_id="curated-ann-" + suffix * 64,
        ),
        evidence_span_index=span_index,
    )


def test_selection_records_provenance_and_is_canonical() -> None:
    first = _selection_record("a")
    second = _selection_record("b", 1)
    selection = SingleTermSelection(
        selector_id="human:selector-1",
        actor_kind=ActorKind.HUMAN,
        method_id="benchmark:explicit-span-selection/v1",
        source_review_set_sha256s=("d" * 64, "c" * 64),
        records=(second, first),
    )

    assert selection.source_review_set_sha256s == ("c" * 64, "d" * 64)
    assert selection.records == (first, second)
    assert SingleTermSelection.model_validate_json(
        selection.canonical_bytes()
    ) == selection
    assert len(selection.sha256()) == 64


def test_selection_rejects_duplicate_reviews_and_records() -> None:
    record = _selection_record("a")
    with pytest.raises(ValidationError, match="duplicate review"):
        SingleTermSelection(
            selector_id="tool:selector/v1",
            actor_kind=ActorKind.TOOL,
            method_id="benchmark:explicit-span-selection/v1",
            source_review_set_sha256s=("c" * 64, "c" * 64),
            records=(record,),
        )
    with pytest.raises(ValidationError, match="duplicate selection"):
        SingleTermSelection(
            selector_id="tool:selector/v1",
            actor_kind=ActorKind.TOOL,
            method_id="benchmark:explicit-span-selection/v1",
            records=(record, record),
        )


def test_single_term_record_has_stable_source_derived_identity() -> None:
    annotation = _selection_record("a").annotation
    first = SingleTermRecord.create(
        document_sha256="b" * 64,
        annotation=annotation,
        evidence_span_index=0,
        hpo_id="HP:0000002",
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
        start_char=1,
        end_char=7,
        term_text="Ataxie",
    )
    second = SingleTermRecord.create(
        document_sha256="b" * 64,
        annotation=annotation,
        evidence_span_index=0,
        hpo_id="HP:0000002",
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
        start_char=1,
        end_char=7,
        term_text="Ataxie",
    )

    assert first == second
    assert first.single_term_id.startswith("single-term-")


def test_single_term_record_rejects_wrong_identity() -> None:
    valid = SingleTermRecord.create(
        document_sha256="b" * 64,
        annotation=_selection_record("a").annotation,
        evidence_span_index=0,
        hpo_id="HP:0000002",
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
        start_char=1,
        end_char=7,
        term_text="Ataxie",
    )
    with pytest.raises(ValidationError, match="single_term_id mismatch"):
        SingleTermRecord.model_validate(
            {
                **valid.model_dump(mode="python"),
                "single_term_id": "single-term-" + "0" * 64,
            }
        )


def test_single_term_set_is_canonical_and_self_describing() -> None:
    first = SingleTermRecord.create(
        document_sha256="a" * 64,
        annotation=_selection_record("a").annotation,
        evidence_span_index=0,
        hpo_id="HP:0000001",
        assertion=AssertionStatus.ABSENT,
        experiencer=Experiencer.OTHER,
        temporality=Temporality.HISTORICAL,
        start_char=0,
        end_char=4,
        term_text="Test",
    )
    second = SingleTermRecord.create(
        document_sha256="b" * 64,
        annotation=_selection_record("b").annotation,
        evidence_span_index=1,
        hpo_id="HP:0000002",
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
        start_char=5,
        end_char=11,
        term_text="Ataxie",
    )
    terms = SingleTermSet(
        selection_sha256="c" * 64,
        ontology=OntologyReference(
            hpo_release="v2026-06-23",
            ontology_sha256="d" * 64,
        ),
        records=(second, first),
    )

    assert terms.records == (first, second)
    assert SingleTermSet.model_validate_json(terms.canonical_bytes()) == terms
    assert len(terms.sha256()) == 64

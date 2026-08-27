from collections.abc import Mapping

from phentrieve_benchmark.curation.validation import (
    CuratedDependencies,
    validate_curated_annotation_set,
)
from phentrieve_benchmark.models.curated_annotation import (
    AnnotationReference,
    CuratedAnnotation,
    CuratedAnnotationSet,
    OntologyReference,
)
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.review_decision import (
    ReviewDecisionSet,
    validate_review_decision_set,
)
from phentrieve_benchmark.models.single_term import (
    SingleTermRecord,
    SingleTermSelection,
    SingleTermSelectionRecord,
    SingleTermSet,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex


def _resolve_document(
    annotation_set: CuratedAnnotationSet,
    dependencies: CuratedDependencies,
) -> Document:
    documents = dependencies.documents.get(
        annotation_set.document.documents_sha256
    )
    if documents is None:
        raise ValueError("referenced document artifact is missing")
    matches = [
        document
        for document in documents
        if document.document_id == annotation_set.document.document_id
        and document.document_sha256
        == annotation_set.document.document_sha256
    ]
    if len(matches) != 1:
        raise ValueError("referenced document does not resolve uniquely")
    return matches[0]


def _resolve_annotation(
    selection_record: SingleTermSelectionRecord,
    dependencies: CuratedDependencies,
) -> tuple[CuratedAnnotationSet, CuratedAnnotation]:
    reference = selection_record.annotation
    annotation_set = dependencies.curated_sets.get(
        reference.annotation_set_sha256
    )
    if annotation_set is None:
        raise ValueError("referenced curated annotation set is missing")
    if annotation_set.sha256() != reference.annotation_set_sha256:
        raise ValueError("curated annotation set hash mismatch")
    matches = [
        annotation
        for annotation in annotation_set.annotations
        if annotation.annotation_id == reference.annotation_id
    ]
    if len(matches) != 1:
        raise ValueError("referenced curated annotation does not resolve uniquely")
    return annotation_set, matches[0]


def _validate_reviews(
    selection: SingleTermSelection,
    review_sets: Mapping[str, ReviewDecisionSet],
    annotation_sets: Mapping[str, CuratedAnnotationSet],
) -> None:
    for review_sha256 in selection.source_review_set_sha256s:
        review_set = review_sets.get(review_sha256)
        if review_set is None:
            raise ValueError("referenced review decision set is missing")
        if review_set.sha256() != review_sha256:
            raise ValueError("review decision set hash mismatch")
        validate_review_decision_set(
            review_set,
            annotation_sets=annotation_sets,
            decision_sets=review_sets,
        )


def _validate_ontology(
    annotation_set: CuratedAnnotationSet,
    hpo_index: HpoIndex,
) -> None:
    if (
        annotation_set.ontology.hpo_release != hpo_index.release
        or annotation_set.ontology.ontology_sha256
        != hpo_index.ontology_sha256
    ):
        raise ValueError("curated annotation set ontology mismatch")


def _derive_record(
    selection_record: SingleTermSelectionRecord,
    *,
    dependencies: CuratedDependencies,
    hpo_index: HpoIndex,
) -> SingleTermRecord:
    annotation_set, annotation = _resolve_annotation(
        selection_record, dependencies
    )
    _validate_ontology(annotation_set, hpo_index)
    validate_curated_annotation_set(annotation_set, dependencies)
    document = _resolve_document(annotation_set, dependencies)

    index = selection_record.evidence_span_index
    if index >= len(annotation.evidence_spans):
        raise ValueError("selected evidence span does not exist")
    span = annotation.evidence_spans[index]
    if span.end_char > len(document.text):
        raise ValueError("selected evidence span ends past document")
    term_text = document.text[span.start_char : span.end_char]
    if term_text != span.text_snippet:
        raise ValueError("selected evidence span text mismatch")
    if annotation.hpo_id not in hpo_index.terms:
        raise ValueError("selected HPO identifier is absent from ontology")

    return SingleTermRecord.create(
        document_sha256=document.document_sha256,
        annotation=AnnotationReference(
            annotation_set_sha256=selection_record.annotation.annotation_set_sha256,
            annotation_id=annotation.annotation_id,
        ),
        evidence_span_index=index,
        hpo_id=annotation.hpo_id,
        assertion=annotation.assertion,
        experiencer=annotation.experiencer,
        temporality=annotation.temporality,
        start_char=span.start_char,
        end_char=span.end_char,
        term_text=term_text,
    )


def derive_single_terms(
    selection: SingleTermSelection,
    *,
    dependencies: CuratedDependencies,
    review_sets: Mapping[str, ReviewDecisionSet],
    hpo_index: HpoIndex,
) -> SingleTermSet:
    # Re-validate even model instances so callers cannot bypass uniqueness or
    # canonicalization with Pydantic's low-level construction helpers.
    selection = SingleTermSelection.model_validate(
        selection.model_dump(mode="python")
    )
    _validate_reviews(selection, review_sets, dependencies.curated_sets)
    stored_index = dependencies.hpo_indexes.get(hpo_index.ontology_sha256)
    if (
        stored_index is None
        or stored_index.release != hpo_index.release
        or stored_index.ontology_sha256 != hpo_index.ontology_sha256
    ):
        raise ValueError("exact ontology dependency is missing")

    records = tuple(
        _derive_record(
            selection_record,
            dependencies=dependencies,
            hpo_index=hpo_index,
        )
        for selection_record in selection.records
    )
    return SingleTermSet(
        selection_sha256=selection.sha256(),
        ontology=OntologyReference(
            hpo_release=hpo_index.release,
            ontology_sha256=hpo_index.ontology_sha256,
        ),
        records=records,
    )

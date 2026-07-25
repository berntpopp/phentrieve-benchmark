from hashlib import sha256

import pytest

from phentrieve_benchmark.curation.validation import CuratedDependencies
from phentrieve_benchmark.derivation.single_term import derive_single_terms
from phentrieve_benchmark.models.annotation import EvidenceSpan
from phentrieve_benchmark.models.curated_annotation import (
    ActorKind,
    AnnotationReference,
    AssertionStatus,
    BoundDocumentReference,
    CuratedAnnotation,
    CuratedAnnotationSet,
    DerivationActivity,
    DerivationMethod,
    DocumentReference,
    Experiencer,
    OntologyReference,
    Temporality,
)
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.review_decision import ReviewDecisionSet
from phentrieve_benchmark.models.single_term import (
    SingleTermSelection,
    SingleTermSelectionRecord,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex, load_hpo_index
from tests.fixtures.hpo import synthetic_hpo_obo


def _index() -> HpoIndex:
    body = synthetic_hpo_obo()
    return load_hpo_index(
        body,
        release="v2026-06-23",
        ontology_sha256=sha256(body).hexdigest(),
    )


def _document(identifier: str, text: str) -> Document:
    return Document.from_text(
        source_case_id=identifier,
        case_group_id=identifier,
        document_id=f"e3c:de:{identifier}",
        language="de",
        translation_status=TranslationStatus.NATIVE,
        text=text,
    )


def _curated(
    document: Document,
    index: HpoIndex,
    documents_sha256: str,
    *,
    hpo_id: str,
    start: int,
    end: int,
) -> CuratedAnnotationSet:
    annotation = CuratedAnnotation.create(
        hpo_id=hpo_id,
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
        evidence_spans=(
            EvidenceSpan(
                start_char=start,
                end_char=end,
                text_snippet=document.text[start:end],
            ),
        ),
        derivations=(
            DerivationActivity(
                method=DerivationMethod.MANUAL_ANNOTATION,
                agent_id="human:curator-1",
                actor_kind=ActorKind.HUMAN,
                sources=(BoundDocumentReference(),),
            ),
        ),
    )
    return CuratedAnnotationSet(
        annotation_set_id=f"curated:{document.document_id}",
        document=DocumentReference(
            documents_sha256=documents_sha256,
            document_id=document.document_id,
            document_sha256=document.document_sha256,
        ),
        ontology=OntologyReference(
            hpo_release=index.release,
            ontology_sha256=index.ontology_sha256,
        ),
        annotations=(annotation,),
    )


def _fixture() -> tuple[
    HpoIndex,
    CuratedDependencies,
    dict[str, ReviewDecisionSet],
    SingleTermSelection,
]:
    index = _index()
    first_doc = _document("case-1", "Keine Ataxie.")
    second_doc = _document("case-2", "Tremor vorhanden.")
    documents_sha = "a" * 64
    first = _curated(
        first_doc,
        index,
        documents_sha,
        hpo_id="HP:0000002",
        start=6,
        end=12,
    )
    second = _curated(
        second_doc,
        index,
        documents_sha,
        hpo_id="HP:0000001",
        start=0,
        end=6,
    )
    curated_sets = {first.sha256(): first, second.sha256(): second}
    review_set = ReviewDecisionSet()
    review_sets = {review_set.sha256(): review_set}
    dependencies = CuratedDependencies(
        documents={documents_sha: (first_doc, second_doc)},
        source_annotations={},
        mappings={},
        raghpo_annotations={},
        raghpo_sidecars={},
        curated_sets=curated_sets,
        hpo_indexes={index.ontology_sha256: index},
    )
    records = tuple(
        SingleTermSelectionRecord(
            annotation=AnnotationReference(
                annotation_set_sha256=set_sha,
                annotation_id=annotation_set.annotations[0].annotation_id,
            ),
            evidence_span_index=0,
        )
        for set_sha, annotation_set in reversed(tuple(curated_sets.items()))
    )
    selection = SingleTermSelection(
        selector_id="human:selector-1",
        actor_kind=ActorKind.HUMAN,
        method_id="benchmark:explicit-span-selection/v1",
        source_review_set_sha256s=(review_set.sha256(),),
        records=records,
    )
    return index, dependencies, review_sets, selection


def test_derives_exact_terms_across_documents_deterministically() -> None:
    index, dependencies, review_sets, selection = _fixture()
    terms = derive_single_terms(
        selection,
        dependencies=dependencies,
        review_sets=review_sets,
        hpo_index=index,
    )
    reversed_dependencies = CuratedDependencies(
        documents=dependencies.documents,
        source_annotations={},
        mappings={},
        raghpo_annotations={},
        raghpo_sidecars={},
        curated_sets=dict(reversed(tuple(dependencies.curated_sets.items()))),
        hpo_indexes=dependencies.hpo_indexes,
    )
    repeated = derive_single_terms(
        selection,
        dependencies=reversed_dependencies,
        review_sets=review_sets,
        hpo_index=index,
    )

    assert terms == repeated
    assert terms.canonical_bytes() == repeated.canonical_bytes()
    assert {record.term_text for record in terms.records} == {
        "Ataxie",
        "Tremor",
    }
    assert {record.hpo_id for record in terms.records} == {
        "HP:0000001",
        "HP:0000002",
    }
    assert terms.selection_sha256 == selection.sha256()


def test_derivation_requires_all_consulted_review_sets() -> None:
    index, dependencies, _, selection = _fixture()
    with pytest.raises(ValueError, match="review decision set"):
        derive_single_terms(
            selection,
            dependencies=dependencies,
            review_sets={},
            hpo_index=index,
        )


def test_derivation_rejects_missing_annotation_or_span() -> None:
    index, dependencies, review_sets, selection = _fixture()
    missing = selection.model_copy(
        update={
            "records": (
                selection.records[0].model_copy(
                    update={
                        "annotation": AnnotationReference(
                            annotation_set_sha256="f" * 64,
                            annotation_id="curated-ann-" + "f" * 64,
                        )
                    }
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="annotation set"):
        derive_single_terms(
            missing,
            dependencies=dependencies,
            review_sets=review_sets,
            hpo_index=index,
        )

    out_of_range = selection.model_copy(
        update={
            "records": (
                selection.records[0].model_copy(
                    update={"evidence_span_index": 10}
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="evidence span"):
        derive_single_terms(
            out_of_range,
            dependencies=dependencies,
            review_sets=review_sets,
            hpo_index=index,
        )


def test_derivation_rejects_annotation_without_evidence_span() -> None:
    index, dependencies, review_sets, selection = _fixture()
    set_sha = selection.records[0].annotation.annotation_set_sha256
    annotation_set = dependencies.curated_sets[set_sha]
    original = annotation_set.annotations[0]
    spanless = CuratedAnnotation.create(
        hpo_id=original.hpo_id,
        assertion=original.assertion,
        experiencer=original.experiencer,
        temporality=original.temporality,
        evidence_spans=(),
        derivations=original.derivations,
    )
    spanless_set = annotation_set.model_copy(
        update={"annotations": (spanless,)}
    )
    spanless_sha = spanless_set.sha256()
    changed = selection.model_copy(
        update={
            "records": (
                SingleTermSelectionRecord(
                    annotation=AnnotationReference(
                        annotation_set_sha256=spanless_sha,
                        annotation_id=spanless.annotation_id,
                    ),
                    evidence_span_index=0,
                ),
            )
        }
    )
    changed_dependencies = CuratedDependencies(
        documents=dependencies.documents,
        source_annotations={},
        mappings={},
        raghpo_annotations={},
        raghpo_sidecars={},
        curated_sets={spanless_sha: spanless_set},
        hpo_indexes=dependencies.hpo_indexes,
    )

    with pytest.raises(ValueError, match="evidence span"):
        derive_single_terms(
            changed,
            dependencies=changed_dependencies,
            review_sets=review_sets,
            hpo_index=index,
        )


def test_derivation_rejects_wrong_document_and_ontology() -> None:
    index, dependencies, review_sets, selection = _fixture()
    wrong_documents = CuratedDependencies(
        documents={},
        source_annotations={},
        mappings={},
        raghpo_annotations={},
        raghpo_sidecars={},
        curated_sets=dependencies.curated_sets,
        hpo_indexes=dependencies.hpo_indexes,
    )
    with pytest.raises(ValueError, match="document artifact"):
        derive_single_terms(
            selection,
            dependencies=wrong_documents,
            review_sets=review_sets,
            hpo_index=index,
        )

    other_body = synthetic_hpo_obo().replace(
        b"name: Active root",
        b"name: Other root",
    )
    other_index = load_hpo_index(
        other_body,
        release=index.release,
        ontology_sha256=sha256(other_body).hexdigest(),
    )
    with pytest.raises(ValueError, match="ontology"):
        derive_single_terms(
            selection,
            dependencies=dependencies,
            review_sets=review_sets,
            hpo_index=other_index,
        )


def test_derivation_does_not_interpret_review_outcomes() -> None:
    index, dependencies, review_sets, selection = _fixture()

    terms = derive_single_terms(
        selection,
        dependencies=dependencies,
        review_sets=review_sets,
        hpo_index=index,
    )

    assert len(terms.records) == len(selection.records)

import json

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.annotation import EvidenceSpan
from phentrieve_benchmark.models.curated_annotation import (
    ActorKind,
    AssertionStatus,
    BoundDocumentReference,
    CuratedAnnotation,
    CuratedAnnotationSet,
    DerivationActivity,
    DerivationMethod,
    DocumentReference,
    E3cSourceAnnotationReference,
    Experiencer,
    OntologyReference,
    Temporality,
    UmlsHpoMappingReference,
)


def _activity(*, reverse_sources: bool = False) -> DerivationActivity:
    sources = (
        E3cSourceAnnotationReference(
            source_annotations_sha256="a" * 64,
            source_annotation_set_id="source-set-1",
            source_annotation_id="source-ann-1",
        ),
        UmlsHpoMappingReference(
            mapping_manifest_sha256="b" * 64,
            mapping_record_id="mapping-1",
        ),
    )
    return DerivationActivity(
        method=DerivationMethod.DIRECT_MAPPING,
        agent_id="tool:hpo-xref/v1",
        actor_kind=ActorKind.TOOL,
        sources=tuple(reversed(sources)) if reverse_sources else sources,
    )


def _annotation(*, reverse: bool = False) -> CuratedAnnotation:
    spans = (
        EvidenceSpan(start_char=10, end_char=16, text_snippet="Ataxie"),
        EvidenceSpan(start_char=0, end_char=6, text_snippet="Schmerz"),
    )
    return CuratedAnnotation.create(
        hpo_id="HP:0001251",
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
        evidence_spans=tuple(reversed(spans)) if reverse else spans,
        derivations=(_activity(reverse_sources=reverse),),
    )


def test_curated_annotation_has_content_id_and_canonical_sets() -> None:
    first = _annotation()
    second = _annotation(reverse=True)

    assert first == second
    assert first.annotation_id.startswith("curated-ann-")
    assert [span.start_char for span in first.evidence_spans] == [0, 10]
    assert [
        source.source_kind for source in first.derivations[0].sources
    ] == ["e3c_source_annotation", "umls_hpo_mapping_record"]


def test_changed_semantic_content_changes_annotation_id() -> None:
    first = _annotation()
    changed = CuratedAnnotation.create(
        hpo_id="HP:0002315",
        assertion=first.assertion,
        experiencer=first.experiencer,
        temporality=first.temporality,
        evidence_spans=first.evidence_spans,
        derivations=first.derivations,
    )

    assert changed.annotation_id != first.annotation_id


def test_explicit_wrong_annotation_id_is_rejected() -> None:
    valid = _annotation()
    payload = valid.model_dump(mode="json")
    payload["annotation_id"] = "curated-ann-" + "0" * 64

    with pytest.raises(ValidationError, match="annotation_id mismatch"):
        CuratedAnnotation.model_validate_json(json.dumps(payload))


def test_duplicate_span_and_source_are_rejected() -> None:
    span = EvidenceSpan(start_char=0, end_char=6, text_snippet="Ataxie")
    with pytest.raises(ValueError, match="duplicate evidence span"):
        CuratedAnnotation.create(
            hpo_id="HP:0001251",
            assertion=AssertionStatus.PRESENT,
            experiencer=Experiencer.PATIENT,
            temporality=Temporality.CURRENT,
            evidence_spans=(span, span),
            derivations=(_activity(),),
        )

    source = BoundDocumentReference()
    with pytest.raises(ValidationError, match="duplicate derivation source"):
        DerivationActivity(
            method=DerivationMethod.MANUAL_ANNOTATION,
            agent_id="human:curator-1",
            actor_kind=ActorKind.HUMAN,
            sources=(source, source),
        )


def test_curated_annotation_set_is_canonical_and_strict() -> None:
    first = _annotation()
    second = CuratedAnnotation.create(
        hpo_id="HP:0002315",
        assertion=AssertionStatus.UNCERTAIN,
        experiencer=Experiencer.OTHER,
        temporality=Temporality.HISTORICAL,
        evidence_spans=(),
        derivations=(
            DerivationActivity(
                method=DerivationMethod.MANUAL_ANNOTATION,
                agent_id="human:curator-1",
                actor_kind=ActorKind.HUMAN,
                sources=(BoundDocumentReference(),),
            ),
        ),
    )
    annotation_set = CuratedAnnotationSet(
        annotation_set_id="e3c:de:case-1:curated/v1",
        document=DocumentReference(
            documents_sha256="c" * 64,
            document_id="e3c:de:case-1",
            document_sha256="d" * 64,
        ),
        ontology=OntologyReference(
            hpo_release="v2026-06-23",
            ontology_sha256="e" * 64,
        ),
        annotations=(second, first),
    )
    reparsed = CuratedAnnotationSet.model_validate_json(
        annotation_set.canonical_bytes()
    )

    assert reparsed == annotation_set
    assert annotation_set.annotations == tuple(
        sorted((first, second), key=lambda item: item.annotation_id)
    )
    assert annotation_set.sha256() == annotation_set.sha256()
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CuratedAnnotationSet.model_validate(
            {
                **json.loads(annotation_set.canonical_bytes()),
                "status": "accepted",
            }
        )

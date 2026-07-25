from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from phentrieve_benchmark.models.annotation import AnnotationSet
from phentrieve_benchmark.models.curated_annotation import (
    BoundDocumentReference,
    CuratedAnnotation,
    CuratedAnnotationReference,
    CuratedAnnotationSet,
    DerivationActivity,
    DerivationMethod,
    E3cSourceAnnotationReference,
    RagHpoSourceAnnotationReference,
    UmlsHpoMappingReference,
)
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.mapping import (
    UmlsHpoMappingManifest,
    UmlsHpoMappingRecord,
)
from phentrieve_benchmark.models.source_annotation import SourceAnnotationSet
from phentrieve_benchmark.normalization.contracts import (
    RagHpoSourceAnnotationRecord,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex

T = TypeVar("T")


@dataclass(frozen=True)
class CuratedDependencies:
    documents: Mapping[str, tuple[Document, ...]]
    source_annotations: Mapping[str, tuple[SourceAnnotationSet, ...]]
    mappings: Mapping[str, UmlsHpoMappingManifest]
    raghpo_annotations: Mapping[str, tuple[AnnotationSet, ...]]
    raghpo_sidecars: Mapping[str, tuple[RagHpoSourceAnnotationRecord, ...]]
    curated_sets: Mapping[str, CuratedAnnotationSet]
    hpo_indexes: Mapping[str, HpoIndex]


def _one_by_id(
    records: tuple[T, ...],
    *,
    identity: str,
    identity_of: Callable[[T], str],
    description: str,
) -> T:
    matched = [
        record for record in records if identity_of(record) == identity
    ]
    if len(matched) != 1:
        raise ValueError(f"{description} does not resolve uniquely")
    return matched[0]


def _document(
    annotation_set: CuratedAnnotationSet,
    dependencies: CuratedDependencies,
) -> Document:
    records = dependencies.documents.get(
        annotation_set.document.documents_sha256
    )
    if records is None:
        raise ValueError("document artifact is missing")
    document = _one_by_id(
        records,
        identity=annotation_set.document.document_id,
        identity_of=lambda record: record.document_id,
        description="document reference",
    )
    if document.document_sha256 != annotation_set.document.document_sha256:
        raise ValueError("document SHA-256 mismatch")
    return document


def _source_annotation(
    reference: E3cSourceAnnotationReference,
    dependencies: CuratedDependencies,
) -> tuple[SourceAnnotationSet, str | None]:
    records = dependencies.source_annotations.get(
        reference.source_annotations_sha256
    )
    if records is None:
        raise ValueError("source annotation artifact is missing")
    annotation_set = _one_by_id(
        records,
        identity=reference.source_annotation_set_id,
        identity_of=lambda record: record.annotation_set_id,
        description="source annotation set",
    )
    annotation = _one_by_id(
        annotation_set.annotations,
        identity=reference.source_annotation_id,
        identity_of=lambda record: record.source_annotation_id,
        description="source annotation",
    )
    return annotation_set, annotation.source_concept_id


def _mapping_record(
    reference: UmlsHpoMappingReference,
    dependencies: CuratedDependencies,
) -> UmlsHpoMappingRecord:
    manifest = dependencies.mappings.get(reference.mapping_manifest_sha256)
    if manifest is None:
        raise ValueError("mapping manifest is missing")
    return _one_by_id(
        manifest.records,
        identity=reference.mapping_record_id,
        identity_of=lambda record: record.mapping_record_id,
        description="mapping record",
    )


def _raghpo_hpo_id(
    reference: RagHpoSourceAnnotationReference,
    dependencies: CuratedDependencies,
) -> str:
    annotation_sets = dependencies.raghpo_annotations.get(
        reference.annotations_sha256
    )
    if annotation_sets is None:
        raise ValueError("RAG-HPO annotation artifact is missing")
    annotation_set = _one_by_id(
        annotation_sets,
        identity=reference.annotation_set_id,
        identity_of=lambda record: record.annotation_set_id,
        description="RAG-HPO annotation set",
    )
    annotation = _one_by_id(
        annotation_set.annotations,
        identity=reference.annotation_id,
        identity_of=lambda record: record.annotation_id,
        description="RAG-HPO annotation",
    )
    sidecars = dependencies.raghpo_sidecars.get(reference.source_sidecar_sha256)
    if sidecars is None:
        raise ValueError("RAG-HPO sidecar artifact is missing")
    sidecar = _one_by_id(
        sidecars,
        identity=reference.source_row_id,
        identity_of=lambda record: record.source_row_id,
        description="RAG-HPO source row",
    )
    if annotation.annotation_id not in sidecar.derived_annotation_ids:
        raise ValueError("RAG-HPO source row does not derive annotation")
    return annotation.hpo_id


def _curated_annotation(
    reference: CuratedAnnotationReference,
    dependencies: CuratedDependencies,
) -> CuratedAnnotation:
    annotation_set = dependencies.curated_sets.get(
        reference.annotation.annotation_set_sha256
    )
    if annotation_set is None:
        raise ValueError("curated annotation artifact is missing")
    return _one_by_id(
        annotation_set.annotations,
        identity=reference.annotation.annotation_id,
        identity_of=lambda record: record.annotation_id,
        description="curated annotation",
    )


def _validate_activity(
    annotation: CuratedAnnotation,
    activity: DerivationActivity,
    dependencies: CuratedDependencies,
) -> None:
    source_annotations: list[
        tuple[E3cSourceAnnotationReference, SourceAnnotationSet, str | None]
    ] = []
    mapping_records: list[
        tuple[UmlsHpoMappingReference, UmlsHpoMappingRecord]
    ] = []
    raghpo_hpo_ids: list[str] = []
    curated_sources = 0
    bound_documents = 0

    for source in activity.sources:
        if isinstance(source, E3cSourceAnnotationReference):
            source_set, concept_id = _source_annotation(source, dependencies)
            source_annotations.append((source, source_set, concept_id))
        elif isinstance(source, UmlsHpoMappingReference):
            mapping_records.append(
                (source, _mapping_record(source, dependencies))
            )
        elif isinstance(source, RagHpoSourceAnnotationReference):
            raghpo_hpo_ids.append(_raghpo_hpo_id(source, dependencies))
        elif isinstance(source, CuratedAnnotationReference):
            _curated_annotation(source, dependencies)
            curated_sources += 1
        elif isinstance(source, BoundDocumentReference):
            bound_documents += 1

    if activity.method is DerivationMethod.DIRECT_MAPPING:
        if not source_annotations or not mapping_records:
            raise ValueError(
                "direct mapping requires source annotation and mapping record"
            )
        matched = False
        for source_ref, _, concept_id in source_annotations:
            for _, record in mapping_records:
                same_source = (
                    record.source_annotation_set_id
                    == source_ref.source_annotation_set_id
                    and record.source_annotation_id
                    == source_ref.source_annotation_id
                    and record.source_concept_id == concept_id
                )
                has_candidate = any(
                    candidate.hpo_id == annotation.hpo_id
                    for candidate in record.candidates
                )
                matched = matched or (same_source and has_candidate)
        if not matched:
            raise ValueError("HPO identifier is not a mapping candidate")
    elif activity.method is DerivationMethod.SOURCE_HPO:
        if annotation.hpo_id not in raghpo_hpo_ids:
            raise ValueError("source HPO annotation does not match proposal")
    elif activity.method is DerivationMethod.REVISION:
        if curated_sources == 0:
            raise ValueError("revision requires curated annotation source")
    elif activity.method is DerivationMethod.MANUAL_ANNOTATION:
        if bound_documents == 0:
            raise ValueError("manual annotation requires bound document")


def validate_curated_annotation_set(
    annotation_set: CuratedAnnotationSet,
    dependencies: CuratedDependencies,
) -> None:
    document = _document(annotation_set, dependencies)
    index = dependencies.hpo_indexes.get(
        annotation_set.ontology.ontology_sha256
    )
    if index is None:
        raise ValueError("HPO ontology artifact is missing")
    if (
        index.ontology_sha256 != annotation_set.ontology.ontology_sha256
        or index.release != annotation_set.ontology.hpo_release
    ):
        raise ValueError("HPO ontology identity mismatch")

    for annotation in annotation_set.annotations:
        if annotation.hpo_id not in index.terms:
            raise ValueError("HPO identifier does not exist in ontology")
        for span in annotation.evidence_spans:
            if span.end_char > len(document.text):
                raise ValueError("span ends past document end")
            if document.text[span.start_char : span.end_char] != span.text_snippet:
                raise ValueError("span text mismatch")
        for activity in annotation.derivations:
            _validate_activity(annotation, activity, dependencies)

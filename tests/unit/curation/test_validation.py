from hashlib import sha256

import pytest
from pydantic import BaseModel

from phentrieve_benchmark.curation.validation import (
    CuratedDependencies,
    validate_curated_annotation_set,
)
from phentrieve_benchmark.mapping.e3c import map_e3c_umls_to_hpo
from phentrieve_benchmark.models.annotation import (
    Annotation,
    AnnotationSet,
    EvidenceSpan,
)
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
    RagHpoSourceAnnotationReference,
    Temporality,
    UmlsHpoMappingReference,
)
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.mapping import UmlsHpoMappingManifest
from phentrieve_benchmark.models.source_annotation import (
    SourceAnnotation,
    SourceAnnotationSet,
)
from phentrieve_benchmark.normalization.contracts import (
    RagHpoSourceAnnotationRecord,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex, load_hpo_index
from phentrieve_benchmark.provenance.canonical import canonical_jsonl_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes
from tests.fixtures.hpo import synthetic_hpo_obo


def _artifact_sha(
    records: tuple[BaseModel, ...], identity_key: str
) -> str:
    return sha256_bytes(
        canonical_jsonl_bytes(
            [record.model_dump(mode="json") for record in records],
            identity_key=identity_key,
        )
    )


def _document() -> Document:
    return Document.from_text(
        source_case_id="case-1",
        case_group_id="case-1",
        document_id="e3c:de:case-1",
        language="de",
        translation_status=TranslationStatus.NATIVE,
        text="Ataxie",
    )


def _source(document: Document) -> SourceAnnotationSet:
    return SourceAnnotationSet(
        annotation_set_id="source-set-1",
        document_sha256=document.document_sha256,
        source_schema_id="e3c",
        annotations=(
            SourceAnnotation(
                source_annotation_id="source-ann-1",
                source_type="CLINENTITY",
                source_concept_id="C0000002",
                evidence_spans=(
                    EvidenceSpan(
                        start_char=0,
                        end_char=6,
                        text_snippet="Ataxie",
                    ),
                ),
            ),
        ),
    )


def _index() -> HpoIndex:
    body = synthetic_hpo_obo()
    return load_hpo_index(
        body,
        release="v2026-06-23",
        ontology_sha256=sha256(body).hexdigest(),
    )


def _direct_fixture() -> tuple[
    Document,
    SourceAnnotationSet,
    HpoIndex,
    UmlsHpoMappingManifest,
    CuratedAnnotationSet,
]:
    document = _document()
    source = _source(document)
    documents_sha = _artifact_sha((document,), "document_id")
    source_annotations_sha = _artifact_sha(
        (source,), "annotation_set_id"
    )
    index = _index()
    mapping = map_e3c_umls_to_hpo(
        documents=(document,),
        annotation_sets=(source,),
        hpo_index=index,
        documents_sha256=documents_sha,
        source_annotations_sha256=source_annotations_sha,
    )
    annotation = CuratedAnnotation.create(
        hpo_id="HP:0000002",
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
        evidence_spans=(
            EvidenceSpan(start_char=0, end_char=6, text_snippet="Ataxie"),
        ),
        derivations=(
            DerivationActivity(
                method=DerivationMethod.DIRECT_MAPPING,
                agent_id="tool:hpo-xref/v1",
                actor_kind=ActorKind.TOOL,
                sources=(
                    E3cSourceAnnotationReference(
                        source_annotations_sha256=source_annotations_sha,
                        source_annotation_set_id=source.annotation_set_id,
                        source_annotation_id="source-ann-1",
                    ),
                    UmlsHpoMappingReference(
                        mapping_manifest_sha256=mapping.sha256(),
                        mapping_record_id=mapping.records[0].mapping_record_id,
                    ),
                ),
            ),
        ),
    )
    curated = CuratedAnnotationSet(
        annotation_set_id="curated-set-1",
        document=DocumentReference(
            documents_sha256=documents_sha,
            document_id=document.document_id,
            document_sha256=document.document_sha256,
        ),
        ontology=OntologyReference(
            hpo_release=index.release,
            ontology_sha256=index.ontology_sha256,
        ),
        annotations=(annotation,),
    )
    return document, source, index, mapping, curated


def _dependencies() -> tuple[CuratedDependencies, CuratedAnnotationSet]:
    document, source, index, mapping, curated = _direct_fixture()
    return (
        CuratedDependencies(
            documents={
                _artifact_sha((document,), "document_id"): (document,)
            },
            source_annotations={
                _artifact_sha((source,), "annotation_set_id"): (source,)
            },
            mappings={mapping.sha256(): mapping},
            raghpo_annotations={},
            raghpo_sidecars={},
            curated_sets={},
            hpo_indexes={index.ontology_sha256: index},
        ),
        curated,
    )


def test_validates_exact_document_ontology_span_and_direct_mapping() -> None:
    dependencies, curated = _dependencies()

    validate_curated_annotation_set(curated, dependencies)


def test_rejects_missing_dependency_and_mapping_candidate_mismatch() -> None:
    dependencies, curated = _dependencies()
    missing = CuratedDependencies(
        documents=dependencies.documents,
        source_annotations={},
        mappings=dependencies.mappings,
        raghpo_annotations={},
        raghpo_sidecars={},
        curated_sets={},
        hpo_indexes=dependencies.hpo_indexes,
    )
    with pytest.raises(ValueError, match="source annotation artifact"):
        validate_curated_annotation_set(curated, missing)

    original = curated.annotations[0]
    wrong = CuratedAnnotation.create(
        hpo_id="HP:0000001",
        assertion=original.assertion,
        experiencer=original.experiencer,
        temporality=original.temporality,
        evidence_spans=original.evidence_spans,
        derivations=original.derivations,
    )
    with pytest.raises(ValueError, match="mapping candidate"):
        validate_curated_annotation_set(
            curated.model_copy(update={"annotations": (wrong,)}),
            dependencies,
        )


def test_rejects_span_mismatch_and_unknown_hpo_id() -> None:
    dependencies, curated = _dependencies()
    original = curated.annotations[0]
    bad_span = EvidenceSpan(start_char=0, end_char=5, text_snippet="Ataxx")
    changed = CuratedAnnotation.create(
        hpo_id=original.hpo_id,
        assertion=original.assertion,
        experiencer=original.experiencer,
        temporality=original.temporality,
        evidence_spans=(bad_span,),
        derivations=original.derivations,
    )
    with pytest.raises(ValueError, match="span text mismatch"):
        validate_curated_annotation_set(
            curated.model_copy(update={"annotations": (changed,)}),
            dependencies,
        )

    unknown = CuratedAnnotation.create(
        hpo_id="HP:9999999",
        assertion=original.assertion,
        experiencer=original.experiencer,
        temporality=original.temporality,
        evidence_spans=original.evidence_spans,
        derivations=(
            DerivationActivity(
                method=DerivationMethod.MANUAL_ANNOTATION,
                agent_id="human:curator-1",
                actor_kind=ActorKind.HUMAN,
                sources=(BoundDocumentReference(),),
            ),
        ),
    )
    with pytest.raises(ValueError, match="HPO identifier"):
        validate_curated_annotation_set(
            curated.model_copy(update={"annotations": (unknown,)}),
            dependencies,
        )


def test_rejects_dependency_stored_under_a_false_artifact_hash() -> None:
    dependencies, curated = _dependencies()
    false_hash = "f" * 64
    false_reference = curated.model_copy(
        update={
            "document": curated.document.model_copy(
                update={"documents_sha256": false_hash}
            )
        }
    )
    false_dependencies = CuratedDependencies(
        documents={
            false_hash: next(iter(dependencies.documents.values()))
        },
        source_annotations=dependencies.source_annotations,
        mappings=dependencies.mappings,
        raghpo_annotations={},
        raghpo_sidecars={},
        curated_sets={},
        hpo_indexes=dependencies.hpo_indexes,
    )

    with pytest.raises(ValueError, match="artifact SHA-256 mismatch"):
        validate_curated_annotation_set(
            false_reference, false_dependencies
        )


def test_validates_raghpo_annotation_and_sidecar_linkage() -> None:
    dependencies, curated = _dependencies()
    source_annotation = Annotation(
        annotation_id="rag-ann-1",
        hpo_id="HP:0000002",
    )
    source_set = AnnotationSet(
        annotation_set_id="rag-set-1",
        document_sha256=curated.document.document_sha256,
        hpo_release="v2026-06-23",
        annotations=(source_annotation,),
    )
    sidecar = RagHpoSourceAnnotationRecord(
        source_row_id="row-1",
        source_case_id="case-1",
        hpo_description="Ataxia",
        raw_hpo_term="HP:0000002",
        derived_annotation_ids=("rag-ann-1",),
    )
    annotations_sha = _artifact_sha((source_set,), "annotation_set_id")
    sidecar_sha = _artifact_sha((sidecar,), "source_row_id")
    annotation = CuratedAnnotation.create(
        hpo_id="HP:0000002",
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
        evidence_spans=(),
        derivations=(
            DerivationActivity(
                method=DerivationMethod.SOURCE_HPO,
                agent_id="tool:raghpo-import/v1",
                actor_kind=ActorKind.TOOL,
                sources=(
                    RagHpoSourceAnnotationReference(
                        annotations_sha256=annotations_sha,
                        annotation_set_id="rag-set-1",
                        annotation_id="rag-ann-1",
                        source_sidecar_sha256=sidecar_sha,
                        source_row_id="row-1",
                    ),
                ),
            ),
        ),
    )
    rag_dependencies = CuratedDependencies(
        documents=dependencies.documents,
        source_annotations={},
        mappings={},
        raghpo_annotations={annotations_sha: (source_set,)},
        raghpo_sidecars={sidecar_sha: (sidecar,)},
        curated_sets={},
        hpo_indexes=dependencies.hpo_indexes,
    )

    validate_curated_annotation_set(
        curated.model_copy(update={"annotations": (annotation,)}),
        rag_dependencies,
    )


def test_obsolete_hpo_term_remains_a_valid_reviewable_proposal() -> None:
    dependencies, curated = _dependencies()
    obsolete = CuratedAnnotation.create(
        hpo_id="HP:0000003",
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
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

    validate_curated_annotation_set(
        curated.model_copy(update={"annotations": (obsolete,)}),
        dependencies,
    )

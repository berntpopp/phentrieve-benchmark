import re
from collections import Counter

from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.mapping import (
    HpoMappingCandidate,
    MappingClassification,
    MappingCount,
    MappingDecision,
    MappingEvidence,
    UmlsHpoMappingManifest,
    UmlsHpoMappingRecord,
    UmlsHpoMappingSummary,
)
from phentrieve_benchmark.models.source_annotation import (
    SourceAnnotationSet,
    validate_source_annotation_set,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex
from phentrieve_benchmark.provenance.digests import sha256_bytes

_CUI = re.compile(r"C[0-9]{7}", re.ASCII)


def _summary(
    records: tuple[UmlsHpoMappingRecord, ...],
    *,
    document_count: int,
) -> UmlsHpoMappingSummary:
    counts = Counter(record.classification for record in records)
    return UmlsHpoMappingSummary(
        document_count=document_count,
        annotation_count=len(records),
        unique_cui_count=len(
            {
                record.source_concept_id
                for record in records
                if record.source_concept_id is not None
                and _CUI.fullmatch(record.source_concept_id)
            }
        ),
        candidate_count=sum(len(record.candidates) for record in records),
        classifications=tuple(
            MappingCount(classification=classification, count=counts[classification])
            for classification in MappingClassification
        ),
    )


def _classification(
    concept_id: str | None, candidate_ids: tuple[str, ...], index: HpoIndex
) -> MappingClassification:
    if concept_id is None or _CUI.fullmatch(concept_id) is None:
        return MappingClassification.INVALID
    if not candidate_ids:
        return MappingClassification.MISSING
    if len(candidate_ids) > 1:
        return MappingClassification.AMBIGUOUS
    return (
        MappingClassification.OBSOLETE
        if index.terms[candidate_ids[0]].obsolete
        else MappingClassification.UNIQUE_ACTIVE
    )


def map_e3c_umls_to_hpo(
    *,
    documents: tuple[Document, ...],
    annotation_sets: tuple[SourceAnnotationSet, ...],
    hpo_index: HpoIndex,
    normalization_sha256: str,
) -> UmlsHpoMappingManifest:
    by_hash: dict[str, Document] = {}
    for document in documents:
        if document.document_sha256 in by_hash:
            raise ValueError("duplicate E3C document hash")
        by_hash[document.document_sha256] = document

    records: list[UmlsHpoMappingRecord] = []
    for annotation_set in annotation_sets:
        source_document = by_hash.get(annotation_set.document_sha256)
        if source_document is None:
            raise ValueError("source annotation set has no E3C document")
        validate_source_annotation_set(source_document, annotation_set)
        for annotation in annotation_set.annotations:
            if annotation.source_type != "CLINENTITY":
                continue
            concept_id = annotation.source_concept_id
            candidate_ids = (
                hpo_index.umls_to_hpo.get(concept_id, ())
                if concept_id is not None and _CUI.fullmatch(concept_id)
                else ()
            )
            classification = _classification(
                concept_id, candidate_ids, hpo_index
            )
            candidates = tuple(
                HpoMappingCandidate(
                    hpo_id=term.hpo_id,
                    label=term.label,
                    obsolete=term.obsolete,
                    replaced_by=term.replaced_by,
                    consider=term.consider,
                )
                for term in (hpo_index.terms[value] for value in candidate_ids)
            )
            records.append(
                UmlsHpoMappingRecord(
                    mapping_record_id=(
                        f"{annotation_set.annotation_set_id}:"
                        f"{annotation.source_annotation_id}:umls-hpo"
                    ),
                    source_case_id=source_document.source_case_id,
                    source_annotation_set_id=annotation_set.annotation_set_id,
                    source_annotation_id=annotation.source_annotation_id,
                    source_document_sha256=source_document.document_sha256,
                    source_concept_id=concept_id,
                    evidence=tuple(
                        MappingEvidence(
                            start_char=span.start_char,
                            end_char=span.end_char,
                            text_sha256=sha256_bytes(
                                span.text_snippet.encode("utf-8")
                            ),
                        )
                        for span in annotation.evidence_spans
                    ),
                    candidates=candidates,
                    hpo_release=hpo_index.release,
                    ontology_sha256=hpo_index.ontology_sha256,
                    classification=classification,
                    decision=(
                        MappingDecision.CANDIDATE
                        if classification
                        is MappingClassification.UNIQUE_ACTIVE
                        else MappingDecision.NEEDS_REVIEW
                    ),
                    rationale=classification.value,
                )
            )
    ordered = tuple(
        sorted(
            records,
            key=lambda record: (
                record.source_case_id,
                record.source_annotation_set_id,
                record.source_annotation_id,
            ),
        )
    )
    population_case_ids = tuple(
        sorted(document.source_case_id for document in documents)
    )
    return UmlsHpoMappingManifest(
        mapping_id=f"e3c-l1-umls-hpo-{hpo_index.release}-v1",
        normalization_sha256=normalization_sha256,
        hpo_release=hpo_index.release,
        ontology_sha256=hpo_index.ontology_sha256,
        population_case_ids=population_case_ids,
        records=ordered,
        summary=_summary(ordered, document_count=len(population_case_ids)),
    )


def select_mapping_manifest(
    complete: UmlsHpoMappingManifest,
    *,
    selected_case_ids: tuple[str, ...],
    selection_id: str,
    selection_sha256: str,
) -> UmlsHpoMappingManifest:
    available = set(complete.population_case_ids)
    missing = sorted(set(selected_case_ids) - available)
    if missing:
        raise ValueError(f"selected case has no mapping population: {missing[0]}")
    selected = set(selected_case_ids)
    population_case_ids = tuple(sorted(selected))
    records = tuple(
        record
        for record in complete.records
        if record.source_case_id in selected
    )
    return UmlsHpoMappingManifest(
        mapping_id=f"{complete.mapping_id}:{selection_id}",
        normalization_sha256=complete.normalization_sha256,
        hpo_release=complete.hpo_release,
        ontology_sha256=complete.ontology_sha256,
        selection_id=selection_id,
        selection_sha256=selection_sha256,
        population_case_ids=population_case_ids,
        records=records,
        summary=_summary(records, document_count=len(population_case_ids)),
    )

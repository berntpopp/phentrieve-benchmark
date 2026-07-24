from hashlib import sha256

import pytest

from phentrieve_benchmark.mapping.e3c import (
    map_e3c_umls_to_hpo,
    select_mapping_manifest,
)
from phentrieve_benchmark.models.annotation import EvidenceSpan
from phentrieve_benchmark.models.document import (
    Document,
    TranslationStatus,
)
from phentrieve_benchmark.models.mapping import (
    MappingClassification,
    MappingDecision,
)
from phentrieve_benchmark.models.source_annotation import (
    SourceAnnotation,
    SourceAnnotationSet,
)
from phentrieve_benchmark.ontology.hpo import load_hpo_index
from tests.fixtures.hpo import synthetic_hpo_obo


def _document(case_id: str, text: str) -> Document:
    return Document.from_text(
        source_case_id=case_id,
        case_group_id=case_id,
        document_id=f"e3c:en:{case_id}",
        language="en",
        translation_status=TranslationStatus.NATIVE,
        text=text,
    )


def _annotation_set(
    document: Document, concepts: tuple[tuple[str, str | None, str], ...]
) -> SourceAnnotationSet:
    annotations = []
    for annotation_id, concept, source_type in concepts:
        snippet = document.text
        annotations.append(
            SourceAnnotation(
                source_annotation_id=annotation_id,
                source_type=source_type,
                source_concept_id=concept,
                evidence_spans=(
                    EvidenceSpan(
                        start_char=0,
                        end_char=len(snippet),
                        text_snippet=snippet,
                    ),
                ),
            )
        )
    return SourceAnnotationSet(
        annotation_set_id=f"{document.source_case_id}:source",
        document_sha256=document.document_sha256,
        source_schema_id="e3c",
        annotations=tuple(annotations),
    )


def _index() -> object:
    body = synthetic_hpo_obo()
    return load_hpo_index(
        body,
        release="v2026-06-23",
        ontology_sha256=sha256(body).hexdigest(),
    )


def test_maps_all_closed_classifications_and_ignores_other_types() -> None:
    document = _document("EN1", "fever")
    annotations = _annotation_set(
        document,
        (
            ("a1", "C0000002", "CLINENTITY"),
            ("a2", "C0000001", "CLINENTITY"),
            ("a3", "C0000009", "CLINENTITY"),
            ("a4", "C0000003", "CLINENTITY"),
            ("a5", "bad", "CLINENTITY"),
            ("a6", "C0000002", "EVENT"),
        ),
    )

    manifest = map_e3c_umls_to_hpo(
        documents=(document,),
        annotation_sets=(annotations,),
        hpo_index=_index(),
        documents_sha256="a" * 64,
        source_annotations_sha256="b" * 64,
    )

    assert [record.classification for record in manifest.records] == [
        MappingClassification.UNIQUE_ACTIVE,
        MappingClassification.AMBIGUOUS,
        MappingClassification.MISSING,
        MappingClassification.OBSOLETE,
        MappingClassification.INVALID,
    ]
    assert manifest.records[0].decision is MappingDecision.CANDIDATE
    assert all(
        record.decision is MappingDecision.NEEDS_REVIEW
        for record in manifest.records[1:]
    )
    assert len(manifest.records) == 5


def test_mapping_manifest_hashes_span_text_without_serializing_it() -> None:
    document = _document("EN1", "secret clinical phrase")
    annotations = _annotation_set(
        document, (("a1", "C0000002", "CLINENTITY"),)
    )

    manifest = map_e3c_umls_to_hpo(
        documents=(document,),
        annotation_sets=(annotations,),
        hpo_index=_index(),
        documents_sha256="a" * 64,
        source_annotations_sha256="b" * 64,
    )

    payload = manifest.canonical_bytes()
    assert b"secret clinical phrase" not in payload
    assert manifest.records[0].evidence[0].text_sha256 == sha256(
        b"secret clinical phrase"
    ).hexdigest()


def test_selected_manifest_is_exact_case_subset() -> None:
    first = _document("EN1", "fever")
    second = _document("EN2", "pain")
    complete = map_e3c_umls_to_hpo(
        documents=(first, second),
        annotation_sets=(
            _annotation_set(first, (("a1", "C0000002", "CLINENTITY"),)),
            _annotation_set(second, (("a2", "C0000009", "CLINENTITY"),)),
        ),
        hpo_index=_index(),
        documents_sha256="a" * 64,
        source_annotations_sha256="b" * 64,
    )

    selected = select_mapping_manifest(
        complete,
        selected_case_ids=("EN2",),
        selection_id="e3c-de-feasibility-30-v1",
        selection_sha256="b" * 64,
    )

    assert [record.source_case_id for record in selected.records] == ["EN2"]
    with pytest.raises(ValueError, match="selected case"):
        select_mapping_manifest(
            complete,
            selected_case_ids=("MISSING",),
            selection_id="e3c-de-feasibility-30-v1",
            selection_sha256="b" * 64,
        )


def test_documents_without_clinentity_remain_in_population() -> None:
    document = _document("EN1", "no mapped entity")
    complete = map_e3c_umls_to_hpo(
        documents=(document,),
        annotation_sets=(
            _annotation_set(document, (("event", None, "EVENT"),)),
        ),
        hpo_index=_index(),
        documents_sha256="a" * 64,
        source_annotations_sha256="b" * 64,
    )

    selected = select_mapping_manifest(
        complete,
        selected_case_ids=("EN1",),
        selection_id="e3c-de-feasibility-30-v1",
        selection_sha256="b" * 64,
    )

    assert complete.summary.document_count == 1
    assert complete.records == ()
    assert selected.population_case_ids == ("EN1",)


def test_mapping_summary_retains_ontology_xref_warnings() -> None:
    body = (
        synthetic_hpo_obo()
        + b"\n[Term]\nid: HP:0000008\nname: Bad xref\n"
        + b"xref: UMLS:0189573\n"
    )
    index = load_hpo_index(
        body,
        release="v2026-06-23",
        ontology_sha256=sha256(body).hexdigest(),
    )
    document = _document("EN1", "fever")

    manifest = map_e3c_umls_to_hpo(
        documents=(document,),
        annotation_sets=(
            _annotation_set(document, (("a1", "C0000002", "CLINENTITY"),)),
        ),
        hpo_index=index,
        documents_sha256="a" * 64,
        source_annotations_sha256="b" * 64,
    )

    assert manifest.summary.ontology_warnings == (
        "HP:0000008:malformed_umls_xref:0189573",
    )

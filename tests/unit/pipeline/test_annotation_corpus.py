import json
from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation_corpus import AnnotationCorpusManifest
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.translation_review import (
    ClinicalChange,
    ClinicalChangeCategory,
    TranslationReviewDecision,
    TranslationReviewImportEntry,
    TranslationReviewImportManifest,
    TranslationReviewRecord,
)
from phentrieve_benchmark.pipeline.annotation_corpus import build_annotation_corpus
from phentrieve_benchmark.provenance.canonical import canonical_jsonl_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationGroupRecord,
)
from phentrieve_benchmark.selection.metrics import LengthStratum, Rational

_TEXTS = {
    "EN1": ("en", "Fever and cough."),
    "EN2": ("en", "No vomiting."),
    "FR1": ("fr", "Fièvre."),
}


def _native(case_id: str) -> Document:
    language, text = _TEXTS[case_id]
    return Document.from_text(
        source_case_id=case_id,
        case_group_id=f"e3c:v2.0.0:{case_id}",
        document_id=f"e3c:v2.0.0:{language}:{case_id}:native",
        language=language,
        translation_status=TranslationStatus.NATIVE,
        text=text,
    )


def _groups(german: set[str]) -> AnnotationGroupManifest:
    records = tuple(
        AnnotationGroupRecord(
            source_case_id=case_id,
            source_language=language,  # type: ignore[arg-type]
            annotation_language="de" if case_id in german else language,  # type: ignore[arg-type]
            document_sha256=_native(case_id).document_sha256,
            length_stratum=LengthStratum.SHORT,
            total_annotation_density=Rational.from_fraction(Fraction(1)),
        )
        for case_id, (language, _) in sorted(_TEXTS.items())
    )
    return AnnotationGroupManifest(
        inventory_sha256="a" * 64, records=records, aggregate_sha256="b" * 64
    )


def _store_native(store: ArtifactStore) -> str:
    return store.put_bytes(
        canonical_jsonl_bytes(
            [_native(case_id).model_dump(mode="json") for case_id in _TEXTS],
            identity_key="document_id",
        )
    )


def _review(
    store: ArtifactStore,
    case_id: str,
    *,
    decision: TranslationReviewDecision,
    proposed: str,
    source_text_sha256: str | None = None,
) -> str:
    native = _native(case_id)
    tllm_sha = store.put_bytes(b"Fieber und Husten (TLLM).")
    proposed_sha = store.put_bytes(proposed.encode())
    changed = decision is not TranslationReviewDecision.ACCEPTED_UNCHANGED
    clinical = decision in {
        TranslationReviewDecision.QUESTION,
        TranslationReviewDecision.REJECTED,
    }
    record = TranslationReviewRecord(
        export_sha256="c" * 64,
        source_case_id=case_id,
        source_language=native.language,  # type: ignore[arg-type]
        target_language="de",
        source_text_sha256=source_text_sha256 or native.document_sha256,
        tllm_text_sha256=tllm_sha if changed else proposed_sha,
        proposed_text_sha256=proposed_sha,
        reviewer_id="reviewer-1",
        reviewer_qualification="physician",
        reviewed_languages="en,de",
        review_date=date(2026, 10, 6),
        review_policy_id="e3c:translation-review/v1",
        decision=decision,
        clinical_change=ClinicalChange.PRESENT if clinical else ClinicalChange.NONE,
        clinical_change_category=(
            ClinicalChangeCategory.TERMINOLOGY if clinical else None
        ),
        clinical_change_rationale="Begriff falsch." if clinical else None,
    )
    record_sha = store.put_bytes(record.canonical_bytes())
    manifest = TranslationReviewImportManifest(
        export_sha256="c" * 64,
        entries=(
            TranslationReviewImportEntry(
                source_case_id=case_id,
                record_sha256=record_sha,
                review_record_sha256="d" * 64,
                proposed_text_sha256=proposed_sha,
                diff_sha256="e" * 64,
            ),
        ),
    )
    return store.put_bytes(manifest.canonical_bytes())


def _load(store: ArtifactStore, digest: str) -> AnnotationCorpusManifest:
    return AnnotationCorpusManifest.model_validate_json(
        store.read_bytes(digest), strict=True
    )


def _documents(
    store: ArtifactStore, manifest: AnnotationCorpusManifest
) -> dict[str, Document]:
    return {
        document.source_case_id: document
        for document in (
            Document.model_validate_json(line, strict=True)
            for line in store.read_bytes(manifest.documents_sha256).splitlines()
            if line
        )
    }


def test_original_groups_use_native_documents(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    digest = build_annotation_corpus(
        store=store,
        groups=_groups(german=set()),
        native_documents_sha256=_store_native(store),
        review_import_sha256s=(),
    )
    manifest = _load(store, digest)
    documents = _documents(store, manifest)
    assert set(documents) == {"EN1", "EN2", "FR1"}
    assert documents["FR1"] == _native("FR1")
    assert manifest.pending_review == ()


def test_german_report_without_accepted_review_is_pending(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    rejected = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.REJECTED,
        proposed="Fieber und Husten (TLLM).",
    )
    digest = build_annotation_corpus(
        store=store,
        groups=_groups(german={"EN1"}),
        native_documents_sha256=_store_native(store),
        review_import_sha256s=(rejected,),
    )
    manifest = _load(store, digest)
    assert manifest.pending_review == ("EN1",)
    assert "EN1" not in _documents(store, manifest)


def test_german_report_uses_the_accepted_reviewed_text(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    accepted = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.ACCEPTED_CORRECTED,
        proposed="Fieber und Husten.",
    )
    digest = build_annotation_corpus(
        store=store,
        groups=_groups(german={"EN1"}),
        native_documents_sha256=_store_native(store),
        review_import_sha256s=(accepted,),
    )
    manifest = _load(store, digest)
    document = _documents(store, manifest)["EN1"]
    assert document.text == "Fieber und Husten."
    assert document.language == "de"
    assert document.translation_status is TranslationStatus.TRANSLATED
    assert document.document_id == "e3c:v2.0.0:de:EN1:translated"
    assert document.case_group_id == "e3c:v2.0.0:EN1"
    entry = next(e for e in manifest.entries if e.source_case_id == "EN1")
    assert entry.review_import_sha256 == accepted
    assert entry.document_sha256 == sha256_bytes(b"Fieber und Husten.")


def test_later_review_import_replaces_earlier_acceptance(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    first = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.ACCEPTED_CORRECTED,
        proposed="Fieber und Husten.",
    )
    second = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.ACCEPTED_CORRECTED,
        proposed="Fieber, Husten.",
    )
    digest = build_annotation_corpus(
        store=store,
        groups=_groups(german={"EN1"}),
        native_documents_sha256=_store_native(store),
        review_import_sha256s=(first, second),
    )
    manifest = _load(store, digest)
    assert _documents(store, manifest)["EN1"].text == "Fieber, Husten."
    entry = next(e for e in manifest.entries if e.source_case_id == "EN1")
    assert entry.review_import_sha256 == second


def test_later_rejection_makes_case_pending(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    accepted = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.ACCEPTED_CORRECTED,
        proposed="Fieber und Husten.",
    )
    rejected = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.REJECTED,
        proposed="Fieber und Husten (TLLM).",
    )
    digest = build_annotation_corpus(
        store=store,
        groups=_groups(german={"EN1"}),
        native_documents_sha256=_store_native(store),
        review_import_sha256s=(accepted, rejected),
    )
    manifest = _load(store, digest)
    assert manifest.pending_review == ("EN1",)
    assert "EN1" not in _documents(store, manifest)


def test_question_decision_is_pending(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    question = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.QUESTION,
        proposed="Fieber und Husten (TLLM).",
    )
    digest = build_annotation_corpus(
        store=store,
        groups=_groups(german={"EN1"}),
        native_documents_sha256=_store_native(store),
        review_import_sha256s=(question,),
    )
    manifest = _load(store, digest)
    assert manifest.pending_review == ("EN1",)
    assert "EN1" not in _documents(store, manifest)


def test_review_of_different_source_text_is_rejected(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    accepted = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.ACCEPTED_CORRECTED,
        proposed="Fieber und Husten.",
        source_text_sha256="9" * 64,
    )
    with pytest.raises(ValueError, match="does not match the native source text"):
        build_annotation_corpus(
            store=store,
            groups=_groups(german={"EN1"}),
            native_documents_sha256=_store_native(store),
            review_import_sha256s=(accepted,),
        )


def test_duplicate_native_case_is_rejected(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    duplicate = _native("EN1").model_copy(
        update={"document_id": "e3c:v2.0.0:fr:EN1:native"}
    )
    native = store.put_bytes(
        canonical_jsonl_bytes(
            [
                _native("EN1").model_dump(mode="json"),
                duplicate.model_dump(mode="json"),
            ],
            identity_key="document_id",
        )
    )
    with pytest.raises(ValueError, match="more than one native document"):
        build_annotation_corpus(
            store=store,
            groups=_groups(german=set()),
            native_documents_sha256=native,
            review_import_sha256s=(),
        )


def test_group_manifest_must_match_native_documents(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    groups = _groups(german=set())
    payload = groups.model_dump(mode="json")
    payload["records"][0]["document_sha256"] = "f" * 64
    tampered = AnnotationGroupManifest.model_validate_json(
        json.dumps(payload), strict=True
    )
    with pytest.raises(ValueError, match="does not match the group manifest"):
        build_annotation_corpus(
            store=store,
            groups=tampered,
            native_documents_sha256=_store_native(store),
            review_import_sha256s=(),
        )


def test_corpus_is_deterministic(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    native = _store_native(store)
    first = build_annotation_corpus(
        store=store,
        groups=_groups(german=set()),
        native_documents_sha256=native,
        review_import_sha256s=(),
    )
    second = build_annotation_corpus(
        store=store,
        groups=_groups(german=set()),
        native_documents_sha256=native,
        review_import_sha256s=(),
    )
    assert first == second

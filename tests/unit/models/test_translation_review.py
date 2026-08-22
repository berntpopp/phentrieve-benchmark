from datetime import date
from itertools import product

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.review import (
    ManualReviewRequirement,
    ManualReviewStatus,
    ReviewKind,
)
from phentrieve_benchmark.models.translation_review import (
    ClinicalChange,
    ClinicalChangeCategory,
    TranslationReviewDecision,
    TranslationReviewDiff,
    TranslationReviewExport,
    TranslationReviewExportCase,
    TranslationReviewImportEntry,
    TranslationReviewImportManifest,
    TranslationReviewRecord,
)
from phentrieve_benchmark.provenance.digests import sha256_bytes


def _record(
    *,
    decision: TranslationReviewDecision,
    proposed_text_sha256: str,
    clinical_change: ClinicalChange,
    clinical_change_category: ClinicalChangeCategory | None = None,
    clinical_change_rationale: str | None = None,
) -> TranslationReviewRecord:
    return TranslationReviewRecord(
        export_sha256="0" * 64,
        source_case_id="EN1",
        source_language="en",
        target_language="de",
        source_text_sha256="1" * 64,
        tllm_text_sha256="3" * 64,
        proposed_text_sha256=proposed_text_sha256,
        reviewer_id="reviewer-1",
        reviewer_qualification="medical translator",
        reviewed_languages="en,de",
        review_date=date(2026, 8, 22),
        review_policy_id="e3c:translation-review/v1",
        decision=decision,
        clinical_change=clinical_change,
        clinical_change_category=clinical_change_category,
        clinical_change_rationale=clinical_change_rationale,
        reviewer_comment=None,
    )


def test_translation_review_record_has_deterministic_gate_projection() -> None:
    record = _record(
        decision=TranslationReviewDecision.ACCEPTED_UNCHANGED,
        proposed_text_sha256="3" * 64,
        clinical_change=ClinicalChange.NONE,
    )

    assert record.sha256() == sha256_bytes(record.canonical_bytes())
    gate = record.review_record()
    assert gate.review_id == f"translation-review:{record.sha256()}"
    assert gate.review_kind is ReviewKind.BILINGUAL
    assert gate.subject_sha256 == "3" * 64
    assert gate.manual_requirement is ManualReviewRequirement.REQUIRED
    assert gate.manual_status is ManualReviewStatus.ACCEPTED


def test_translation_review_diff_canonicalizes_its_text_payload() -> None:
    diff = TranslationReviewDiff(
        tllm_text_sha256="2" * 64,
        proposed_text_sha256="3" * 64,
        payload="Cafe\u0301\r\n",
    )

    assert diff.payload == "Café\n"
    assert diff.sha256() == sha256_bytes(diff.canonical_bytes())


@pytest.mark.parametrize(
    (
        "decision",
        "proposed_text_sha256",
        "clinical_change",
        "category",
        "rationale",
        "manual_status",
    ),
    [
        (
            TranslationReviewDecision.ACCEPTED_UNCHANGED,
            "3" * 64,
            ClinicalChange.NONE,
            None,
            None,
            ManualReviewStatus.ACCEPTED,
        ),
        (
            TranslationReviewDecision.ACCEPTED_CORRECTED,
            "4" * 64,
            ClinicalChange.NONE,
            None,
            None,
            ManualReviewStatus.ACCEPTED,
        ),
        (
            TranslationReviewDecision.ACCEPTED_CORRECTED,
            "4" * 64,
            ClinicalChange.PRESENT,
            ClinicalChangeCategory.TERMINOLOGY,
            "The clinical meaning changed.",
            ManualReviewStatus.ACCEPTED,
        ),
        (
            TranslationReviewDecision.QUESTION,
            "3" * 64,
            ClinicalChange.PRESENT,
            ClinicalChangeCategory.SOURCE,
            "The source is ambiguous.",
            ManualReviewStatus.CHANGES_REQUESTED,
        ),
        (
            TranslationReviewDecision.REJECTED,
            "4" * 64,
            ClinicalChange.PRESENT,
            ClinicalChangeCategory.OMISSION,
            "A clinically relevant omission remains.",
            ManualReviewStatus.REJECTED,
        ),
    ],
)
def test_translation_review_record_allows_exactly_the_decision_table_rows(
    decision: TranslationReviewDecision,
    proposed_text_sha256: str,
    clinical_change: ClinicalChange,
    category: ClinicalChangeCategory | None,
    rationale: str | None,
    manual_status: ManualReviewStatus,
) -> None:
    record = _record(
        decision=decision,
        proposed_text_sha256=proposed_text_sha256,
        clinical_change=clinical_change,
        clinical_change_category=category,
        clinical_change_rationale=rationale,
    )

    assert record.review_record().manual_status is manual_status


@pytest.mark.parametrize(
    (
        "decision",
        "proposed_text_sha256",
        "clinical_change",
        "category",
        "rationale",
    ),
    [
        (
            TranslationReviewDecision.ACCEPTED_UNCHANGED,
            "4" * 64,
            ClinicalChange.NONE,
            None,
            None,
        ),
        (
            TranslationReviewDecision.ACCEPTED_UNCHANGED,
            "3" * 64,
            ClinicalChange.PRESENT,
            ClinicalChangeCategory.VALUE,
            "A change exists.",
        ),
        (
            TranslationReviewDecision.ACCEPTED_CORRECTED,
            "3" * 64,
            ClinicalChange.NONE,
            None,
            None,
        ),
        (
            TranslationReviewDecision.ACCEPTED_CORRECTED,
            "4" * 64,
            ClinicalChange.PRESENT,
            None,
            None,
        ),
        (
            TranslationReviewDecision.QUESTION,
            "3" * 64,
            ClinicalChange.NONE,
            None,
            None,
        ),
        (
            TranslationReviewDecision.REJECTED,
            "4" * 64,
            ClinicalChange.PRESENT,
            ClinicalChangeCategory.ADDITION,
            None,
        ),
    ],
)
def test_translation_review_record_rejects_other_decision_table_combinations(
    decision: TranslationReviewDecision,
    proposed_text_sha256: str,
    clinical_change: ClinicalChange,
    category: ClinicalChangeCategory | None,
    rationale: str | None,
) -> None:
    with pytest.raises(ValidationError, match="decision"):
        _record(
            decision=decision,
            proposed_text_sha256=proposed_text_sha256,
            clinical_change=clinical_change,
            clinical_change_category=category,
            clinical_change_rationale=rationale,
        )


@pytest.mark.parametrize(
    (
        "decision",
        "proposed_text_sha256",
        "clinical_change",
        "category",
        "rationale",
    ),
    tuple(
        product(
            TranslationReviewDecision,
            ("3" * 64, "4" * 64),
            ClinicalChange,
            (None, ClinicalChangeCategory.VALUE),
            (None, "A clinical rationale."),
        )
    ),
)
def test_translation_review_record_rejects_every_other_decision_combination(
    decision: TranslationReviewDecision,
    proposed_text_sha256: str,
    clinical_change: ClinicalChange,
    category: ClinicalChangeCategory | None,
    rationale: str | None,
) -> None:
    same_as_tllm = proposed_text_sha256 == "3" * 64
    has_details = category is not None and rationale is not None
    has_no_details = category is None and rationale is None
    allowed = (
        (
            decision is TranslationReviewDecision.ACCEPTED_UNCHANGED
            and same_as_tllm
            and clinical_change is ClinicalChange.NONE
            and has_no_details
        )
        or (
            decision is TranslationReviewDecision.ACCEPTED_CORRECTED
            and not same_as_tllm
            and (
                (clinical_change is ClinicalChange.NONE and has_no_details)
                or (clinical_change is ClinicalChange.PRESENT and has_details)
            )
        )
        or (
            decision
            in {
                TranslationReviewDecision.QUESTION,
                TranslationReviewDecision.REJECTED,
            }
            and clinical_change is ClinicalChange.PRESENT
            and has_details
        )
    )

    if allowed:
        _record(
            decision=decision,
            proposed_text_sha256=proposed_text_sha256,
            clinical_change=clinical_change,
            clinical_change_category=category,
            clinical_change_rationale=rationale,
        )
    else:
        with pytest.raises(ValidationError, match="decision"):
            _record(
                decision=decision,
                proposed_text_sha256=proposed_text_sha256,
                clinical_change=clinical_change,
                clinical_change_category=category,
                clinical_change_rationale=rationale,
            )


def test_export_and_import_manifests_canonicalize_order_and_reject_duplicates() -> None:
    fr_case = TranslationReviewExportCase(
        source_case_id="FR1",
        source_language="fr",
        source_text_sha256="4" * 64,
        tllm_text_sha256="5" * 64,
    )
    en_case = TranslationReviewExportCase(
        source_case_id="EN1",
        source_language="en",
        source_text_sha256="6" * 64,
        tllm_text_sha256="7" * 64,
    )
    export = TranslationReviewExport(
        selection_id="e3c-de-feasibility-30-v1",
        review_policy_id="e3c:translation-review/v1",
        cases=(fr_case, en_case),
    )
    first = TranslationReviewImportEntry(
        source_case_id="EN1",
        record_sha256="8" * 64,
        review_record_sha256="9" * 64,
        proposed_text_sha256="a" * 64,
        diff_sha256="b" * 64,
    )
    second = TranslationReviewImportEntry(
        source_case_id="FR1",
        record_sha256="c" * 64,
        review_record_sha256="d" * 64,
        proposed_text_sha256="e" * 64,
        diff_sha256="f" * 64,
    )
    manifest = TranslationReviewImportManifest(
        export_sha256=export.sha256(), entries=(second, first)
    )

    assert [case.source_case_id for case in export.cases] == ["EN1", "FR1"]
    assert [entry.source_case_id for entry in manifest.entries] == ["EN1", "FR1"]
    with pytest.raises(ValidationError, match="duplicate"):
        TranslationReviewExport(
            selection_id=export.selection_id,
            review_policy_id=export.review_policy_id,
            cases=(en_case, en_case),
        )
    with pytest.raises(ValidationError, match="duplicate"):
        TranslationReviewImportManifest(
            export_sha256=export.sha256(), entries=(first, first)
        )

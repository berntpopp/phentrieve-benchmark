import pytest

from phentrieve_benchmark.models.annotation import (
    Annotation,
    AnnotationSet,
    EvidenceSpan,
    validate_annotation_set,
)
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.review import (
    ManualReviewRequirement,
    ManualReviewStatus,
    ReviewKind,
    ReviewRecord,
)


def test_annotation_set_validates_unicode_half_open_span() -> None:
    document = Document.from_text(
        source_case_id="case-1",
        case_group_id="group-1",
        document_id="document-1",
        language="de",
        translation_status=TranslationStatus.TRANSLATED,
        text="Der Patient hat große Hände.",
    )
    start = document.text.index("große")
    end = start + len("große")
    annotation_set = AnnotationSet(
        annotation_set_id="annotations-1",
        document_sha256=document.document_sha256,
        hpo_release="v2025-01-01",
        annotations=(
            Annotation(
                annotation_id="annotation-1",
                hpo_id="HP:0001176",
                evidence_spans=(
                    EvidenceSpan(
                        start_char=start,
                        end_char=end,
                        snippet="große",
                    ),
                ),
            ),
        ),
    )

    validate_annotation_set(document, annotation_set)


def test_annotation_set_rejects_mismatched_span_text() -> None:
    document = Document.from_text(
        source_case_id="case-1",
        case_group_id="group-1",
        document_id="document-1",
        language="de",
        translation_status=TranslationStatus.NATIVE,
        text="Keine Ataxie.",
    )
    annotation_set = AnnotationSet(
        annotation_set_id="annotations-1",
        document_sha256=document.document_sha256,
        hpo_release="v2025-01-01",
        annotations=(
            Annotation(
                annotation_id="annotation-1",
                hpo_id="HP:0001251",
                evidence_spans=(
                    EvidenceSpan(start_char=6, end_char=12, snippet="Ataxia"),
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"span text mismatch.*annotation-1"):
        validate_annotation_set(document, annotation_set)


def test_not_selected_not_applicable_review_is_not_manual_acceptance() -> None:
    record = ReviewRecord(
        review_id="review-1",
        kind=ReviewKind.BILINGUAL,
        subject_sha256="a" * 64,
        review_policy_id="policy-1",
        requirement=ManualReviewRequirement.NOT_SELECTED,
        status=ManualReviewStatus.NOT_APPLICABLE,
        reviewer_role="reviewer",
    )

    assert record.is_manual_acceptance is False


def test_not_selected_review_cannot_be_accepted() -> None:
    with pytest.raises(ValueError, match="not_selected requires not_applicable"):
        ReviewRecord(
            review_id="review-1",
            kind=ReviewKind.BILINGUAL,
            subject_sha256="a" * 64,
            review_policy_id="policy-1",
            requirement=ManualReviewRequirement.NOT_SELECTED,
            status=ManualReviewStatus.ACCEPTED,
            reviewer_role="reviewer",
        )

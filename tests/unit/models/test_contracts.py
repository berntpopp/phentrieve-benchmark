import json

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
                        text_snippet="große",
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
                    EvidenceSpan(
                        start_char=6, end_char=12, text_snippet="Ataxia"
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"span text mismatch.*annotation-1"):
        validate_annotation_set(document, annotation_set)


def test_annotation_set_rejects_span_ending_past_document_eof() -> None:
    document = Document.from_text(
        source_case_id="case-1",
        case_group_id="group-1",
        document_id="document-1",
        language="de",
        translation_status=TranslationStatus.NATIVE,
        text="Ärger",
    )
    annotation_set = AnnotationSet(
        annotation_set_id="annotations-1",
        document_sha256=document.document_sha256,
        hpo_release="v2025-01-01",
        annotations=(
            Annotation(
                annotation_id="annotation-past-eof",
                hpo_id="HP:0001251",
                evidence_spans=(
                    EvidenceSpan(start_char=0, end_char=6, text_snippet="Ärger"),
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"past document end.*annotation-past-eof"):
        validate_annotation_set(document, annotation_set)


def test_annotation_set_accepts_unicode_span_ending_at_document_eof() -> None:
    document = Document.from_text(
        source_case_id="case-1",
        case_group_id="group-1",
        document_id="document-1",
        language="de",
        translation_status=TranslationStatus.NATIVE,
        text="Ärger",
    )
    annotation_set = AnnotationSet(
        annotation_set_id="annotations-1",
        document_sha256=document.document_sha256,
        hpo_release="v2025-01-01",
        annotations=(
            Annotation(
                annotation_id="annotation-eof",
                hpo_id="HP:0001251",
                evidence_spans=(
                    EvidenceSpan(start_char=2, end_char=5, text_snippet="ger"),
                ),
            ),
        ),
    )

    validate_annotation_set(document, annotation_set)


def test_document_rejects_direct_construction_with_wrong_hash() -> None:
    with pytest.raises(ValueError, match="document_sha256 mismatch"):
        Document(
            source_case_id="case-1",
            case_group_id="group-1",
            document_id="document-1",
            language="de",
            translation_status=TranslationStatus.NATIVE,
            text="Keine Ataxie.",
            document_sha256="a" * 64,
        )


def test_document_rejects_json_with_wrong_hash() -> None:
    document = Document.from_text(
        source_case_id="case-1",
        case_group_id="group-1",
        document_id="document-1",
        language="de",
        translation_status=TranslationStatus.NATIVE,
        text="Keine Ataxie.",
    )
    payload = document.model_dump(mode="json")
    payload["document_sha256"] = "a" * 64

    with pytest.raises(ValueError, match="document_sha256 mismatch"):
        Document.model_validate_json(json.dumps(payload))


def test_document_rejects_noncanonical_direct_text() -> None:
    with pytest.raises(ValueError, match="text must be canonical"):
        Document(
            source_case_id="case-1",
            case_group_id="group-1",
            document_id="document-1",
            language="de",
            translation_status=TranslationStatus.NATIVE,
            text="Gro\u0308ße\r\n",
            document_sha256="a" * 64,
        )


def test_annotation_rejects_non_ascii_hpo_digits() -> None:
    with pytest.raises(ValueError, match="hpo_id"):
        Annotation(annotation_id="annotation-1", hpo_id="HP:٠٠٠١١٧٦")


def test_not_selected_not_applicable_review_is_not_manual_acceptance() -> None:
    record = ReviewRecord(
        review_id="review-1",
        review_kind=ReviewKind.BILINGUAL,
        subject_sha256="a" * 64,
        review_policy_id="policy-1",
        manual_requirement=ManualReviewRequirement.NOT_SELECTED,
        manual_status=ManualReviewStatus.NOT_APPLICABLE,
        reviewer_role="reviewer",
    )

    assert record.is_manual_acceptance is False


def test_not_selected_review_cannot_be_accepted() -> None:
    with pytest.raises(ValueError, match="not_selected requires not_applicable"):
        ReviewRecord(
            review_id="review-1",
            review_kind=ReviewKind.BILINGUAL,
            subject_sha256="a" * 64,
            review_policy_id="policy-1",
            manual_requirement=ManualReviewRequirement.NOT_SELECTED,
            manual_status=ManualReviewStatus.ACCEPTED,
            reviewer_role="reviewer",
        )


def test_public_model_schema_uses_only_contract_field_names() -> None:
    span = EvidenceSpan(start_char=0, end_char=6, text_snippet="Ataxia")
    review = ReviewRecord(
        review_id="review-1",
        review_kind=ReviewKind.BILINGUAL,
        subject_sha256="a" * 64,
        review_policy_id="policy-1",
        manual_requirement=ManualReviewRequirement.REQUIRED,
        manual_status=ManualReviewStatus.ACCEPTED,
        reviewer_role="reviewer",
    )

    assert span.model_dump(mode="json") == {
        "start_char": 0,
        "end_char": 6,
        "text_snippet": "Ataxia",
    }
    assert set(ReviewRecord.model_json_schema()["properties"]) == {
        "review_id",
        "review_kind",
        "subject_sha256",
        "review_policy_id",
        "manual_requirement",
        "manual_status",
        "reviewer_role",
    }
    assert review.model_dump(mode="json")["review_kind"] == "bilingual"
    assert EvidenceSpan.model_validate_json(
        '{"start_char":0,"end_char":6,"text_snippet":"Ataxia"}'
    ) == span
    assert ReviewRecord.model_validate_json(
        json.dumps(review.model_dump(mode="json"))
    ) == review


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            EvidenceSpan,
            {"start_char": 0, "end_char": 6, "snippet": "Ataxia"},
        ),
        (
            ReviewRecord,
            {
                "review_id": "review-1",
                "kind": "bilingual",
                "subject_sha256": "a" * 64,
                "review_policy_id": "policy-1",
                "requirement": "required",
                "status": "accepted",
                "reviewer_role": "reviewer",
            },
        ),
    ],
)
def test_legacy_public_model_field_names_are_rejected(
    model: type[EvidenceSpan] | type[ReviewRecord], payload: dict[str, object]
) -> None:
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        model.model_validate_json(json.dumps(payload))

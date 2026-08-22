from datetime import date
from enum import StrEnum
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from phentrieve_benchmark.models.review import (
    ManualReviewRequirement,
    ManualReviewStatus,
    ReviewKind,
    ReviewRecord,
)
from phentrieve_benchmark.provenance.canonical import (
    canonical_json_bytes,
    canonical_text_bytes,
)
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class TranslationReviewDecision(StrEnum):
    ACCEPTED_UNCHANGED = "unverändert akzeptiert"
    ACCEPTED_CORRECTED = "korrigiert akzeptiert"
    QUESTION = "Rückfrage"
    REJECTED = "abgelehnt"


class ClinicalChange(StrEnum):
    NONE = "keine"
    PRESENT = "vorhanden"


class ClinicalChangeCategory(StrEnum):
    OMISSION = "Auslassung"
    ADDITION = "Hinzufügung"
    ASSERTION = "Negation oder Aussagesicherheit"
    VALUE = "Zahl oder Einheit"
    ANATOMY = "Anatomie oder Lateralität"
    TERMINOLOGY = "Terminologie"
    SOURCE = "Quellproblem"


class _CanonicalModel(BaseModel):
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())


class TranslationReviewExportCase(_CanonicalModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_case_id: str = Field(min_length=1)
    source_language: Literal["en", "es", "fr"]
    source_text_sha256: Sha256Hex
    tllm_text_sha256: Sha256Hex
    nmt_text_sha256: Sha256Hex | None = None


class TranslationReviewExport(_CanonicalModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["translation-review-export/v1"] = (
        "translation-review-export/v1"
    )
    selection_id: str = Field(min_length=1)
    review_policy_id: str = Field(min_length=1)
    nmt_recipe_sha256: Sha256Hex | None = None
    cases: tuple[TranslationReviewExportCase, ...] = Field(min_length=1)

    @field_validator("cases")
    @classmethod
    def canonicalize_cases(
        cls, cases: tuple[TranslationReviewExportCase, ...]
    ) -> tuple[TranslationReviewExportCase, ...]:
        return tuple(
            sorted(
                cases,
                key=lambda case: (case.source_language, case.source_case_id),
            )
        )

    @model_validator(mode="after")
    def cases_are_complete(self) -> Self:
        case_ids = [case.source_case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("duplicate source case in translation review export")
        includes_nmt = [case.nmt_text_sha256 is not None for case in self.cases]
        if any(includes_nmt) != all(includes_nmt):
            raise ValueError("NMT text must be present for every export case")
        if all(includes_nmt) != (self.nmt_recipe_sha256 is not None):
            raise ValueError("NMT recipe and text references must agree")
        return self


class TranslationReviewRecord(_CanonicalModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["translation-review-record/v1"] = (
        "translation-review-record/v1"
    )
    export_sha256: Sha256Hex
    source_case_id: str = Field(min_length=1)
    source_language: Literal["en", "es", "fr"]
    target_language: Literal["de"]
    source_text_sha256: Sha256Hex
    tllm_text_sha256: Sha256Hex
    proposed_text_sha256: Sha256Hex
    reviewer_id: str = Field(min_length=1)
    reviewer_qualification: str = Field(min_length=1)
    reviewed_languages: str = Field(min_length=1)
    review_date: date
    review_policy_id: str = Field(min_length=1)
    decision: TranslationReviewDecision
    clinical_change: ClinicalChange
    clinical_change_category: ClinicalChangeCategory | None = None
    clinical_change_rationale: str | None = Field(default=None, min_length=1)
    reviewer_comment: str | None = None

    @model_validator(mode="after")
    def follows_decision_table(self) -> Self:
        same_as_tllm = self.proposed_text_sha256 == self.tllm_text_sha256
        has_clinical_details = (
            self.clinical_change_category is not None
            and self.clinical_change_rationale is not None
        )
        has_no_clinical_details = (
            self.clinical_change_category is None
            and self.clinical_change_rationale is None
        )
        if self.decision is TranslationReviewDecision.ACCEPTED_UNCHANGED:
            if (
                not same_as_tllm
                or self.clinical_change is not ClinicalChange.NONE
                or not has_no_clinical_details
            ):
                raise ValueError("decision table rejects accepted unchanged row")
        elif self.decision is TranslationReviewDecision.ACCEPTED_CORRECTED:
            if same_as_tllm:
                raise ValueError("decision table requires corrected final text")
            if self.clinical_change is ClinicalChange.NONE:
                if not has_no_clinical_details:
                    raise ValueError(
                        "decision table forbids clinical details without a change"
                    )
            elif not has_clinical_details:
                raise ValueError("decision table requires clinical details")
        elif self.decision in {
            TranslationReviewDecision.QUESTION,
            TranslationReviewDecision.REJECTED,
        } and (
            self.clinical_change is not ClinicalChange.PRESENT
            or not has_clinical_details
        ):
            raise ValueError("decision table requires a clinical change")
        return self

    def review_record(self) -> ReviewRecord:
        manual_status = {
            TranslationReviewDecision.ACCEPTED_UNCHANGED: (ManualReviewStatus.ACCEPTED),
            TranslationReviewDecision.ACCEPTED_CORRECTED: (ManualReviewStatus.ACCEPTED),
            TranslationReviewDecision.QUESTION: (ManualReviewStatus.CHANGES_REQUESTED),
            TranslationReviewDecision.REJECTED: ManualReviewStatus.REJECTED,
        }[self.decision]
        return ReviewRecord(
            review_id=f"translation-review:{self.sha256()}",
            review_kind=ReviewKind.BILINGUAL,
            subject_sha256=self.proposed_text_sha256,
            review_policy_id=self.review_policy_id,
            manual_requirement=ManualReviewRequirement.REQUIRED,
            manual_status=manual_status,
            reviewer_role=self.reviewer_qualification,
        )


class TranslationReviewDiff(_CanonicalModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["unified-text-diff/v1"] = "unified-text-diff/v1"
    tllm_text_sha256: Sha256Hex
    proposed_text_sha256: Sha256Hex
    payload: str

    @field_validator("payload")
    @classmethod
    def canonicalize_payload(cls, value: str) -> str:
        return canonical_text_bytes(value).decode("utf-8")


class TranslationReviewImportEntry(_CanonicalModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_case_id: str = Field(min_length=1)
    record_sha256: Sha256Hex
    review_record_sha256: Sha256Hex
    proposed_text_sha256: Sha256Hex
    diff_sha256: Sha256Hex


class TranslationReviewImportManifest(_CanonicalModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["translation-review-import/v1"] = (
        "translation-review-import/v1"
    )
    export_sha256: Sha256Hex
    entries: tuple[TranslationReviewImportEntry, ...] = Field(min_length=1)

    @field_validator("entries")
    @classmethod
    def canonicalize_entries(
        cls, entries: tuple[TranslationReviewImportEntry, ...]
    ) -> tuple[TranslationReviewImportEntry, ...]:
        return tuple(sorted(entries, key=lambda entry: entry.source_case_id))

    @model_validator(mode="after")
    def entries_are_unique(self) -> Self:
        case_ids = [entry.source_case_id for entry in self.entries]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("duplicate source case in translation review import")
        return self

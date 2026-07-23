from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.provenance.digests import Sha256Hex


class ReviewKind(StrEnum):
    AUTOMATED = "automated"
    BILINGUAL = "bilingual"
    ANNOTATION = "annotation"
    ADJUDICATION = "adjudication"


class ManualReviewRequirement(StrEnum):
    REQUIRED = "required"
    NOT_SELECTED = "not_selected"


class ManualReviewStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"
    NOT_APPLICABLE = "not_applicable"


class ReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str = Field(min_length=1)
    kind: ReviewKind
    subject_sha256: Sha256Hex
    review_policy_id: str = Field(min_length=1)
    requirement: ManualReviewRequirement
    status: ManualReviewStatus
    reviewer_role: str = Field(min_length=1)

    @model_validator(mode="after")
    def has_valid_requirement_status_pair(self) -> "ReviewRecord":
        if (
            self.requirement is ManualReviewRequirement.NOT_SELECTED
            and self.status is not ManualReviewStatus.NOT_APPLICABLE
        ):
            raise ValueError("not_selected requires not_applicable")
        if (
            self.requirement is ManualReviewRequirement.REQUIRED
            and self.status is ManualReviewStatus.NOT_APPLICABLE
        ):
            raise ValueError("required cannot be not_applicable")
        return self

    @property
    def is_manual_acceptance(self) -> bool:
        return (
            self.requirement is ManualReviewRequirement.REQUIRED
            and self.status is ManualReviewStatus.ACCEPTED
        )

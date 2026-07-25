from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from phentrieve_benchmark.models.curated_annotation import (
    ActorKind,
    AnnotationReference,
    CuratedAnnotation,
    CuratedAnnotationSet,
)
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class ReviewScope(StrEnum):
    HPO_IDENTITY = "hpo_identity"
    EVIDENCE = "evidence"
    ASSERTION = "assertion"
    EXPERIENCER = "experiencer"
    TEMPORALITY = "temporality"
    COMPLETE = "complete"


class ReviewOutcome(StrEnum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class DecisionReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    decision_set_sha256: Sha256Hex
    decision_id: str = Field(pattern=r"^review-decision-[0-9a-f]{64}$")


def _canonical_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def review_decision_id(payload: dict[str, object]) -> str:
    return "review-decision-" + sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": "review-decision-id/v1",
                "decision": payload,
            }
        )
    )


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    decision_id: str = Field(pattern=r"^review-decision-[0-9a-f]{64}$")
    target: AnnotationReference
    reviewer_id: str = Field(
        pattern=r"^[a-z][a-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9._/-]*$"
    )
    actor_kind: ActorKind
    reviewer_role: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )
    stage_id: str = Field(
        pattern=r"^[a-z][a-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9._/-]*$"
    )
    scopes: tuple[ReviewScope, ...] = Field(min_length=1)
    outcome: ReviewOutcome
    decided_at: AwareDatetime
    rationale: str | None = None
    counterproposal: AnnotationReference | None = None
    supersedes: DecisionReference | None = None

    @field_validator("scopes")
    @classmethod
    def canonicalize_scopes(
        cls, scopes: tuple[ReviewScope, ...]
    ) -> tuple[ReviewScope, ...]:
        values = [scope.value for scope in scopes]
        if len(values) != len(set(values)):
            raise ValueError("duplicate review scope")
        return tuple(sorted(scopes, key=lambda scope: scope.value))

    @field_validator("decided_at")
    @classmethod
    def timestamp_is_whole_second_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != UTC.utcoffset(value) or value.microsecond != 0:
            raise ValueError("decided_at must be whole-second UTC")
        return value

    @field_serializer("decided_at")
    def serialize_decided_at(self, value: datetime) -> str:
        return _canonical_timestamp(value)

    @model_validator(mode="after")
    def decision_is_structurally_consistent(self) -> Self:
        if (
            self.outcome is ReviewOutcome.CONFIRMED
            and self.counterproposal is not None
        ):
            raise ValueError(
                "confirmed decision cannot carry counterproposal"
            )
        payload = self.model_dump(mode="json", exclude={"decision_id"})
        if self.decision_id != review_decision_id(payload):
            raise ValueError("decision_id mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        target: AnnotationReference,
        reviewer_id: str,
        actor_kind: ActorKind,
        reviewer_role: str | None,
        stage_id: str,
        scopes: tuple[ReviewScope, ...],
        outcome: ReviewOutcome,
        decided_at: datetime,
        rationale: str | None,
        counterproposal: AnnotationReference | None,
        supersedes: DecisionReference | None,
    ) -> Self:
        # Let normal model construction report invalid scopes and timestamps as
        # Pydantic validation errors. Sorting here only makes the derived ID
        # independent of input ordering.
        canonical_scopes = tuple(sorted(scopes, key=lambda scope: scope.value))
        payload: dict[str, object] = {
            "target": target.model_dump(mode="json"),
            "reviewer_id": reviewer_id,
            "actor_kind": actor_kind,
            "reviewer_role": reviewer_role,
            "stage_id": stage_id,
            "scopes": [scope.value for scope in canonical_scopes],
            "outcome": outcome,
            "decided_at": _canonical_timestamp(decided_at),
            "rationale": rationale,
            "counterproposal": (
                None
                if counterproposal is None
                else counterproposal.model_dump(mode="json")
            ),
            "supersedes": (
                None
                if supersedes is None
                else supersedes.model_dump(mode="json")
            ),
        }
        return cls(
            decision_id=review_decision_id(payload),
            target=target,
            reviewer_id=reviewer_id,
            actor_kind=actor_kind,
            reviewer_role=reviewer_role,
            stage_id=stage_id,
            scopes=canonical_scopes,
            outcome=outcome,
            decided_at=decided_at,
            rationale=rationale,
            counterproposal=counterproposal,
            supersedes=supersedes,
        )


class ReviewDecisionSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["review-decision-set/v1"] = (
        "review-decision-set/v1"
    )
    decisions: tuple[ReviewDecision, ...] = ()

    @field_validator("decisions")
    @classmethod
    def canonicalize_decisions(
        cls, decisions: tuple[ReviewDecision, ...]
    ) -> tuple[ReviewDecision, ...]:
        identities = [decision.decision_id for decision in decisions]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate review decision")
        return tuple(
            sorted(decisions, key=lambda decision: decision.decision_id)
        )

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())


def _annotation(
    reference: AnnotationReference,
    annotation_sets: Mapping[str, CuratedAnnotationSet],
) -> tuple[CuratedAnnotationSet, CuratedAnnotation]:
    annotation_set = annotation_sets.get(reference.annotation_set_sha256)
    if annotation_set is None:
        raise ValueError("review target annotation set is missing")
    if annotation_set.sha256() != reference.annotation_set_sha256:
        raise ValueError("review target annotation set SHA-256 mismatch")
    matches = [
        annotation
        for annotation in annotation_set.annotations
        if annotation.annotation_id == reference.annotation_id
    ]
    if len(matches) != 1:
        raise ValueError("review target annotation does not resolve uniquely")
    return annotation_set, matches[0]


def validate_review_decision_set(
    decision_set: ReviewDecisionSet,
    *,
    annotation_sets: Mapping[str, CuratedAnnotationSet],
    decision_sets: Mapping[str, ReviewDecisionSet],
) -> None:
    for decision in decision_set.decisions:
        target_set, _ = _annotation(decision.target, annotation_sets)
        if decision.counterproposal is not None:
            counter_set, _ = _annotation(
                decision.counterproposal, annotation_sets
            )
            if (
                counter_set.document.document_sha256
                != target_set.document.document_sha256
            ):
                raise ValueError("counterproposal belongs to another document")
        if decision.supersedes is not None:
            previous_set = decision_sets.get(
                decision.supersedes.decision_set_sha256
            )
            if previous_set is None:
                raise ValueError("superseded decision does not resolve")
            if (
                previous_set.sha256()
                != decision.supersedes.decision_set_sha256
            ):
                raise ValueError("superseded decision set SHA-256 mismatch")
            if not any(
                previous.decision_id == decision.supersedes.decision_id
                for previous in previous_set.decisions
            ):
                raise ValueError("superseded decision does not resolve")

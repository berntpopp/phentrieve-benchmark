from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.curated_annotation import (
    ActorKind,
    AnnotationReference,
)
from phentrieve_benchmark.models.review_decision import (
    DecisionReference,
    ReviewDecision,
    ReviewDecisionSet,
    ReviewOutcome,
    ReviewScope,
)


def _target(suffix: str = "a") -> AnnotationReference:
    return AnnotationReference(
        annotation_set_sha256=suffix * 64,
        annotation_id="curated-ann-" + suffix * 64,
    )


def _decision(
    *,
    outcome: ReviewOutcome = ReviewOutcome.CONFIRMED,
    counterproposal: AnnotationReference | None = None,
    scopes: tuple[ReviewScope, ...] = (
        ReviewScope.EVIDENCE,
        ReviewScope.HPO_IDENTITY,
    ),
) -> ReviewDecision:
    return ReviewDecision.create(
        target=_target(),
        reviewer_id="human:reviewer-1",
        actor_kind=ActorKind.HUMAN,
        reviewer_role="qualification:physician/v1",
        stage_id="e3c:hpo-mapping-review/v1",
        scopes=scopes,
        outcome=outcome,
        decided_at=datetime(2026, 7, 26, 10, 30, tzinfo=UTC),
        rationale="Checked against the source text.",
        counterproposal=counterproposal,
        supersedes=None,
    )


def test_review_decision_is_scoped_canonical_and_content_identified() -> None:
    first = _decision()
    second = _decision(scopes=tuple(reversed(first.scopes)))

    assert first == second
    assert first.decision_id.startswith("review-decision-")
    assert first.scopes == (
        ReviewScope.EVIDENCE,
        ReviewScope.HPO_IDENTITY,
    )
    assert first.model_dump(mode="json")["decided_at"] == (
        "2026-07-26T10:30:00Z"
    )


def test_review_decision_rejects_ambiguous_or_noncanonical_metadata() -> None:
    with pytest.raises(ValidationError, match="duplicate review scope"):
        _decision(scopes=(ReviewScope.EVIDENCE, ReviewScope.EVIDENCE))

    with pytest.raises(ValidationError, match="whole-second UTC"):
        ReviewDecision.create(
            target=_target(),
            reviewer_id="human:reviewer-1",
            actor_kind=ActorKind.HUMAN,
            reviewer_role=None,
            stage_id="e3c:hpo-mapping-review/v1",
            scopes=(ReviewScope.COMPLETE,),
            outcome=ReviewOutcome.REJECTED,
            decided_at=datetime(
                2026, 7, 26, 10, 30, 0, 1, tzinfo=UTC
            ),
            rationale=None,
            counterproposal=None,
            supersedes=None,
        )


def test_confirmed_decision_cannot_carry_counterproposal() -> None:
    with pytest.raises(
        ValidationError, match=r"confirmed.*counterproposal"
    ):
        _decision(counterproposal=_target("b"))


def test_change_request_can_reference_counterproposal_and_prior_decision() -> None:
    previous = _decision()
    changed = ReviewDecision.create(
        target=previous.target,
        reviewer_id=previous.reviewer_id,
        actor_kind=previous.actor_kind,
        reviewer_role=previous.reviewer_role,
        stage_id=previous.stage_id,
        scopes=(ReviewScope.EVIDENCE,),
        outcome=ReviewOutcome.CHANGES_REQUESTED,
        decided_at=datetime(2026, 7, 26, 11, 0, tzinfo=UTC),
        rationale="Use the complete phrase.",
        counterproposal=_target("b"),
        supersedes=DecisionReference(
            decision_set_sha256="c" * 64,
            decision_id=previous.decision_id,
        ),
    )

    assert changed.counterproposal == _target("b")
    assert changed.supersedes is not None
    assert changed.decision_id != previous.decision_id


def test_review_decision_set_is_canonical_and_hashed() -> None:
    first = _decision()
    second = ReviewDecision.create(
        target=_target("b"),
        reviewer_id="tool:reviewer/v1",
        actor_kind=ActorKind.TOOL,
        reviewer_role=None,
        stage_id="e3c:assertion-review/v1",
        scopes=(ReviewScope.ASSERTION,),
        outcome=ReviewOutcome.REJECTED,
        decided_at=datetime(2026, 7, 26, 10, 31, tzinfo=UTC),
        rationale=None,
        counterproposal=None,
        supersedes=None,
    )
    decision_set = ReviewDecisionSet(decisions=(second, first))

    assert decision_set.decisions == tuple(
        sorted((first, second), key=lambda item: item.decision_id)
    )
    assert ReviewDecisionSet.model_validate_json(
        decision_set.canonical_bytes()
    ) == decision_set
    assert len(decision_set.sha256()) == 64

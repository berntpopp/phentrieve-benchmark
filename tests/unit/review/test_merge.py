from datetime import UTC, datetime

import pytest

from phentrieve_benchmark.models.curated_annotation import (
    ActorKind,
    AnnotationReference,
)
from phentrieve_benchmark.models.review_decision import (
    ReviewDecision,
    ReviewDecisionSet,
    ReviewOutcome,
    ReviewScope,
)
from phentrieve_benchmark.review.merge import merge_review_decision_sets


def _decision(
    identifier: str,
    outcome: ReviewOutcome,
) -> ReviewDecision:
    return ReviewDecision.create(
        target=AnnotationReference(
            annotation_set_sha256=identifier * 64,
            annotation_id="curated-ann-" + identifier * 64,
        ),
        reviewer_id=f"human:reviewer-{identifier}",
        actor_kind=ActorKind.HUMAN,
        reviewer_role=None,
        stage_id="e3c:annotation-review/v1",
        scopes=(ReviewScope.COMPLETE,),
        outcome=outcome,
        decided_at=datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
        rationale=None,
        counterproposal=None,
        supersedes=None,
    )


def test_merge_is_associative_commutative_and_idempotent() -> None:
    first = ReviewDecisionSet(
        decisions=(_decision("a", ReviewOutcome.CONFIRMED),)
    )
    second = ReviewDecisionSet(
        decisions=(_decision("b", ReviewOutcome.REJECTED),)
    )

    assert merge_review_decision_sets((first, second)) == (
        merge_review_decision_sets((second, first))
    )
    assert merge_review_decision_sets((first, first)) == first
    assert merge_review_decision_sets(
        (merge_review_decision_sets((first,)), second)
    ) == merge_review_decision_sets((first, second))


def test_merge_retains_contradictory_reviews_of_same_target() -> None:
    confirmed = _decision("a", ReviewOutcome.CONFIRMED)
    rejected = ReviewDecision.create(
        target=confirmed.target,
        reviewer_id="human:reviewer-other",
        actor_kind=confirmed.actor_kind,
        reviewer_role=confirmed.reviewer_role,
        stage_id=confirmed.stage_id,
        scopes=confirmed.scopes,
        outcome=ReviewOutcome.REJECTED,
        decided_at=confirmed.decided_at,
        rationale=confirmed.rationale,
        counterproposal=None,
        supersedes=None,
    )
    merged = merge_review_decision_sets(
        (
            ReviewDecisionSet(decisions=(confirmed,)),
            ReviewDecisionSet(decisions=(rejected,)),
        )
    )

    assert {decision.outcome for decision in merged.decisions} == {
        ReviewOutcome.CONFIRMED,
        ReviewOutcome.REJECTED,
    }


def test_merge_rejects_same_id_with_different_content() -> None:
    first = _decision("a", ReviewOutcome.CONFIRMED)
    corrupted = first.model_copy(update={"outcome": ReviewOutcome.REJECTED})
    corrupted_set = ReviewDecisionSet.model_construct(
        decisions=(corrupted,)
    )

    with pytest.raises(ValueError, match="decision ID collision"):
        merge_review_decision_sets(
            (
                ReviewDecisionSet(decisions=(first,)),
                corrupted_set,
            )
        )

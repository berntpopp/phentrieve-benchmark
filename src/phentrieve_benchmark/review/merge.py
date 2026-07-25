from phentrieve_benchmark.models.review_decision import (
    ReviewDecision,
    ReviewDecisionSet,
)
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes


def _decision_bytes(decision: ReviewDecision) -> bytes:
    return canonical_json_bytes(decision.model_dump(mode="json"))


def merge_review_decision_sets(
    decision_sets: tuple[ReviewDecisionSet, ...],
) -> ReviewDecisionSet:
    by_id: dict[str, ReviewDecision] = {}
    for decision_set in decision_sets:
        for decision in decision_set.decisions:
            previous = by_id.get(decision.decision_id)
            if previous is not None:
                if _decision_bytes(previous) != _decision_bytes(decision):
                    raise ValueError("review decision ID collision")
                continue
            by_id[decision.decision_id] = decision
    return ReviewDecisionSet(decisions=tuple(by_id.values()))

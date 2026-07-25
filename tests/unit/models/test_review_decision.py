from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.curated_annotation import (
    ActorKind,
    AnnotationReference,
    AssertionStatus,
    BoundDocumentReference,
    CuratedAnnotation,
    CuratedAnnotationSet,
    DerivationActivity,
    DerivationMethod,
    DocumentReference,
    Experiencer,
    OntologyReference,
    Temporality,
)
from phentrieve_benchmark.models.review_decision import (
    DecisionReference,
    ReviewDecision,
    ReviewDecisionSet,
    ReviewOutcome,
    ReviewScope,
    validate_review_decision_set,
)


def _target(suffix: str = "a") -> AnnotationReference:
    return AnnotationReference(
        annotation_set_sha256=suffix * 64,
        annotation_id="curated-ann-" + suffix * 64,
    )


def _curated_set(suffix: str) -> CuratedAnnotationSet:
    annotation = CuratedAnnotation.create(
        hpo_id="HP:0000001",
        assertion=AssertionStatus.PRESENT,
        experiencer=Experiencer.PATIENT,
        temporality=Temporality.CURRENT,
        evidence_spans=(),
        derivations=(
            DerivationActivity(
                method=DerivationMethod.MANUAL_ANNOTATION,
                agent_id="human:curator-1",
                actor_kind=ActorKind.HUMAN,
                sources=(BoundDocumentReference(),),
            ),
        ),
    )
    return CuratedAnnotationSet(
        annotation_set_id=f"curated:{suffix}",
        document=DocumentReference(
            documents_sha256="a" * 64,
            document_id=f"document:{suffix}",
            document_sha256=suffix * 64,
        ),
        ontology=OntologyReference(
            hpo_release="v2026-06-23",
            ontology_sha256="b" * 64,
        ),
        annotations=(annotation,),
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


def test_review_validation_binds_exact_annotation_and_prior_decision_sets() -> None:
    curated = _curated_set("c")
    target = AnnotationReference(
        annotation_set_sha256=curated.sha256(),
        annotation_id=curated.annotations[0].annotation_id,
    )
    previous = ReviewDecision.create(
        target=target,
        reviewer_id="human:reviewer-1",
        actor_kind=ActorKind.HUMAN,
        reviewer_role=None,
        stage_id="e3c:annotation-review/v1",
        scopes=(ReviewScope.COMPLETE,),
        outcome=ReviewOutcome.REJECTED,
        decided_at=datetime(2026, 7, 26, 10, 30, tzinfo=UTC),
        rationale=None,
        counterproposal=None,
        supersedes=None,
    )
    previous_set = ReviewDecisionSet(decisions=(previous,))
    replacement = ReviewDecision.create(
        target=target,
        reviewer_id="human:reviewer-1",
        actor_kind=ActorKind.HUMAN,
        reviewer_role=None,
        stage_id="e3c:annotation-review/v1",
        scopes=(ReviewScope.COMPLETE,),
        outcome=ReviewOutcome.CONFIRMED,
        decided_at=datetime(2026, 7, 26, 11, 30, tzinfo=UTC),
        rationale="Corrected the previous decision.",
        counterproposal=None,
        supersedes=DecisionReference(
            decision_set_sha256=previous_set.sha256(),
            decision_id=previous.decision_id,
        ),
    )
    replacement_set = ReviewDecisionSet(decisions=(replacement,))

    validate_review_decision_set(
        replacement_set,
        annotation_sets={curated.sha256(): curated},
        decision_sets={previous_set.sha256(): previous_set},
    )

    with pytest.raises(ValueError, match="annotation set SHA-256"):
        validate_review_decision_set(
            replacement_set,
            annotation_sets={curated.sha256(): _curated_set("d")},
            decision_sets={previous_set.sha256(): previous_set},
        )
    with pytest.raises(ValueError, match="decision set SHA-256"):
        validate_review_decision_set(
            replacement_set,
            annotation_sets={curated.sha256(): curated},
            decision_sets={
                previous_set.sha256(): ReviewDecisionSet()
            },
        )

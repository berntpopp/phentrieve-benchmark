import json
from datetime import date

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.hpo_proposal import (
    PROPOSAL_PROVENANCE,
    BatchDocument,
    ProposalBatch,
    ProposalBatchOutput,
    ProposalRun,
    ProposedAnnotation,
    ResolvedMention,
    ValidationSummary,
)


def _document(document_id: str) -> BatchDocument:
    return BatchDocument(
        document_id=document_id,
        document_sha256="a" * 64,
        source_case_id=document_id.upper(),
        annotation_language="en",
    )


def _run(*batches: ProposalBatch) -> ProposalRun:
    return ProposalRun(
        run_id="pilot-v1",
        run_date=date(2026, 10, 7),
        model_id="claude-sonnet-5-5",
        corpus_manifest_sha256="1" * 64,
        documents_sha256="2" * 64,
        hpo_release="v2026-06-23",
        ontology_sha256="3" * 64,
        prompt_sha256="4" * 64,
        guideline_path="docs/annotation-guidelines/hpo-span-annotation.md",
        guideline_commit="5" * 40,
        guideline_sha256="6" * 64,
        batches=batches,
    )


def test_run_round_trips_through_canonical_json() -> None:
    run = _run(ProposalBatch(batch_id="batch-01", documents=(_document("d1"),)))
    assert ProposalRun.model_validate_json(run.canonical_bytes(), strict=True) == run


def test_run_rejects_a_document_in_two_batches() -> None:
    with pytest.raises(ValidationError, match="more than one batch"):
        _run(
            ProposalBatch(batch_id="batch-01", documents=(_document("d1"),)),
            ProposalBatch(batch_id="batch-02", documents=(_document("d1"),)),
        )


def test_run_rejects_duplicate_batch_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate batch"):
        _run(
            ProposalBatch(batch_id="batch-01", documents=(_document("d1"),)),
            ProposalBatch(batch_id="batch-01", documents=(_document("d2"),)),
        )


def test_run_id_must_be_a_safe_directory_name() -> None:
    run = _run(ProposalBatch(batch_id="batch-01", documents=(_document("d1"),)))
    payload = run.model_dump(mode="json")
    payload["run_id"] = "../x"
    with pytest.raises(ValidationError):
        ProposalRun.model_validate_json(json.dumps(payload), strict=True)


def test_batch_output_requires_the_provenance_notice() -> None:
    payload = {
        "schema_version": "e3c-hpo-proposal-batch/v1",
        "provenance": "gold",
        "run_id": "pilot-v1",
        "batch_id": "batch-01",
        "reports": [],
    }
    with pytest.raises(ValidationError):
        ProposalBatchOutput.model_validate_json(json.dumps(payload), strict=True)
    payload["provenance"] = PROPOSAL_PROVENANCE
    output = ProposalBatchOutput.model_validate_json(json.dumps(payload), strict=True)
    assert output.provenance == PROPOSAL_PROVENANCE


@pytest.mark.parametrize(
    ("field", "value"),
    [("experiencer", "unknown"), ("temporality", "future"), ("assertion", "yes")],
)
def test_proposed_annotation_uses_guideline_r3_values(field: str, value: str) -> None:
    payload: dict[str, object] = {
        "proposal_id": "p001",
        "hpo_id": "HP:0001945",
        "hpo_label": "Fever",
        "assertion": "present",
        "experiencer": "patient",
        "temporality": "current",
        "verbalized": True,
        "mentions": [{"phrase": "Fieber", "context": "hohem Fieber"}],
        "note": None,
    }
    annotation = ProposedAnnotation.model_validate_json(
        json.dumps(payload), strict=True
    )
    assert annotation.hpo_id == "HP:0001945"
    payload[field] = value
    with pytest.raises(ValidationError):
        ProposedAnnotation.model_validate_json(json.dumps(payload), strict=True)


def test_resolved_mention_rejects_inverted_or_empty_span() -> None:
    assert ResolvedMention(
        source_proposal_id="p001", mention_index=0, start=3, end=10, phrase="Fieber"
    )
    for start, end in [(10, 3), (5, 5)]:
        with pytest.raises(ValidationError, match="end must be greater"):
            ResolvedMention(
                source_proposal_id="p001",
                mention_index=0,
                start=start,
                end=end,
                phrase="Fieber",
            )


def test_validation_summary_rejects_negative_counts() -> None:
    counts = {
        "documents": 1,
        "proposals_received": 1,
        "proposals_rejected": 0,
        "validated_proposals": 1,
        "mentions_evaluated": 1,
        "mentions_rejected": 0,
        "validated_mentions": 1,
        "rejections_by_reason": {},
    }
    assert ValidationSummary(**counts).documents == 1  # type: ignore[arg-type]
    counts["mentions_rejected"] = -1
    with pytest.raises(ValidationError):
        ValidationSummary(**counts)  # type: ignore[arg-type]

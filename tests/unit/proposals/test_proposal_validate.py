import json
from datetime import date
from hashlib import sha256
from typing import Any

import pytest

from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.hpo_proposal import (
    MAX_EXCERPT_CHARS,
    PROPOSAL_PROVENANCE,
    BatchDocument,
    ProposalBatch,
    ProposalRun,
    ProposalValidationReport,
    RejectionReason,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex, load_hpo_index
from phentrieve_benchmark.proposals.validate import (
    ProposalBatchError,
    validate_proposal_run,
)
from tests.fixtures.hpo import proposal_hpo_obo

_GERMAN = Document.from_text(
    source_case_id="EN1",
    case_group_id="e3c:v2.0.0:EN1",
    document_id="e3c:v2.0.0:de:EN1:translated",
    language="de",
    translation_status=TranslationStatus.TRANSLATED,
    text=(
        "Die Schwellung ging mit hohem Fieber\u00a0einher. "
        "Diese Symptome waren nicht mit Erbrechen verbunden. "
        "Am dritten Tag erneut Fieber, Temperatur 39,5\u00a0\u00b0C."
    ),
)
_FIRST_FEVER = {"phrase": "Fieber", "context": "mit hohem Fieber einher"}
_SECOND_FEVER = {"phrase": "Fieber", "context": "erneut Fieber, Temperatur"}


def _index() -> HpoIndex:
    body = proposal_hpo_obo()
    return load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )


def _run() -> ProposalRun:
    return ProposalRun(
        run_id="test-run",
        run_date=date(2026, 10, 7),
        model_id="claude-sonnet-5-5",
        corpus_manifest_sha256="1" * 64,
        documents_sha256="2" * 64,
        hpo_release="v2026-06-23",
        ontology_sha256=sha256(proposal_hpo_obo()).hexdigest(),
        prompt_sha256="3" * 64,
        guideline_path="docs/annotation-guidelines/hpo-span-annotation.md",
        guideline_commit="4" * 40,
        guideline_sha256="5" * 64,
        batches=(
            ProposalBatch(
                batch_id="batch-01",
                documents=(
                    BatchDocument(
                        document_id=_GERMAN.document_id,
                        document_sha256=_GERMAN.document_sha256,
                        source_case_id="EN1",
                        annotation_language="de",
                    ),
                ),
            ),
        ),
    )


def _proposal(
    proposal_id: str = "p001",
    *,
    mentions: list[dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "proposal_id": proposal_id,
        "hpo_id": "HP:0001945",
        "hpo_label": "Fever",
        "assertion": "present",
        "experiencer": "patient",
        "temporality": "current",
        "verbalized": True,
        "mentions": mentions if mentions is not None else [_FIRST_FEVER],
        "note": None,
    }
    payload.update(overrides)
    return payload


def _output(reports: list[dict[str, Any]], **overrides: Any) -> bytes:
    payload: dict[str, Any] = {
        "schema_version": "e3c-hpo-proposal-batch/v1",
        "provenance": PROPOSAL_PROVENANCE,
        "run_id": "test-run",
        "batch_id": "batch-01",
        "reports": reports,
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False).encode()


def _report(annotations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "document_id": _GERMAN.document_id,
        "document_sha256": _GERMAN.document_sha256,
        "annotations": annotations,
    }


def _validate_outputs(outputs: dict[str, bytes]) -> ProposalValidationReport:
    return validate_proposal_run(
        run=_run(),
        run_sha256="6" * 64,
        batch_outputs=outputs,
        documents={_GERMAN.document_id: _GERMAN},
        hpo_index=_index(),
    )


def _validate(annotations: list[dict[str, Any]]) -> ProposalValidationReport:
    return _validate_outputs({"batch-01": _output([_report(annotations)])})


def _reasons(report: ProposalValidationReport) -> list[RejectionReason]:
    return [rejection.reason for rejection in report.rejections]


def test_valid_proposal_resolves_offsets_in_the_original_text() -> None:
    report = _validate([_proposal()])
    (document,) = report.documents
    (proposal,) = document.proposals
    (mention,) = proposal.mentions
    assert mention.start == _GERMAN.text.index("Fieber")
    assert _GERMAN.text[mention.start : mention.end] == "Fieber" == mention.phrase
    assert proposal.hpo_label == "Fever"
    assert report.rejections == ()


def test_measurement_span_keeps_the_original_spacing() -> None:
    report = _validate(
        [
            _proposal(),
            _proposal(
                "p002",
                verbalized=False,
                mentions=[
                    {"phrase": "39,5 \u00b0C", "context": "Temperatur 39,5 \u00b0C"}
                ],
            ),
        ]
    )
    proposals = report.documents[0].proposals
    assert len(proposals) == 2
    measurement = next(p for p in proposals if not p.verbalized)
    assert measurement.mentions[0].phrase == "39,5\u00a0\u00b0C"


def test_same_term_and_status_are_merged() -> None:
    report = _validate(
        [_proposal(), _proposal("p002", mentions=[_SECOND_FEVER], note="again")]
    )
    (proposal,) = report.documents[0].proposals
    assert proposal.proposal_id == "p001"
    assert proposal.source_proposal_ids == ("p001", "p002")
    assert [m.source_proposal_id for m in proposal.mentions] == ["p001", "p002"]
    assert proposal.notes == ("again",)


def test_different_status_stays_separate() -> None:
    report = _validate(
        [_proposal(), _proposal("p002", assertion="absent", mentions=[_SECOND_FEVER])]
    )
    assert len(report.documents[0].proposals) == 2


@pytest.mark.parametrize(
    ("hpo_id", "reason", "detail"),
    [
        ("HP:1234567", RejectionReason.UNKNOWN_HPO_ID, "not in the pinned"),
        ("HP:0009998", RejectionReason.UNKNOWN_HPO_ID, "alternate ID of HP:0001945"),
        ("HP:0009999", RejectionReason.OBSOLETE_HPO_ID, "obsolete"),
    ],
)
def test_invalid_hpo_ids_are_rejected(
    hpo_id: str, reason: RejectionReason, detail: str
) -> None:
    report = _validate([_proposal(hpo_id=hpo_id)])
    (rejection,) = report.rejections
    assert rejection.reason is reason
    assert detail in rejection.detail
    assert rejection.proposal_id == "p001"
    assert report.documents[0].proposals == ()


def test_schema_violation_is_rejected_with_the_proposal_id() -> None:
    report = _validate([_proposal(experiencer="unknown")])
    (rejection,) = report.rejections
    assert rejection.reason is RejectionReason.INVALID_SCHEMA
    assert rejection.proposal_id == "p001"
    assert "experiencer" in rejection.detail


def test_duplicate_proposal_id_is_rejected() -> None:
    report = _validate([_proposal(), _proposal(mentions=[_SECOND_FEVER])])
    assert _reasons(report) == [RejectionReason.DUPLICATE_PROPOSAL_ID]
    assert len(report.documents[0].proposals[0].mentions) == 1


def test_mention_rejection_keeps_the_rest_of_the_proposal() -> None:
    report = _validate(
        [
            _proposal(
                mentions=[_FIRST_FEVER, {"phrase": "Fieber", "context": "kein Fieber"}]
            )
        ]
    )
    (rejection,) = report.rejections
    assert rejection.reason is RejectionReason.CONTEXT_NOT_FOUND
    assert rejection.mention_index == 1
    assert len(report.documents[0].proposals[0].mentions) == 1


def test_proposal_without_located_mentions_is_rejected() -> None:
    report = _validate(
        [_proposal(mentions=[{"phrase": "Fieber", "context": "kein Fieber"}])]
    )
    assert _reasons(report) == [
        RejectionReason.CONTEXT_NOT_FOUND,
        RejectionReason.NO_VALID_MENTIONS,
    ]
    assert report.documents[0].proposals == ()


def test_overlapping_mentions_of_one_merged_proposal_are_rejected() -> None:
    report = _validate(
        [
            _proposal(
                mentions=[
                    {"phrase": "hohem Fieber", "context": "mit hohem Fieber einher"}
                ]
            ),
            _proposal("p002", mentions=[_FIRST_FEVER]),
        ]
    )
    (rejection,) = report.rejections
    assert rejection.reason is RejectionReason.OVERLAPPING_MENTION
    assert (rejection.proposal_id, rejection.mention_index) == ("p002", 0)
    (proposal,) = report.documents[0].proposals
    assert proposal.source_proposal_ids == ("p001", "p002")
    assert [m.phrase for m in proposal.mentions] == ["hohem Fieber"]


def test_label_mismatch_is_only_a_warning() -> None:
    report = _validate([_proposal(hpo_label="Pyrexia")])
    (warning,) = report.warnings
    assert (warning.proposed_label, warning.pinned_label) == ("Pyrexia", "Fever")
    assert len(report.documents[0].proposals) == 1


def test_summary_counts_add_up() -> None:
    report = _validate(
        [
            _proposal(
                mentions=[_FIRST_FEVER, {"phrase": "Fieber", "context": "kein Fieber"}]
            ),
            _proposal("p002", mentions=[_SECOND_FEVER]),
            _proposal(
                "p003",
                hpo_id="HP:0002013",
                hpo_label="Vomiting",
                assertion="absent",
                mentions=[
                    {"phrase": "Erbrechen", "context": "nicht mit Erbrechen verbunden"}
                ],
            ),
            _proposal("p004", hpo_id="HP:1234567"),
        ]
    )
    summary = report.summary
    accepted_sources = sum(
        len(p.source_proposal_ids) for p in report.documents[0].proposals
    )
    assert summary.proposals_received == 4
    assert summary.proposals_received == summary.proposals_rejected + accepted_sources
    assert summary.validated_proposals == 2
    assert summary.mentions_evaluated == 4
    assert (
        summary.mentions_evaluated
        == summary.mentions_rejected + summary.validated_mentions
    )
    assert summary.rejections_by_reason == {
        "context_not_found": 1,
        "unknown_hpo_id": 1,
    }


def test_report_is_deterministic_and_binds_the_batch_bytes() -> None:
    first = _validate([_proposal()])
    second = _validate([_proposal()])
    assert first.canonical_bytes() == second.canonical_bytes()
    raw = _output([_report([_proposal()])])
    assert first.batches[0].sha256 == sha256(raw).hexdigest()


def test_wrong_document_hash_fails_the_batch() -> None:
    report = _report([])
    report["document_sha256"] = "0" * 64
    with pytest.raises(ProposalBatchError, match="does not match"):
        _validate_outputs({"batch-01": _output([report])})


def test_missing_report_fails_the_batch() -> None:
    with pytest.raises(ProposalBatchError, match="missing"):
        _validate_outputs({"batch-01": _output([])})


def test_missing_batch_output_fails_the_run() -> None:
    with pytest.raises(ProposalBatchError, match="batch outputs missing"):
        _validate_outputs({})


def test_wrong_provenance_fails_the_batch() -> None:
    with pytest.raises(ProposalBatchError, match="invalid batch output"):
        _validate_outputs({"batch-01": _output([_report([])], provenance="gold")})


_VALID_REPORT = _report([_proposal()])


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"{", "not valid JSON"),
        (
            _output([_VALID_REPORT, {**_VALID_REPORT, "document_id": "other"}]),
            r"unknown=\['other'\]",
        ),
        (_output([_VALID_REPORT, _VALID_REPORT]), "duplicate report"),
        (_output([_VALID_REPORT], batch_id="batch-09"), "output names"),
        (
            _output([_report([_proposal(note="x" * (MAX_EXCERPT_CHARS + 1))])]),
            f"exceed {MAX_EXCERPT_CHARS} characters",
        ),
    ],
)
def test_batch_level_defects_fail_the_batch(raw: bytes, message: str) -> None:
    with pytest.raises(ProposalBatchError, match=message):
        _validate_outputs({"batch-01": raw})


def test_extra_batch_output_fails_the_run() -> None:
    with pytest.raises(ProposalBatchError, match="not in the run"):
        _validate_outputs(
            {"batch-01": _output([_VALID_REPORT]), "batch-02": _output([])}
        )


def test_all_batch_errors_are_reported_together() -> None:
    english = Document.from_text(
        source_case_id="EN2",
        case_group_id="e3c:v2.0.0:EN2",
        document_id="e3c:v2.0.0:en:EN2:native",
        language="en",
        translation_status=TranslationStatus.NATIVE,
        text="Fever.",
    )
    second = ProposalBatch(
        batch_id="batch-02",
        documents=(
            BatchDocument(
                document_id=english.document_id,
                document_sha256=english.document_sha256,
                source_case_id="EN2",
                annotation_language="en",
            ),
        ),
    )
    run = _run().model_copy(update={"batches": (*_run().batches, second)})
    with pytest.raises(ProposalBatchError) as caught:
        validate_proposal_run(
            run=run,
            run_sha256="6" * 64,
            batch_outputs={"batch-01": b"{", "batch-02": b"["},
            documents={_GERMAN.document_id: _GERMAN, english.document_id: english},
            hpo_index=_index(),
        )
    assert "batch-01" in str(caught.value)
    assert "batch-02" in str(caught.value)

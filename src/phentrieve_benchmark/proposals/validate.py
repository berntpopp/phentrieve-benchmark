"""Validate archived proposal batches without changing them.

Batch-level defects (unparseable output, any string longer than
MAX_EXCERPT_CHARS, wrong envelope, missing or unknown reports, hash mismatch)
raise one ProposalBatchError naming every affected batch: those outputs are
discarded and dispatched again, so an over-long excerpt is never tracked.
Proposal- and mention-level defects are listed as rejections. Accepted
proposals with the same HPO ID, assertion, experiencer, temporality, and
verbalized flag are merged (guideline R5). `verbalized` is part of the key so
that a measurement (R6) never inherits the flag of a worded mention.
"""

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.hpo_proposal import (
    MAX_EXCERPT_CHARS,
    BatchDigest,
    DocumentProposals,
    LabelWarning,
    ProposalBatch,
    ProposalBatchOutput,
    ProposalRun,
    ProposalValidationReport,
    ProposedAnnotation,
    Rejection,
    RejectionReason,
    ReportOutput,
    ResolvedMention,
    ValidatedProposal,
    ValidationSummary,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex
from phentrieve_benchmark.proposals.locate import (
    LocatedSpan,
    MentionLocationError,
    NormalizedText,
    locate_mention,
    normalize_typography,
)
from phentrieve_benchmark.provenance.digests import sha256_bytes

_StatusKey = tuple[str, str, str, str, bool]
_Located = tuple[ProposedAnnotation, list[tuple[int, LocatedSpan]]]


class ProposalBatchError(ValueError):
    """A batch output cannot be validated at all; dispatch the batch again."""


@dataclass
class _ReportLog:
    batch_id: str
    document_id: str
    rejections: list[Rejection] = field(default_factory=list)
    warnings: list[LabelWarning] = field(default_factory=list)

    def reject(
        self,
        reason: RejectionReason,
        detail: str,
        *,
        proposal_id: str | None,
        mention_index: int | None = None,
    ) -> None:
        self.rejections.append(
            Rejection(
                batch_id=self.batch_id,
                document_id=self.document_id,
                proposal_id=proposal_id,
                mention_index=mention_index,
                reason=reason,
                detail=detail,
            )
        )


def _error_detail(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(str(part) for part in first["loc"])
    return f"{location}: {first['msg']}" if location else str(first["msg"])


def _proposal_id_of(item: Any) -> str | None:
    if isinstance(item, dict):
        value = item.get("proposal_id")
        if isinstance(value, str):
            return value
    return None


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return []


def parse_batch_output(
    raw: bytes, *, run_id: str, batch: ProposalBatch
) -> ProposalBatchOutput:
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProposalBatchError(f"{batch.batch_id}: not valid JSON") from error
    too_long = [s for s in _strings(parsed) if len(s) > MAX_EXCERPT_CHARS]
    if too_long:
        raise ProposalBatchError(
            f"{batch.batch_id}: {len(too_long)} strings exceed "
            f"{MAX_EXCERPT_CHARS} characters; discard the output and dispatch "
            "the batch again"
        )
    try:
        output = ProposalBatchOutput.model_validate_json(raw, strict=True)
    except ValidationError as error:
        raise ProposalBatchError(
            f"{batch.batch_id}: invalid batch output ({_error_detail(error)})"
        ) from error
    if output.run_id != run_id or output.batch_id != batch.batch_id:
        raise ProposalBatchError(
            f"{batch.batch_id}: output names run {output.run_id!r} "
            f"and batch {output.batch_id!r}"
        )
    expected = {document.document_id: document for document in batch.documents}
    reported = [report.document_id for report in output.reports]
    if len(reported) != len(set(reported)):
        raise ProposalBatchError(f"{batch.batch_id}: duplicate report")
    missing = sorted(set(expected) - set(reported))
    unknown = sorted(set(reported) - set(expected))
    if missing or unknown:
        raise ProposalBatchError(
            f"{batch.batch_id}: reports differ from the batch: "
            f"missing={missing} unknown={unknown}"
        )
    for report in output.reports:
        if report.document_sha256 != expected[report.document_id].document_sha256:
            raise ProposalBatchError(
                f"{batch.batch_id}: hash of {report.document_id} does not match the run"
            )
    return output


def _accepted_proposal(
    item: Any, *, seen: set[str], hpo_index: HpoIndex, log: _ReportLog
) -> ProposedAnnotation | None:
    try:
        proposal = ProposedAnnotation.model_validate_json(json.dumps(item), strict=True)
    except ValidationError as error:
        log.reject(
            RejectionReason.INVALID_SCHEMA,
            _error_detail(error),
            proposal_id=_proposal_id_of(item),
        )
        return None
    if proposal.proposal_id in seen:
        log.reject(
            RejectionReason.DUPLICATE_PROPOSAL_ID,
            "proposal ID already used in this report",
            proposal_id=proposal.proposal_id,
        )
        return None
    seen.add(proposal.proposal_id)
    term = hpo_index.terms.get(proposal.hpo_id)
    if term is None:
        primary = hpo_index.alternate_to_primary.get(proposal.hpo_id)
        detail = (
            f"alternate ID of {primary}"
            if primary is not None
            else "not in the pinned HPO release"
        )
        log.reject(
            RejectionReason.UNKNOWN_HPO_ID, detail, proposal_id=proposal.proposal_id
        )
        return None
    if term.obsolete:
        log.reject(
            RejectionReason.OBSOLETE_HPO_ID,
            "obsolete in the pinned HPO release",
            proposal_id=proposal.proposal_id,
        )
        return None
    if term.label is None or term.label.casefold() != proposal.hpo_label.casefold():
        log.warnings.append(
            LabelWarning(
                batch_id=log.batch_id,
                document_id=log.document_id,
                proposal_id=proposal.proposal_id,
                hpo_id=proposal.hpo_id,
                proposed_label=proposal.hpo_label,
                pinned_label=term.label,
            )
        )
    return proposal


def _locate_all(
    proposal: ProposedAnnotation, text: NormalizedText, log: _ReportLog
) -> list[tuple[int, LocatedSpan]]:
    located: list[tuple[int, LocatedSpan]] = []
    for index, mention in enumerate(proposal.mentions):
        try:
            span = locate_mention(
                text,
                phrase=mention.phrase,
                context=mention.context,
                occurrence=mention.occurrence,
            )
        except MentionLocationError as error:
            log.reject(
                error.reason,
                error.detail,
                proposal_id=proposal.proposal_id,
                mention_index=index,
            )
            continue
        located.append((index, span))
    return located


def _merged(
    members: list[_Located],
    *,
    document: Document,
    hpo_index: HpoIndex,
    log: _ReportLog,
) -> ValidatedProposal:
    accepted: list[ResolvedMention] = []
    for proposal, located in members:
        for index, span in located:
            if any(
                span.start < mention.end and mention.start < span.end
                for mention in accepted
            ):
                log.reject(
                    RejectionReason.OVERLAPPING_MENTION,
                    "overlaps another mention of the same term and status",
                    proposal_id=proposal.proposal_id,
                    mention_index=index,
                )
                continue
            accepted.append(
                ResolvedMention(
                    source_proposal_id=proposal.proposal_id,
                    mention_index=index,
                    start=span.start,
                    end=span.end,
                    phrase=document.text[span.start : span.end],
                )
            )
    first = members[0][0]
    label = hpo_index.terms[first.hpo_id].label
    return ValidatedProposal(
        proposal_id=first.proposal_id,
        source_proposal_ids=tuple(proposal.proposal_id for proposal, _ in members),
        hpo_id=first.hpo_id,
        hpo_label=label if label is not None else first.hpo_id,
        assertion=first.assertion,
        experiencer=first.experiencer,
        temporality=first.temporality,
        verbalized=first.verbalized,
        mentions=tuple(
            sorted(accepted, key=lambda mention: (mention.start, mention.end))
        ),
        notes=tuple(proposal.note for proposal, _ in members if proposal.note),
    )


def _validate_report(
    *,
    report: ReportOutput,
    document: Document,
    hpo_index: HpoIndex,
    log: _ReportLog,
) -> tuple[DocumentProposals, int]:
    """Return the document's validated proposals and its evaluated mentions."""
    text = normalize_typography(document.text)
    seen: set[str] = set()
    groups: dict[_StatusKey, list[_Located]] = {}
    evaluated = 0
    for item in report.annotations:
        proposal = _accepted_proposal(item, seen=seen, hpo_index=hpo_index, log=log)
        if proposal is None:
            continue
        evaluated += len(proposal.mentions)
        located = _locate_all(proposal, text, log)
        if not located:
            log.reject(
                RejectionReason.NO_VALID_MENTIONS,
                "no mention could be located",
                proposal_id=proposal.proposal_id,
            )
            continue
        key: _StatusKey = (
            proposal.hpo_id,
            proposal.assertion,
            proposal.experiencer,
            proposal.temporality,
            proposal.verbalized,
        )
        groups.setdefault(key, []).append((proposal, located))
    proposals = tuple(
        _merged(members, document=document, hpo_index=hpo_index, log=log)
        for members in groups.values()
    )
    return (
        DocumentProposals(
            batch_id=log.batch_id,
            document_id=document.document_id,
            document_sha256=document.document_sha256,
            proposals=proposals,
        ),
        evaluated,
    )


def validate_proposal_run(
    *,
    run: ProposalRun,
    run_sha256: str,
    batch_outputs: Mapping[str, bytes],
    documents: Mapping[str, Document],
    hpo_index: HpoIndex,
) -> ProposalValidationReport:
    if (
        hpo_index.release != run.hpo_release
        or hpo_index.ontology_sha256 != run.ontology_sha256
    ):
        raise ValueError("HPO index does not match the run")
    batch_ids = [batch.batch_id for batch in run.batches]
    missing = [batch_id for batch_id in batch_ids if batch_id not in batch_outputs]
    if missing:
        raise ProposalBatchError(f"batch outputs missing: {missing}")
    extra = sorted(set(batch_outputs) - set(batch_ids))
    if extra:
        raise ProposalBatchError(f"batch outputs not in the run: {extra}")
    parsed: list[ProposalBatchOutput] = []
    errors: list[str] = []
    for batch in run.batches:
        try:
            parsed.append(
                parse_batch_output(
                    batch_outputs[batch.batch_id], run_id=run.run_id, batch=batch
                )
            )
        except ProposalBatchError as error:
            errors.append(str(error))
    if errors:
        raise ProposalBatchError("; ".join(errors))
    results: list[DocumentProposals] = []
    rejections: list[Rejection] = []
    warnings: list[LabelWarning] = []
    received = 0
    evaluated = 0
    for batch, output in zip(run.batches, parsed, strict=True):
        for report in output.reports:
            document = documents.get(report.document_id)
            if document is None or document.document_sha256 != report.document_sha256:
                raise ValueError(
                    f"corpus document {report.document_id} is missing or differs "
                    "from the run"
                )
            log = _ReportLog(batch_id=batch.batch_id, document_id=document.document_id)
            result, count = _validate_report(
                report=report, document=document, hpo_index=hpo_index, log=log
            )
            results.append(result)
            rejections.extend(log.rejections)
            warnings.extend(log.warnings)
            received += len(report.annotations)
            evaluated += count
    validated = [proposal for result in results for proposal in result.proposals]
    summary = ValidationSummary(
        documents=len(results),
        proposals_received=received,
        proposals_rejected=sum(1 for r in rejections if r.mention_index is None),
        validated_proposals=len(validated),
        mentions_evaluated=evaluated,
        mentions_rejected=sum(1 for r in rejections if r.mention_index is not None),
        validated_mentions=sum(len(proposal.mentions) for proposal in validated),
        rejections_by_reason=dict(
            sorted(Counter(r.reason.value for r in rejections).items())
        ),
    )
    return ProposalValidationReport(
        run_id=run.run_id,
        run_sha256=run_sha256,
        corpus_manifest_sha256=run.corpus_manifest_sha256,
        hpo_release=run.hpo_release,
        ontology_sha256=run.ontology_sha256,
        batches=tuple(
            BatchDigest(batch_id=batch_id, sha256=sha256_bytes(batch_outputs[batch_id]))
            for batch_id in batch_ids
        ),
        documents=tuple(sorted(results, key=lambda result: result.document_id)),
        rejections=tuple(rejections),
        warnings=tuple(warnings),
        summary=summary,
    )

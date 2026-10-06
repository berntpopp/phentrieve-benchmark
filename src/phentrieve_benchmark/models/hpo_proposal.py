"""Models for the LLM proposal step.

Proposals are machine generated, not review data, and not gold. A run lists
its batches; each batch output is the unchanged subagent JSON; the validation
report resolves offsets, merges, and rejections deterministically.
"""

from datetime import date
from enum import StrEnum
from typing import Any, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes
from phentrieve_benchmark.selection.groups import AnnotationLanguage

PROPOSAL_PROVENANCE: Final = "machine generated, not review data, not gold"
# Longest string allowed anywhere in a tracked batch output (licence: excerpts only).
MAX_EXCERPT_CHARS: Final = 300
Provenance = Literal["machine generated, not review data, not gold"]
Assertion = Literal["present", "absent", "uncertain"]
ProposalExperiencer = Literal["patient", "family_member", "other"]
ProposalTemporality = Literal["current", "historical"]
_RUN_ID = r"^[a-z0-9][a-z0-9-]{0,62}$"
_BATCH_ID = r"^batch-[0-9]{2,}$"
_HPO_ID = r"^HP:[0-9]{7}$"


class BatchDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    document_id: str = Field(min_length=1)
    document_sha256: Sha256Hex
    source_case_id: str = Field(min_length=1)
    annotation_language: AnnotationLanguage


class ProposalBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str = Field(pattern=_BATCH_ID)
    documents: tuple[BatchDocument, ...] = Field(min_length=1)


class ProposalRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-hpo-proposal-run/v1"] = "e3c-hpo-proposal-run/v1"
    run_id: str = Field(pattern=_RUN_ID)
    run_date: date
    model_id: str = Field(min_length=1)
    corpus_manifest_sha256: Sha256Hex
    documents_sha256: Sha256Hex
    hpo_release: str = Field(pattern=r"^v[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    ontology_sha256: Sha256Hex
    prompt_sha256: Sha256Hex
    guideline_path: str = Field(min_length=1)
    guideline_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    guideline_sha256: Sha256Hex
    batches: tuple[ProposalBatch, ...] = Field(min_length=1)
    # German reports of the selection left out because their review is pending.
    pending_review: tuple[str, ...] = ()

    @model_validator(mode="after")
    def batches_are_disjoint(self) -> Self:
        batch_ids = [batch.batch_id for batch in self.batches]
        if len(batch_ids) != len(set(batch_ids)):
            raise ValueError("duplicate batch ID")
        document_ids = [
            document.document_id
            for batch in self.batches
            for document in batch.documents
        ]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("a document appears in more than one batch slot")
        return self

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))


class ProposalMention(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    phrase: str = Field(min_length=1)
    context: str = Field(min_length=1)
    occurrence: int | None = Field(default=None, ge=1)


class ProposedAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    proposal_id: str = Field(pattern=r"^p[0-9]{3,}$")
    hpo_id: str = Field(pattern=_HPO_ID)
    hpo_label: str = Field(min_length=1)
    assertion: Assertion
    experiencer: ProposalExperiencer
    temporality: ProposalTemporality
    verbalized: bool
    mentions: tuple[ProposalMention, ...] = Field(min_length=1)
    note: str | None = None


class ReportOutput(BaseModel):
    """One report of a batch output; annotations are checked one by one."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    document_id: str = Field(min_length=1)
    document_sha256: Sha256Hex
    annotations: tuple[Any, ...]


class ProposalBatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-hpo-proposal-batch/v1"]
    provenance: Provenance
    run_id: str
    batch_id: str
    reports: tuple[ReportOutput, ...]


class RejectionReason(StrEnum):
    INVALID_SCHEMA = "invalid_schema"
    DUPLICATE_PROPOSAL_ID = "duplicate_proposal_id"
    UNKNOWN_HPO_ID = "unknown_hpo_id"
    OBSOLETE_HPO_ID = "obsolete_hpo_id"
    NO_VALID_MENTIONS = "no_valid_mentions"
    PHRASE_NOT_TRIMMED = "phrase_not_trimmed"
    CONTEXT_NOT_FOUND = "context_not_found"
    CONTEXT_NOT_UNIQUE = "context_not_unique"
    PHRASE_NOT_IN_CONTEXT = "phrase_not_in_context"
    PHRASE_NOT_UNIQUE_IN_CONTEXT = "phrase_not_unique_in_context"
    OCCURRENCE_OUT_OF_RANGE = "occurrence_out_of_range"
    OVERLAPPING_MENTION = "overlapping_mention"


class Rejection(BaseModel):
    """A rejected proposal (no mention index) or mention (with index)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str
    document_id: str
    proposal_id: str | None
    mention_index: int | None = Field(default=None, ge=0)
    reason: RejectionReason
    detail: str


class LabelWarning(BaseModel):
    """The proposed label differs from the pinned label; the ID still counts."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str
    document_id: str
    proposal_id: str
    hpo_id: str
    proposed_label: str
    pinned_label: str | None


class ResolvedMention(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_proposal_id: str
    mention_index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    phrase: str = Field(min_length=1)

    @model_validator(mode="after")
    def has_nonempty_range(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class ValidatedProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    proposal_id: str
    source_proposal_ids: tuple[str, ...] = Field(min_length=1)
    hpo_id: str = Field(pattern=_HPO_ID)
    hpo_label: str
    assertion: Assertion
    experiencer: ProposalExperiencer
    temporality: ProposalTemporality
    verbalized: bool
    mentions: tuple[ResolvedMention, ...] = Field(min_length=1)
    notes: tuple[str, ...]


class DocumentProposals(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str
    document_id: str
    document_sha256: Sha256Hex
    proposals: tuple[ValidatedProposal, ...]


class BatchDigest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str
    sha256: Sha256Hex


class ValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    documents: int = Field(ge=0)
    proposals_received: int = Field(ge=0)
    proposals_rejected: int = Field(ge=0)
    validated_proposals: int = Field(ge=0)
    mentions_evaluated: int = Field(ge=0)
    mentions_rejected: int = Field(ge=0)
    validated_mentions: int = Field(ge=0)
    rejections_by_reason: dict[str, int]


class ProposalValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-hpo-proposal-validation/v1"] = (
        "e3c-hpo-proposal-validation/v1"
    )
    provenance: Provenance = PROPOSAL_PROVENANCE
    run_id: str
    run_sha256: Sha256Hex
    corpus_manifest_sha256: Sha256Hex
    hpo_release: str
    ontology_sha256: Sha256Hex
    batches: tuple[BatchDigest, ...]
    documents: tuple[DocumentProposals, ...]
    rejections: tuple[Rejection, ...]
    warnings: tuple[LabelWarning, ...]
    summary: ValidationSummary

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

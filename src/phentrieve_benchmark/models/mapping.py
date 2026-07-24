from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.models.identifiers import HpoRelease
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class MappingClassification(StrEnum):
    UNIQUE_ACTIVE = "unique_active"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"
    OBSOLETE = "obsolete"
    INVALID = "invalid"


class MappingDecision(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"


class MappingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    text_sha256: Sha256Hex


class HpoMappingCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    hpo_id: str = Field(pattern=r"^HP:[0-9]{7}$")
    label: str | None
    obsolete: bool
    replaced_by: tuple[str, ...] = ()
    consider: tuple[str, ...] = ()


class UmlsHpoMappingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["umls-hpo-mapping-record/v1"] = (
        "umls-hpo-mapping-record/v1"
    )
    mapping_record_id: str = Field(min_length=1)
    source_case_id: str = Field(min_length=1)
    source_annotation_set_id: str = Field(min_length=1)
    source_annotation_id: str = Field(min_length=1)
    source_document_sha256: Sha256Hex
    source_concept_id: str | None
    evidence: tuple[MappingEvidence, ...]
    candidates: tuple[HpoMappingCandidate, ...]
    hpo_release: HpoRelease
    ontology_sha256: Sha256Hex
    mapping_method: Literal["hpo-umls-xref"] = "hpo-umls-xref"
    classification: MappingClassification
    decision: MappingDecision
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def classification_is_consistent(self) -> Self:
        candidate_ids = [candidate.hpo_id for candidate in self.candidates]
        if candidate_ids != sorted(candidate_ids):
            raise ValueError("mapping candidates must be sorted")
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("duplicate mapping candidate")
        expected_decision = (
            MappingDecision.CANDIDATE
            if self.classification is MappingClassification.UNIQUE_ACTIVE
            else MappingDecision.NEEDS_REVIEW
        )
        if self.decision is not expected_decision:
            raise ValueError("mapping decision contradicts classification")
        return self


class MappingCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    classification: MappingClassification
    count: int = Field(ge=0)


class UmlsHpoMappingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    document_count: int = Field(ge=0)
    annotation_count: int = Field(ge=0)
    unique_cui_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    classifications: tuple[MappingCount, ...]


class UmlsHpoMappingManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["umls-hpo-mapping-manifest/v1"] = (
        "umls-hpo-mapping-manifest/v1"
    )
    mapping_id: str = Field(min_length=1)
    normalization_sha256: Sha256Hex
    hpo_release: HpoRelease
    ontology_sha256: Sha256Hex
    selection_id: str | None = None
    selection_sha256: Sha256Hex | None = None
    population_case_ids: tuple[str, ...]
    records: tuple[UmlsHpoMappingRecord, ...]
    summary: UmlsHpoMappingSummary

    @model_validator(mode="after")
    def manifest_is_consistent(self) -> Self:
        record_ids = [record.mapping_record_id for record in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("duplicate mapping record identity")
        ordered = sorted(
            self.records,
            key=lambda record: (
                record.source_case_id,
                record.source_annotation_set_id,
                record.source_annotation_id,
            ),
        )
        if list(self.records) != ordered:
            raise ValueError("mapping records must be sorted")
        if self.summary.annotation_count != len(self.records):
            raise ValueError("mapping annotation count mismatch")
        if tuple(sorted(set(self.population_case_ids))) != self.population_case_ids:
            raise ValueError("mapping population case IDs must be unique and sorted")
        if self.summary.document_count != len(self.population_case_ids):
            raise ValueError("mapping document count mismatch")
        if any(
            record.source_case_id not in self.population_case_ids
            for record in self.records
        ):
            raise ValueError("mapping record is outside document population")
        if (self.selection_id is None) != (self.selection_sha256 is None):
            raise ValueError("selection identity must be complete")
        return self

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

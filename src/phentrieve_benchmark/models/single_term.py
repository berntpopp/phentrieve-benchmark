from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from phentrieve_benchmark.models.curated_annotation import (
    ActorKind,
    AnnotationReference,
    AssertionStatus,
    Experiencer,
    OntologyReference,
    Temporality,
)
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class SingleTermSelectionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    annotation: AnnotationReference
    evidence_span_index: int = Field(ge=0)


def _selection_key(
    record: SingleTermSelectionRecord,
) -> tuple[str, str, int]:
    return (
        record.annotation.annotation_set_sha256,
        record.annotation.annotation_id,
        record.evidence_span_index,
    )


class SingleTermSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["single-term-selection/v1"] = (
        "single-term-selection/v1"
    )
    selector_id: str = Field(
        pattern=r"^[a-z][a-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9._/-]*$"
    )
    actor_kind: ActorKind
    method_id: str = Field(
        pattern=r"^[a-z][a-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9._/-]*$"
    )
    source_review_set_sha256s: tuple[Sha256Hex, ...] = ()
    records: tuple[SingleTermSelectionRecord, ...] = ()

    @field_validator("source_review_set_sha256s")
    @classmethod
    def canonicalize_review_hashes(
        cls, hashes: tuple[Sha256Hex, ...]
    ) -> tuple[Sha256Hex, ...]:
        if len(hashes) != len(set(hashes)):
            raise ValueError("duplicate review decision set")
        return tuple(sorted(hashes))

    @field_validator("records")
    @classmethod
    def canonicalize_records(
        cls, records: tuple[SingleTermSelectionRecord, ...]
    ) -> tuple[SingleTermSelectionRecord, ...]:
        keys = [_selection_key(record) for record in records]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate selection record")
        return tuple(sorted(records, key=_selection_key))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())


def single_term_id(
    *,
    document_sha256: str,
    annotation: AnnotationReference,
    evidence_span_index: int,
) -> str:
    return "single-term-" + sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": "single-term-id/v1",
                "document_sha256": document_sha256,
                "annotation_set_sha256": annotation.annotation_set_sha256,
                "annotation_id": annotation.annotation_id,
                "evidence_span_index": evidence_span_index,
            }
        )
    )


class SingleTermRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    single_term_id: str = Field(pattern=r"^single-term-[0-9a-f]{64}$")
    document_sha256: Sha256Hex
    annotation: AnnotationReference
    evidence_span_index: int = Field(ge=0)
    hpo_id: str = Field(pattern=r"^HP:[0-9]{7}$")
    assertion: AssertionStatus
    experiencer: Experiencer
    temporality: Temporality
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    term_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity_and_range(self) -> Self:
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        expected = single_term_id(
            document_sha256=self.document_sha256,
            annotation=self.annotation,
            evidence_span_index=self.evidence_span_index,
        )
        if self.single_term_id != expected:
            raise ValueError("single_term_id mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        document_sha256: str,
        annotation: AnnotationReference,
        evidence_span_index: int,
        hpo_id: str,
        assertion: AssertionStatus,
        experiencer: Experiencer,
        temporality: Temporality,
        start_char: int,
        end_char: int,
        term_text: str,
    ) -> Self:
        return cls(
            single_term_id=single_term_id(
                document_sha256=document_sha256,
                annotation=annotation,
                evidence_span_index=evidence_span_index,
            ),
            document_sha256=document_sha256,
            annotation=annotation,
            evidence_span_index=evidence_span_index,
            hpo_id=hpo_id,
            assertion=assertion,
            experiencer=experiencer,
            temporality=temporality,
            start_char=start_char,
            end_char=end_char,
            term_text=term_text,
        )


def _term_key(record: SingleTermRecord) -> tuple[str, str, str, int]:
    return (
        record.document_sha256,
        record.annotation.annotation_set_sha256,
        record.annotation.annotation_id,
        record.evidence_span_index,
    )


class SingleTermSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["single-term-set/v1"] = "single-term-set/v1"
    selection_sha256: Sha256Hex
    ontology: OntologyReference
    records: tuple[SingleTermRecord, ...] = ()

    @field_validator("records")
    @classmethod
    def canonicalize_records(
        cls, records: tuple[SingleTermRecord, ...]
    ) -> tuple[SingleTermRecord, ...]:
        keys = [_term_key(record) for record in records]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate single-term record")
        return tuple(sorted(records, key=_term_key))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

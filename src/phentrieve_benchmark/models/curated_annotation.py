from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from phentrieve_benchmark.models.annotation import EvidenceSpan
from phentrieve_benchmark.models.identifiers import HpoRelease
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class ActorKind(StrEnum):
    HUMAN = "human"
    TOOL = "tool"


class AssertionStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNCERTAIN = "uncertain"


class Experiencer(StrEnum):
    PATIENT = "patient"
    OTHER = "other"


class Temporality(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    FUTURE = "future"


class DerivationMethod(StrEnum):
    DIRECT_MAPPING = "direct_mapping"
    CONTEXTUAL_REFINEMENT = "contextual_refinement"
    SOURCE_HPO = "source_hpo"
    MANUAL_ANNOTATION = "manual_annotation"
    REVISION = "revision"


class DocumentReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    documents_sha256: Sha256Hex
    document_id: str = Field(min_length=1)
    document_sha256: Sha256Hex


class OntologyReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    hpo_release: HpoRelease
    ontology_sha256: Sha256Hex


class AnnotationReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    annotation_set_sha256: Sha256Hex
    annotation_id: str = Field(min_length=1)


class E3cSourceAnnotationReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_kind: Literal["e3c_source_annotation"] = "e3c_source_annotation"
    source_annotations_sha256: Sha256Hex
    source_annotation_set_id: str = Field(min_length=1)
    source_annotation_id: str = Field(min_length=1)


class UmlsHpoMappingReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_kind: Literal["umls_hpo_mapping_record"] = (
        "umls_hpo_mapping_record"
    )
    mapping_manifest_sha256: Sha256Hex
    mapping_record_id: str = Field(min_length=1)


class RagHpoSourceAnnotationReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_kind: Literal["raghpo_source_annotation"] = (
        "raghpo_source_annotation"
    )
    annotations_sha256: Sha256Hex
    annotation_set_id: str = Field(min_length=1)
    annotation_id: str = Field(min_length=1)
    source_sidecar_sha256: Sha256Hex
    source_row_id: str = Field(min_length=1)


class CuratedAnnotationReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_kind: Literal["curated_annotation"] = "curated_annotation"
    annotation: AnnotationReference


class BoundDocumentReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_kind: Literal["bound_document"] = "bound_document"


DerivationSourceReference = Annotated[
    E3cSourceAnnotationReference
    | UmlsHpoMappingReference
    | RagHpoSourceAnnotationReference
    | CuratedAnnotationReference
    | BoundDocumentReference,
    Field(discriminator="source_kind"),
]


def _model_sort_key(model: BaseModel) -> bytes:
    return canonical_json_bytes(model.model_dump(mode="json"))


def _source_sort_key(source: DerivationSourceReference) -> tuple[str, bytes]:
    return source.source_kind, _model_sort_key(source)


class DerivationActivity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    method: DerivationMethod
    agent_id: str = Field(
        min_length=3,
        pattern=r"^[a-z][a-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )
    actor_kind: ActorKind
    sources: tuple[DerivationSourceReference, ...] = Field(min_length=1)

    @field_validator("sources")
    @classmethod
    def canonicalize_sources(
        cls, sources: tuple[DerivationSourceReference, ...]
    ) -> tuple[DerivationSourceReference, ...]:
        keys = [_model_sort_key(source) for source in sources]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate derivation source")
        return tuple(sorted(sources, key=_source_sort_key))


def curated_annotation_id(payload: dict[str, object]) -> str:
    identity_payload = {
        "schema_version": "curated-annotation-id/v1",
        "annotation": payload,
    }
    return "curated-ann-" + sha256_bytes(
        canonical_json_bytes(identity_payload)
    )


class CuratedAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    annotation_id: str = Field(pattern=r"^curated-ann-[0-9a-f]{64}$")
    hpo_id: str = Field(pattern=r"^HP:[0-9]{7}$")
    assertion: AssertionStatus
    experiencer: Experiencer
    temporality: Temporality
    evidence_spans: tuple[EvidenceSpan, ...] = ()
    derivations: tuple[DerivationActivity, ...] = Field(min_length=1)

    @field_validator("evidence_spans")
    @classmethod
    def canonicalize_spans(
        cls, spans: tuple[EvidenceSpan, ...]
    ) -> tuple[EvidenceSpan, ...]:
        identities = [
            (span.start_char, span.end_char, span.text_snippet)
            for span in spans
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate evidence span")
        return tuple(
            sorted(
                spans,
                key=lambda span: (
                    span.start_char,
                    span.end_char,
                    span.text_snippet,
                ),
            )
        )

    @field_validator("derivations")
    @classmethod
    def canonicalize_derivations(
        cls, derivations: tuple[DerivationActivity, ...]
    ) -> tuple[DerivationActivity, ...]:
        keys = [_model_sort_key(derivation) for derivation in derivations]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate derivation activity")
        return tuple(sorted(derivations, key=_model_sort_key))

    @model_validator(mode="after")
    def annotation_id_matches_content(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"annotation_id"})
        expected = curated_annotation_id(payload)
        if self.annotation_id != expected:
            raise ValueError("annotation_id mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        hpo_id: str,
        assertion: AssertionStatus,
        experiencer: Experiencer,
        temporality: Temporality,
        evidence_spans: tuple[EvidenceSpan, ...],
        derivations: tuple[DerivationActivity, ...],
    ) -> Self:
        canonical_spans = cls.canonicalize_spans(evidence_spans)
        canonical_derivations = cls.canonicalize_derivations(derivations)
        payload: dict[str, object] = {
            "hpo_id": hpo_id,
            "assertion": assertion,
            "experiencer": experiencer,
            "temporality": temporality,
            "evidence_spans": [
                span.model_dump(mode="json") for span in canonical_spans
            ],
            "derivations": [
                derivation.model_dump(mode="json")
                for derivation in canonical_derivations
            ],
        }
        return cls(
            annotation_id=curated_annotation_id(payload),
            hpo_id=hpo_id,
            assertion=assertion,
            experiencer=experiencer,
            temporality=temporality,
            evidence_spans=canonical_spans,
            derivations=canonical_derivations,
        )


class CuratedAnnotationSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["curated-annotation-set/v1"] = (
        "curated-annotation-set/v1"
    )
    annotation_set_id: str = Field(min_length=1)
    document: DocumentReference
    ontology: OntologyReference
    annotations: tuple[CuratedAnnotation, ...] = ()

    @field_validator("annotations")
    @classmethod
    def canonicalize_annotations(
        cls, annotations: tuple[CuratedAnnotation, ...]
    ) -> tuple[CuratedAnnotation, ...]:
        identities = [annotation.annotation_id for annotation in annotations]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate curated annotation")
        return tuple(
            sorted(annotations, key=lambda annotation: annotation.annotation_id)
        )

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

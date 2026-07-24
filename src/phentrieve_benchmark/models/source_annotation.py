from typing import Literal, Self
from unicodedata import category, normalize

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from phentrieve_benchmark.models.annotation import EvidenceSpan
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.provenance.digests import Sha256Hex


def _canonical_string(value: str) -> str:
    canonical = normalize("NFC", value)
    if not canonical:
        raise ValueError("value must not be empty")
    if any(category(character).startswith("C") for character in canonical):
        raise ValueError("value must not contain control characters")
    return canonical


class SourceAttribute(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    namespace: str = Field(min_length=1)
    name: str = Field(min_length=1)
    value: str = Field(min_length=1)

    @field_validator("namespace", "name", "value")
    @classmethod
    def canonicalize_strings(cls, value: str) -> str:
        return _canonical_string(value)


class SourceRelationArgument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    role: str = Field(min_length=1)
    referenced_annotation_id: str = Field(min_length=1)

    @field_validator("role", "referenced_annotation_id")
    @classmethod
    def canonicalize_strings(cls, value: str) -> str:
        return _canonical_string(value)


class SourceAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_annotation_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_concept_id: str | None = None
    attributes: tuple[SourceAttribute, ...] = ()
    evidence_spans: tuple[EvidenceSpan, ...] = ()

    @field_validator("source_annotation_id", "source_type", "source_concept_id")
    @classmethod
    def canonicalize_optional_strings(cls, value: str | None) -> str | None:
        return None if value is None else _canonical_string(value)

    @field_validator("attributes")
    @classmethod
    def canonicalize_attributes(
        cls, attributes: tuple[SourceAttribute, ...]
    ) -> tuple[SourceAttribute, ...]:
        identities = [
            (attribute.namespace, attribute.name) for attribute in attributes
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate attribute identity")
        return tuple(
            sorted(
                attributes,
                key=lambda attribute: (attribute.namespace, attribute.name),
            )
        )

    @field_validator("evidence_spans")
    @classmethod
    def canonicalize_evidence_spans(
        cls, spans: tuple[EvidenceSpan, ...]
    ) -> tuple[EvidenceSpan, ...]:
        identities = [
            (span.start_char, span.end_char, span.text_snippet) for span in spans
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


class SourceRelation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_relation_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    arguments: tuple[SourceRelationArgument, ...] = ()
    attributes: tuple[SourceAttribute, ...] = ()

    @field_validator("source_relation_id", "source_type")
    @classmethod
    def canonicalize_strings(cls, value: str) -> str:
        return _canonical_string(value)

    @field_validator("arguments")
    @classmethod
    def canonicalize_arguments(
        cls, arguments: tuple[SourceRelationArgument, ...]
    ) -> tuple[SourceRelationArgument, ...]:
        identities = [
            (argument.role, argument.referenced_annotation_id)
            for argument in arguments
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate argument identity")
        return tuple(
            sorted(
                arguments,
                key=lambda argument: (
                    argument.role,
                    argument.referenced_annotation_id,
                ),
            )
        )

    @field_validator("attributes")
    @classmethod
    def canonicalize_attributes(
        cls, attributes: tuple[SourceAttribute, ...]
    ) -> tuple[SourceAttribute, ...]:
        identities = [
            (attribute.namespace, attribute.name) for attribute in attributes
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate attribute identity")
        return tuple(
            sorted(
                attributes,
                key=lambda attribute: (attribute.namespace, attribute.name),
            )
        )


class SourceAnnotationSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["source-annotation-set/v1"] = (
        "source-annotation-set/v1"
    )
    annotation_set_id: str = Field(min_length=1)
    document_sha256: Sha256Hex
    source_schema_id: str = Field(min_length=1)
    annotations: tuple[SourceAnnotation, ...] = ()
    relations: tuple[SourceRelation, ...] = ()

    @field_validator("annotation_set_id", "source_schema_id")
    @classmethod
    def canonicalize_strings(cls, value: str) -> str:
        return _canonical_string(value)

    @field_validator("annotations")
    @classmethod
    def canonicalize_annotations(
        cls, annotations: tuple[SourceAnnotation, ...]
    ) -> tuple[SourceAnnotation, ...]:
        identities = [
            annotation.source_annotation_id for annotation in annotations
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate source annotation identity")
        return tuple(
            sorted(
                annotations,
                key=lambda annotation: annotation.source_annotation_id,
            )
        )

    @field_validator("relations")
    @classmethod
    def canonicalize_relations(
        cls, relations: tuple[SourceRelation, ...]
    ) -> tuple[SourceRelation, ...]:
        identities = [relation.source_relation_id for relation in relations]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate source relation identity")
        return tuple(
            sorted(relations, key=lambda relation: relation.source_relation_id)
        )

    @model_validator(mode="after")
    def relation_arguments_resolve(self) -> Self:
        annotation_ids = {
            annotation.source_annotation_id for annotation in self.annotations
        }
        for relation in self.relations:
            for argument in relation.arguments:
                if argument.referenced_annotation_id not in annotation_ids:
                    raise ValueError(
                        "relation argument references missing annotation "
                        f"{argument.referenced_annotation_id!r}"
                    )
        return self


def validate_source_annotation_set(
    document: Document,
    annotation_set: SourceAnnotationSet,
) -> None:
    if annotation_set.document_sha256 != document.document_sha256:
        raise ValueError("source annotation set document hash mismatch")
    for annotation in annotation_set.annotations:
        for span in annotation.evidence_spans:
            if span.end_char > len(document.text):
                raise ValueError(
                    "span ends past document end for source annotation "
                    f"{annotation.source_annotation_id}"
                )
            actual = document.text[span.start_char : span.end_char]
            if actual != span.text_snippet:
                raise ValueError(
                    "span text mismatch for source annotation "
                    f"{annotation.source_annotation_id}: "
                    f"expected {span.text_snippet!r}, got {actual!r}"
                )

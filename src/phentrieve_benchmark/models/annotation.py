from pydantic import BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.provenance.digests import Sha256Hex


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    snippet: str = Field(min_length=1)

    @model_validator(mode="after")
    def has_nonempty_range(self) -> "EvidenceSpan":
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        return self


class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    annotation_id: str = Field(min_length=1)
    hpo_id: str = Field(pattern=r"^HP:[0-9]{7}$")
    assertion: str = "present"
    experiencer: str = "patient"
    temporality: str = "current"
    evidence_spans: tuple[EvidenceSpan, ...] = ()


class AnnotationSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    annotation_set_id: str = Field(min_length=1)
    document_sha256: Sha256Hex
    hpo_release: str = Field(pattern=r"^v\d{4}-\d{2}-\d{2}$")
    annotations: tuple[Annotation, ...] = ()


def validate_annotation_set(document: Document, annotation_set: AnnotationSet) -> None:
    if annotation_set.document_sha256 != document.document_sha256:
        raise ValueError("annotation set document hash mismatch")
    for annotation in annotation_set.annotations:
        for span in annotation.evidence_spans:
            if span.end_char > len(document.text):
                raise ValueError(
                    "span ends past document end for annotation "
                    f"{annotation.annotation_id}"
                )
            actual = document.text[span.start_char : span.end_char]
            if actual != span.snippet:
                raise ValueError(
                    f"span text mismatch for annotation {annotation.annotation_id}: "
                    f"expected {span.snippet!r}, got {actual!r}"
                )

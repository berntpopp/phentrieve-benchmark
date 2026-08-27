from collections import Counter
from enum import StrEnum
from fractions import Fraction
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.source_annotation import SourceAnnotationSet
from phentrieve_benchmark.provenance.digests import Sha256Hex

_FACTUALITY_ATTRIBUTES = {
    "contextualAspect",
    "contextualModality",
    "degree",
    "docTimeRel",
    "permanence",
    "polarity",
}


class Rational(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    numerator: int = Field(ge=0)
    denominator: int = Field(gt=0)

    @model_validator(mode="after")
    def is_reduced(self) -> Self:
        reduced = Fraction(self.numerator, self.denominator)
        if (
            reduced.numerator != self.numerator
            or reduced.denominator != self.denominator
        ):
            raise ValueError("rational must be reduced")
        return self

    @classmethod
    def from_fraction(cls, value: Fraction) -> Self:
        if value < 0:
            raise ValueError("rational must be non-negative")
        return cls(numerator=value.numerator, denominator=value.denominator)

    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)


class LengthStratum(StrEnum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class E3cInventoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_case_id: str = Field(min_length=1)
    language: str = Field(pattern=r"^(en|fr|es)$")
    document_sha256: Sha256Hex
    codepoint_count: int = Field(gt=0)
    whitespace_token_count: int = Field(gt=0)
    sentence_count: int = Field(ge=0)
    annotation_counts: tuple[tuple[str, int], ...]
    total_annotation_density: Rational
    marker_counts: tuple[tuple[str, int], ...]
    marker_densities: tuple[tuple[str, Rational], ...]
    length_stratum: LengthStratum
    warnings: tuple[str, ...] = ()


def _stratum(token_count: int) -> LengthStratum:
    if token_count < 200:
        return LengthStratum.SHORT
    if token_count <= 400:
        return LengthStratum.MEDIUM
    return LengthStratum.LONG


def build_e3c_inventory_record(
    document: Document,
    annotation_set: SourceAnnotationSet,
    *,
    sentence_count: int,
) -> E3cInventoryRecord:
    token_count = len(document.text.split())
    if token_count == 0:
        raise ValueError("E3C document has no whitespace tokens")
    annotation_counts = Counter(
        annotation.source_type for annotation in annotation_set.annotations
    )
    factuality = 0
    negation = 0
    for annotation in annotation_set.annotations:
        if annotation.source_type != "EVENT":
            continue
        for attribute in annotation.attributes:
            if attribute.name in _FACTUALITY_ATTRIBUTES:
                factuality += 1
            if (
                attribute.name == "polarity"
                and attribute.value.casefold() in {"neg", "negative"}
            ):
                negation += 1
    marker_counts = {
        "bodypart": annotation_counts["BODYPART"],
        "factuality": factuality,
        "negation": negation,
    }
    return E3cInventoryRecord(
        source_case_id=document.source_case_id,
        language=document.language,
        document_sha256=document.document_sha256,
        codepoint_count=len(document.text),
        whitespace_token_count=token_count,
        sentence_count=sentence_count,
        annotation_counts=tuple(sorted(annotation_counts.items())),
        total_annotation_density=Rational.from_fraction(
            Fraction(sum(annotation_counts.values()) * 100, token_count)
        ),
        marker_counts=tuple(sorted(marker_counts.items())),
        marker_densities=tuple(
            (
                name,
                Rational.from_fraction(Fraction(count * 100, token_count)),
            )
            for name, count in sorted(marker_counts.items())
        ),
        length_stratum=_stratum(token_count),
    )

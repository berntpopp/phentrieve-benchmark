"""Deterministic split of the E3C inventory into four annotation groups.

Every report is annotated in exactly one language: German (machine-translated)
or its original language. Per source language, reports are sorted by length
stratum, annotation density, and a seeded hash; every fourth report, starting
at a seeded offset, goes to German. This spreads the German share evenly over
length and density without a search.
"""

from collections.abc import Iterable
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes
from phentrieve_benchmark.selection.e3c import canonical_e3c_inventory_bytes
from phentrieve_benchmark.selection.metrics import (
    E3cInventoryRecord,
    LengthStratum,
    Rational,
)

AnnotationLanguage = Literal["de", "en", "fr", "es"]
GROUP_SEED = "phentrieve-e3c-annotation-groups-v1"
_SOURCE_LANGUAGES: tuple[Literal["en", "fr", "es"], ...] = ("en", "fr", "es")
_STRATUM_ORDER = {
    LengthStratum.SHORT: 0,
    LengthStratum.MEDIUM: 1,
    LengthStratum.LONG: 2,
}
_GROUP_COUNT = 4


class AnnotationGroupRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_case_id: str = Field(min_length=1)
    source_language: Literal["en", "fr", "es"]
    annotation_language: AnnotationLanguage
    document_sha256: Sha256Hex
    length_stratum: LengthStratum
    total_annotation_density: Rational

    @model_validator(mode="after")
    def is_german_or_source(self) -> Self:
        if self.annotation_language not in {"de", self.source_language}:
            raise ValueError(
                "annotation language must be German or the source language"
            )
        return self


class AnnotationGroupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-annotation-groups/v1"] = "e3c-annotation-groups/v1"
    selection_id: Literal["e3c-annotation-groups-v1"] = "e3c-annotation-groups-v1"
    inventory_sha256: Sha256Hex
    algorithm_id: Literal["e3c-stratified-systematic/v1"] = (
        "e3c-stratified-systematic/v1"
    )
    selection_seed: str = GROUP_SEED
    records: tuple[AnnotationGroupRecord, ...]
    aggregate_sha256: Sha256Hex

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def case_ids(self, annotation_language: AnnotationLanguage) -> tuple[str, ...]:
        return tuple(
            sorted(
                record.source_case_id
                for record in self.records
                if record.annotation_language == annotation_language
            )
        )


def _seeded(value: str) -> bytes:
    return sha256(f"{GROUP_SEED}\0{value}".encode()).digest()


def load_e3c_inventory(payload: bytes) -> tuple[E3cInventoryRecord, ...]:
    return tuple(
        TypeAdapter(list[E3cInventoryRecord]).validate_json(payload, strict=True)
    )


def assign_annotation_groups(
    inventory: Iterable[E3cInventoryRecord],
) -> AnnotationGroupManifest:
    records = list(inventory)
    inventory_bytes = canonical_e3c_inventory_bytes(records)
    assigned: list[AnnotationGroupRecord] = []
    for language in _SOURCE_LANGUAGES:
        ordered = sorted(
            (record for record in records if record.language == language),
            key=lambda record: (
                _STRATUM_ORDER[record.length_stratum],
                record.total_annotation_density.fraction(),
                _seeded(record.source_case_id),
            ),
        )
        offset = int.from_bytes(_seeded(language), "big") % _GROUP_COUNT
        for index, record in enumerate(ordered):
            annotation_language: AnnotationLanguage = (
                "de" if index % _GROUP_COUNT == offset else language
            )
            assigned.append(
                AnnotationGroupRecord(
                    source_case_id=record.source_case_id,
                    source_language=language,
                    annotation_language=annotation_language,
                    document_sha256=record.document_sha256,
                    length_stratum=record.length_stratum,
                    total_annotation_density=record.total_annotation_density,
                )
            )
    output = tuple(
        sorted(
            assigned,
            key=lambda record: (record.source_language, record.source_case_id),
        )
    )
    aggregate = sha256_bytes(
        canonical_json_bytes([record.model_dump(mode="json") for record in output])
    )
    return AnnotationGroupManifest(
        inventory_sha256=sha256_bytes(inventory_bytes),
        records=output,
        aggregate_sha256=aggregate,
    )

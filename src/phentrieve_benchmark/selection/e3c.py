from collections.abc import Iterable
from fractions import Fraction
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes
from phentrieve_benchmark.selection.metrics import (
    E3cInventoryRecord,
    LengthStratum,
)

_LANGUAGE_ORDER = {"en": 0, "fr": 1, "es": 2}
_STRATUM_ORDER = {
    LengthStratum.SHORT: 0,
    LengthStratum.MEDIUM: 1,
    LengthStratum.LONG: 2,
}
_ALLOCATION = {
    LengthStratum.SHORT: 3,
    LengthStratum.MEDIUM: 4,
    LengthStratum.LONG: 3,
}
_ENTITY_TYPES = ("CLINENTITY", "EVENT", "ACTOR", "BODYPART", "TIMEX3", "RML")
_SEED = "phentrieve-e3c-de-feasibility-30-v1"


class E3cSelectionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    language: str
    stratum: LengthStratum
    source_case_id: str
    metrics: E3cInventoryRecord


class E3cSelectionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-selection-manifest/v1"] = (
        "e3c-selection-manifest/v1"
    )
    selection_id: Literal["e3c-de-feasibility-30-v1"] = (
        "e3c-de-feasibility-30-v1"
    )
    inventory_sha256: Sha256Hex
    algorithm_id: Literal["e3c-diversity-maximin/v1"] = (
        "e3c-diversity-maximin/v1"
    )
    selection_seed: str = _SEED
    overrides: tuple[object, ...] = ()
    records: tuple[E3cSelectionRecord, ...]
    aggregate_sha256: Sha256Hex

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))


def _feature_vector(record: E3cInventoryRecord) -> tuple[Fraction, ...]:
    counts = dict(record.annotation_counts)
    markers = {name: value.fraction() for name, value in record.marker_densities}
    tokens = record.whitespace_token_count
    densities = [
        Fraction(counts.get(name, 0) * 100, tokens) for name in _ENTITY_TYPES
    ]
    return (
        Fraction(tokens),
        record.total_annotation_density.fraction(),
        *densities,
        Fraction(len([value for value in counts.values() if value > 0])),
        markers.get("factuality", Fraction()),
        markers.get("negation", Fraction()),
        markers.get("bodypart", Fraction()),
    )


def _scaled_vectors(
    records: list[E3cInventoryRecord],
) -> dict[str, tuple[Fraction, ...]]:
    raw = {record.source_case_id: _feature_vector(record) for record in records}
    dimensions = len(next(iter(raw.values())))
    minima = [
        min(value[index] for value in raw.values())
        for index in range(dimensions)
    ]
    maxima = [
        max(value[index] for value in raw.values())
        for index in range(dimensions)
    ]
    return {
        identity: tuple(
            Fraction()
            if maxima[index] == minima[index]
            else (value - minima[index]) / (maxima[index] - minima[index])
            for index, value in enumerate(vector)
        )
        for identity, vector in raw.items()
    }


def _distance(
    first: tuple[Fraction, ...], second: tuple[Fraction, ...]
) -> Fraction:
    return sum(
        ((left - right) ** 2 for left, right in zip(first, second, strict=True)),
        start=Fraction(),
    )


def _tie_key(source_case_id: str) -> bytes:
    return sha256(f"{_SEED}\0{source_case_id}".encode()).digest()


def _select_group(
    records: list[E3cInventoryRecord], count: int
) -> list[E3cInventoryRecord]:
    if len(records) < count:
        raise ValueError("insufficient E3C cases in required stratum")
    vectors = _scaled_vectors(records)
    dimensions = len(next(iter(vectors.values())))
    centroid = tuple(
        sum((vector[index] for vector in vectors.values()), start=Fraction())
        / len(vectors)
        for index in range(dimensions)
    )
    by_id = {record.source_case_id: record for record in records}
    remaining = set(by_id)

    def choose(scores: dict[str, Fraction]) -> str:
        maximum = max(scores.values())
        return min(
            (identity for identity, score in scores.items() if score == maximum),
            key=_tie_key,
        )

    first = choose(
        {
            identity: _distance(vector, centroid)
            for identity, vector in vectors.items()
        }
    )
    selected = [first]
    remaining.remove(first)
    while len(selected) < count:
        candidate = choose(
            {
                identity: min(
                    _distance(vectors[identity], vectors[chosen])
                    for chosen in selected
                )
                for identity in remaining
            }
        )
        selected.append(candidate)
        remaining.remove(candidate)
    return [by_id[identity] for identity in selected]


def select_e3c_feasibility(
    inventory: Iterable[E3cInventoryRecord],
) -> E3cSelectionManifest:
    records = list(inventory)
    identities = [
        (record.language, record.source_case_id) for record in records
    ]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate E3C inventory identity")
    inventory_bytes = canonical_e3c_inventory_bytes(records)
    selected: list[E3cInventoryRecord] = []
    for language in ("en", "fr", "es"):
        for stratum in LengthStratum:
            group = [
                record
                for record in records
                if record.language == language
                and record.length_stratum is stratum
            ]
            selected.extend(_select_group(group, _ALLOCATION[stratum]))
    output_records = tuple(
        E3cSelectionRecord(
            language=record.language,
            stratum=record.length_stratum,
            source_case_id=record.source_case_id,
            metrics=record,
        )
        for record in sorted(
            selected,
            key=lambda item: (
                _LANGUAGE_ORDER[item.language],
                _STRATUM_ORDER[item.length_stratum],
                item.source_case_id,
            ),
        )
    )
    aggregate = sha256_bytes(
        canonical_json_bytes(
            [record.model_dump(mode="json") for record in output_records]
        )
    )
    return E3cSelectionManifest(
        inventory_sha256=sha256_bytes(inventory_bytes),
        records=output_records,
        aggregate_sha256=aggregate,
    )


def canonical_e3c_inventory_bytes(
    inventory: Iterable[E3cInventoryRecord],
) -> bytes:
    records = list(inventory)
    identities = [
        (record.language, record.source_case_id) for record in records
    ]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate E3C inventory identity")
    return canonical_json_bytes(
        [
            record.model_dump(mode="json")
            for record in sorted(
                records,
                key=lambda item: (item.language, item.source_case_id),
            )
        ]
    )

import json
from fractions import Fraction

import pytest

from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.e3c import canonical_e3c_inventory_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    assign_annotation_groups,
    load_e3c_inventory,
)
from phentrieve_benchmark.selection.metrics import (
    E3cInventoryRecord,
    LengthStratum,
    Rational,
)

_PREFIX = {"en": "EN", "fr": "FR", "es": "ES"}


def _record(language: str, stratum: LengthStratum, index: int) -> E3cInventoryRecord:
    tokens = {
        LengthStratum.SHORT: 100,
        LengthStratum.MEDIUM: 300,
        LengthStratum.LONG: 500,
    }[stratum] + index
    case_id = f"{_PREFIX[language]}{stratum.value}{index:02d}"
    return E3cInventoryRecord(
        source_case_id=case_id,
        language=language,
        document_sha256=sha256_bytes(case_id.encode()),
        codepoint_count=tokens * 4,
        whitespace_token_count=tokens,
        sentence_count=1,
        annotation_counts=(("EVENT", index + 1),),
        total_annotation_density=Rational.from_fraction(
            Fraction((index + 1) * 100, tokens)
        ),
        marker_counts=(),
        marker_densities=(),
        length_stratum=stratum,
        warnings=(),
    )


def _inventory(per_stratum: int = 7) -> list[E3cInventoryRecord]:
    return [
        _record(language, stratum, index)
        for language in ("en", "fr", "es")
        for stratum in LengthStratum
        for index in range(per_stratum)
    ]


def test_split_is_deterministic_and_order_independent() -> None:
    records = _inventory()
    first = assign_annotation_groups(records)
    second = assign_annotation_groups(list(reversed(records)))
    assert first.canonical_bytes() == second.canonical_bytes()


def test_every_report_is_assigned_exactly_once() -> None:
    records = _inventory()
    manifest = assign_annotation_groups(records)
    assert len(manifest.records) == len(records)
    assert {record.source_case_id for record in manifest.records} == {
        record.source_case_id for record in records
    }


def test_about_a_quarter_of_each_language_goes_to_german() -> None:
    manifest = assign_annotation_groups(_inventory())
    for language in ("en", "fr", "es"):
        german = [
            record
            for record in manifest.records
            if record.source_language == language and record.annotation_language == "de"
        ]
        assert len(german) in {21 // 4, 21 // 4 + 1}
        source = [
            record
            for record in manifest.records
            if record.source_language == language
            and record.annotation_language == language
        ]
        assert len(source) == 21 - len(german)


def test_german_share_covers_every_length_stratum() -> None:
    manifest = assign_annotation_groups(_inventory())
    for language in ("en", "fr", "es"):
        for stratum in LengthStratum:
            assert any(
                record.source_language == language
                and record.length_stratum is stratum
                and record.annotation_language == "de"
                for record in manifest.records
            )


def test_manifest_binds_the_inventory_and_lists_group_case_ids() -> None:
    records = _inventory()
    manifest = assign_annotation_groups(records)
    assert manifest.inventory_sha256 == sha256_bytes(
        canonical_e3c_inventory_bytes(records)
    )
    german = manifest.case_ids("de")
    assert german == tuple(sorted(german))
    assert len(german) + sum(
        len(manifest.case_ids(language)) for language in ("en", "fr", "es")
    ) == len(records)


def test_duplicate_inventory_identity_is_rejected() -> None:
    record = _record("en", LengthStratum.SHORT, 0)
    with pytest.raises(ValueError, match="duplicate"):
        assign_annotation_groups([record, record])


def test_annotation_language_must_be_german_or_source() -> None:
    manifest = assign_annotation_groups(_inventory())
    payload = manifest.model_dump(mode="json")
    payload["records"][0]["annotation_language"] = (
        "fr" if payload["records"][0]["source_language"] != "fr" else "en"
    )
    with pytest.raises(ValueError, match="German or the source language"):
        AnnotationGroupManifest.model_validate_json(json.dumps(payload), strict=True)


def test_inventory_round_trips_from_canonical_bytes() -> None:
    records = _inventory()
    loaded = load_e3c_inventory(canonical_e3c_inventory_bytes(records))
    assert {record.source_case_id for record in loaded} == {
        record.source_case_id for record in records
    }

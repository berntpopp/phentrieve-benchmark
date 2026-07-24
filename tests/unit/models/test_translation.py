from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.translation import (
    TranslationCheck,
    TranslationManifest,
    TranslationRecord,
    TranslationStatus,
)


def _record_values() -> dict[str, object]:
    return {
        "translation_id": "e3c-google-nmt-EN101318-r1",
        "selection_id": "e3c-de-feasibility-30-v1",
        "source_case_id": "EN101318",
        "source_language": "en",
        "target_language": "de",
        "source_sha256": "a" * 64,
        "translation_sha256": "b" * 64,
        "provider": "google-cloud-translation",
        "api_version": "v3",
        "model": "general/nmt",
        "project_id": "benchmark-project",
        "location": "global",
        "created_at": datetime(2026, 7, 24, tzinfo=UTC),
        "input_codepoints": 601,
        "output_codepoints": 640,
        "price_per_million_input_characters": Decimal("20"),
        "estimated_max_cost": Decimal("0.01202"),
        "previous_translation_id": None,
        "status": TranslationStatus.TRANSLATED,
        "checks": (),
    }


def test_translation_record_is_text_free_and_serializes_exact_money() -> None:
    record = TranslationRecord(**_record_values())

    payload = record.model_dump(mode="json")

    assert "text" not in payload
    assert payload["estimated_max_cost"] == "0.01202"


def test_ready_record_rejects_failed_check() -> None:
    values = {
        **_record_values(),
        "status": TranslationStatus.READY_FOR_REVIEW,
        "checks": (TranslationCheck(code="target_language_de", passed=False),),
    }

    with pytest.raises(ValidationError, match="ready_for_review"):
        TranslationRecord(**values)


def test_manifest_rejects_duplicate_cases() -> None:
    record = TranslationRecord(**_record_values())

    with pytest.raises(ValidationError, match="duplicate"):
        TranslationManifest(
            selection_id="e3c-de-feasibility-30-v1",
            selection_sha256="c" * 64,
            recipe_sha256="d" * 64,
            records=(record, record),
        )


def test_translation_manifest_round_trips_through_canonical_json() -> None:
    manifest = TranslationManifest(
        selection_id="e3c-de-feasibility-30-v1",
        selection_sha256="c" * 64,
        recipe_sha256="d" * 64,
        records=(TranslationRecord(**_record_values()),),
    )

    restored = TranslationManifest.model_validate_json(
        manifest.canonical_bytes(), strict=True
    )

    assert restored == manifest

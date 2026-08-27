from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.translation import (
    TranslationCheck,
    TranslationManifest,
    TranslationRecord,
    TranslationStatus,
)
from phentrieve_benchmark.translation.recheck import recheck_translations


def _manifest(
    store: ArtifactStore,
    *,
    source: str,
    translation: str,
    status: TranslationStatus,
    checks: tuple[TranslationCheck, ...],
) -> TranslationManifest:
    record = TranslationRecord(
        translation_id="e3c-de-feasibility-30-google-nmt-v1-EN101318-abc",
        selection_id="e3c-de-feasibility-30-v1",
        source_case_id="EN101318",
        source_language="en",
        target_language="de",
        source_sha256=store.put_bytes(source.encode("utf-8")),
        translation_sha256=store.put_bytes(translation.encode("utf-8")),
        provider="google-cloud-translation",
        api_version="v3",
        model="general/nmt",
        project_id="phentrieve",
        location="global",
        created_at=datetime(2026, 7, 27, tzinfo=UTC),
        input_codepoints=len(source),
        output_codepoints=len(translation),
        price_per_million_input_characters=Decimal("20"),
        estimated_max_cost=Decimal("0"),
        status=status,
        checks=checks,
    )
    return TranslationManifest(
        selection_id="e3c-de-feasibility-30-v1",
        selection_sha256="a" * 64,
        recipe_sha256="b" * 64,
        records=(record,),
    )


def _stale_failure() -> tuple[TranslationCheck, ...]:
    return (
        TranslationCheck(code="nonempty_output", passed=True),
        TranslationCheck(code="numbers_preserved", passed=False),
    )


def test_recheck_clears_a_verdict_the_removed_checks_produced(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    manifest = _manifest(
        store,
        source="Sodium Valproate 200mg once a day for 2 weeks.",
        translation="Natriumvalproat 200 mg einmal täglich für zwei Wochen.",
        status=TranslationStatus.AUTOMATIC_CHECK_FAILED,
        checks=_stale_failure(),
    )

    result = recheck_translations(
        manifest=manifest, store=store, language_detector=lambda _: "de"
    )
    record = result.manifest.records[0]

    assert result.changed_case_ids == ("EN101318",)
    assert result.failed_case_ids == ()
    assert record.status is TranslationStatus.READY_FOR_REVIEW
    assert {item.code for item in record.checks} == {
        "nonempty_output",
        "source_changed",
        "length_ratio",
        "units_added",
        "target_language_de",
    }


def test_recheck_flags_an_invented_unit(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    manifest = _manifest(
        store,
        source="Alfa-Feto-Proteina: 38,2 y Beta-HGC de 1,48.",
        translation="Alpha-Fetoprotein 38,2 mg/dl und Beta-hCG 1,48 mg/dl.",
        status=TranslationStatus.READY_FOR_REVIEW,
        checks=(TranslationCheck(code="nonempty_output", passed=True),),
    )

    result = recheck_translations(
        manifest=manifest, store=store, language_detector=lambda _: "de"
    )
    record = result.manifest.records[0]
    units = next(
        item for item in record.checks if item.code == "units_added"
    )

    assert result.failed_case_ids == ("EN101318",)
    assert record.status is TranslationStatus.AUTOMATIC_CHECK_FAILED
    assert not units.passed
    assert units.detail == "mg"


def test_recheck_preserves_identity_and_provider_metadata(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    manifest = _manifest(
        store,
        source="The patient had fever.",
        translation="Der Patient hatte Fieber.",
        status=TranslationStatus.AUTOMATIC_CHECK_FAILED,
        checks=_stale_failure(),
    )
    before = manifest.records[0]

    after = recheck_translations(
        manifest=manifest, store=store, language_detector=lambda _: "de"
    ).manifest.records[0]

    assert after.translation_id == before.translation_id
    assert after.source_sha256 == before.source_sha256
    assert after.translation_sha256 == before.translation_sha256
    assert after.created_at == before.created_at
    assert after.estimated_max_cost == before.estimated_max_cost


def test_recheck_does_not_revoke_a_human_verdict(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    manifest = _manifest(
        store,
        source="Alfa-Feto-Proteina: 38,2.",
        translation="Alpha-Fetoprotein 38,2 mg/dl.",
        status=TranslationStatus.ACCEPTED,
        checks=(TranslationCheck(code="nonempty_output", passed=True),),
    )

    result = recheck_translations(
        manifest=manifest, store=store, language_detector=lambda _: "de"
    )
    record = result.manifest.records[0]

    assert record.status is TranslationStatus.ACCEPTED
    assert result.failed_case_ids == ("EN101318",)


def test_recheck_reports_no_change_when_verdicts_already_current(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    manifest = _manifest(
        store,
        source="The patient had fever.",
        translation="Der Patient hatte Fieber.",
        status=TranslationStatus.AUTOMATIC_CHECK_FAILED,
        checks=_stale_failure(),
    )
    current = recheck_translations(
        manifest=manifest, store=store, language_detector=lambda _: "de"
    ).manifest

    again = recheck_translations(
        manifest=current, store=store, language_detector=lambda _: "de"
    )

    assert not again.changed
    assert again.manifest == current

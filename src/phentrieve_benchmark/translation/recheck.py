"""Re-evaluate stored translations against the current automatic checks.

Check definitions change; the translated text does not. Re-running the checks
over the artifacts already in the store keeps the recorded verdict in step with
the current definitions without contacting the provider or spending anything.
"""

from collections.abc import Callable
from dataclasses import dataclass

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.translation import (
    TranslationManifest,
    TranslationRecord,
    TranslationStatus,
)
from phentrieve_benchmark.translation.checks import check_translation

# Verdicts a person owns. An automatic re-run records findings but must not
# revoke or manufacture a human decision.
_MANUAL_STATUSES = frozenset(
    {
        TranslationStatus.REVIEWED,
        TranslationStatus.ACCEPTED,
    }
)


@dataclass(frozen=True)
class RecheckResult:
    manifest: TranslationManifest
    changed_case_ids: tuple[str, ...]
    failed_case_ids: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return bool(self.changed_case_ids)


def recheck_translations(
    *,
    manifest: TranslationManifest,
    store: ArtifactStore,
    language_detector: Callable[[str], str | None],
) -> RecheckResult:
    records: list[TranslationRecord] = []
    changed: list[str] = []
    failed: list[str] = []

    for record in sorted(manifest.records, key=lambda item: item.source_case_id):
        source_text = store.read_bytes(record.source_sha256).decode("utf-8")
        translated_text = store.read_bytes(record.translation_sha256).decode(
            "utf-8"
        )
        checks = check_translation(
            source_text=source_text,
            translated_text=translated_text,
            detected_language=language_detector(translated_text),
        )
        passed = all(check.passed for check in checks)
        if record.status in _MANUAL_STATUSES:
            status = record.status
        else:
            status = (
                TranslationStatus.READY_FOR_REVIEW
                if passed
                else TranslationStatus.AUTOMATIC_CHECK_FAILED
            )
        if not passed:
            failed.append(record.source_case_id)
        updated = record.model_copy(update={"status": status, "checks": checks})
        if updated != record:
            changed.append(record.source_case_id)
        records.append(updated)

    return RecheckResult(
        manifest=manifest.model_copy(update={"records": tuple(records)}),
        changed_case_ids=tuple(changed),
        failed_case_ids=tuple(failed),
    )

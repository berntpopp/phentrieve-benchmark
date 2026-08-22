from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.translation import (
    TranslationManifest,
    TranslationRecord,
    TranslationStatus,
)
from phentrieve_benchmark.provenance.canonical import canonical_text_bytes
from phentrieve_benchmark.translation.checks import check_translation
from phentrieve_benchmark.translation.google_nmt import TranslationProvider
from phentrieve_benchmark.translation.pricing import (
    E3cTranslationRecipe,
    estimate_google_nmt,
)


@dataclass(frozen=True)
class TranslationInput:
    document: Document
    expected_source_sha256: str


@dataclass(frozen=True)
class E3cTranslationResult:
    manifest: TranslationManifest
    translated_case_ids: tuple[str, ...]
    failed_case_ids: tuple[str, ...]
    reused_case_ids: tuple[str, ...]


def is_reusable_translation(
    record: TranslationRecord,
    *,
    item: TranslationInput,
    recipe: E3cTranslationRecipe,
    project_id: str,
) -> bool:
    return (
        record.status
        in {
            TranslationStatus.READY_FOR_REVIEW,
            TranslationStatus.REVIEWED,
            TranslationStatus.ACCEPTED,
        }
        and record.source_sha256 == item.expected_source_sha256
        and record.source_language == item.document.language
        and record.target_language == recipe.target_language
        and record.provider == recipe.provider
        and record.api_version == recipe.api_version
        and record.model == recipe.model
        and record.project_id == project_id
        and record.location == recipe.location
    )


def translate_documents(
    *,
    inputs: tuple[TranslationInput, ...],
    provider: TranslationProvider,
    store: ArtifactStore,
    recipe: E3cTranslationRecipe,
    selection_sha256: str,
    project_id: str,
    created_at: datetime,
    language_detector: Callable[[str], str | None],
    previous_manifest: TranslationManifest | None = None,
    recipe_sha256: str = "0" * 64,
) -> E3cTranslationResult:
    previous = (
        {record.source_case_id: record for record in previous_manifest.records}
        if previous_manifest is not None
        else {}
    )
    records: list[TranslationRecord] = []
    translated: list[str] = []
    failed: list[str] = []
    reused: list[str] = []
    seen: set[str] = set()

    for item in sorted(
        inputs,
        key=lambda value: (
            value.document.language,
            value.document.source_case_id,
        ),
    ):
        document = item.document
        if document.source_case_id in seen:
            raise ValueError("duplicate selected E3C case")
        seen.add(document.source_case_id)
        if document.document_sha256 != item.expected_source_sha256:
            raise ValueError(f"document hash mismatch for {document.source_case_id}")
        old = previous.get(document.source_case_id)
        if old is not None and is_reusable_translation(
            old, item=item, recipe=recipe, project_id=project_id
        ):
            store.read_bytes(old.source_sha256)
            store.read_bytes(old.translation_sha256)
            if old.selection_id == recipe.selection_id:
                records.append(old)
            else:
                records.append(
                    old.model_copy(
                        update={
                            "translation_id": (
                                f"{recipe.translation_id}-"
                                f"{document.source_case_id}-"
                                f"{old.translation_sha256[:12]}"
                            ),
                            "selection_id": recipe.selection_id,
                            "previous_translation_id": old.translation_id,
                        }
                    )
                )
            reused.append(document.source_case_id)
            continue

        source_sha256 = store.put_bytes(canonical_text_bytes(document.text))
        translated_value = provider.translate(
            document.text,
            source_language=document.language,  # type: ignore[arg-type]
            target_language="de",
        )
        translated_bytes = canonical_text_bytes(translated_value.text)
        translation_sha256 = store.put_bytes(translated_bytes)
        checks = check_translation(
            source_text=document.text,
            translated_text=translated_value.text,
            detected_language=language_detector(translated_value.text),
        )
        status = (
            TranslationStatus.READY_FOR_REVIEW
            if all(check.passed for check in checks)
            else TranslationStatus.AUTOMATIC_CHECK_FAILED
        )
        estimate = estimate_google_nmt(len(document.text), recipe.pricing).upper_bound
        records.append(
            TranslationRecord(
                translation_id=(
                    f"{recipe.translation_id}-{document.source_case_id}-"
                    f"{translation_sha256[:12]}"
                ),
                selection_id=recipe.selection_id,
                source_case_id=document.source_case_id,
                source_language=document.language,  # type: ignore[arg-type]
                target_language="de",
                source_sha256=source_sha256,
                translation_sha256=translation_sha256,
                provider="google-cloud-translation",
                api_version="v3",
                model=recipe.model,
                project_id=project_id,
                location=recipe.location,
                created_at=created_at,
                input_codepoints=len(document.text),
                output_codepoints=len(translated_value.text),
                price_per_million_input_characters=(
                    recipe.pricing.price_per_million_input_characters
                ),
                estimated_max_cost=estimate,
                previous_translation_id=(
                    old.translation_id if old is not None else None
                ),
                status=status,
                checks=checks,
            )
        )
        translated.append(document.source_case_id)
        if status is TranslationStatus.AUTOMATIC_CHECK_FAILED:
            failed.append(document.source_case_id)

    manifest = TranslationManifest(
        selection_id=recipe.selection_id,
        selection_sha256=selection_sha256,
        recipe_sha256=recipe_sha256,
        records=tuple(records),
    )
    return E3cTranslationResult(
        manifest=manifest,
        translated_case_ids=tuple(translated),
        failed_case_ids=tuple(failed),
        reused_case_ids=tuple(reused),
    )

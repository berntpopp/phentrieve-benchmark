from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.translation import (
    TranslationManifest,
    TranslationRecord,
)
from phentrieve_benchmark.models.translation_review import (
    TranslationReviewExport,
    TranslationReviewExportCase,
)
from phentrieve_benchmark.review.translation_workbook import (
    WorkbookCase,
    write_review_workbook,
)


def _records_by_case(
    manifest: TranslationManifest,
    *,
    model: str,
    variant: str,
) -> dict[str, TranslationRecord]:
    if not manifest.records:
        raise ValueError(f"{variant} translation manifest has no cases")
    if any(record.selection_id != manifest.selection_id for record in manifest.records):
        raise ValueError(f"{variant} records do not match the manifest selection ID")
    if any(record.model != model for record in manifest.records):
        raise ValueError(f"{variant} manifest contains the wrong translation model")
    return {record.source_case_id: record for record in manifest.records}


def _validate_nmt_manifest(
    tllm_manifest: TranslationManifest,
    nmt_manifest: TranslationManifest,
    *,
    tllm_records: dict[str, TranslationRecord],
) -> dict[str, TranslationRecord]:
    if nmt_manifest.selection_id != tllm_manifest.selection_id:
        raise ValueError("TLLM and NMT manifests have different selection IDs")
    nmt_records = _records_by_case(nmt_manifest, model="general/nmt", variant="NMT")
    if nmt_records.keys() != tllm_records.keys():
        raise ValueError("TLLM and NMT manifests have different case sets")
    for case_id, tllm_record in tllm_records.items():
        nmt_record = nmt_records[case_id]
        if nmt_record.source_sha256 != tllm_record.source_sha256:
            raise ValueError("TLLM and NMT manifests have different source hashes")
        if nmt_record.source_language != tllm_record.source_language:
            raise ValueError("TLLM and NMT manifests have different source languages")
    return nmt_records


def export_translation_review(
    *,
    store: ArtifactStore,
    tllm_manifest: TranslationManifest,
    destination: Path,
    review_policy_id: str,
    nmt_manifest: TranslationManifest | None = None,
) -> str:
    """Store a canonical review export and write its Excel review workbook."""
    tllm_records = _records_by_case(
        tllm_manifest,
        model="general/translation-llm",
        variant="TLLM",
    )
    nmt_records = (
        _validate_nmt_manifest(
            tllm_manifest,
            nmt_manifest,
            tllm_records=tllm_records,
        )
        if nmt_manifest is not None
        else None
    )

    export_cases: list[TranslationReviewExportCase] = []
    workbook_cases: list[WorkbookCase] = []
    for tllm_record in sorted(
        tllm_records.values(),
        key=lambda record: (record.source_language, record.source_case_id),
    ):
        source_text = store.read_bytes(tllm_record.source_sha256).decode("utf-8")
        tllm_text = store.read_bytes(tllm_record.translation_sha256).decode("utf-8")
        nmt_record = (
            nmt_records[tllm_record.source_case_id] if nmt_records is not None else None
        )
        nmt_text = None
        if nmt_record is not None:
            store.read_bytes(nmt_record.source_sha256)
            nmt_text = store.read_bytes(nmt_record.translation_sha256).decode("utf-8")
        export_cases.append(
            TranslationReviewExportCase(
                source_case_id=tllm_record.source_case_id,
                source_language=tllm_record.source_language,
                source_text_sha256=tllm_record.source_sha256,
                tllm_text_sha256=tllm_record.translation_sha256,
                nmt_text_sha256=(
                    nmt_record.translation_sha256 if nmt_record is not None else None
                ),
            )
        )
        workbook_cases.append(
            WorkbookCase(
                source_case_id=tllm_record.source_case_id,
                source_language=tllm_record.source_language,
                source_text=source_text,
                tllm_text=tllm_text,
                nmt_text=nmt_text,
            )
        )

    export = TranslationReviewExport(
        selection_id=tllm_manifest.selection_id,
        review_policy_id=review_policy_id,
        nmt_recipe_sha256=(
            nmt_manifest.recipe_sha256 if nmt_manifest is not None else None
        ),
        cases=tuple(export_cases),
    )
    export_sha256 = store.put_bytes(export.canonical_bytes())
    write_review_workbook(destination, export, tuple(workbook_cases))
    return export_sha256

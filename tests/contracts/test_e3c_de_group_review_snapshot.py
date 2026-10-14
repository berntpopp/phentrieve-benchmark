import csv
from pathlib import Path

from phentrieve_benchmark.models.translation import TranslationManifest
from phentrieve_benchmark.models.translation_review import (
    TranslationReviewDecision,
    TranslationReviewDiff,
    TranslationReviewExport,
    TranslationReviewImportManifest,
    TranslationReviewRecord,
)
from phentrieve_benchmark.pipeline.translation_review import unified_text_diff
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import AnnotationGroupManifest

ROOT = Path(__file__).parents[2]
GROUPS_PATH = ROOT / "datasets/e3c-de/selections/e3c-annotation-groups-v1.json"
TLLM_SNAPSHOT = ROOT / "datasets/e3c-de/translations/e3c-de-full-246-google-tllm-v1"
REVIEW_SNAPSHOT = ROOT / "datasets/e3c-de/translations/e3c-de-group-61-review-v1"
EXPORT_SHA256 = (
    "ce2736cfbfe17d96b59b2f74e4b10e61b71a722a3ae82803051c6287077af652"
)
IMPORT_SHA256 = (
    "c83c4bb7f8fcca845a16f253f6a3821055f0946eb1130f055c910470f146ceb4"
)


def test_e3c_de_group_review_snapshot_preserves_full_provenance_chain() -> None:
    groups = AnnotationGroupManifest.model_validate_json(
        GROUPS_PATH.read_bytes(), strict=True
    )
    de_case_ids = set(groups.case_ids("de"))
    assert len(de_case_ids) == 61

    tllm_manifest = TranslationManifest.model_validate_json(
        (TLLM_SNAPSHOT / "manifest.json").read_bytes(), strict=True
    )
    tllm_by_case = {r.source_case_id: r for r in tllm_manifest.records}

    export_bytes = (REVIEW_SNAPSHOT / "export.json").read_bytes()
    assert sha256_bytes(export_bytes) == EXPORT_SHA256
    export = TranslationReviewExport.model_validate_json(export_bytes, strict=True)
    assert {c.source_case_id for c in export.cases} == de_case_ids

    import_bytes = (REVIEW_SNAPSHOT / "import-manifest.json").read_bytes()
    assert sha256_bytes(import_bytes) == IMPORT_SHA256
    import_manifest = TranslationReviewImportManifest.model_validate_json(
        import_bytes, strict=True
    )
    assert import_manifest.export_sha256 == EXPORT_SHA256
    assert len(import_manifest.entries) == 61

    with (REVIEW_SNAPSHOT / "index.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = tuple(csv.DictReader(stream))
    assert len(rows) == 61
    rows_by_case = {row["source_case_id"]: row for row in rows}
    assert set(rows_by_case) == de_case_ids

    unchanged_count = 0
    edited_count = 0

    for entry in import_manifest.entries:
        case_id = entry.source_case_id
        row = rows_by_case[case_id]
        tllm_record = tllm_by_case[case_id]

        translation_bytes = (REVIEW_SNAPSHOT / row["translation_path"]).read_bytes()
        assert sha256_bytes(translation_bytes) == entry.proposed_text_sha256
        assert row["proposed_text_sha256"] == entry.proposed_text_sha256

        record_bytes = (REVIEW_SNAPSHOT / row["record_path"]).read_bytes()
        assert sha256_bytes(record_bytes) == entry.record_sha256
        record = TranslationReviewRecord.model_validate_json(
            record_bytes, strict=True
        )
        assert record.source_case_id == case_id
        assert record.export_sha256 == EXPORT_SHA256
        assert record.source_text_sha256 == tllm_record.source_sha256
        assert record.tllm_text_sha256 == tllm_record.translation_sha256
        assert record.proposed_text_sha256 == entry.proposed_text_sha256

        review_record_bytes = canonical_json_bytes(
            record.review_record().model_dump(mode="json")
        )
        assert sha256_bytes(review_record_bytes) == entry.review_record_sha256

        diff_bytes = (REVIEW_SNAPSHOT / row["diff_path"]).read_bytes()
        assert sha256_bytes(diff_bytes) == entry.diff_sha256
        diff = TranslationReviewDiff.model_validate_json(diff_bytes, strict=True)

        raw_tllm_text = (
            TLLM_SNAPSHOT / f"{case_id}.translation.de.txt"
        ).read_text(encoding="utf-8")
        proposed_text = translation_bytes.decode("utf-8")
        expected_diff = unified_text_diff(raw_tllm_text, proposed_text)
        assert diff == expected_diff

        if record.decision is TranslationReviewDecision.ACCEPTED_UNCHANGED:
            unchanged_count += 1
            assert diff.payload == ""
            assert entry.proposed_text_sha256 == tllm_record.translation_sha256
        elif record.decision is TranslationReviewDecision.ACCEPTED_CORRECTED:
            edited_count += 1
            assert diff.payload != ""
            assert entry.proposed_text_sha256 != tllm_record.translation_sha256

    assert unchanged_count == 35
    assert edited_count == 26
    assert (REVIEW_SNAPSHOT / "README.md").is_file()

import csv
import json
from pathlib import Path

from phentrieve_benchmark.models.translation import TranslationManifest
from phentrieve_benchmark.provenance.digests import sha256_bytes

ROOT = Path(__file__).parents[2]
SNAPSHOT = (
    ROOT
    / "datasets/e3c-de/translations/e3c-de-full-246-google-tllm-v1"
)
MANIFEST_SHA256 = (
    "759f00260dab85a3fbeb24204683f790b4b14a18759c2bb80910ff1725b4451a"
)


def test_full_tllm_snapshot_preserves_the_published_view() -> None:
    manifest_bytes = (SNAPSHOT / "manifest.json").read_bytes()
    assert sha256_bytes(manifest_bytes) == MANIFEST_SHA256
    manifest = TranslationManifest.model_validate_json(
        manifest_bytes, strict=True
    )
    assert manifest.selection_id == "e3c-de-full-246-v1"
    assert len(manifest.records) == 246

    marker = json.loads(
        (SNAPSHOT / ".phentrieve-translation-view.json").read_text(
            encoding="utf-8"
        )
    )
    assert marker["manifest_sha256"] == MANIFEST_SHA256

    with (SNAPSHOT / "index.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = tuple(csv.DictReader(stream))
    assert len(rows) == 246
    by_case = {row["source_case_id"]: row for row in rows}
    assert len(by_case) == 246

    for record in manifest.records:
        row = by_case[record.source_case_id]
        source = SNAPSHOT / row["source_path"]
        translation = SNAPSHOT / row["translation_path"]
        assert sha256_bytes(source.read_bytes()) == record.source_sha256
        assert (
            sha256_bytes(translation.read_bytes())
            == record.translation_sha256
        )

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.translation import (
    TranslationCheck,
    TranslationManifest,
    TranslationRecord,
    TranslationStatus,
)
from phentrieve_benchmark.translation.view import (
    materialize_published_translation_view,
    materialize_translation_view,
)


def _manifest(store: ArtifactStore) -> TranslationManifest:
    source = store.put_bytes(b"The patient had fever.\n")
    translated = store.put_bytes(b"Der Patient hatte Fieber.\n")
    record = TranslationRecord(
        translation_id="translation-1",
        selection_id="selection-1",
        source_case_id="EN000001",
        source_language="en",
        target_language="de",
        source_sha256=source,
        translation_sha256=translated,
        provider="google-cloud-translation",
        api_version="v3",
        model="general/nmt",
        project_id="phentrieve",
        location="global",
        created_at=datetime(2026, 7, 27, tzinfo=UTC),
        input_codepoints=23,
        output_codepoints=25,
        price_per_million_input_characters=Decimal("20"),
        estimated_max_cost=Decimal("0.00046"),
        status=TranslationStatus.AUTOMATIC_CHECK_FAILED,
        checks=(TranslationCheck(code="numbers_preserved", passed=False),),
    )
    return TranslationManifest(
        selection_id="selection-1",
        selection_sha256="a" * 64,
        recipe_sha256="b" * 64,
        records=(record,),
    )


def test_materializes_flat_readable_view(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    destination = tmp_path / "views" / "e3c-de"

    result = materialize_translation_view(
        manifest=_manifest(store), store=store, destination=destination
    )

    assert result.case_count == 1
    assert (destination / "EN000001.source.en.txt").read_text() == (
        "The patient had fever.\n"
    )
    assert (destination / "EN000001.translation.de.txt").read_text() == (
        "Der Patient hatte Fieber.\n"
    )
    index = (destination / "index.csv").read_text()
    assert "source_case_id,source_language" in index
    assert "EN000001,en" in index
    assert "numbers_preserved" in index


def test_refuses_to_replace_unowned_directory(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    destination = tmp_path / "views" / "e3c-de"
    destination.mkdir(parents=True)
    (destination / "personal.txt").write_text("keep")

    with pytest.raises(ValueError, match="not a generated translation view"):
        materialize_translation_view(
            manifest=_manifest(store), store=store, destination=destination
        )


def test_published_view_selects_the_variant_and_directory(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    manifest = _manifest(store)
    digest = store.put_bytes(manifest.canonical_bytes())
    state = tmp_path / "state" / "translate" / "e3c"
    state.mkdir(parents=True)
    (state / "pointer.json").write_text(
        '{"schema_version":"stage-pointer/v1",'
        '"subject_role":"translation_manifest",'
        f'"subject_sha256":"{digest}",'
        f'"semantic_hashes":{{"recipe_sha256":"{"c" * 64}"}}}}'
    )

    result = materialize_published_translation_view(
        artifact_root=tmp_path,
        store=store,
        recipe_sha256="b" * 64,
        variant="tllm",
    )

    assert result.case_count == 1
    assert result.destination == (tmp_path / "views" / "e3c-de-tllm").resolve()
    assert (result.destination / "EN000001.translation.de.txt").is_file()

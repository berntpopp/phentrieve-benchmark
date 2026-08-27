import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.models.translation import (
    TranslationCheck,
    TranslationManifest,
    TranslationRecord,
    TranslationStatus,
)
from phentrieve_benchmark.pipeline.state import StageState
from phentrieve_benchmark.translation.variants import (
    resolve_translation_pointer,
    translation_recipe_path,
    translation_view_destination,
)


def _manifest(
    store: ArtifactStore,
    *,
    recipe_sha256: str,
    project_id: str = "phentrieve",
    identity: str = "default",
) -> str:
    source = store.put_bytes(b"The patient had fever.\n")
    translated = store.put_bytes(b"Der Patient hatte Fieber.\n")
    manifest = TranslationManifest(
        selection_id="selection-1",
        selection_sha256="a" * 64,
        recipe_sha256=recipe_sha256,
        records=(
            TranslationRecord(
                translation_id=f"translation-{recipe_sha256[:4]}-{identity}",
                selection_id="selection-1",
                source_case_id="EN000001",
                source_language="en",
                target_language="de",
                source_sha256=source,
                translation_sha256=translated,
                provider="google-cloud-translation",
                api_version="v3",
                model="general/nmt",
                project_id=project_id,
                location="global",
                created_at=datetime(2026, 7, 27, tzinfo=UTC),
                input_codepoints=23,
                output_codepoints=25,
                price_per_million_input_characters=Decimal("20"),
                estimated_max_cost=Decimal("0.00046"),
                status=TranslationStatus.READY_FOR_REVIEW,
                checks=(TranslationCheck(code="nonempty_output", passed=True),),
            ),
        ),
    )
    return store.put_bytes(manifest.canonical_bytes())


def test_recipe_path_and_view_destination_per_variant(tmp_path: Path) -> None:
    assert translation_recipe_path(tmp_path, "nmt") == (
        tmp_path / "e3c-de" / "translation.yaml"
    )
    assert translation_recipe_path(tmp_path, "tllm") == (
        tmp_path / "e3c-de" / "translation-llm.yaml"
    )
    assert translation_recipe_path(tmp_path, "tllm-full") == (
        tmp_path / "e3c-de" / "translation-llm-full.yaml"
    )
    assert translation_view_destination(tmp_path, "nmt") == (
        tmp_path / "views" / "e3c-de-nmt"
    )
    assert translation_view_destination(tmp_path, "tllm") == (
        tmp_path / "views" / "e3c-de-tllm"
    )
    assert translation_view_destination(tmp_path, "tllm-full") == (
        tmp_path / "views" / "e3c-de-tllm-full"
    )


def test_unknown_variant_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown translation variant"):
        translation_recipe_path(tmp_path, "gemini")
    with pytest.raises(ValueError, match="unknown translation variant"):
        translation_view_destination(tmp_path, "gemini")


def test_resolver_picks_the_pointer_matching_the_recipe(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    state = StageState(tmp_path / "state", store)
    first = _manifest(store, recipe_sha256="1" * 64)
    second = _manifest(store, recipe_sha256="2" * 64)
    for subject, key in ((first, "3" * 64), (second, "4" * 64)):
        state.publish(
            stage="translate",
            target="e3c",
            subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
            subject_sha256=subject,
            semantic_hashes={"recipe_sha256": key},
        )

    pointer = resolve_translation_pointer(
        artifact_root=tmp_path, store=store, recipe_sha256="1" * 64
    )

    assert pointer.subject_sha256 == first


def test_project_resolver_scans_past_newer_manifest_for_other_project(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    state = StageState(tmp_path / "state", store)
    older_requested = _manifest(
        store,
        recipe_sha256="1" * 64,
        project_id="requested-project",
        identity="older",
    )
    newer_requested = _manifest(
        store,
        recipe_sha256="1" * 64,
        project_id="requested-project",
        identity="newer",
    )
    other = _manifest(
        store,
        recipe_sha256="1" * 64,
        project_id="other-project",
        identity="newest-other",
    )
    semantics = (
        ({"recipe_sha256": "2" * 64}, older_requested, 1),
        ({"recipe_sha256": "3" * 64}, newer_requested, 2),
        ({"recipe_sha256": "4" * 64}, other, 3),
    )
    for semantic_hashes, subject, timestamp in semantics:
        state.publish(
            stage="translate",
            target="e3c",
            subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
            subject_sha256=subject,
            semantic_hashes=semantic_hashes,
        )
        os.utime(
            state.path_for("translate", "e3c", semantic_hashes),
            ns=(timestamp, timestamp),
        )

    pointer = resolve_translation_pointer(
        artifact_root=tmp_path,
        store=store,
        recipe_sha256="1" * 64,
        project_id="requested-project",
    )

    assert pointer.subject_sha256 == newer_requested


def test_resolver_reports_a_missing_variant(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    state = StageState(tmp_path / "state", store)
    state.publish(
        stage="translate",
        target="e3c",
        subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
        subject_sha256=_manifest(store, recipe_sha256="1" * 64),
        semantic_hashes={"recipe_sha256": "3" * 64},
    )

    with pytest.raises(ValueError, match="no published E3C translation"):
        resolve_translation_pointer(
            artifact_root=tmp_path, store=store, recipe_sha256="9" * 64
        )

from collections import Counter
from pathlib import Path

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.pipeline import NormalizationManifest
from phentrieve_benchmark.models.translation import (
    TranslationManifest,
    TranslationStatus,
)
from phentrieve_benchmark.pipeline.state import StagePointer
from phentrieve_benchmark.pipeline.translate import (
    PreparedE3cTranslation,
    _full_translation_inputs,
    _jsonl_documents,
    estimate_prepared_translation,
)
from phentrieve_benchmark.translation.e3c import is_reusable_translation
from phentrieve_benchmark.translation.pricing import load_translation_recipe
from phentrieve_benchmark.translation.variants import (
    resolve_translation_pointer,
)

ROOT = Path(__file__).parents[2]
ARTIFACT_ROOT = ROOT / ".artifacts"
FLAGGED_CASES = {
    "EN100114",
    "ES100417",
    "ES100778",
    "ES100937",
    "FR100344",
}


def _published_normalization(store: ArtifactStore) -> NormalizationManifest:
    paths = sorted(
        (ARTIFACT_ROOT / "state/normalize/e3c").glob("*.json"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for path in paths:
        pointer = StagePointer.model_validate_json(path.read_bytes(), strict=True)
        try:
            manifest = NormalizationManifest.model_validate_json(
                store.read_bytes(pointer.subject_sha256), strict=True
            )
        except (FileNotFoundError, ValueError):
            continue
        if manifest.inventory.record_count == 246:
            return manifest
    pytest.skip("published local E3C normalization artifacts are unavailable")


def test_published_tllm_reuses_all_30_including_five_flagged_records() -> None:
    if not ARTIFACT_ROOT.exists():
        pytest.skip("published local E3C translation artifacts are unavailable")
    store = ArtifactStore(ARTIFACT_ROOT / "objects")
    legacy_recipe = load_translation_recipe(
        ROOT / "datasets/e3c-de/translation-llm.yaml"
    )
    try:
        pointer = resolve_translation_pointer(
            artifact_root=ARTIFACT_ROOT,
            store=store,
            recipe_sha256=legacy_recipe.sha256,
            project_id="phentrieve",
        )
    except ValueError:
        pytest.skip("published local 30-case TLLM manifest is unavailable")
    previous = TranslationManifest.model_validate_json(
        store.read_bytes(pointer.subject_sha256), strict=True
    )
    normalization = _published_normalization(store)
    inputs = _full_translation_inputs(
        _jsonl_documents(store.read_bytes(normalization.documents.sha256)),
        store.read_bytes(normalization.inventory.sha256),
    )
    full_recipe = load_translation_recipe(
        ROOT / "datasets/e3c-de/translation-llm-full.yaml"
    )
    prepared = PreparedE3cTranslation(
        inputs=inputs,
        recipe=full_recipe.value,
        recipe_sha256=full_recipe.sha256,
        selection_sha256=normalization.inventory.sha256,
        previous_manifest=previous,
        project_id="phentrieve",
    )
    by_case = {item.document.source_case_id: item for item in inputs}
    reusable = {
        record.source_case_id
        for record in previous.records
        if is_reusable_translation(
            record,
            item=by_case[record.source_case_id],
            recipe=full_recipe.value,
            project_id="phentrieve",
        )
    }

    estimate = estimate_prepared_translation(prepared)

    assert len(previous.records) == 30
    assert Counter(record.status for record in previous.records) == {
        TranslationStatus.READY_FOR_REVIEW: 25,
        TranslationStatus.AUTOMATIC_CHECK_FAILED: 5,
    }
    assert reusable == {record.source_case_id for record in previous.records}
    assert reusable >= FLAGGED_CASES
    assert estimate.case_count == 216
    assert estimate.input_codepoints == 441_414
    assert str(estimate.cost.upper_bound) == "10.152522"

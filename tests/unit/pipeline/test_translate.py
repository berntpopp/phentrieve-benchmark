from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.document import (
    Document,
)
from phentrieve_benchmark.models.document import (
    TranslationStatus as DocumentTranslationStatus,
)
from phentrieve_benchmark.pipeline.prepare import PipelineContext
from phentrieve_benchmark.pipeline.translate import (
    PreparedE3cTranslation,
    estimate_prepared_translation,
    recheck_e3c_translations,
    translate_e3c,
)
from phentrieve_benchmark.translation.e3c import TranslationInput
from phentrieve_benchmark.translation.google_nmt import ProviderTranslation
from phentrieve_benchmark.translation.pricing import (
    E3cTranslationRecipe,
    GoogleNmtPricing,
)


def _prepared() -> PreparedE3cTranslation:
    document = Document.from_text(
        source_case_id="EN101318",
        case_group_id="EN101318",
        document_id="e3c:en:EN101318",
        language="en",
        translation_status=DocumentTranslationStatus.NATIVE,
        text="The patient had fever.",
    )
    recipe = E3cTranslationRecipe(
        schema_version="e3c-translation-recipe/v1",
        translation_id="e3c-de-feasibility-30-google-nmt-v1",
        selection_id="e3c-de-feasibility-30-v1",
        provider="google-cloud-translation",
        api_version="v3",
        model="general/nmt",
        location="global",
        target_language="de",
        pricing=GoogleNmtPricing(
            currency="USD",
            price_per_million_input_characters=Decimal("20"),
            pricing_snapshot_id="google-cloud-translation-2026-07-24",
        ),
    )
    return PreparedE3cTranslation(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        recipe=recipe,
        recipe_sha256="a" * 64,
        selection_sha256="b" * 64,
        previous_manifest=None,
    )


def _context(tmp_path: Path) -> PipelineContext:
    return PipelineContext(
        repository_root=tmp_path,
        dataset_root=tmp_path / "datasets",
        artifact_root=tmp_path / "artifacts",
        store=ArtifactStore(tmp_path / "artifacts" / "objects"),
        code_sha256="c" * 64,
        pipeline_commit="d" * 40,
        dirty_state=False,
        clock=lambda: datetime(2026, 7, 24, tzinfo=UTC),
        run_id_provider=lambda: "translation-run",
    )


def test_estimate_prepared_translation_is_character_based() -> None:
    estimate = estimate_prepared_translation(_prepared())

    assert estimate.case_count == 1
    assert estimate.input_codepoints == 22
    assert estimate.cost.upper_bound == Decimal("0.00044")


def test_denied_translation_does_not_construct_provider(tmp_path: Path) -> None:
    providers: list[object] = []

    result = translate_e3c(
        prepared=_prepared(),
        context=_context(tmp_path),
        project_id="benchmark-project",
        authorized=False,
        provider_factory=lambda: providers.append(object()) or object(),
    )

    assert not result.authorized
    assert providers == []
    assert result.subject_sha256 is None


def test_successful_translation_materializes_readable_view(tmp_path: Path) -> None:
    class Provider:
        def translate(self, *args: object, **kwargs: object) -> ProviderTranslation:
            return ProviderTranslation(text="Der Patient hatte Fieber.")

    result = translate_e3c(
        prepared=_prepared(),
        context=_context(tmp_path),
        project_id="benchmark-project",
        authorized=True,
        provider_factory=Provider,
    )

    view = tmp_path / "artifacts" / "views" / "e3c-de-nmt"
    assert result.translated_count == 1
    assert (view / "EN101318.translation.de.txt").read_text() == (
        "Der Patient hatte Fieber."
    )


def test_recheck_reports_a_missing_variant(tmp_path: Path) -> None:
    source = Path(__file__).parents[3] / "datasets" / "e3c-de"
    target = tmp_path / "datasets" / "e3c-de"
    target.mkdir(parents=True)
    (target / "translation-llm.yaml").write_bytes(
        (source / "translation-llm.yaml").read_bytes()
    )
    context = _context(tmp_path)

    with pytest.raises(ValueError, match="no published E3C translation"):
        recheck_e3c_translations(context, "tllm")

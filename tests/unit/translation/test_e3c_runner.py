from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.document import (
    Document,
)
from phentrieve_benchmark.models.document import (
    TranslationStatus as DocumentTranslationStatus,
)
from phentrieve_benchmark.models.translation import (
    TranslationCheck,
    TranslationStatus,
)
from phentrieve_benchmark.translation.e3c import (
    TranslationInput,
    translate_documents,
)
from phentrieve_benchmark.translation.google_nmt import ProviderTranslation
from phentrieve_benchmark.translation.pricing import (
    E3cTranslationRecipe,
    GoogleNmtPricing,
)


class _Provider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def translate(
        self, text: str, *, source_language: str, target_language: str
    ) -> ProviderTranslation:
        self.calls.append((text, source_language, target_language))
        return ProviderTranslation(text="Der Patient hatte Fieber.")


def _document() -> Document:
    return Document.from_text(
        source_case_id="EN101318",
        case_group_id="EN101318",
        document_id="e3c:en:EN101318",
        language="en",
        translation_status=DocumentTranslationStatus.NATIVE,
        text="The patient had fever.",
    )


def _recipe() -> E3cTranslationRecipe:
    return E3cTranslationRecipe(
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


def test_runner_translates_and_stores_source_and_output_separately(
    tmp_path: Path,
) -> None:
    document = _document()
    provider = _Provider()
    store = ArtifactStore(tmp_path / "objects")

    result = translate_documents(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        provider=provider,
        store=store,
        recipe=_recipe(),
        selection_sha256="c" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
        language_detector=lambda _text: "de",
    )

    assert provider.calls == [("The patient had fever.", "en", "de")]
    record = result.manifest.records[0]
    assert store.read_bytes(record.source_sha256) == b"The patient had fever."
    assert store.read_bytes(record.translation_sha256) == (b"Der Patient hatte Fieber.")
    assert record.source_sha256 != record.translation_sha256
    assert result.translated_case_ids == ("EN101318",)


def test_runner_reuses_compatible_successful_record(tmp_path: Path) -> None:
    document = _document()
    store = ArtifactStore(tmp_path / "objects")
    first_provider = _Provider()
    first = translate_documents(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        provider=first_provider,
        store=store,
        recipe=_recipe(),
        selection_sha256="c" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
        language_detector=lambda _text: "de",
    )
    second_provider = _Provider()

    second = translate_documents(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        provider=second_provider,
        store=store,
        recipe=_recipe(),
        selection_sha256="c" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 7, 25, tzinfo=UTC),
        language_detector=lambda _text: "de",
        previous_manifest=first.manifest,
    )

    assert second_provider.calls == []
    assert second.reused_case_ids == ("EN101318",)


def test_runner_rebinds_compatible_record_from_prior_selection(
    tmp_path: Path,
) -> None:
    document = _document()
    store = ArtifactStore(tmp_path / "objects")
    prior_recipe = _recipe().model_copy(
        update={
            "translation_id": "e3c-de-feasibility-30-google-tllm-v1",
            "model": "general/translation-llm",
            "location": "us-central1",
        }
    )
    prior = translate_documents(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        provider=_Provider(),
        store=store,
        recipe=prior_recipe,
        selection_sha256="c" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
        language_detector=lambda _text: "de",
    )
    old = prior.manifest.records[0]
    full_recipe = prior_recipe.model_copy(
        update={
            "translation_id": "e3c-de-full-246-google-tllm-v1",
            "selection_id": "e3c-de-full-246-v1",
        }
    )
    provider = _Provider()

    full = translate_documents(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        provider=provider,
        store=store,
        recipe=full_recipe,
        selection_sha256="d" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
        language_detector=lambda _text: "de",
        previous_manifest=prior.manifest,
    )

    assert provider.calls == []
    assert full.reused_case_ids == ("EN101318",)
    rebound = full.manifest.records[0]
    assert rebound.selection_id == "e3c-de-full-246-v1"
    assert rebound.translation_id.startswith("e3c-de-full-246-google-tllm-v1-")
    assert rebound.previous_translation_id == old.translation_id
    assert rebound.source_sha256 == old.source_sha256
    assert rebound.translation_sha256 == old.translation_sha256
    assert rebound.checks == old.checks


def test_runner_reuses_failed_automatic_check_as_completed_provider_output(
    tmp_path: Path,
) -> None:
    document = _document()
    store = ArtifactStore(tmp_path / "objects")
    prior_recipe = _recipe().model_copy(
        update={"model": "general/translation-llm", "location": "us-central1"}
    )
    prior = translate_documents(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        provider=_Provider(),
        store=store,
        recipe=prior_recipe,
        selection_sha256="c" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
        language_detector=lambda _text: "de",
    )
    failed_check = TranslationCheck(code="length_ratio", passed=False, detail="warning")
    failed_record = prior.manifest.records[0].model_copy(
        update={
            "status": TranslationStatus.AUTOMATIC_CHECK_FAILED,
            "checks": (failed_check,),
        }
    )
    prior_manifest = prior.manifest.model_copy(update={"records": (failed_record,)})
    provider = _Provider()

    full = translate_documents(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        provider=provider,
        store=store,
        recipe=prior_recipe.model_copy(update={"selection_id": "e3c-de-full-246-v1"}),
        selection_sha256="d" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
        language_detector=lambda _text: "de",
        previous_manifest=prior_manifest,
    )

    assert provider.calls == []
    rebound = full.manifest.records[0]
    assert rebound.status is TranslationStatus.AUTOMATIC_CHECK_FAILED
    assert rebound.checks == (failed_check,)
    assert rebound.previous_translation_id == failed_record.translation_id


def test_runner_does_not_cross_reuse_record_from_another_project(
    tmp_path: Path,
) -> None:
    document = _document()
    store = ArtifactStore(tmp_path / "objects")
    recipe = _recipe().model_copy(
        update={"model": "general/translation-llm", "location": "us-central1"}
    )
    prior = translate_documents(
        inputs=(
            TranslationInput(
                document=document, expected_source_sha256=document.document_sha256
            ),
        ),
        provider=_Provider(),
        store=store,
        recipe=recipe,
        selection_sha256="c" * 64,
        project_id="other-project",
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
        language_detector=lambda _text: "de",
    )
    provider = _Provider()

    result = translate_documents(
        inputs=(
            TranslationInput(
                document=document, expected_source_sha256=document.document_sha256
            ),
        ),
        provider=provider,
        store=store,
        recipe=recipe.model_copy(update={"selection_id": "e3c-de-full-246-v1"}),
        selection_sha256="d" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
        language_detector=lambda _text: "de",
        previous_manifest=prior.manifest,
    )

    assert provider.calls == [("The patient had fever.", "en", "de")]
    assert result.reused_case_ids == ()


def test_record_carries_the_recipe_model(tmp_path: Path) -> None:
    document = _document()
    store = ArtifactStore(tmp_path / "objects")
    recipe = _recipe().model_copy(
        update={"model": "general/translation-llm", "location": "us-central1"}
    )

    result = translate_documents(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        provider=_Provider(),
        store=store,
        recipe=recipe,
        selection_sha256="c" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 7, 27, tzinfo=UTC),
        language_detector=lambda _text: "de",
    )

    record = result.manifest.records[0]
    assert record.model == "general/translation-llm"
    assert record.location == "us-central1"

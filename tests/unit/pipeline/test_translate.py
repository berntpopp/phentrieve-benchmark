import json
from dataclasses import replace
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
from phentrieve_benchmark.models.translation import (
    TranslationCheck,
    TranslationManifest,
    TranslationRecord,
    TranslationStatus,
)
from phentrieve_benchmark.pipeline.prepare import PipelineContext
from phentrieve_benchmark.pipeline.translate import (
    PreparedE3cTranslation,
    _full_translation_inputs,
    estimate_prepared_translation,
    recheck_e3c_translations,
    translate_e3c,
)
from phentrieve_benchmark.translation.e3c import (
    TranslationInput,
    translate_documents,
)
from phentrieve_benchmark.translation.google_nmt import ProviderTranslation
from phentrieve_benchmark.translation.pricing import (
    E3cTranslationRecipe,
    GoogleNmtPricing,
    load_translation_recipe,
)

ROOT = Path(__file__).parents[3]


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
        project_id="benchmark-project",
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


def test_estimate_counts_only_inputs_without_compatible_prior_translation(
    tmp_path: Path,
) -> None:
    prepared = _prepared()
    store = ArtifactStore(tmp_path / "objects")

    class Provider:
        def translate(self, *args: object, **kwargs: object) -> ProviderTranslation:
            return ProviderTranslation(text="Der Patient hatte Fieber.")

    prior_recipe = prepared.recipe.model_copy(
        update={
            "translation_id": "e3c-de-feasibility-30-google-tllm-v1",
            "model": "general/translation-llm",
            "location": "us-central1",
        }
    )
    prior = translate_documents(
        inputs=prepared.inputs,
        provider=Provider(),
        store=store,
        recipe=prior_recipe,
        selection_sha256="a" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
        language_detector=lambda _text: "de",
    )
    full = replace(
        prepared,
        recipe=prior_recipe.model_copy(update={"selection_id": "e3c-de-full-246-v1"}),
        previous_manifest=prior.manifest,
    )

    estimate = estimate_prepared_translation(full)

    assert estimate.case_count == 0
    assert estimate.input_codepoints == 0
    assert estimate.cost.upper_bound == Decimal("0")


def test_full_input_preparation_binds_every_document_to_inventory() -> None:
    inventory_path = ROOT / "datasets/e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json"
    template = json.loads(inventory_path.read_text(encoding="utf-8"))[0]
    documents = tuple(
        Document.from_text(
            source_case_id=case_id,
            case_group_id=case_id,
            document_id=f"e3c:{language}:{case_id}",
            language=language,
            translation_status=DocumentTranslationStatus.NATIVE,
            text=text,
        )
        for case_id, language, text in (
            ("FR2", "fr", "Deux mots"),
            ("EN1", "en", "Two words"),
        )
    )
    inventory = [
        {
            **template,
            "source_case_id": document.source_case_id,
            "language": document.language,
            "document_sha256": document.document_sha256,
            "codepoint_count": len(document.text),
        }
        for document in reversed(documents)
    ]

    inputs = _full_translation_inputs(documents, json.dumps(inventory).encode("utf-8"))

    assert [item.document.source_case_id for item in inputs] == ["EN1", "FR2"]
    assert all(
        item.expected_source_sha256 == item.document.document_sha256 for item in inputs
    )


def test_current_full_tllm_preview_counts_only_216_untranslated_cases() -> None:
    inventory = json.loads(
        (ROOT / "datasets/e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json").read_text(
            encoding="utf-8"
        )
    )
    selected = json.loads(
        (ROOT / "datasets/e3c-de/selections/e3c-de-feasibility-30-v1.json").read_text(
            encoding="utf-8"
        )
    )
    selected_ids = {item["source_case_id"] for item in selected["records"]}
    recipe = load_translation_recipe(
        ROOT / "datasets/e3c-de/translation-llm-full.yaml"
    ).value
    inputs: list[TranslationInput] = []
    prior_records: list[TranslationRecord] = []
    for item in inventory:
        document = Document.from_text(
            source_case_id=item["source_case_id"],
            case_group_id=item["source_case_id"],
            document_id=f"e3c:{item['language']}:{item['source_case_id']}",
            language=item["language"],
            translation_status=DocumentTranslationStatus.NATIVE,
            text="x" * item["codepoint_count"],
        )
        inputs.append(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            )
        )
        if item["source_case_id"] in selected_ids:
            prior_records.append(
                TranslationRecord(
                    translation_id=f"prior-{item['source_case_id']}",
                    selection_id="e3c-de-feasibility-30-v1",
                    source_case_id=item["source_case_id"],
                    source_language=item["language"],
                    target_language="de",
                    source_sha256=document.document_sha256,
                    translation_sha256="f" * 64,
                    provider="google-cloud-translation",
                    api_version="v3",
                    model="general/translation-llm",
                    project_id="phentrieve",
                    location="us-central1",
                    created_at=datetime(2026, 7, 27, tzinfo=UTC),
                    input_codepoints=len(document.text),
                    output_codepoints=1,
                    price_per_million_input_characters=Decimal("10"),
                    estimated_max_cost=Decimal("0"),
                    status=TranslationStatus.READY_FOR_REVIEW,
                    checks=(TranslationCheck(code="nonempty_output", passed=True),),
                )
            )
    prepared = PreparedE3cTranslation(
        inputs=tuple(inputs),
        recipe=recipe,
        recipe_sha256="a" * 64,
        selection_sha256="b" * 64,
        previous_manifest=TranslationManifest(
            selection_id="e3c-de-feasibility-30-v1",
            selection_sha256="c" * 64,
            recipe_sha256="d" * 64,
            records=tuple(prior_records),
        ),
        project_id="phentrieve",
    )

    estimate = estimate_prepared_translation(prepared)

    assert estimate.case_count == 216
    assert estimate.input_codepoints == 441_414
    assert estimate.cost.upper_bound == Decimal("10.152522")


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

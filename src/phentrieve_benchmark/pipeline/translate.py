import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from phentrieve_benchmark.acquisition.recipes import load_source_recipe
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.manifest import (
    RunManifest,
    RunStatus,
    UsageMetrics,
)
from phentrieve_benchmark.models.pipeline import (
    NormalizationManifest,
    ProvenanceRunLink,
    ProvenanceSubjectRole,
)
from phentrieve_benchmark.models.translation import TranslationManifest
from phentrieve_benchmark.pipeline.prepare import PipelineContext
from phentrieve_benchmark.pipeline.state import StageState
from phentrieve_benchmark.policies.paid_operations import CostEstimate
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.selection.e3c import E3cSelectionManifest
from phentrieve_benchmark.selection.metrics import E3cInventoryRecord
from phentrieve_benchmark.translation.checks import detect_supported_language
from phentrieve_benchmark.translation.e3c import (
    TranslationInput,
    is_reusable_translation,
    translate_documents,
)
from phentrieve_benchmark.translation.google_nmt import TranslationProvider
from phentrieve_benchmark.translation.pricing import (
    E3cTranslationRecipe,
    estimate_google_nmt,
    load_translation_recipe,
)
from phentrieve_benchmark.translation.recheck import recheck_translations
from phentrieve_benchmark.translation.variants import (
    resolve_translation_pointer,
    translation_recipe_path,
    translation_view_destination,
)
from phentrieve_benchmark.translation.view import materialize_translation_view


@dataclass(frozen=True)
class PreparedE3cTranslation:
    inputs: tuple[TranslationInput, ...]
    recipe: E3cTranslationRecipe
    recipe_sha256: str
    selection_sha256: str
    previous_manifest: TranslationManifest | None
    project_id: str


@dataclass(frozen=True)
class TranslationEstimate:
    case_count: int
    input_codepoints: int
    cost: CostEstimate


@dataclass(frozen=True)
class TranslationStageResult:
    authorized: bool
    subject_sha256: str | None = None
    run_manifest_sha256: str | None = None
    provenance_link_sha256: str | None = None
    translated_count: int = 0
    failed_count: int = 0
    reused_count: int = 0


@dataclass(frozen=True)
class TranslationRecheckStageResult:
    subject_sha256: str
    run_manifest_sha256: str | None
    provenance_link_sha256: str | None
    case_count: int
    changed_count: int
    failed_count: int


def _semantic_hashes(
    prepared: PreparedE3cTranslation,
    context: PipelineContext,
    project_id: str,
) -> dict[str, str]:
    return {
        "selection_sha256": prepared.selection_sha256,
        "recipe_sha256": prepared.recipe_sha256,
        "project_sha256": context.store.put_bytes(project_id.encode("utf-8")),
        "code_sha256": context.code_sha256,
    }


def _jsonl_documents(payload: bytes) -> tuple[Document, ...]:
    return tuple(
        Document.model_validate_json(line, strict=True)
        for line in payload.splitlines()
        if line
    )


def prepare_e3c_translation(
    context: PipelineContext, project_id: str, variant: str = "nmt"
) -> PreparedE3cTranslation:
    source_recipe = load_source_recipe(context.dataset_root / "e3c-de" / "dataset.yaml")
    state = StageState(context.artifact_root / "state", context.store)
    source_pointer = state.reuse(
        stage="acquire",
        target="e3c",
        semantic_hashes={
            "recipe_sha256": source_recipe.sha256,
            "code_sha256": context.code_sha256,
        },
    )
    if source_pointer is None:
        raise ValueError("missing verified E3C acquisition")
    normalization_pointer = state.reuse(
        stage="normalize",
        target="e3c",
        semantic_hashes={
            "recipe_sha256": source_recipe.sha256,
            "source_snapshot_sha256": source_pointer.subject_sha256,
            "code_sha256": context.code_sha256,
        },
    )
    if normalization_pointer is None:
        raise ValueError("missing verified E3C normalization")
    normalization = NormalizationManifest.model_validate_json(
        context.store.read_bytes(normalization_pointer.subject_sha256),
        strict=True,
    )
    documents = _jsonl_documents(
        context.store.read_bytes(normalization.documents.sha256)
    )
    loaded_recipe = load_translation_recipe(
        translation_recipe_path(context.dataset_root, variant)
    )
    if variant == "tllm-full":
        inputs = _full_translation_inputs(
            documents,
            context.store.read_bytes(normalization.inventory.sha256),
        )
        selection_sha256 = normalization.inventory.sha256
    else:
        seed_sha256 = context.store.put_bytes(b"phentrieve-e3c-de-feasibility-30-v1")
        override_sha256 = context.store.put_bytes(canonical_json_bytes([]))
        selection_pointer = state.reuse(
            stage="select",
            target="e3c",
            semantic_hashes={
                "input_sha256": normalization.inventory.sha256,
                "selection_seed_sha256": seed_sha256,
                "override_sha256": override_sha256,
                "code_sha256": context.code_sha256,
            },
        )
        if selection_pointer is None:
            raise ValueError("missing verified E3C selection")
        selection = E3cSelectionManifest.model_validate_json(
            context.store.read_bytes(selection_pointer.subject_sha256),
            strict=True,
        )
        by_case = {
            (document.source_case_id, document.language): document
            for document in documents
        }
        selected_inputs: list[TranslationInput] = []
        for record in selection.records:
            document = by_case.get((record.source_case_id, record.language))
            if document is None:
                raise ValueError(
                    f"selected E3C document is missing: {record.source_case_id}"
                )
            selected_inputs.append(
                TranslationInput(
                    document=document,
                    expected_source_sha256=record.metrics.document_sha256,
                )
            )
        inputs = tuple(selected_inputs)
        selection_sha256 = selection_pointer.subject_sha256
    prepared = PreparedE3cTranslation(
        inputs=inputs,
        recipe=loaded_recipe.value,
        recipe_sha256=loaded_recipe.sha256,
        selection_sha256=selection_sha256,
        previous_manifest=None,
        project_id=project_id,
    )
    previous_pointer = state.reuse(
        stage="translate",
        target="e3c",
        semantic_hashes=_semantic_hashes(prepared, context, project_id),
    )
    previous_manifest = (
        TranslationManifest.model_validate_json(
            context.store.read_bytes(previous_pointer.subject_sha256),
            strict=True,
        )
        if previous_pointer is not None
        else None
    )
    if previous_manifest is None and variant == "tllm-full":
        try:
            full_pointer = resolve_translation_pointer(
                artifact_root=context.artifact_root,
                store=context.store,
                recipe_sha256=prepared.recipe_sha256,
                project_id=project_id,
            )
        except ValueError:
            full_pointer = None
        if full_pointer is not None:
            previous_manifest = TranslationManifest.model_validate_json(
                context.store.read_bytes(full_pointer.subject_sha256),
                strict=True,
            )
    if previous_manifest is None and variant == "tllm-full":
        legacy_recipe = load_translation_recipe(
            translation_recipe_path(context.dataset_root, "tllm")
        )
        try:
            legacy_pointer = resolve_translation_pointer(
                artifact_root=context.artifact_root,
                store=context.store,
                recipe_sha256=legacy_recipe.sha256,
                project_id=project_id,
            )
        except ValueError:
            legacy_pointer = None
        if legacy_pointer is not None:
            candidate = TranslationManifest.model_validate_json(
                context.store.read_bytes(legacy_pointer.subject_sha256),
                strict=True,
            )
            previous_manifest = candidate
    return PreparedE3cTranslation(
        inputs=prepared.inputs,
        recipe=prepared.recipe,
        recipe_sha256=prepared.recipe_sha256,
        selection_sha256=prepared.selection_sha256,
        previous_manifest=previous_manifest,
        project_id=project_id,
    )


def _full_translation_inputs(
    documents: tuple[Document, ...], inventory_payload: bytes
) -> tuple[TranslationInput, ...]:
    raw_inventory = json.loads(inventory_payload)
    if not isinstance(raw_inventory, list):
        raise ValueError("E3C inventory must be a list")
    inventory = tuple(
        E3cInventoryRecord.model_validate_json(
            json.dumps(item, ensure_ascii=False), strict=True
        )
        for item in raw_inventory
    )
    metrics_by_identity = {
        (item.source_case_id, item.language): item for item in inventory
    }
    documents_by_identity = {
        (item.source_case_id, item.language): item for item in documents
    }
    if (
        len(metrics_by_identity) != len(inventory)
        or len(documents_by_identity) != len(documents)
        or metrics_by_identity.keys() != documents_by_identity.keys()
    ):
        raise ValueError("normalized E3C documents do not match inventory")
    inputs: list[TranslationInput] = []
    for identity in sorted(metrics_by_identity, key=lambda value: (value[1], value[0])):
        document = documents_by_identity[identity]
        metrics = metrics_by_identity[identity]
        if document.document_sha256 != metrics.document_sha256:
            raise ValueError(f"document hash mismatch for {document.source_case_id}")
        inputs.append(
            TranslationInput(
                document=document,
                expected_source_sha256=metrics.document_sha256,
            )
        )
    return tuple(inputs)


def estimate_prepared_translation(
    prepared: PreparedE3cTranslation,
) -> TranslationEstimate:
    previous = {
        record.source_case_id: record
        for record in (
            prepared.previous_manifest.records
            if prepared.previous_manifest is not None
            else ()
        )
    }
    billable = tuple(
        item
        for item in prepared.inputs
        if not (
            (record := previous.get(item.document.source_case_id)) is not None
            and is_reusable_translation(
                record,
                item=item,
                recipe=prepared.recipe,
                project_id=prepared.project_id,
            )
        )
    )
    codepoints = sum(len(item.document.text) for item in billable)
    if codepoints == 0:
        cost = CostEstimate(
            currency=prepared.recipe.pricing.currency,
            estimated_cost=Decimal(0),
            upper_bound=Decimal(0),
            pricing_snapshot_id=(prepared.recipe.pricing.pricing_snapshot_id),
        )
    else:
        cost = estimate_google_nmt(codepoints, prepared.recipe.pricing)
    return TranslationEstimate(
        case_count=len(billable),
        input_codepoints=codepoints,
        cost=cost,
    )


def translate_e3c(
    *,
    prepared: PreparedE3cTranslation,
    context: PipelineContext,
    project_id: str,
    authorized: bool,
    provider_factory: Callable[[], object],
    variant: str = "nmt",
) -> TranslationStageResult:
    if not authorized:
        return TranslationStageResult(authorized=False)

    provider = cast(TranslationProvider, provider_factory())
    translated = translate_documents(
        inputs=prepared.inputs,
        provider=provider,
        store=context.store,
        recipe=prepared.recipe,
        recipe_sha256=prepared.recipe_sha256,
        selection_sha256=prepared.selection_sha256,
        project_id=project_id,
        created_at=context.clock(),
        language_detector=detect_supported_language,
        previous_manifest=prepared.previous_manifest,
    )
    manifest_bytes = translated.manifest.canonical_bytes()
    subject_sha256 = context.store.put_bytes(manifest_bytes)
    estimate = estimate_prepared_translation(prepared)
    finished = context.clock()
    run = RunManifest(
        run_id=context.run_id_provider(),
        stage="translate",
        status=RunStatus.COMPLETE,
        started_at=finished,
        finished_at=finished,
        pipeline_commit=context.pipeline_commit,
        dirty_state=context.dirty_state,
        code_sha256=context.code_sha256,
        config_sha256=prepared.recipe_sha256,
        input_sha256=(prepared.selection_sha256,),
        output_sha256=(subject_sha256,),
        selection_id=prepared.recipe.selection_id,
        pricing_snapshot_id=(prepared.recipe.pricing.pricing_snapshot_id),
        usage=UsageMetrics(
            input_characters=estimate.input_codepoints,
            estimated_cost=float(estimate.cost.estimated_cost),
        ),
    )
    run_sha256 = context.store.put_bytes(
        canonical_json_bytes(run.model_dump(mode="json"))
    )
    link = ProvenanceRunLink(
        subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
        subject_sha256=subject_sha256,
        run_manifest_sha256=run_sha256,
    )
    link_sha256 = context.store.put_bytes(link.canonical_bytes())
    semantic = _semantic_hashes(prepared, context, project_id)
    StageState(context.artifact_root / "state", context.store).publish(
        stage="translate",
        target="e3c",
        subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
        subject_sha256=subject_sha256,
        semantic_hashes=semantic,
    )
    materialize_translation_view(
        manifest=translated.manifest,
        store=context.store,
        destination=translation_view_destination(context.artifact_root, variant),
    )
    return TranslationStageResult(
        authorized=True,
        subject_sha256=subject_sha256,
        run_manifest_sha256=run_sha256,
        provenance_link_sha256=link_sha256,
        translated_count=len(translated.translated_case_ids),
        failed_count=len(translated.failed_case_ids),
        reused_count=len(translated.reused_case_ids),
    )


def recheck_e3c_translations(
    context: PipelineContext, variant: str = "nmt"
) -> TranslationRecheckStageResult:
    """Re-run the automatic checks over already translated artifacts.

    Contacts no provider and spends nothing. When the verdicts are unchanged
    the existing manifest is returned untouched rather than republished.
    """
    recipe = load_translation_recipe(
        translation_recipe_path(context.dataset_root, variant)
    )
    pointer = resolve_translation_pointer(
        artifact_root=context.artifact_root,
        store=context.store,
        recipe_sha256=recipe.sha256,
    )
    manifest = TranslationManifest.model_validate_json(
        context.store.read_bytes(pointer.subject_sha256), strict=True
    )
    result = recheck_translations(
        manifest=manifest,
        store=context.store,
        language_detector=detect_supported_language,
    )
    if not result.changed:
        return TranslationRecheckStageResult(
            subject_sha256=pointer.subject_sha256,
            run_manifest_sha256=None,
            provenance_link_sha256=None,
            case_count=len(manifest.records),
            changed_count=0,
            failed_count=len(result.failed_case_ids),
        )

    subject_sha256 = context.store.put_bytes(result.manifest.canonical_bytes())
    finished = context.clock()
    run = RunManifest(
        run_id=context.run_id_provider(),
        stage="translate-recheck",
        status=RunStatus.COMPLETE,
        started_at=finished,
        finished_at=finished,
        pipeline_commit=context.pipeline_commit,
        dirty_state=context.dirty_state,
        code_sha256=context.code_sha256,
        config_sha256=manifest.recipe_sha256,
        input_sha256=(pointer.subject_sha256,),
        output_sha256=(subject_sha256,),
        selection_id=manifest.selection_id,
    )
    run_sha256 = context.store.put_bytes(
        canonical_json_bytes(run.model_dump(mode="json"))
    )
    link = ProvenanceRunLink(
        subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
        subject_sha256=subject_sha256,
        run_manifest_sha256=run_sha256,
    )
    link_sha256 = context.store.put_bytes(link.canonical_bytes())
    project_ids = {record.project_id for record in manifest.records}
    if len(project_ids) != 1:
        raise ValueError("translation manifest spans multiple projects")
    StageState(context.artifact_root / "state", context.store).publish(
        stage="translate",
        target="e3c",
        subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
        subject_sha256=subject_sha256,
        semantic_hashes={
            "selection_sha256": manifest.selection_sha256,
            "recipe_sha256": manifest.recipe_sha256,
            "project_sha256": context.store.put_bytes(
                project_ids.pop().encode("utf-8")
            ),
            "code_sha256": context.code_sha256,
        },
    )
    materialize_translation_view(
        manifest=result.manifest,
        store=context.store,
        destination=translation_view_destination(context.artifact_root, variant),
    )
    return TranslationRecheckStageResult(
        subject_sha256=subject_sha256,
        run_manifest_sha256=run_sha256,
        provenance_link_sha256=link_sha256,
        case_count=len(result.manifest.records),
        changed_count=len(result.changed_case_ids),
        failed_count=len(result.failed_case_ids),
    )

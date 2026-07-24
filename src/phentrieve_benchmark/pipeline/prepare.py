from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from phentrieve_benchmark.acquisition.archives import publish_source_snapshot
from phentrieve_benchmark.acquisition.downloader import download_archive
from phentrieve_benchmark.acquisition.recipes import (
    LoadedRecipe,
    NormalizationRecipe,
    SourceRecipe,
    load_source_recipe,
    load_target_recipe,
)
from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.manifest import RunManifest, RunStatus
from phentrieve_benchmark.models.pipeline import (
    ArtifactReference,
    NormalizationCount,
    NormalizationManifest,
    ProvenanceRunLink,
    ProvenanceSubjectRole,
    SourceSnapshotManifest,
    WarningCount,
)
from phentrieve_benchmark.normalization.contracts import NormalizedTarget
from phentrieve_benchmark.normalization.e3c import normalize_e3c_members
from phentrieve_benchmark.normalization.raghpo import normalize_raghpo_target
from phentrieve_benchmark.pipeline.state import StageState
from phentrieve_benchmark.provenance.canonical import (
    canonical_json_bytes,
    canonical_jsonl_bytes,
)
from phentrieve_benchmark.selection.e3c import select_e3c_feasibility
from phentrieve_benchmark.selection.metrics import (
    E3cInventoryRecord,
    build_e3c_inventory_record,
)

SourceId = Literal["e3c", "raghpo"]
TargetId = Literal["e3c", "csc", "gsc"]
CohortId = Literal["feasibility-30"]


@dataclass(frozen=True)
class PipelineContext:
    repository_root: Path
    dataset_root: Path
    artifact_root: Path
    store: ArtifactStore
    code_sha256: str
    pipeline_commit: str
    dirty_state: bool
    clock: Callable[[], datetime] = field(
        default=lambda: datetime.now(UTC), repr=False
    )
    run_id_provider: Callable[[], str] = field(
        default=lambda: uuid4().hex, repr=False
    )


@dataclass(frozen=True)
class StageResult:
    stage: Literal["acquire", "normalize", "select"]
    target: str
    subject_role: ProvenanceSubjectRole
    subject_sha256: str
    run_manifest_sha256: str
    provenance_link_sha256: str
    reused: bool


def _source_recipe_path(source_id: SourceId, dataset_root: Path) -> Path:
    return dataset_root / (
        "e3c-de/dataset.yaml" if source_id == "e3c" else "raghpo/source.yaml"
    )


def _target_recipe_path(target_id: TargetId, dataset_root: Path) -> Path:
    if target_id == "e3c":
        return dataset_root / "e3c-de" / "dataset.yaml"
    return dataset_root / "raghpo" / target_id / "dataset.yaml"


def _load_target_config(
    target_id: TargetId, dataset_root: Path
) -> LoadedRecipe[SourceRecipe] | LoadedRecipe[NormalizationRecipe]:
    path = _target_recipe_path(target_id, dataset_root)
    if target_id == "e3c":
        return load_source_recipe(path)
    return load_target_recipe(path)


def _acquire_snapshot(
    recipe: LoadedRecipe[SourceRecipe], context: PipelineContext
) -> object:
    archive = download_archive(
        recipe.value,
        store=context.store,
        staging_root=context.artifact_root / "staging",
    )
    return publish_source_snapshot(recipe, archive, store=context.store)


def _record_success(
    *,
    stage: Literal["acquire", "normalize", "select"],
    target: str,
    role: ProvenanceSubjectRole,
    subject_sha256: str,
    config_sha256: str,
    inputs: tuple[str, ...],
    context: PipelineContext,
    reused: bool,
) -> StageResult:
    started = context.clock()
    run = RunManifest(
        run_id=context.run_id_provider(),
        stage=stage,
        status=RunStatus.COMPLETE,
        started_at=started,
        finished_at=context.clock(),
        pipeline_commit=context.pipeline_commit,
        dirty_state=context.dirty_state,
        code_sha256=context.code_sha256,
        config_sha256=config_sha256,
        input_sha256=inputs,
        output_sha256=(subject_sha256,),
    )
    run_bytes = canonical_json_bytes(run.model_dump(mode="json"))
    run_sha256 = context.store.put_bytes(run_bytes)
    link = ProvenanceRunLink(
        subject_role=role,
        subject_sha256=subject_sha256,
        run_manifest_sha256=run_sha256,
    )
    link_sha256 = context.store.put_bytes(link.canonical_bytes())
    return StageResult(
        stage=stage,
        target=target,
        subject_role=role,
        subject_sha256=subject_sha256,
        run_manifest_sha256=run_sha256,
        provenance_link_sha256=link_sha256,
        reused=reused,
    )


def acquire_target(source_id: SourceId, context: PipelineContext) -> StageResult:
    recipe = load_source_recipe(_source_recipe_path(source_id, context.dataset_root))
    semantic = {
        "recipe_sha256": recipe.sha256,
        "code_sha256": context.code_sha256,
    }
    state = StageState(context.artifact_root / "state", context.store)
    pointer = state.reuse(
        stage="acquire", target=source_id, semantic_hashes=semantic
    )
    reused = pointer is not None
    if pointer is None:
        snapshot = _acquire_snapshot(recipe, context)
        subject_bytes = snapshot.canonical_bytes()  # type: ignore[attr-defined]
        subject_sha256 = context.store.put_bytes(subject_bytes)
        if subject_sha256 != snapshot.sha256():  # type: ignore[attr-defined]
            raise ValueError("source snapshot canonical identity mismatch")
        state.publish(
            stage="acquire",
            target=source_id,
            subject_role=ProvenanceSubjectRole.SOURCE_SNAPSHOT,
            subject_sha256=subject_sha256,
            semantic_hashes=semantic,
        )
    else:
        subject_sha256 = pointer.subject_sha256
    return _record_success(
        stage="acquire",
        target=source_id,
        role=ProvenanceSubjectRole.SOURCE_SNAPSHOT,
        subject_sha256=subject_sha256,
        config_sha256=recipe.sha256,
        inputs=(),
        context=context,
        reused=reused,
    )


def _normalize(
    target_id: TargetId,
    members: dict[str, bytes],
    source_recipe: SourceRecipe,
    target_recipe: SourceRecipe | NormalizationRecipe,
) -> NormalizedTarget:
    if target_id == "e3c":
        return normalize_e3c_members(members, source_recipe=source_recipe)
    if not isinstance(target_recipe, NormalizationRecipe):
        raise TypeError("RAG-HPO normalization recipe required")
    workbook_path = target_recipe.required_paths[0]
    return normalize_raghpo_target(
        workbook_bytes=members[workbook_path],
        source_recipe=source_recipe,
        target_recipe=target_recipe,
    )


def _publish_records(
    records: list[dict[str, object]],
    *,
    identity_key: str,
    schema_id: str,
    context: PipelineContext,
) -> ArtifactReference:
    payload = canonical_jsonl_bytes(records, identity_key=identity_key)
    return ArtifactReference(
        schema_id=schema_id,
        sha256=context.store.put_bytes(payload),
        byte_length=len(payload),
        record_count=len(records),
    )


def _publish_normalization(
    *,
    target_id: TargetId,
    normalized: NormalizedTarget,
    source_snapshot_sha256: str,
    source_recipe: LoadedRecipe[SourceRecipe],
    target_recipe: LoadedRecipe[SourceRecipe]
    | LoadedRecipe[NormalizationRecipe],
    context: PipelineContext,
) -> NormalizationManifest:
    documents = _publish_records(
        [value.model_dump(mode="json") for value in normalized.documents],
        identity_key="document_id",
        schema_id="document/v1",
        context=context,
    )
    annotations = (
        _publish_records(
            [value.model_dump(mode="json") for value in normalized.annotation_sets],
            identity_key="annotation_set_id",
            schema_id="annotation-set/v1",
            context=context,
        )
        if normalized.annotation_sets
        else None
    )
    source_annotations = (
        _publish_records(
            [
                value.model_dump(mode="json")
                for value in normalized.source_annotation_sets
            ],
            identity_key="annotation_set_id",
            schema_id="source-annotation-set/v1",
            context=context,
        )
        if normalized.source_annotation_sets
        else None
    )
    sidecar = (
        _publish_records(
            [value.model_dump(mode="json") for value in normalized.source_sidecar],
            identity_key="source_row_id",
            schema_id="raghpo-source-annotation-record/v1",
            context=context,
        )
        if normalized.source_sidecar
        else None
    )
    if target_id == "e3c":
        by_document = {
            value.document_sha256: value
            for value in normalized.source_annotation_sets
        }
        sentence_counts = {
            (language, case_id): count
            for language, case_id, kind, count in normalized.source_structure_counts
            if kind == "sentences"
        }
        inventory_records = [
            build_e3c_inventory_record(
                document,
                by_document[document.document_sha256],
                sentence_count=sentence_counts[
                    (document.language, document.source_case_id)
                ],
            ).model_dump(mode="json")
            for document in normalized.documents
        ]
        inventory_schema = "e3c-inventory-record/v1"
        inventory_identity = "source_case_id"
    else:
        inventory_records = [
            {
                "schema_version": "normalized-document-inventory/v1",
                "document_id": document.document_id,
                "document_sha256": document.document_sha256,
            }
            for document in normalized.documents
        ]
        inventory_schema = "normalized-document-inventory/v1"
        inventory_identity = "document_id"
    inventory = _publish_records(
        inventory_records,
        identity_key=inventory_identity,
        schema_id=inventory_schema,
        context=context,
    )
    adapter_id = source_recipe.value.adapter_id
    if isinstance(target_recipe.value, NormalizationRecipe):
        adapter_id = target_recipe.value.adapter_id
    return NormalizationManifest(
        target_id=target_id,
        source_snapshot_sha256=source_snapshot_sha256,
        recipe_sha256=target_recipe.sha256,
        adapter_id=adapter_id,
        code_sha256=context.code_sha256,
        documents=documents,
        annotations=annotations,
        source_annotations=source_annotations,
        source_sidecar=sidecar,
        inventory=inventory,
        counts=tuple(
            NormalizationCount(record_type=name, count=count)
            for name, count in normalized.counts
        ),
        warnings=tuple(
            WarningCount(code=name, count=count)
            for name, count in normalized.warnings
        ),
    )


def normalize_target(target_id: TargetId, context: PipelineContext) -> StageResult:
    source_id: SourceId = "e3c" if target_id == "e3c" else "raghpo"
    source_recipe = load_source_recipe(
        _source_recipe_path(source_id, context.dataset_root)
    )
    source_state = StageState(context.artifact_root / "state", context.store)
    source_pointer = source_state.reuse(
        stage="acquire",
        target=source_id,
        semantic_hashes={
            "recipe_sha256": source_recipe.sha256,
            "code_sha256": context.code_sha256,
        },
    )
    if source_pointer is None:
        raise ValueError(f"missing verified acquisition for {source_id}")
    snapshot = SourceSnapshotManifest.model_validate_json(
        context.store.read_bytes(source_pointer.subject_sha256), strict=True
    )
    target_recipe = _load_target_config(target_id, context.dataset_root)
    semantic = {
        "recipe_sha256": target_recipe.sha256,
        "source_snapshot_sha256": source_pointer.subject_sha256,
        "code_sha256": context.code_sha256,
    }
    pointer = source_state.reuse(
        stage="normalize", target=target_id, semantic_hashes=semantic
    )
    reused = pointer is not None
    if pointer is None:
        members = {
            member.path: context.store.read_bytes(member.sha256)
            for member in snapshot.members
        }
        normalized = _normalize(
            target_id, members, source_recipe.value, target_recipe.value
        )
        manifest = _publish_normalization(
            target_id=target_id,
            normalized=normalized,
            source_snapshot_sha256=source_pointer.subject_sha256,
            source_recipe=source_recipe,
            target_recipe=target_recipe,
            context=context,
        )
        subject_sha256 = context.store.put_bytes(manifest.canonical_bytes())
        source_state.publish(
            stage="normalize",
            target=target_id,
            subject_role=ProvenanceSubjectRole.NORMALIZATION_MANIFEST,
            subject_sha256=subject_sha256,
            semantic_hashes=semantic,
        )
    else:
        subject_sha256 = pointer.subject_sha256
    return _record_success(
        stage="normalize",
        target=target_id,
        role=ProvenanceSubjectRole.NORMALIZATION_MANIFEST,
        subject_sha256=subject_sha256,
        config_sha256=target_recipe.sha256,
        inputs=(source_pointer.subject_sha256,),
        context=context,
        reused=reused,
    )


def select_e3c(cohort: CohortId, context: PipelineContext) -> StageResult:
    if cohort != "feasibility-30":
        raise ValueError("unsupported E3C cohort")
    source_recipe = load_source_recipe(
        _source_recipe_path("e3c", context.dataset_root)
    )
    target_recipe = _load_target_config("e3c", context.dataset_root)
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
            "recipe_sha256": target_recipe.sha256,
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
    seed_sha256 = context.store.put_bytes(
        b"phentrieve-e3c-de-feasibility-30-v1"
    )
    override_sha256 = context.store.put_bytes(canonical_json_bytes([]))
    semantic = {
        "input_sha256": normalization.inventory.sha256,
        "selection_seed_sha256": seed_sha256,
        "override_sha256": override_sha256,
        "code_sha256": context.code_sha256,
    }
    pointer = state.reuse(
        stage="select", target="e3c", semantic_hashes=semantic
    )
    reused = pointer is not None
    if pointer is None:
        records = tuple(
            E3cInventoryRecord.model_validate_json(line, strict=True)
            for line in context.store.read_bytes(
                normalization.inventory.sha256
            ).splitlines()
        )
        selection = select_e3c_feasibility(records)
        subject_sha256 = context.store.put_bytes(selection.canonical_bytes())
        state.publish(
            stage="select",
            target="e3c",
            subject_role=ProvenanceSubjectRole.SELECTION_MANIFEST,
            subject_sha256=subject_sha256,
            semantic_hashes=semantic,
        )
    else:
        subject_sha256 = pointer.subject_sha256
    return _record_success(
        stage="select",
        target="e3c",
        role=ProvenanceSubjectRole.SELECTION_MANIFEST,
        subject_sha256=subject_sha256,
        config_sha256=target_recipe.sha256,
        inputs=(normalization_pointer.subject_sha256,),
        context=context,
        reused=reused,
    )


def prepare_target(
    target_id: TargetId, context: PipelineContext
) -> tuple[StageResult, ...]:
    source_id: SourceId = "e3c" if target_id == "e3c" else "raghpo"
    results = [
        acquire_target(source_id, context),
        normalize_target(target_id, context),
    ]
    if target_id == "e3c":
        results.append(select_e3c("feasibility-30", context))
    return tuple(results)

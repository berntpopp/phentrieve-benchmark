from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from phentrieve_benchmark.acquisition.recipes import (
    _load_model,
    load_source_recipe,
)
from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.mapping.e3c import (
    map_e3c_umls_to_hpo,
    select_mapping_manifest,
)
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.manifest import RunManifest, RunStatus
from phentrieve_benchmark.models.mapping import E3cMappingStageManifest
from phentrieve_benchmark.models.pipeline import (
    ArtifactReference,
    NormalizationManifest,
    ProvenanceRunLink,
    ProvenanceSubjectRole,
)
from phentrieve_benchmark.models.source_annotation import SourceAnnotationSet
from phentrieve_benchmark.ontology.hpo import (
    HpoSourceRecipe,
    load_hpo_index,
    load_hpo_source_recipe,
)
from phentrieve_benchmark.pipeline.prepare import PipelineContext
from phentrieve_benchmark.pipeline.state import StageState
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.selection.e3c import E3cSelectionManifest


class E3cMappingRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-umls-hpo-mapping-recipe/v1"]
    mapping_id: str = Field(min_length=1)
    method: Literal["hpo-umls-xref"]
    hpo_release: str = Field(pattern=r"^v[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    hpo_recipe: str
    complete_population: Literal["all-e3c-l1"]
    selected_population: Literal["e3c-de-feasibility-30-v1"]


@dataclass(frozen=True)
class E3cMappingResult:
    stage_manifest_sha256: str
    complete_sha256: str
    selected_sha256: str
    summary_sha256: str
    record_count: int
    selected_record_count: int
    reused: bool


def _download_hpo(recipe: HpoSourceRecipe) -> bytes:
    with (
        httpx.Client(follow_redirects=True, timeout=60) as client,
        client.stream("GET", recipe.url) as response,
    ):
        response.raise_for_status()
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > recipe.maximum_byte_length:
                raise ValueError("HPO download exceeds maximum byte length")
            chunks.append(chunk)
    return b"".join(chunks)


def _verified_hpo_bytes(body: bytes, recipe: HpoSourceRecipe) -> bytes:
    if len(body) != recipe.expected_byte_length:
        raise ValueError("HPO byte length mismatch")
    if sha256(body).hexdigest() != recipe.sha256:
        raise ValueError("HPO SHA-256 mismatch")
    return body


def load_or_acquire_hpo(
    recipe: HpoSourceRecipe,
    *,
    artifact_root: Path,
    store: ArtifactStore,
    downloader: Callable[[HpoSourceRecipe], bytes] = _download_hpo,
) -> str:
    try:
        store.read_bytes(recipe.sha256)
        return recipe.sha256
    except FileNotFoundError:
        pass
    local = artifact_root / "source-locks" / f"hp-{recipe.release}.obo"
    body = local.read_bytes() if local.exists() else downloader(recipe)
    verified = _verified_hpo_bytes(body, recipe)
    digest = store.put_bytes(verified)
    if digest != recipe.sha256:
        raise ValueError("published HPO identity mismatch")
    return digest


def _jsonl(payload: bytes, model: type[BaseModel]) -> tuple[BaseModel, ...]:
    return tuple(
        model.model_validate_json(line, strict=True)
        for line in payload.splitlines()
        if line
    )


def _reference(
    payload: bytes,
    *,
    schema_id: str,
    record_count: int,
    store: ArtifactStore,
) -> ArtifactReference:
    return ArtifactReference(
        schema_id=schema_id,
        sha256=store.put_bytes(payload),
        byte_length=len(payload),
        record_count=record_count,
    )


def map_hpo_e3c(context: PipelineContext) -> E3cMappingResult:
    source_recipe = load_source_recipe(
        context.dataset_root / "e3c-de" / "dataset.yaml"
    )
    mapping_recipe = _load_model(
        context.dataset_root / "e3c-de" / "mapping.yaml",
        E3cMappingRecipe,
    )
    hpo_recipe_path = (
        context.dataset_root
        / "e3c-de"
        / mapping_recipe.value.hpo_recipe
    ).resolve()
    hpo_recipe = load_hpo_source_recipe(hpo_recipe_path)
    if hpo_recipe.value.release != mapping_recipe.value.hpo_release:
        raise ValueError("mapping and HPO release mismatch")

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
    seed_sha256 = context.store.put_bytes(
        b"phentrieve-e3c-de-feasibility-30-v1"
    )
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
    ontology_sha256 = load_or_acquire_hpo(
        hpo_recipe.value,
        artifact_root=context.artifact_root,
        store=context.store,
    )
    semantic = {
        "normalization_sha256": normalization_pointer.subject_sha256,
        "selection_sha256": selection_pointer.subject_sha256,
        "ontology_sha256": ontology_sha256,
        "recipe_sha256": mapping_recipe.sha256,
        "code_sha256": context.code_sha256,
    }
    previous = state.reuse(
        stage="map-hpo", target="e3c", semantic_hashes=semantic
    )
    if previous is not None:
        stage_manifest = E3cMappingStageManifest.model_validate_json(
            context.store.read_bytes(previous.subject_sha256), strict=True
        )
        complete = context.store.read_bytes(stage_manifest.complete.sha256)
        selected = context.store.read_bytes(stage_manifest.selected.sha256)
        complete_count = stage_manifest.complete.record_count
        selected_count = stage_manifest.selected.record_count
        if complete_count is None or selected_count is None:
            raise ValueError("mapping manifests require record counts")
        return E3cMappingResult(
            stage_manifest_sha256=previous.subject_sha256,
            complete_sha256=stage_manifest.complete.sha256,
            selected_sha256=stage_manifest.selected.sha256,
            summary_sha256=stage_manifest.summary.sha256,
            record_count=complete_count,
            selected_record_count=selected_count,
            reused=bool(complete or selected),
        )

    documents = tuple(
        value
        for value in _jsonl(
            context.store.read_bytes(normalization.documents.sha256), Document
        )
        if isinstance(value, Document)
    )
    if normalization.source_annotations is None:
        raise ValueError("E3C source annotations are missing")
    annotation_sets = tuple(
        value
        for value in _jsonl(
            context.store.read_bytes(normalization.source_annotations.sha256),
            SourceAnnotationSet,
        )
        if isinstance(value, SourceAnnotationSet)
    )
    ontology_bytes = context.store.read_bytes(ontology_sha256)
    hpo_index = load_hpo_index(
        ontology_bytes,
        release=hpo_recipe.value.release,
        ontology_sha256=ontology_sha256,
    )
    complete_manifest = map_e3c_umls_to_hpo(
        documents=documents,
        annotation_sets=annotation_sets,
        hpo_index=hpo_index,
        documents_sha256=normalization.documents.sha256,
        source_annotations_sha256=normalization.source_annotations.sha256,
    )
    selected_manifest = select_mapping_manifest(
        complete_manifest,
        selected_case_ids=tuple(
            record.source_case_id for record in selection.records
        ),
        selection_id=selection.selection_id,
        selection_sha256=selection_pointer.subject_sha256,
    )
    complete_bytes = complete_manifest.canonical_bytes()
    selected_bytes = selected_manifest.canonical_bytes()
    summary_bytes = canonical_json_bytes(
        complete_manifest.summary.model_dump(mode="json")
    )
    complete_ref = _reference(
        complete_bytes,
        schema_id="umls-hpo-mapping-manifest/v1",
        record_count=len(complete_manifest.records),
        store=context.store,
    )
    selected_ref = _reference(
        selected_bytes,
        schema_id="umls-hpo-mapping-manifest/v1",
        record_count=len(selected_manifest.records),
        store=context.store,
    )
    summary_ref = _reference(
        summary_bytes,
        schema_id="umls-hpo-mapping-summary/v1",
        record_count=1,
        store=context.store,
    )
    stage_manifest = E3cMappingStageManifest(
        mapping_id=mapping_recipe.value.mapping_id,
        normalization_sha256=normalization_pointer.subject_sha256,
        selection_sha256=selection_pointer.subject_sha256,
        ontology_sha256=ontology_sha256,
        recipe_sha256=mapping_recipe.sha256,
        complete=complete_ref,
        selected=selected_ref,
        summary=summary_ref,
    )
    stage_sha256 = context.store.put_bytes(stage_manifest.canonical_bytes())
    state.publish(
        stage="map-hpo",
        target="e3c",
        subject_role=ProvenanceSubjectRole.UMLS_HPO_MAPPING_MANIFEST,
        subject_sha256=stage_sha256,
        semantic_hashes=semantic,
    )
    finished = context.clock()
    run = RunManifest(
        run_id=context.run_id_provider(),
        stage="map-hpo",
        status=RunStatus.COMPLETE,
        started_at=finished,
        finished_at=finished,
        pipeline_commit=context.pipeline_commit,
        dirty_state=context.dirty_state,
        code_sha256=context.code_sha256,
        config_sha256=mapping_recipe.sha256,
        input_sha256=(
            normalization_pointer.subject_sha256,
            selection_pointer.subject_sha256,
            ontology_sha256,
        ),
        output_sha256=(
            stage_sha256,
            complete_ref.sha256,
            selected_ref.sha256,
            summary_ref.sha256,
        ),
        hpo_release=hpo_recipe.value.release,
        selection_id=selection.selection_id,
    )
    run_sha256 = context.store.put_bytes(
        canonical_json_bytes(run.model_dump(mode="json"))
    )
    context.store.put_bytes(
        ProvenanceRunLink(
            subject_role=ProvenanceSubjectRole.UMLS_HPO_MAPPING_MANIFEST,
            subject_sha256=stage_sha256,
            run_manifest_sha256=run_sha256,
        ).canonical_bytes()
    )
    return E3cMappingResult(
        stage_manifest_sha256=stage_sha256,
        complete_sha256=complete_ref.sha256,
        selected_sha256=selected_ref.sha256,
        summary_sha256=summary_ref.sha256,
        record_count=len(complete_manifest.records),
        selected_record_count=len(selected_manifest.records),
        reused=False,
    )

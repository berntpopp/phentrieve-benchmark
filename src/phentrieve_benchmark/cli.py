import subprocess
from pathlib import Path
from typing import Annotated, Literal

import typer

from phentrieve_benchmark import __version__
from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.review import ManualReviewStatus, ReviewRecord
from phentrieve_benchmark.models.translation import TranslationManifest
from phentrieve_benchmark.models.translation_review import (
    TranslationReviewImportManifest,
)
from phentrieve_benchmark.pipeline.map_hpo import map_hpo_e3c
from phentrieve_benchmark.pipeline.prepare import (
    PipelineContext,
    StageResult,
    acquire_target,
    normalize_target,
    prepare_target,
    select_e3c,
)
from phentrieve_benchmark.pipeline.translate import (
    estimate_prepared_translation,
    prepare_e3c_translation,
    recheck_e3c_translations,
    translate_e3c,
)
from phentrieve_benchmark.pipeline.translation_review import (
    export_translation_review,
    import_translation_review,
)
from phentrieve_benchmark.provenance.code_identity import code_sha256
from phentrieve_benchmark.translation.google_nmt import create_google_nmt_adapter
from phentrieve_benchmark.translation.pricing import load_translation_recipe
from phentrieve_benchmark.translation.variants import (
    resolve_translation_pointer,
    translation_recipe_path,
)
from phentrieve_benchmark.translation.view import (
    materialize_published_translation_view,
)

app = typer.Typer(no_args_is_help=True)
acquire_app = typer.Typer(no_args_is_help=True)
normalize_app = typer.Typer(no_args_is_help=True)
select_app = typer.Typer(no_args_is_help=True)
prepare_app = typer.Typer(no_args_is_help=True)
smoke_app = typer.Typer(no_args_is_help=True)
translate_app = typer.Typer(no_args_is_help=True)
materialize_app = typer.Typer(no_args_is_help=True)
materialize_translations_app = typer.Typer(no_args_is_help=True)
recheck_app = typer.Typer(no_args_is_help=True)
recheck_translations_app = typer.Typer(no_args_is_help=True)
map_hpo_app = typer.Typer(no_args_is_help=True)
review_workbook_app = typer.Typer(no_args_is_help=True)
DatasetRoot = Annotated[Path, typer.Option()]
ArtifactRoot = Annotated[Path, typer.Option()]
Cohort = Annotated[Literal["feasibility-30"], typer.Option()]
Variant = Annotated[str, typer.Option()]
app.add_typer(acquire_app, name="acquire")
app.add_typer(normalize_app, name="normalize")
app.add_typer(select_app, name="select")
app.add_typer(prepare_app, name="prepare")
app.add_typer(smoke_app, name="smoke")
app.add_typer(translate_app, name="translate")
app.add_typer(materialize_app, name="materialize")
materialize_app.add_typer(materialize_translations_app, name="translations")
app.add_typer(recheck_app, name="recheck")
recheck_app.add_typer(recheck_translations_app, name="translations")
app.add_typer(map_hpo_app, name="map-hpo")
app.add_typer(review_workbook_app, name="review-workbook")

_TRANSLATION_REVIEW_POLICY_ID = "e3c:translation-review/v1"


@app.callback()
def main() -> None:
    """Run Phentrieve Benchmark commands."""


@app.command()
def version() -> None:
    """Print the installed package version."""
    typer.echo(f"phentrieve-benchmark {__version__}")


def _pipeline_context(
    dataset_root: Path, artifact_root: Path
) -> PipelineContext:
    repository_root = Path.cwd().resolve()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    return PipelineContext(
        repository_root=repository_root,
        dataset_root=dataset_root.resolve(),
        artifact_root=artifact_root.resolve(),
        store=ArtifactStore(artifact_root.resolve() / "objects"),
        code_sha256=code_sha256(repository_root),
        pipeline_commit=commit,
        dirty_state=dirty,
    )


def _emit(result: StageResult) -> None:
    typer.echo(
        f"stage={result.stage} target={result.target} "
        f"subject_sha256={result.subject_sha256} "
        f"reused={str(result.reused).lower()}"
    )


def _resolve_review_translation_manifest(
    *, context: PipelineContext, variant: str
) -> TranslationManifest:
    recipe = load_translation_recipe(
        translation_recipe_path(context.dataset_root, variant)
    )
    pointer = resolve_translation_pointer(
        artifact_root=context.artifact_root,
        store=context.store,
        recipe_sha256=recipe.sha256,
    )
    return TranslationManifest.model_validate_json(
        context.store.read_bytes(pointer.subject_sha256), strict=True
    )


@review_workbook_app.command("export-e3c")
def export_e3c_review_workbook_command(
    destination: Path,
    include_nmt: Annotated[bool, typer.Option("--include-nmt")] = False,
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    context = _pipeline_context(dataset_root, artifact_root)
    tllm_manifest = _resolve_review_translation_manifest(
        context=context, variant="tllm"
    )
    nmt_manifest = (
        _resolve_review_translation_manifest(context=context, variant="nmt")
        if include_nmt
        else None
    )
    export_sha256 = export_translation_review(
        store=context.store,
        tllm_manifest=tllm_manifest,
        destination=destination.resolve(),
        review_policy_id=_TRANSLATION_REVIEW_POLICY_ID,
        nmt_manifest=nmt_manifest,
    )
    typer.echo(
        f"export_sha256={export_sha256} cases={len(tllm_manifest.records)}"
    )


@review_workbook_app.command("import-e3c")
def import_e3c_review_workbook_command(
    source: Path,
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    context = _pipeline_context(dataset_root, artifact_root)
    import_sha256 = import_translation_review(
        store=context.store, workbook_path=source.resolve()
    )
    manifest = TranslationReviewImportManifest.model_validate_json(
        context.store.read_bytes(import_sha256), strict=True
    )
    counts = {status: 0 for status in ManualReviewStatus}
    for entry in manifest.entries:
        record = ReviewRecord.model_validate_json(
            context.store.read_bytes(entry.review_record_sha256), strict=True
        )
        counts[record.manual_status] += 1
    typer.echo(
        f"import_sha256={import_sha256} cases={len(manifest.entries)} "
        f"accepted={counts[ManualReviewStatus.ACCEPTED]} "
        "changes_requested="
        f"{counts[ManualReviewStatus.CHANGES_REQUESTED]} "
        f"rejected={counts[ManualReviewStatus.REJECTED]}"
    )


@map_hpo_app.command("e3c")
def map_hpo_e3c_command(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    result = map_hpo_e3c(_pipeline_context(dataset_root, artifact_root))
    typer.echo(
        f"complete_sha256={result.complete_sha256} "
        f"selected_sha256={result.selected_sha256} "
        f"summary_sha256={result.summary_sha256} "
        f"records={result.record_count} "
        f"selected_records={result.selected_record_count} "
        f"reused={str(result.reused).lower()}"
    )


@translate_app.command("e3c")
def translate_e3c_command(
    project_id: Annotated[str, typer.Option()],
    variant: Variant = "nmt",
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    context = _pipeline_context(dataset_root, artifact_root)
    prepared = prepare_e3c_translation(context, project_id, variant)
    estimate = estimate_prepared_translation(prepared)
    typer.echo(
        f"variant={variant} model={prepared.recipe.model} "
        f"cases={estimate.case_count} "
        f"input_characters={estimate.input_codepoints} "
        f"upper_bound={estimate.cost.currency} "
        f"{estimate.cost.upper_bound:f}"
    )
    if not typer.confirm(
        f"Google translation ({prepared.recipe.model}) starten?"
    ):
        raise typer.Exit(code=1)
    result = translate_e3c(
        prepared=prepared,
        context=context,
        project_id=project_id,
        authorized=True,
        variant=variant,
        provider_factory=lambda: create_google_nmt_adapter(
            project_id=project_id,
            location=prepared.recipe.location,
            model=prepared.recipe.model,
        ),
    )
    typer.echo(
        f"subject_sha256={result.subject_sha256} "
        f"translated={result.translated_count} "
        f"failed={result.failed_count} reused={result.reused_count}"
    )


@materialize_translations_app.command("e3c")
def materialize_e3c_translations_command(
    variant: Variant = "nmt",
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    context = _pipeline_context(dataset_root, artifact_root)
    recipe = load_translation_recipe(
        translation_recipe_path(context.dataset_root, variant)
    )
    result = materialize_published_translation_view(
        artifact_root=context.artifact_root,
        store=context.store,
        recipe_sha256=recipe.sha256,
        variant=variant,
    )
    typer.echo(
        f"destination={result.destination} cases={result.case_count}"
    )


@recheck_translations_app.command("e3c")
def recheck_e3c_translations_command(
    variant: Variant = "nmt",
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    """Re-run the automatic checks over already translated artifacts."""
    context = _pipeline_context(dataset_root, artifact_root)
    result = recheck_e3c_translations(context, variant)
    typer.echo(
        f"subject_sha256={result.subject_sha256} "
        f"cases={result.case_count} changed={result.changed_count} "
        f"failed={result.failed_count}"
    )


@acquire_app.command("e3c")
def acquire_e3c(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    _emit(acquire_target("e3c", _pipeline_context(dataset_root, artifact_root)))


@acquire_app.command("raghpo")
def acquire_raghpo(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    _emit(
        acquire_target("raghpo", _pipeline_context(dataset_root, artifact_root))
    )


@normalize_app.command("e3c")
def normalize_e3c(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    _emit(normalize_target("e3c", _pipeline_context(dataset_root, artifact_root)))


@normalize_app.command("csc")
def normalize_csc(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    _emit(normalize_target("csc", _pipeline_context(dataset_root, artifact_root)))


@normalize_app.command("gsc")
def normalize_gsc(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    _emit(normalize_target("gsc", _pipeline_context(dataset_root, artifact_root)))


@select_app.command("e3c")
def select_e3c_command(
    cohort: Cohort = "feasibility-30",
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    _emit(
        select_e3c(
            cohort, _pipeline_context(dataset_root, artifact_root)
        )
    )


def _prepare_command(
    target: Literal["e3c", "csc", "gsc"],
    dataset_root: Path,
    artifact_root: Path,
) -> None:
    for result in prepare_target(
        target, _pipeline_context(dataset_root, artifact_root)
    ):
        _emit(result)


@prepare_app.command("e3c")
def prepare_e3c(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    _prepare_command("e3c", dataset_root, artifact_root)


@prepare_app.command("csc")
def prepare_csc(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    _prepare_command("csc", dataset_root, artifact_root)


@prepare_app.command("gsc")
def prepare_gsc(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    _prepare_command("gsc", dataset_root, artifact_root)


@smoke_app.command("live-download")
def smoke_live_download(
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    context = _pipeline_context(dataset_root, artifact_root)
    first = (
        *prepare_target("e3c", context),
        *prepare_target("csc", context),
        *prepare_target("gsc", context),
    )
    second = (
        *prepare_target("e3c", context),
        *prepare_target("csc", context),
        *prepare_target("gsc", context),
    )
    if [value.subject_sha256 for value in first] != [
        value.subject_sha256 for value in second
    ]:
        raise typer.Exit(code=2)
    for result in second:
        _emit(result)

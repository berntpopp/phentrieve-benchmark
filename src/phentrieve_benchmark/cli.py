import subprocess
from pathlib import Path
from typing import Annotated, Literal

import typer

from phentrieve_benchmark import __version__
from phentrieve_benchmark.artifacts.store import ArtifactStore
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
    translate_e3c,
)
from phentrieve_benchmark.provenance.code_identity import code_sha256
from phentrieve_benchmark.translation.google_nmt import create_google_nmt_adapter

app = typer.Typer(no_args_is_help=True)
acquire_app = typer.Typer(no_args_is_help=True)
normalize_app = typer.Typer(no_args_is_help=True)
select_app = typer.Typer(no_args_is_help=True)
prepare_app = typer.Typer(no_args_is_help=True)
smoke_app = typer.Typer(no_args_is_help=True)
translate_app = typer.Typer(no_args_is_help=True)
map_hpo_app = typer.Typer(no_args_is_help=True)
DatasetRoot = Annotated[Path, typer.Option()]
ArtifactRoot = Annotated[Path, typer.Option()]
Cohort = Annotated[Literal["feasibility-30"], typer.Option()]
app.add_typer(acquire_app, name="acquire")
app.add_typer(normalize_app, name="normalize")
app.add_typer(select_app, name="select")
app.add_typer(prepare_app, name="prepare")
app.add_typer(smoke_app, name="smoke")
app.add_typer(translate_app, name="translate")
app.add_typer(map_hpo_app, name="map-hpo")


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
    location: Annotated[str, typer.Option()] = "global",
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    context = _pipeline_context(dataset_root, artifact_root)
    prepared = prepare_e3c_translation(context, project_id)
    estimate = estimate_prepared_translation(prepared)
    typer.echo(
        f"cases={estimate.case_count} "
        f"input_characters={estimate.input_codepoints} "
        f"upper_bound={estimate.cost.currency} "
        f"{estimate.cost.upper_bound:f}"
    )
    if not typer.confirm("Google NMT translation starten?"):
        raise typer.Exit(code=1)
    result = translate_e3c(
        prepared=prepared,
        context=context,
        project_id=project_id,
        authorized=True,
        provider_factory=lambda: create_google_nmt_adapter(
            project_id=project_id, location=location
        ),
    )
    typer.echo(
        f"subject_sha256={result.subject_sha256} "
        f"translated={result.translated_count} "
        f"failed={result.failed_count} reused={result.reused_count}"
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

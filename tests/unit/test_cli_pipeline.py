from pathlib import Path

from typer.testing import CliRunner

from phentrieve_benchmark import cli
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.pipeline.prepare import StageResult


def test_acquire_command_prints_only_stable_stage_identity(
    tmp_path: Path, monkeypatch: object
) -> None:
    result = StageResult(
        stage="acquire",
        target="e3c",
        subject_role=ProvenanceSubjectRole.SOURCE_SNAPSHOT,
        subject_sha256="a" * 64,
        run_manifest_sha256="b" * 64,
        provenance_link_sha256="c" * 64,
        reused=False,
    )
    monkeypatch.setattr(cli, "acquire_target", lambda *_: result)  # type: ignore[attr-defined]
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: object())  # type: ignore[attr-defined]

    invocation = CliRunner().invoke(
        cli.app,
        [
            "acquire",
            "e3c",
            "--dataset-root",
            str(tmp_path / "datasets"),
            "--artifact-root",
            str(tmp_path / "artifacts"),
        ],
    )

    assert invocation.exit_code == 0
    assert (
        invocation.stdout
        == f"stage=acquire target=e3c subject_sha256={'a' * 64} reused=false\n"
    )


def test_pipeline_command_groups_are_exposed() -> None:
    help_text = CliRunner().invoke(cli.app, ["--help"]).stdout

    for command in ("acquire", "normalize", "select", "prepare", "smoke"):
        assert command in help_text

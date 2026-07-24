from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

from phentrieve_benchmark import cli
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.pipeline.prepare import StageResult
from phentrieve_benchmark.pipeline.translate import (
    TranslationEstimate,
    TranslationStageResult,
)
from phentrieve_benchmark.policies.paid_operations import CostEstimate


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

    for command in (
        "acquire",
        "normalize",
        "select",
        "prepare",
        "translate",
        "map-hpo",
        "smoke",
    ):
        assert command in help_text


def test_translate_command_stops_before_provider_when_declined(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: object())  # type: ignore[attr-defined]
    monkeypatch.setattr(
        cli, "prepare_e3c_translation", lambda *_: object()
    )  # type: ignore[attr-defined]
    monkeypatch.setattr(
        cli,
        "estimate_prepared_translation",
        lambda *_: TranslationEstimate(
            case_count=30,
            input_codepoints=59_517,
            cost=CostEstimate(
                currency="USD",
                estimated_cost=Decimal("1.19034"),
                upper_bound=Decimal("1.19034"),
                pricing_snapshot_id="google-cloud-translation-2026-07-24",
            ),
        ),
    )  # type: ignore[attr-defined]
    calls: list[object] = []
    monkeypatch.setattr(
        cli, "translate_e3c", lambda **_: calls.append(object())
    )  # type: ignore[attr-defined]

    invocation = CliRunner().invoke(
        cli.app,
        ["translate", "e3c", "--project-id", "benchmark-project"],
        input="n\n",
    )

    assert invocation.exit_code == 1
    assert "59517" in invocation.stdout
    assert "USD 1.19034" in invocation.stdout
    assert calls == []


def test_translate_command_delegates_after_confirmation(
    monkeypatch: object,
) -> None:
    prepared = object()
    context = object()
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: context)  # type: ignore[attr-defined]
    monkeypatch.setattr(
        cli, "prepare_e3c_translation", lambda *_: prepared
    )  # type: ignore[attr-defined]
    monkeypatch.setattr(
        cli,
        "estimate_prepared_translation",
        lambda *_: TranslationEstimate(
            case_count=1,
            input_codepoints=22,
            cost=CostEstimate(
                currency="USD",
                estimated_cost=Decimal("0.00044"),
                upper_bound=Decimal("0.00044"),
                pricing_snapshot_id="google-cloud-translation-2026-07-24",
            ),
        ),
    )  # type: ignore[attr-defined]
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        cli,
        "translate_e3c",
        lambda **kwargs: calls.append(kwargs)
        or TranslationStageResult(authorized=True, subject_sha256="a" * 64),
    )  # type: ignore[attr-defined]

    invocation = CliRunner().invoke(
        cli.app,
        ["translate", "e3c", "--project-id", "benchmark-project"],
        input="y\n",
    )

    assert invocation.exit_code == 0, invocation.exception
    assert calls[0]["prepared"] is prepared
    assert calls[0]["context"] is context


def test_map_hpo_command_delegates_to_independent_stage(
    monkeypatch: object,
) -> None:
    context = object()
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: context)  # type: ignore[attr-defined]
    calls: list[object] = []
    monkeypatch.setattr(
        cli,
        "map_hpo_e3c",
        lambda value: calls.append(value)
        or type(
            "Result",
            (),
            {
                "complete_sha256": "a" * 64,
                "selected_sha256": "b" * 64,
                    "summary_sha256": "c" * 64,
                    "record_count": 12,
                    "selected_record_count": 3,
                    "reused": False,
            },
        )(),
    )  # type: ignore[attr-defined]

    invocation = CliRunner().invoke(cli.app, ["map-hpo", "e3c"])

    assert invocation.exit_code == 0, invocation.exception
    assert calls == [context]
    assert "records=12" in invocation.stdout


def test_all_thin_commands_delegate_to_stage_services(
    tmp_path: Path, monkeypatch: object
) -> None:
    result = StageResult(
        stage="normalize",
        target="csc",
        subject_role=ProvenanceSubjectRole.NORMALIZATION_MANIFEST,
        subject_sha256="a" * 64,
        run_manifest_sha256="b" * 64,
        provenance_link_sha256="c" * 64,
        reused=True,
    )
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: object())  # type: ignore[attr-defined]
    monkeypatch.setattr(cli, "acquire_target", lambda *_: result)  # type: ignore[attr-defined]
    monkeypatch.setattr(cli, "normalize_target", lambda *_: result)  # type: ignore[attr-defined]
    monkeypatch.setattr(cli, "select_e3c", lambda *_: result)  # type: ignore[attr-defined]
    monkeypatch.setattr(cli, "prepare_target", lambda *_: (result,))  # type: ignore[attr-defined]
    runner = CliRunner()
    roots = [
        "--dataset-root",
        str(tmp_path / "datasets"),
        "--artifact-root",
        str(tmp_path / "artifacts"),
    ]

    commands = [
        ["acquire", "raghpo"],
        ["normalize", "e3c"],
        ["normalize", "csc"],
        ["normalize", "gsc"],
        ["select", "e3c", "--cohort", "feasibility-30"],
        ["prepare", "e3c"],
        ["prepare", "csc"],
        ["prepare", "gsc"],
    ]
    for command in commands:
        invocation = runner.invoke(cli.app, [*command, *roots])
        assert invocation.exit_code == 0, invocation.exception

    smoke = runner.invoke(cli.app, ["smoke", "live-download", *roots])
    assert smoke.exit_code == 0, smoke.exception

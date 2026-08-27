from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

from phentrieve_benchmark import cli
from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.models.review import (
    ManualReviewRequirement,
    ManualReviewStatus,
    ReviewKind,
    ReviewRecord,
)
from phentrieve_benchmark.models.translation_review import (
    TranslationReviewImportEntry,
    TranslationReviewImportManifest,
)
from phentrieve_benchmark.pipeline.prepare import StageResult
from phentrieve_benchmark.pipeline.translate import (
    TranslationEstimate,
    TranslationStageResult,
)
from phentrieve_benchmark.policies.paid_operations import CostEstimate
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes


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
        "review-workbook",
        "map-hpo",
        "smoke",
    ):
        assert command in help_text


def test_review_workbook_export_resolves_tllm_and_omits_nmt_by_default(
    tmp_path: Path, monkeypatch: object
) -> None:
    tllm_manifest = type("Manifest", (), {"records": (object(),) * 30})()
    nmt_manifest = object()
    context = type(
        "Context",
        (),
        {
            "store": object(),
            "artifact_root": tmp_path / "artifacts",
            "dataset_root": tmp_path / "datasets",
        },
    )()
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: context)  # type: ignore[attr-defined]
    monkeypatch.setattr(
        cli,
        "_resolve_review_translation_manifest",
        lambda *, context, variant: {
            "tllm": tllm_manifest,
            "nmt": nmt_manifest,
        }[variant],
    )  # type: ignore[attr-defined]
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        cli,
        "export_translation_review",
        lambda **kwargs: calls.append(kwargs) or "a" * 64,
    )  # type: ignore[attr-defined]
    destination = tmp_path / "review.xlsx"

    invocation = CliRunner().invoke(
        cli.app,
        ["review-workbook", "export-e3c", str(destination)],
    )

    assert invocation.exit_code == 0, invocation.exception
    assert calls == [
        {
            "store": context.store,
            "tllm_manifest": tllm_manifest,
            "destination": destination.resolve(),
            "review_policy_id": "e3c:translation-review/v1",
            "nmt_manifest": None,
            "source_language": None,
        }
    ]
    assert invocation.stdout == f"export_sha256={'a' * 64} cases=30\n"


def test_review_workbook_export_resolves_nmt_only_when_requested(
    tmp_path: Path, monkeypatch: object
) -> None:
    resolved: list[str] = []
    tllm_manifest = type("Manifest", (), {"records": (object(),) * 30})()
    nmt_manifest = object()
    context = type(
        "Context",
        (),
        {
            "store": object(),
            "artifact_root": tmp_path / "artifacts",
            "dataset_root": tmp_path / "datasets",
        },
    )()
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: context)  # type: ignore[attr-defined]
    monkeypatch.setattr(
        cli,
        "_resolve_review_translation_manifest",
        lambda *, context, variant: resolved.append(variant)
        or {"tllm": tllm_manifest, "nmt": nmt_manifest}[variant],
    )  # type: ignore[attr-defined]
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        cli,
        "export_translation_review",
        lambda **kwargs: calls.append(kwargs) or "a" * 64,
    )  # type: ignore[attr-defined]

    invocation = CliRunner().invoke(
        cli.app,
        [
            "review-workbook",
            "export-e3c",
            str(tmp_path / "review.xlsx"),
            "--include-nmt",
        ],
    )

    assert invocation.exit_code == 0, invocation.exception
    assert resolved == ["tllm", "nmt"]
    assert calls[0]["nmt_manifest"] is nmt_manifest


def test_review_workbook_import_prints_manifest_and_status_counts(
    tmp_path: Path, monkeypatch: object
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    statuses = (
        ManualReviewStatus.ACCEPTED,
        ManualReviewStatus.CHANGES_REQUESTED,
        ManualReviewStatus.REJECTED,
    )
    entries = []
    for index, status in enumerate(statuses):
        record = ReviewRecord(
            review_id=f"review-{index}",
            review_kind=ReviewKind.BILINGUAL,
            subject_sha256=str(index + 1) * 64,
            review_policy_id="e3c:translation-review/v1",
            manual_requirement=ManualReviewRequirement.REQUIRED,
            manual_status=status,
            reviewer_role="Ärztin",
        )
        review_record_sha256 = store.put_bytes(
            canonical_json_bytes(record.model_dump(mode="json"))
        )
        entries.append(
            TranslationReviewImportEntry(
                source_case_id=f"case-{index}",
                record_sha256="a" * 64,
                review_record_sha256=review_record_sha256,
                proposed_text_sha256="b" * 64,
                diff_sha256="c" * 64,
            )
        )
    manifest = TranslationReviewImportManifest(
        export_sha256="d" * 64,
        entries=tuple(entries),
    )
    import_sha256 = store.put_bytes(manifest.canonical_bytes())
    context = type("Context", (), {"store": store})()
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: context)  # type: ignore[attr-defined]
    monkeypatch.setattr(
        cli, "import_translation_review", lambda **_: import_sha256
    )  # type: ignore[attr-defined]

    invocation = CliRunner().invoke(
        cli.app,
        ["review-workbook", "import-e3c", str(tmp_path / "review.xlsx")],
    )

    assert invocation.exit_code == 0, invocation.exception
    assert invocation.stdout == (
        f"import_sha256={import_sha256} cases=3 accepted=1 "
        "changes_requested=1 rejected=1\n"
    )


@dataclass(frozen=True)
class _PreparedStub:
    recipe: object
    previous_manifest: object | None = None


def _prepared_stub(*, previous_manifest: object | None = None) -> object:
    recipe = type(
        "Recipe", (), {"model": "general/nmt", "location": "global"}
    )()
    return _PreparedStub(
        recipe=recipe, previous_manifest=previous_manifest
    )


def test_full_tllm_command_stops_before_provider_when_declined(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: object())  # type: ignore[attr-defined]
    prepared_variants: list[str] = []
    monkeypatch.setattr(
        cli,
        "prepare_e3c_translation",
        lambda _context, _project, variant: prepared_variants.append(variant)
        or _prepared_stub(),
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
        [
            "translate",
            "e3c",
            "--project-id",
            "benchmark-project",
            "--variant",
            "tllm-full",
        ],
        input="n\n",
    )

    assert invocation.exit_code == 1
    assert "59517" in invocation.stdout
    assert "USD 1.19034" in invocation.stdout
    assert prepared_variants == ["tllm-full"]
    assert calls == []


def test_full_tllm_retranslate_all_previews_every_case_without_reuse(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: object())  # type: ignore[attr-defined]
    prior_manifest = object()
    monkeypatch.setattr(
        cli,
        "prepare_e3c_translation",
        lambda *_: _prepared_stub(previous_manifest=prior_manifest),
    )  # type: ignore[attr-defined]
    estimated_previous: list[object | None] = []

    def estimate(prepared: _PreparedStub) -> TranslationEstimate:
        estimated_previous.append(prepared.previous_manifest)
        return TranslationEstimate(
            case_count=246,
            input_codepoints=500_931,
            cost=CostEstimate(
                currency="USD",
                estimated_cost=Decimal("11.521413"),
                upper_bound=Decimal("11.521413"),
                pricing_snapshot_id="google-cloud-translation-llm-2026-07-27",
            ),
        )

    monkeypatch.setattr(cli, "estimate_prepared_translation", estimate)  # type: ignore[attr-defined]
    provider_calls: list[object] = []
    monkeypatch.setattr(
        cli, "translate_e3c", lambda **_: provider_calls.append(object())
    )  # type: ignore[attr-defined]

    invocation = CliRunner().invoke(
        cli.app,
        [
            "translate",
            "e3c",
            "--project-id",
            "phentrieve",
            "--variant",
            "tllm-full",
            "--retranslate-all",
        ],
        input="n\n",
    )

    assert invocation.exit_code == 1
    assert "cases=246" in invocation.stdout
    assert "input_characters=500931" in invocation.stdout
    assert "upper_bound=USD 11.521413" in invocation.stdout
    assert estimated_previous == [None]
    assert provider_calls == []


def test_retranslate_all_rejects_non_full_variant() -> None:
    invocation = CliRunner().invoke(
        cli.app,
        [
            "translate",
            "e3c",
            "--project-id",
            "phentrieve",
            "--variant",
            "tllm",
            "--retranslate-all",
        ],
    )

    assert invocation.exit_code == 2
    assert "requires --variant tllm-full" in invocation.stderr


def test_translate_command_delegates_after_confirmation(
    monkeypatch: object,
) -> None:
    prepared = _prepared_stub()
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


def test_materialize_translation_command_rebuilds_existing_view(
    monkeypatch: object,
) -> None:
    context = type(
        "Context",
        (),
        {
            "store": object(),
            "artifact_root": Path("artifacts"),
            "dataset_root": Path(__file__).parents[2] / "datasets",
        },
    )()
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: context)  # type: ignore[attr-defined]
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        cli,
        "materialize_published_translation_view",
        lambda **kw: calls.append(kw)
        or type("Result", (), {"destination": Path("view"), "case_count": 1})(),
    )  # type: ignore[attr-defined]

    invocation = CliRunner().invoke(
        cli.app,
        ["materialize", "translations", "e3c", "--variant", "tllm"],
    )

    assert invocation.exit_code == 0, invocation.exception
    assert calls[0]["artifact_root"] == Path("artifacts")
    assert calls[0]["variant"] == "tllm"


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


def test_translate_command_accepts_a_variant() -> None:
    result = CliRunner().invoke(cli.app, ["translate", "e3c", "--help"])

    assert result.exit_code == 0
    assert "--variant" in result.stdout
    assert "--location" not in result.stdout


def test_recheck_and_materialize_accept_a_variant() -> None:
    runner = CliRunner()
    for command in (
        ["recheck", "translations", "e3c", "--help"],
        ["materialize", "translations", "e3c", "--help"],
    ):
        invocation = runner.invoke(cli.app, command)
        assert invocation.exit_code == 0, invocation.exception
        assert "--variant" in invocation.stdout


def test_review_workbook_export_filters_language_and_reports_that_count(
    tmp_path: Path, monkeypatch: object
) -> None:
    records = tuple(
        type("Record", (), {"source_language": language})()
        for language in ("en",) * 10 + ("es",) * 10 + ("fr",) * 10
    )
    tllm_manifest = type("Manifest", (), {"records": records})()
    context = type(
        "Context",
        (),
        {
            "store": object(),
            "artifact_root": tmp_path / "artifacts",
            "dataset_root": tmp_path / "datasets",
        },
    )()
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: context)  # type: ignore[attr-defined]
    monkeypatch.setattr(
        cli,
        "_resolve_review_translation_manifest",
        lambda *, context, variant: tllm_manifest,
    )  # type: ignore[attr-defined]
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        cli,
        "export_translation_review",
        lambda **kwargs: calls.append(kwargs) or "a" * 64,
    )  # type: ignore[attr-defined]
    destination = tmp_path / "review-fr.xlsx"

    invocation = CliRunner().invoke(
        cli.app,
        [
            "review-workbook",
            "export-e3c",
            str(destination),
            "--language",
            "fr",
        ],
    )

    assert invocation.exit_code == 0, invocation.exception
    assert calls[0]["source_language"] == "fr"
    assert invocation.stdout == f"export_sha256={'a' * 64} cases=10\n"

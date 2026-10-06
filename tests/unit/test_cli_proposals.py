import io
import subprocess
import sys
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from phentrieve_benchmark import cli
from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.hpo_proposal import (
    BatchDocument,
    ProposalBatch,
    ProposalRun,
    ProposalValidationReport,
    ValidationSummary,
)
from phentrieve_benchmark.proposals.validate import ProposalBatchError
from phentrieve_benchmark.selection.groups import AnnotationGroupManifest
from tests.fixtures.hpo import proposal_hpo_obo


def _run() -> ProposalRun:
    return ProposalRun(
        run_id="full-v1",
        run_date=date(2026, 10, 7),
        model_id="claude-sonnet-5-5",
        corpus_manifest_sha256="1" * 64,
        documents_sha256="2" * 64,
        hpo_release="v2026-06-23",
        ontology_sha256="3" * 64,
        prompt_sha256="4" * 64,
        guideline_path="docs/annotation-guidelines/hpo-span-annotation.md",
        guideline_commit="5" * 40,
        guideline_sha256="6" * 64,
        batches=(
            ProposalBatch(
                batch_id="batch-01",
                documents=(
                    BatchDocument(
                        document_id="d1",
                        document_sha256="7" * 64,
                        source_case_id="EN1",
                        annotation_language="en",
                    ),
                ),
            ),
        ),
    )


def _message(output: str) -> str:
    return " ".join(output.replace("\u2502", " ").split())


@pytest.mark.parametrize("option", [("--language", "en"), ("--case", "EN100001")])
def test_prepare_run_rejects_pilot_with_a_selection(option: tuple[str, str]) -> None:
    invocation = CliRunner().invoke(
        cli.app,
        [
            "proposals", "prepare-run", "pilot-v1",
            "--corpus", "a" * 64,
            "--model-id", "claude-sonnet-5-5",
            "--pilot", *option,
        ],
    )
    assert invocation.exit_code == 2
    assert "selects its own reports" in _message(invocation.stderr)


def test_prepare_run_delegates_with_pinned_inputs(
    tmp_path: Path, monkeypatch: Any
) -> None:
    dataset_root = tmp_path / "datasets"
    groups_path = dataset_root / cli._E3C_GROUPS
    groups_path.parent.mkdir(parents=True)
    groups_path.write_bytes(
        AnnotationGroupManifest(
            inventory_sha256="e" * 64, records=(), aggregate_sha256="f" * 64
        ).canonical_bytes()
    )
    blobs = {
        "docs/annotation-guidelines/hpo-span-annotation.md": b"# guideline\n",
        "configs/prompts/hpo-span-proposal-v2.md": b"template",
    }
    context = type(
        "Context",
        (),
        {
            "repository_root": tmp_path,
            "dataset_root": dataset_root,
            "artifact_root": tmp_path / "artifacts",
            "store": object(),
            "clock": lambda self: datetime(2026, 10, 7, 8, 0, tzinfo=UTC),
        },
    )()
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: context)
    monkeypatch.setattr(
        cli, "_committed_blob", lambda root, path: ("c" * 40, blobs[path.as_posix()])
    )
    monkeypatch.setattr(
        cli,
        "_pinned_hpo_sha256",
        lambda *_: (type("Recipe", (), {"release": "v2026-06-23"})(), "d" * 64),
    )
    calls: list[dict[str, Any]] = []

    def fake_prepare(**kwargs: Any) -> ProposalRun:
        calls.append(kwargs)
        return _run()

    monkeypatch.setattr(cli, "prepare_proposal_run", fake_prepare)

    invocation = CliRunner().invoke(
        cli.app,
        [
            "proposals", "prepare-run", "full-v1",
            "--corpus", "a" * 64,
            "--model-id", "claude-sonnet-5-5",
            "--language", "en", "--language", "fr",
            "--case", "EN100001", "--case", "FR100002",
        ],
    )

    assert invocation.exit_code == 0, invocation.exception
    (call,) = calls
    assert call["languages"] == ("en", "fr")
    assert call["case_ids"] == ("EN100001", "FR100002")
    assert call["pilot"] is False
    assert call["batch_size"] == 10
    assert call["run_date"] == date(2026, 10, 7)
    assert call["guideline"].commit == "c" * 40
    assert call["guideline"].sha256 == sha256(b"# guideline\n").hexdigest()
    assert call["ontology_sha256"] == "d" * 64
    assert call["prompt_template"] == b"template"
    assert call["run_directory"] == dataset_root / "e3c-de/proposals/full-v1"
    assert call["input_directory"] == tmp_path / "artifacts/proposals/full-v1"
    assert invocation.stdout.startswith(
        "run_id=full-v1 documents=1 batches=1 pending_review=0 "
    )


def _git(root: Path, *arguments: str) -> None:
    identity = ["-c", "user.name=test", "-c", "user.email=test@example.org"]
    subprocess.run(
        ["git", *identity, *arguments],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_committed_blob_returns_the_commit_and_committed_bytes(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "prompt.md").write_bytes(b"line one\nline two\n")
    _git(tmp_path, "add", "prompt.md")
    _git(tmp_path, "commit", "-q", "-m", "add prompt")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert cli._committed_blob(tmp_path, Path("prompt.md")) == (
        head,
        b"line one\nline two\n",
    )


def test_committed_blob_rejects_uncommitted_changes(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "prompt.md").write_bytes(b"one\n")
    _git(tmp_path, "add", "prompt.md")
    _git(tmp_path, "commit", "-q", "-m", "add prompt")
    (tmp_path / "prompt.md").write_bytes(b"two\n")
    with pytest.raises(typer.BadParameter, match="uncommitted changes"):
        cli._committed_blob(tmp_path, Path("prompt.md"))
    with pytest.raises(typer.BadParameter, match="not committed"):
        cli._committed_blob(tmp_path, Path("missing.md"))


def test_validate_reports_batch_errors_and_exits_nonzero(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(cli, "_pinned_hpo_index", lambda *_: object())

    def fail(**_: Any) -> None:
        raise ProposalBatchError("batch-02: reports differ from the batch")

    monkeypatch.setattr(cli, "validate_run_directory", fail)
    invocation = CliRunner().invoke(
        cli.app,
        ["proposals", "validate", "pilot-v1", "--artifact-root", str(tmp_path)],
    )
    assert invocation.exit_code == 1
    assert "batch-02" in invocation.stderr


def test_validate_reports_other_errors_without_a_traceback(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(cli, "_pinned_hpo_index", lambda *_: object())

    def fail(**_: Any) -> None:
        raise ValueError("prompt.md differs from the prompt recorded in run.json")

    monkeypatch.setattr(cli, "validate_run_directory", fail)
    invocation = CliRunner().invoke(
        cli.app,
        ["proposals", "validate", "pilot-v1", "--artifact-root", str(tmp_path)],
    )
    assert invocation.exit_code == 1
    assert invocation.stderr.startswith("error=prompt.md differs")


def test_validate_prints_the_summary(tmp_path: Path, monkeypatch: Any) -> None:
    report = ProposalValidationReport(
        run_id="pilot-v1",
        run_sha256="1" * 64,
        corpus_manifest_sha256="2" * 64,
        hpo_release="v2026-06-23",
        ontology_sha256="3" * 64,
        batches=(),
        documents=(),
        rejections=(),
        warnings=(),
        summary=ValidationSummary(
            documents=9,
            proposals_received=120,
            proposals_rejected=4,
            validated_proposals=110,
            mentions_evaluated=150,
            mentions_rejected=6,
            validated_mentions=144,
            rejections_by_reason={},
        ),
    )
    monkeypatch.setattr(cli, "_pinned_hpo_index", lambda *_: object())
    monkeypatch.setattr(
        cli, "validate_run_directory", lambda **_: (report, "f" * 64)
    )
    invocation = CliRunner().invoke(
        cli.app,
        ["proposals", "validate", "pilot-v1", "--artifact-root", str(tmp_path)],
    )
    assert invocation.exit_code == 0, invocation.exception
    assert invocation.stdout == (
        f"validation_sha256={'f' * 64} documents=9 proposals=120 "
        "rejected_proposals=4 validated_proposals=110 mentions=150 "
        "rejected_mentions=6 warnings=0\n"
    )


def test_hpo_lookup_prints_matches_per_query(
    tmp_path: Path, monkeypatch: Any
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    digest = store.put_bytes(proposal_hpo_obo())
    monkeypatch.setattr(cli, "_pinned_hpo_sha256", lambda *_: (object(), digest))
    invocation = CliRunner().invoke(
        cli.app,
        [
            "proposals", "hpo-lookup", "muscle pain", "HP:0009999", "nothing",
            "--artifact-root", str(tmp_path),
        ],
    )
    assert invocation.exit_code == 0, invocation.exception
    assert invocation.stdout == (
        "# muscle pain\n"
        "HP:0003326\tMyalgia\tsynonym: Muscle pain\n"
        "# HP:0009999\n"
        "HP:0009999\tObsolete fever variant\tobsolete\n"
        "# nothing\n"
        "(no match)\n"
    )


def test_hpo_lookup_prints_queries_outside_the_console_code_page(
    tmp_path: Path, monkeypatch: Any
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    digest = store.put_bytes(proposal_hpo_obo())
    monkeypatch.setattr(cli, "_pinned_hpo_sha256", lambda *_: (object(), digest))
    buffer = io.BytesIO()
    monkeypatch.setattr(
        sys, "stdout", io.TextIOWrapper(buffer, encoding="cp1252", newline="\n")
    )
    cli.hpo_lookup_command(["\u03b2-thalassemia", "fever"], 1, tmp_path)
    sys.stdout.flush()
    assert buffer.getvalue().decode("utf-8") == (
        "# \u03b2-thalassemia\n(no match)\n# fever\nHP:0001945\tFever\n"
    )

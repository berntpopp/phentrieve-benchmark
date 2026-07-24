from pathlib import Path

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.pipeline import prepare
from phentrieve_benchmark.pipeline.prepare import PipelineContext, StageResult
from phentrieve_benchmark.provenance.digests import sha256_bytes


def _result(stage: str, target: str) -> StageResult:
    return StageResult(
        stage=stage,
        target=target,
        subject_role=ProvenanceSubjectRole.SOURCE_SNAPSHOT
        if stage == "acquire"
        else ProvenanceSubjectRole.NORMALIZATION_MANIFEST,
        subject_sha256="a" * 64,
        run_manifest_sha256="b" * 64,
        provenance_link_sha256="c" * 64,
        reused=False,
    )


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("e3c", ["acquire:e3c", "normalize:e3c", "select:feasibility-30"]),
        ("csc", ["acquire:raghpo", "normalize:csc"]),
        ("gsc", ["acquire:raghpo", "normalize:gsc"]),
    ],
)
def test_prepare_runs_only_the_stages_for_its_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    expected: list[str],
) -> None:
    calls: list[str] = []
    context = PipelineContext(
        repository_root=tmp_path,
        dataset_root=tmp_path / "datasets",
        artifact_root=tmp_path / ".artifacts",
        store=ArtifactStore(tmp_path / ".artifacts" / "objects"),
        code_sha256="d" * 64,
        pipeline_commit="e" * 40,
        dirty_state=False,
    )

    def acquire(source_id: str, _: PipelineContext) -> StageResult:
        calls.append(f"acquire:{source_id}")
        return _result("acquire", source_id)

    def normalize(target_id: str, _: PipelineContext) -> StageResult:
        calls.append(f"normalize:{target_id}")
        return _result("normalize", target_id)

    def select(cohort: str, _: PipelineContext) -> StageResult:
        calls.append(f"select:{cohort}")
        return _result("select", "e3c")

    monkeypatch.setattr(prepare, "acquire_target", acquire)
    monkeypatch.setattr(prepare, "normalize_target", normalize)
    monkeypatch.setattr(prepare, "select_e3c", select)

    prepare.prepare_target(target, context)  # type: ignore[arg-type]

    assert calls == expected


def test_acquire_emits_subject_run_and_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_root = tmp_path / "datasets"
    recipe_path = dataset_root / "e3c-de" / "dataset.yaml"
    recipe_path.parent.mkdir(parents=True)
    recipe_path.write_text("synthetic recipe", encoding="utf-8")
    context = PipelineContext(
        repository_root=tmp_path,
        dataset_root=dataset_root,
        artifact_root=tmp_path / ".artifacts",
        store=ArtifactStore(tmp_path / ".artifacts" / "objects"),
        code_sha256="d" * 64,
        pipeline_commit="e" * 40,
        dirty_state=False,
    )
    subject = b'{"schema_version":"source-snapshot-manifest/v1"}'
    subject_sha256 = sha256_bytes(subject)

    class Loaded:
        sha256 = "f" * 64
        value = object()

    class Snapshot:
        def canonical_bytes(self) -> bytes:
            return subject

        def sha256(self) -> str:
            return subject_sha256

    monkeypatch.setattr(prepare, "load_source_recipe", lambda _: Loaded())
    monkeypatch.setattr(prepare, "_acquire_snapshot", lambda *_: Snapshot())

    result = prepare.acquire_target("e3c", context)

    assert result.subject_sha256 == subject_sha256
    assert context.store.read_bytes(result.subject_sha256) == subject
    assert context.store.read_bytes(result.run_manifest_sha256)
    assert context.store.read_bytes(result.provenance_link_sha256)

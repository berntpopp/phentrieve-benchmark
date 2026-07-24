from pathlib import Path
from types import SimpleNamespace

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.document import (
    Document,
    TranslationStatus,
)
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.normalization.contracts import NormalizedTarget
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


def test_normalize_consumes_verified_local_snapshot_without_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = PipelineContext(
        repository_root=tmp_path,
        dataset_root=tmp_path / "datasets",
        artifact_root=tmp_path / ".artifacts",
        store=ArtifactStore(tmp_path / ".artifacts" / "objects"),
        code_sha256="d" * 64,
        pipeline_commit="e" * 40,
        dirty_state=False,
    )
    snapshot_sha256 = context.store.put_bytes(b"snapshot")
    loaded_source = SimpleNamespace(sha256="1" * 64, value=object())
    loaded_target = SimpleNamespace(sha256="2" * 64, value=object())
    normalized = object()
    subject = b'{"schema_version":"normalization-manifest/v1"}'

    class FakeState:
        def __init__(self, *_: object) -> None:
            pass

        def reuse(self, *, stage: str, **_: object) -> object | None:
            if stage == "acquire":
                return SimpleNamespace(subject_sha256=snapshot_sha256)
            return None

        def publish(self, **_: object) -> None:
            return None

    monkeypatch.setattr(prepare, "StageState", FakeState)
    monkeypatch.setattr(prepare, "load_source_recipe", lambda *_: loaded_source)
    monkeypatch.setattr(prepare, "_load_target_config", lambda *_: loaded_target)
    monkeypatch.setattr(
        prepare.SourceSnapshotManifest,
        "model_validate_json",
        lambda *_args, **_kwargs: SimpleNamespace(members=()),
    )
    monkeypatch.setattr(
        prepare,
        "_normalize",
        lambda *_args, **_kwargs: normalized,
    )
    monkeypatch.setattr(
        prepare,
        "_publish_normalization",
        lambda **_kwargs: SimpleNamespace(canonical_bytes=lambda: subject),
    )
    monkeypatch.setattr(
        prepare,
        "acquire_target",
        lambda *_: pytest.fail("normalize must not acquire"),
    )

    result = prepare.normalize_target("csc", context)

    assert result.stage == "normalize"
    assert result.target == "csc"
    assert context.store.read_bytes(result.subject_sha256) == subject


def test_normalization_publication_creates_text_free_inventory_and_counts(
    tmp_path: Path,
) -> None:
    context = PipelineContext(
        repository_root=tmp_path,
        dataset_root=tmp_path / "datasets",
        artifact_root=tmp_path / ".artifacts",
        store=ArtifactStore(tmp_path / ".artifacts" / "objects"),
        code_sha256="d" * 64,
        pipeline_commit="e" * 40,
        dirty_state=False,
    )
    document = Document.from_text(
        source_case_id="case-1",
        case_group_id="synthetic:case-1",
        document_id="synthetic:csc:case-1:native",
        language="en",
        translation_status=TranslationStatus.NATIVE,
        text="Synthetic clinical fixture.",
    )
    normalized = NormalizedTarget(
        documents=(document,),
        counts=(("documents", 1),),
        warnings=(("annotations_without_evidence_spans", 0),),
    )
    source = SimpleNamespace(
        sha256="1" * 64,
        value=SimpleNamespace(adapter_id="synthetic-adapter/v1"),
    )
    target = SimpleNamespace(sha256="2" * 64, value=object())

    manifest = prepare._publish_normalization(
        target_id="csc",
        normalized=normalized,
        source_snapshot_sha256="3" * 64,
        source_recipe=source,
        target_recipe=target,
        context=context,
    )

    assert manifest.documents.record_count == 1
    assert manifest.inventory.record_count == 1
    assert context.store.read_bytes(manifest.documents.sha256)
    inventory = context.store.read_bytes(manifest.inventory.sha256)
    assert b"document_sha256" in inventory
    assert b"Synthetic clinical fixture." not in inventory
    assert manifest.counts[0].count == 1
    assert manifest.warnings[0].count == 0

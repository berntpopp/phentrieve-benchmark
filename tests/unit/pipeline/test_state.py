from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.pipeline.state import StageState
from phentrieve_benchmark.provenance.digests import sha256_bytes


def _digest(value: bytes) -> str:
    return sha256_bytes(value)


def test_published_state_is_reused_only_while_subject_is_verified(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    subject = b'{"schema_version":"example/v1"}'
    subject_sha256 = store.put_bytes(subject)
    state = StageState(tmp_path / "state", store)
    semantic = {
        "recipe_sha256": _digest(b"recipe"),
        "code_sha256": _digest(b"code"),
    }

    pointer = state.publish(
        stage="normalize",
        target="csc",
        subject_role=ProvenanceSubjectRole.SELECTION_MANIFEST,
        subject_sha256=subject_sha256,
        semantic_hashes=semantic,
    )

    assert state.reuse(
        stage="normalize", target="csc", semantic_hashes=semantic
    ) == pointer
    store.path_for(subject_sha256).write_bytes(b"corrupt")
    assert (
        state.reuse(
            stage="normalize", target="csc", semantic_hashes=semantic
        )
        is None
    )


def test_semantic_key_change_never_reuses_pointer(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    subject_sha256 = store.put_bytes(b"subject")
    state = StageState(tmp_path / "state", store)
    semantic = {
        "recipe_sha256": _digest(b"recipe"),
        "selection_seed_sha256": _digest(b"seed"),
    }
    state.publish(
        stage="select",
        target="e3c",
        subject_role=ProvenanceSubjectRole.SELECTION_MANIFEST,
        subject_sha256=subject_sha256,
        semantic_hashes=semantic,
    )

    changed = dict(semantic)
    changed["selection_seed_sha256"] = _digest(b"other-seed")
    assert state.reuse(stage="select", target="e3c", semantic_hashes=changed) is None


def test_pointer_contains_no_volatile_run_identity(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    subject_sha256 = store.put_bytes(b"subject")
    state = StageState(tmp_path / "state", store)
    semantic = {"input_sha256": _digest(b"input")}

    pointer = state.publish(
        stage="normalize",
        target="gsc",
        subject_role=ProvenanceSubjectRole.SELECTION_MANIFEST,
        subject_sha256=subject_sha256,
        semantic_hashes=semantic,
    )
    payload = state.path_for("normalize", "gsc", semantic).read_text("utf-8")

    assert pointer.semantic_hashes == semantic
    assert "run_id" not in payload
    assert "timestamp" not in payload

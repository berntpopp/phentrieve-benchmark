from pathlib import Path

import pytest

from phentrieve_benchmark.artifacts import store as store_module
from phentrieve_benchmark.artifacts.store import (
    ArtifactCorruptionError,
    ArtifactStore,
)
from phentrieve_benchmark.provenance.digests import sha256_bytes


def test_put_bytes_stores_and_deduplicates_content(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    digest = store.put_bytes(b"clinical fixture")

    assert digest == sha256_bytes(b"clinical fixture")
    assert store.read_bytes(digest) == b"clinical fixture"
    assert store.put_bytes(b"clinical fixture") == digest


def test_put_bytes_rejects_corrupt_existing_artifact(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    digest = sha256_bytes(b"expected")
    destination = store.path_for(digest)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"corrupt")

    with pytest.raises(ArtifactCorruptionError):
        store.put_bytes(b"expected")


@pytest.mark.parametrize("digest", ["A" * 64, "a" * 63])
def test_path_for_rejects_invalid_digest(tmp_path: Path, digest: str) -> None:
    with pytest.raises(ValueError):
        ArtifactStore(tmp_path).path_for(digest)


def test_read_bytes_rejects_corrupt_artifact(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    digest = sha256_bytes(b"expected")
    destination = store.path_for(digest)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"corrupt")

    with pytest.raises(ArtifactCorruptionError):
        store.read_bytes(digest)


def test_put_bytes_accepts_concurrent_publication_after_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ArtifactStore(tmp_path)
    value = b"concurrent fixture"
    digest = sha256_bytes(value)
    destination = store.path_for(digest)

    def publish_then_fail(source: Path, target: Path) -> None:
        assert target == destination
        target.write_bytes(source.read_bytes())
        raise OSError("destination was concurrently published")

    monkeypatch.setattr(store_module.os, "replace", publish_then_fail)

    assert store.put_bytes(value) == digest
    assert destination.read_bytes() == value
    assert not list(destination.parent.glob(f".{digest}.*"))


def test_put_bytes_rejects_corrupt_concurrent_publication_after_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ArtifactStore(tmp_path)
    value = b"concurrent fixture"

    def publish_corrupt_then_fail(source: Path, target: Path) -> None:
        del source
        target.write_bytes(b"corrupt")
        raise OSError("destination was concurrently published")

    monkeypatch.setattr(store_module.os, "replace", publish_corrupt_then_fail)

    with pytest.raises(ArtifactCorruptionError):
        store.put_bytes(value)


def test_put_bytes_closes_descriptor_and_removes_temp_when_fdopen_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ArtifactStore(tmp_path)
    closed_descriptors: list[int] = []
    original_close = store_module.os.close

    def fail_fdopen(file_descriptor: int, mode: str) -> None:
        del file_descriptor, mode
        raise OSError("fdopen failed")

    def track_close(file_descriptor: int) -> None:
        closed_descriptors.append(file_descriptor)
        original_close(file_descriptor)

    monkeypatch.setattr(store_module.os, "fdopen", fail_fdopen)
    monkeypatch.setattr(store_module.os, "close", track_close)

    with pytest.raises(OSError, match="fdopen failed"):
        store.put_bytes(b"fdopen fixture")

    assert closed_descriptors
    digest = sha256_bytes(b"fdopen fixture")
    assert not list(store.path_for(digest).parent.glob(f".{digest}.*"))


def test_put_bytes_syncs_directory_after_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ArtifactStore(tmp_path)
    digest = sha256_bytes(b"directory sync")
    destination = store.path_for(digest)
    destination.parent.mkdir(parents=True)
    synced_directories: list[Path] = []

    monkeypatch.setattr(
        store_module,
        "_fsync_directory",
        lambda directory: synced_directories.append(directory),
    )

    store.put_bytes(b"directory sync")

    assert synced_directories == [
        tmp_path.parent,
        tmp_path,
        tmp_path / "sha256",
        destination.parent,
    ]


def test_put_bytes_syncs_new_directory_entries_in_creation_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "artifact-root"
    store = ArtifactStore(root)
    digest = sha256_bytes(b"directory creation")
    destination = store.path_for(digest)
    synced_directories: list[Path] = []

    monkeypatch.setattr(
        store_module,
        "_fsync_directory",
        lambda directory: synced_directories.append(directory),
    )

    store.put_bytes(b"directory creation")

    assert synced_directories == [
        tmp_path,
        root,
        root / "sha256",
        destination.parent,
    ]


def test_put_bytes_retries_destination_directory_sync_after_publish_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ArtifactStore(tmp_path)
    value = b"retry publication sync"
    digest = sha256_bytes(value)
    destination = store.path_for(digest)
    destination.parent.mkdir(parents=True)
    synced_directories: list[Path] = []

    def fail_once(directory: Path) -> None:
        synced_directories.append(directory)
        if (
            directory == destination.parent
            and synced_directories.count(destination.parent) == 1
        ):
            raise OSError("directory sync failed")

    monkeypatch.setattr(store_module, "_fsync_directory", fail_once)

    with pytest.raises(OSError, match="directory sync failed"):
        store.put_bytes(value)

    assert destination.read_bytes() == value
    assert store.put_bytes(value) == digest
    assert [
        directory for directory in synced_directories if directory == destination.parent
    ] == [destination.parent, destination.parent]


def test_put_bytes_retries_directory_chain_sync_after_creation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "retry-root"
    store = ArtifactStore(root)
    value = b"retry directory creation"
    destination = store.path_for(sha256_bytes(value))
    synced_directories: list[Path] = []

    def fail_once(directory: Path) -> None:
        synced_directories.append(directory)
        if len(synced_directories) == 1:
            raise OSError("directory sync failed")

    monkeypatch.setattr(store_module, "_fsync_directory", fail_once)

    with pytest.raises(OSError, match="directory sync failed"):
        store.put_bytes(value)

    assert root.is_dir()
    store.put_bytes(value)
    assert synced_directories == [
        tmp_path,
        tmp_path,
        root,
        root / "sha256",
        destination.parent,
    ]


def test_put_bytes_syncs_temp_deletion_after_concurrent_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ArtifactStore(tmp_path)
    value = b"concurrent deletion sync"
    digest = sha256_bytes(value)
    destination = store.path_for(digest)
    synced_directories: list[Path] = []

    def publish_then_fail(source: Path, target: Path) -> None:
        target.write_bytes(source.read_bytes())
        raise OSError("destination was concurrently published")

    monkeypatch.setattr(store_module.os, "replace", publish_then_fail)
    monkeypatch.setattr(
        store_module,
        "_fsync_directory",
        lambda directory: synced_directories.append(directory),
    )

    assert store.put_bytes(value) == digest
    assert synced_directories == [
        tmp_path.parent,
        tmp_path,
        tmp_path / "sha256",
        destination.parent,
        destination.parent,
    ]


def test_fsync_directory_is_a_no_op_on_non_posix_platforms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_open(path: Path, flags: int) -> int:
        del path, flags
        raise AssertionError("unsupported platforms must not open directories")

    monkeypatch.setattr(store_module.os, "name", "nt")
    monkeypatch.setattr(store_module.os, "open", fail_open)

    store_module._fsync_directory(tmp_path)

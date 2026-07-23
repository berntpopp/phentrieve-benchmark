from pathlib import Path

import pytest

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

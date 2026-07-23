import os
import re
import tempfile
from pathlib import Path

from phentrieve_benchmark.provenance.digests import sha256_bytes

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ArtifactCorruptionError(RuntimeError):
    """An artifact's contents do not match its digest."""


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, digest: str) -> Path:
        if _SHA256_PATTERN.fullmatch(digest) is None:
            raise ValueError(
                "digest must be exactly 64 lowercase hexadecimal characters"
            )
        return self.root / "sha256" / digest[:2] / digest

    def put_bytes(self, value: bytes) -> str:
        digest = sha256_bytes(value)
        destination = self.path_for(digest)
        if destination.exists():
            self._verify(destination, digest)
            return digest

        destination.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{digest}.", dir=destination.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "wb") as temporary_file:
                temporary_file.write(value)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
        return digest

    def read_bytes(self, digest: str) -> bytes:
        artifact = self.path_for(digest)
        value = artifact.read_bytes()
        if sha256_bytes(value) != digest:
            raise ArtifactCorruptionError(f"artifact is corrupt: {digest}")
        return value

    def _verify(self, artifact: Path, digest: str) -> None:
        if sha256_bytes(artifact.read_bytes()) != digest:
            raise ArtifactCorruptionError(f"artifact is corrupt: {digest}")

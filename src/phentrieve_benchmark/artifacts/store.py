import os
import re
import tempfile
from contextlib import suppress
from pathlib import Path

from phentrieve_benchmark.provenance.digests import sha256_bytes

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ArtifactCorruptionError(RuntimeError):
    """An artifact's contents do not match its digest."""


class ArtifactStore:
    """Content-addressed artifacts rooted in a trusted local directory.

    On Windows, directory-entry durability is weaker because directory fsync is
    unavailable; successful file replacement is still atomic.
    """

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

        self._ensure_directory(destination.parent)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{digest}.", dir=destination.parent
        )
        temporary_path = Path(temporary_name)
        descriptor_is_open = True
        try:
            temporary_file = os.fdopen(file_descriptor, "wb")
            descriptor_is_open = False
            with temporary_file:
                temporary_file.write(value)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            if destination.exists():
                self._verify(destination, digest)
            else:
                try:
                    os.replace(temporary_path, destination)
                except OSError:
                    if destination.exists():
                        self._verify(destination, digest)
                    else:
                        raise
                else:
                    _fsync_directory(destination.parent)
        except BaseException:
            if descriptor_is_open:
                with suppress(OSError):
                    os.close(file_descriptor)
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
            raise
        else:
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

    def _ensure_directory(self, directory: Path) -> None:
        missing_directories: list[Path] = []
        current = directory
        while not current.exists():
            missing_directories.append(current)
            current = current.parent
        for missing_directory in reversed(missing_directories):
            try:
                missing_directory.mkdir()
            except FileExistsError:
                if not missing_directory.is_dir():
                    raise
            else:
                _fsync_directory(missing_directory.parent)


def _fsync_directory(directory: Path) -> None:
    """Persist a directory entry on POSIX; Windows has no equivalent flush API."""
    if os.name != "posix":
        return
    directory_descriptor = os.open(
        directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    )
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)

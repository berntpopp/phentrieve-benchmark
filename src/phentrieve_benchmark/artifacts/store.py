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
        self._root_directory_chain: list[Path] = []

    def path_for(self, digest: str) -> Path:
        if _SHA256_PATTERN.fullmatch(digest) is None:
            raise ValueError(
                "digest must be exactly 64 lowercase hexadecimal characters"
            )
        return self.root / "sha256" / digest[:2] / digest

    def put_bytes(self, value: bytes) -> str:
        digest = sha256_bytes(value)
        destination = self.path_for(digest)
        self._ensure_directory(destination.parent)
        if destination.exists():
            self._verify(destination, digest)
            _fsync_directory(destination.parent)
            return digest

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
                _fsync_directory(destination.parent)
            else:
                try:
                    os.replace(temporary_path, destination)
                except OSError:
                    if destination.exists():
                        self._verify(destination, digest)
                        _fsync_directory(destination.parent)
                    else:
                        raise
                else:
                    _fsync_directory(destination.parent)
        except BaseException:
            if descriptor_is_open:
                with suppress(OSError):
                    os.close(file_descriptor)
            with suppress(OSError):
                _unlink_temporary(temporary_path)
            raise
        else:
            _unlink_temporary(temporary_path)
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
        if not self._root_directory_chain:
            missing_ancestors: list[Path] = []
            ancestor = self.root
            while not ancestor.exists():
                missing_ancestors.append(ancestor)
                ancestor = ancestor.parent
            self._root_directory_chain = list(reversed(missing_ancestors)) or [
                self.root
            ]
        chain = [
            *self._root_directory_chain,
            self.root / "sha256",
            directory,
        ]
        for chain_directory in chain:
            try:
                chain_directory.mkdir()
            except FileExistsError:
                if not chain_directory.is_dir():
                    raise
            _fsync_directory(chain_directory.parent)


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


def _unlink_temporary(temporary_path: Path) -> None:
    try:
        temporary_path.unlink()
    except FileNotFoundError:
        return
    _fsync_directory(temporary_path.parent)

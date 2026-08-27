import os
import re
import stat
import tempfile
from contextlib import suppress
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO

from phentrieve_benchmark.provenance.digests import sha256_bytes

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ArtifactCorruptionError(RuntimeError):
    """An artifact's contents do not match its digest."""


class ArtifactIntegrityError(ValueError):
    """A source file does not match its declared or stable identity."""


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

    def put_file(
        self,
        source: Path,
        *,
        expected_sha256: str | None = None,
        expected_byte_length: int | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> tuple[str, int]:
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        if (
            expected_sha256 is not None
            and _SHA256_PATTERN.fullmatch(expected_sha256) is None
        ):
            raise ValueError(
                "expected_sha256 must be exactly 64 lowercase hexadecimal characters"
            )
        if (
            expected_byte_length is not None
            and (
                type(expected_byte_length) is not int
                or expected_byte_length < 0
            )
        ):
            raise ValueError("expected_byte_length must be a non-negative integer")

        digest, byte_length, source_snapshot = _stream_stable_file(
            source,
            chunk_size=chunk_size,
        )
        if expected_sha256 is not None and digest != expected_sha256:
            raise ArtifactIntegrityError(
                f"digest mismatch: expected {expected_sha256}, got {digest}"
            )
        if (
            expected_byte_length is not None
            and byte_length != expected_byte_length
        ):
            raise ArtifactIntegrityError(
                "byte length mismatch: "
                f"expected {expected_byte_length}, got {byte_length}"
            )

        destination = self.path_for(digest)
        self._ensure_directory(destination.parent)
        if destination.exists():
            self._verify(destination, digest)
            _fsync_directory(destination.parent)
            return digest, byte_length

        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{digest}.", dir=destination.parent
        )
        temporary_path = Path(temporary_name)
        descriptor_is_open = True
        try:
            temporary_file = os.fdopen(file_descriptor, "wb")
            descriptor_is_open = False
            with temporary_file:
                copied_digest, copied_length, copied_snapshot = _stream_stable_file(
                    source,
                    chunk_size=chunk_size,
                    destination=temporary_file,
                )
                if copied_snapshot != source_snapshot:
                    raise ArtifactIntegrityError(
                        "source changed while reading: file snapshot changed"
                    )
                if copied_digest != digest or copied_length != byte_length:
                    raise ArtifactIntegrityError(
                        "source changed while reading: content identity changed"
                    )
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
        return digest, byte_length

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
            self._root_directory_chain = [
                ancestor,
                *reversed(missing_ancestors),
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


def _stream_stable_file(
    source: Path,
    *,
    chunk_size: int,
    destination: BinaryIO | None = None,
) -> tuple[str, int, tuple[int, ...]]:
    path_before = source.lstat()
    if not stat.S_ISREG(path_before.st_mode):
        raise ArtifactIntegrityError("source must be a regular file")

    digest = sha256()
    byte_length = 0
    with source.open("rb") as source_file:
        descriptor_before = os.fstat(source_file.fileno())
        if not _same_file(path_before, descriptor_before):
            raise ArtifactIntegrityError(
                "source changed while reading: path and descriptor differ"
            )
        while chunk := source_file.read(chunk_size):
            digest.update(chunk)
            byte_length += len(chunk)
            if destination is not None:
                destination.write(chunk)
        descriptor_after = os.fstat(source_file.fileno())

    path_after = source.lstat()
    if (
        not _same_file(descriptor_after, path_after)
        or _file_snapshot(path_before) != _file_snapshot(path_after)
        or _file_snapshot(descriptor_before) != _file_snapshot(descriptor_after)
        or byte_length != descriptor_after.st_size
    ):
        raise ArtifactIntegrityError(
            "source changed while reading: file metadata changed"
        )
    return digest.hexdigest(), byte_length, _file_snapshot(path_after)


def _same_file(first: os.stat_result, second: os.stat_result) -> bool:
    return (
        first.st_dev,
        first.st_ino,
        stat.S_IFMT(first.st_mode),
    ) == (
        second.st_dev,
        second.st_ino,
        stat.S_IFMT(second.st_mode),
    )


def _file_snapshot(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        stat.S_IFMT(value.st_mode),
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )

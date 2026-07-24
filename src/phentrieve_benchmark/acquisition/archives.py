import os
import re
import stat
import tarfile
import tempfile
import zipfile
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import IO
from unicodedata import category, normalize

from phentrieve_benchmark.acquisition.downloader import DownloadedArchive
from phentrieve_benchmark.acquisition.recipes import LoadedRecipe, SourceRecipe
from phentrieve_benchmark.artifacts.store import (
    ArtifactIntegrityError,
    ArtifactStore,
)
from phentrieve_benchmark.models.pipeline import (
    ArchiveFormat,
    SourceMember,
    SourceSnapshotManifest,
)

_WINDOWS_DRIVE = re.compile(r"[A-Za-z]:")
_CHUNK_SIZE = 1024 * 1024


class ArchiveValidationError(RuntimeError):
    """An archive does not satisfy its immutable source recipe."""


@dataclass(frozen=True)
class _Member:
    archive_name: str
    relative_path: str | None
    size: int
    compressed_size: int | None
    is_directory: bool
    handle: object


def _validated_path(name: str, expected_root: str) -> str | None:
    if (
        not name
        or name != normalize("NFC", name)
        or name.startswith("/")
        or name.startswith("//")
        or _WINDOWS_DRIVE.match(name) is not None
        or "\\" in name
        or "\x00" in name
        or "//" in name
        or any(category(character).startswith("C") for character in name)
    ):
        raise ArchiveValidationError("unsafe archive member path")
    trimmed = name[:-1] if name.endswith("/") else name
    parts = trimmed.split("/")
    if not trimmed or any(part in {"", ".", ".."} for part in parts):
        raise ArchiveValidationError("unsafe archive member path")
    if parts[0] != expected_root:
        raise ArchiveValidationError("archive has unexpected top-level directory")
    if PurePosixPath(trimmed).as_posix() != trimmed:
        raise ArchiveValidationError("unsafe archive member path")
    return None if len(parts) == 1 else "/".join(parts[1:])


def _is_selected(path: str, patterns: tuple[str, ...]) -> bool:
    candidate = PurePosixPath(path)
    return any(candidate.match(pattern) for pattern in patterns)


def _is_ignored(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)


def _inspect_zip(
    archive: zipfile.ZipFile, recipe: SourceRecipe
) -> list[_Member]:
    members: list[_Member] = []
    for info in archive.infolist():
        mode = info.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        is_directory = info.is_dir()
        if info.flag_bits & 0x1:
            raise ArchiveValidationError("encrypted archive members are unsupported")
        if not is_directory and file_type not in {0, stat.S_IFREG}:
            raise ArchiveValidationError("archive members must be regular files")
        members.append(
            _Member(
                archive_name=info.filename,
                relative_path=_validated_path(
                    info.filename, recipe.archive.expected_top_level_directory
                ),
                size=info.file_size,
                compressed_size=info.compress_size,
                is_directory=is_directory,
                handle=info,
            )
        )
    return members


def _inspect_tar(
    archive: tarfile.TarFile, recipe: SourceRecipe
) -> list[_Member]:
    members: list[_Member] = []
    for info in archive.getmembers():
        if info.issparse() or not (info.isdir() or info.isreg()):
            raise ArchiveValidationError("archive members must be regular files")
        members.append(
            _Member(
                archive_name=info.name,
                relative_path=_validated_path(
                    info.name, recipe.archive.expected_top_level_directory
                ),
                size=info.size,
                compressed_size=None,
                is_directory=info.isdir(),
                handle=info,
            )
        )
    return members


def _validate_inventory(
    members: list[_Member],
    recipe: SourceRecipe,
    archive_byte_length: int,
) -> list[_Member]:
    limits = recipe.archive
    if len(members) > limits.maximum_member_count:
        raise ArchiveValidationError("archive member count exceeds maximum")
    names = [member.archive_name.rstrip("/") for member in members]
    if len(names) != len(set(names)):
        raise ArchiveValidationError("duplicate archive member path")

    declared_total = 0
    selected: list[_Member] = []
    matched_patterns: set[str] = set()
    for member in members:
        if member.size < 0 or member.size > limits.maximum_member_bytes:
            raise ArchiveValidationError("archive member size exceeds maximum")
        if member.is_directory and member.size != 0:
            raise ArchiveValidationError("archive directory has nonzero size")
        declared_total += member.size
        if declared_total > limits.maximum_expanded_bytes:
            raise ArchiveValidationError("declared expanded size exceeds maximum")
        if (
            member.compressed_size is not None
            and member.size
            > max(member.compressed_size, 1) * limits.maximum_compression_ratio
        ):
            raise ArchiveValidationError("archive compression ratio exceeds maximum")
        path = member.relative_path
        if path is None or member.is_directory or _is_ignored(
            path, recipe.ignored_path_prefixes
        ):
            continue
        for pattern in recipe.included_paths:
            if PurePosixPath(path).match(pattern):
                matched_patterns.add(pattern)
        if _is_selected(path, recipe.included_paths):
            selected.append(member)

    if declared_total > archive_byte_length * limits.maximum_compression_ratio:
        raise ArchiveValidationError("archive compression ratio exceeds maximum")
    missing = set(recipe.included_paths) - matched_patterns
    if missing:
        raise ArchiveValidationError("required included path has no archive match")
    return selected


def _copy_member_to_store(
    source: IO[bytes],
    *,
    declared_size: int,
    streamed_total: list[int],
    recipe: SourceRecipe,
    store: ArtifactStore,
) -> tuple[str, int]:
    descriptor, temporary_name = tempfile.mkstemp(prefix=".source-member.")
    temporary_path = Path(temporary_name)
    os.close(descriptor)
    measured = 0
    try:
        with temporary_path.open("wb") as destination:
            while chunk := source.read(_CHUNK_SIZE):
                measured += len(chunk)
                streamed_total[0] += len(chunk)
                if measured > recipe.archive.maximum_member_bytes:
                    raise ArchiveValidationError(
                        "streamed member size exceeds maximum"
                    )
                if streamed_total[0] > recipe.archive.maximum_expanded_bytes:
                    raise ArchiveValidationError(
                        "streamed expanded size exceeds maximum"
                    )
                destination.write(chunk)
        if measured != declared_size:
            raise ArchiveValidationError(
                "streamed member size differs from declared size"
            )
        try:
            return store.put_file(
                temporary_path, expected_byte_length=declared_size
            )
        except ArtifactIntegrityError as error:
            raise ArchiveValidationError(
                "selected member changed while publishing"
            ) from error
    finally:
        with suppress(OSError):
            temporary_path.unlink()


def _publish_zip_members(
    archive: zipfile.ZipFile,
    members: Iterable[_Member],
    *,
    recipe: SourceRecipe,
    store: ArtifactStore,
) -> tuple[SourceMember, ...]:
    published: list[SourceMember] = []
    streamed_total = [0]
    for member in members:
        assert isinstance(member.handle, zipfile.ZipInfo)
        with archive.open(member.handle, "r") as source:
            digest, length = _copy_member_to_store(
                source,
                declared_size=member.size,
                streamed_total=streamed_total,
                recipe=recipe,
                store=store,
            )
        assert member.relative_path is not None
        published.append(
            SourceMember(
                path=member.relative_path,
                sha256=digest,
                byte_length=length,
            )
        )
    return tuple(published)


def _publish_tar_members(
    archive: tarfile.TarFile,
    members: Iterable[_Member],
    *,
    recipe: SourceRecipe,
    store: ArtifactStore,
) -> tuple[SourceMember, ...]:
    published: list[SourceMember] = []
    streamed_total = [0]
    for member in members:
        assert isinstance(member.handle, tarfile.TarInfo)
        source = archive.extractfile(member.handle)
        if source is None:
            raise ArchiveValidationError("regular member cannot be opened")
        with source:
            digest, length = _copy_member_to_store(
                source,
                declared_size=member.size,
                streamed_total=streamed_total,
                recipe=recipe,
                store=store,
            )
        assert member.relative_path is not None
        published.append(
            SourceMember(
                path=member.relative_path,
                sha256=digest,
                byte_length=length,
            )
        )
    return tuple(published)


def publish_source_snapshot(
    recipe: LoadedRecipe[SourceRecipe],
    archive: DownloadedArchive,
    *,
    store: ArtifactStore,
) -> SourceSnapshotManifest:
    source = recipe.value
    if (
        archive.sha256 != source.archive.sha256
        or archive.byte_length != source.archive.expected_byte_length
    ):
        raise ArchiveValidationError("downloaded archive does not match recipe")
    archive_path = store.path_for(archive.sha256)
    try:
        store.put_file(
            archive_path,
            expected_sha256=archive.sha256,
            expected_byte_length=archive.byte_length,
        )
    except (OSError, ArtifactIntegrityError) as error:
        raise ArchiveValidationError("archive artifact identity is invalid") from error

    try:
        if source.archive.format == "zip":
            with zipfile.ZipFile(archive_path, "r") as opened:
                members = _inspect_zip(opened, source)
                selected = _validate_inventory(
                    members, source, archive.byte_length
                )
                published = _publish_zip_members(
                    opened, selected, recipe=source, store=store
                )
        else:
            with tarfile.open(archive_path, mode="r:*") as opened:
                members = _inspect_tar(opened, source)
                selected = _validate_inventory(
                    members, source, archive.byte_length
                )
                published = _publish_tar_members(
                    opened, selected, recipe=source, store=store
                )
    except (zipfile.BadZipFile, tarfile.TarError, OSError) as error:
        raise ArchiveValidationError("invalid source archive") from error

    return SourceSnapshotManifest(
        source_id=source.source_id,
        source_commit=source.source_commit,
        recipe_sha256=recipe.sha256,
        archive_sha256=archive.sha256,
        archive_byte_length=archive.byte_length,
        archive_format=ArchiveFormat(source.archive.format),
        members=published,
    )

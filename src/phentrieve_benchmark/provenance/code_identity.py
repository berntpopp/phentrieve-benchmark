import os
import stat
import subprocess
from pathlib import Path

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes

_EMPTY_SHA256 = sha256_bytes(b"")
_PATH_SAFE_BYTES = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._/"
)
_READ_ATTEMPTS = 3


def _git(repo: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def _repository_top_level(repo: Path) -> Path:
    top_level = _git(repo, "rev-parse", "--show-toplevel").decode().strip()
    return Path(top_level)


def _encode_path(raw_path: bytes) -> str:
    return "".join(
        chr(byte) if byte in _PATH_SAFE_BYTES else f"%{byte:02X}"
        for byte in raw_path
    )


def _filesystem_path(repo: Path, raw_path: bytes) -> str | bytes:
    if os.name == "posix":
        return os.fsencode(repo) + b"/" + raw_path
    return os.fspath(repo / os.fsdecode(raw_path))


def _index_modes(repo: Path) -> dict[bytes, bytes]:
    modes: dict[bytes, bytes] = {}
    staged = _git(repo, "ls-files", "--stage", "-z")
    for record in (item for item in staged.split(b"\0") if item):
        metadata, raw_path = record.split(b"\t", maxsplit=1)
        mode = metadata.split(b" ", maxsplit=1)[0]
        if raw_path in modes:
            raise ValueError("multiple index entries for path")
        modes[raw_path] = mode
    return modes


def _file_metadata(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
    )


def _regular_file_sha256(path: str | bytes) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    for _ in range(_READ_ATTEMPTS):
        try:
            before = os.lstat(path)
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(before.st_mode):
            continue
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            continue
        except OSError:
            continue
        try:
            opened = os.fstat(descriptor)
            is_same_file = _file_metadata(before) == _file_metadata(opened)
            if not stat.S_ISREG(opened.st_mode) or not is_same_file:
                continue
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            after = os.fstat(descriptor)
            if _file_metadata(before) == _file_metadata(after):
                return sha256_bytes(b"".join(chunks))
        finally:
            os.close(descriptor)
    raise ValueError("concurrent mutation detected while reading regular file")


def _symlink_target_bytes(path: str | bytes) -> bytes:
    if isinstance(path, bytes):
        target = os.readlink(path)
        return target
    return os.fsencode(os.readlink(path))


def _entry(
    repo: Path, raw_path: bytes, index_modes: dict[bytes, bytes]
) -> dict[str, object]:
    if index_modes.get(raw_path) == b"160000":
        raise ValueError("gitlinks are not supported by code identity")

    path = _filesystem_path(repo, raw_path)
    encoded_path = _encode_path(raw_path)
    try:
        path_stat = os.lstat(path)
    except FileNotFoundError:
        return {
            "path": encoded_path,
            "state": "deleted",
            "kind": "missing",
            "executable": False,
            "sha256": _EMPTY_SHA256,
        }

    if stat.S_ISREG(path_stat.st_mode):
        return {
            "path": encoded_path,
            "state": "present",
            "kind": "file",
            "executable": bool(path_stat.st_mode & 0o111),
            "sha256": _regular_file_sha256(path),
        }
    if stat.S_ISLNK(path_stat.st_mode):
        return {
            "path": encoded_path,
            "state": "present",
            "kind": "symlink",
            "executable": False,
            "sha256": sha256_bytes(_symlink_target_bytes(path)),
        }
    raise ValueError(f"unsupported file kind at {encoded_path!r}")


def code_sha256(repo: Path) -> str:
    top_level = _repository_top_level(repo)
    head = _git(top_level, "rev-parse", "HEAD").decode().strip()
    listed = _git(
        top_level,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-per-directory=.gitignore",
    )
    raw_paths = [item for item in listed.split(b"\0") if item]
    if len(raw_paths) != len(set(raw_paths)):
        raise ValueError("git listed a path more than once")

    encoded_paths = [(_encode_path(raw_path), raw_path) for raw_path in raw_paths]
    if len(encoded_paths) != len({path for path, _ in encoded_paths}):
        raise ValueError("encoded path collision")
    index_modes = _index_modes(top_level)
    entries = [
        _entry(top_level, raw_path, index_modes)
        for _, raw_path in sorted(encoded_paths, key=lambda item: item[0])
    ]
    payload = {
        "schema_version": "code-identity/v2",
        "head": head,
        "exclusion_policy": "repository-gitignore/v1",
        "path_encoding": "percent-encoded-git-path-bytes/v1",
        "entries": entries,
    }
    return sha256_bytes(canonical_json_bytes(payload))

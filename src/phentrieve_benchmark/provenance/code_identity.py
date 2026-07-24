import errno
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
    candidate = repo.resolve()
    if candidate.is_file():
        candidate = candidate.parent
    while candidate != candidate.parent:
        marker = candidate / ".git"
        if marker.is_dir() or marker.is_file():
            if _git(candidate, "rev-parse", "--is-inside-work-tree") != b"true\n":
                raise ValueError(f"not a Git worktree: {candidate}")
            return candidate
        candidate = candidate.parent
    raise ValueError(f"unable to find a Git worktree for {repo}")


def _encode_path(raw_path: bytes) -> str:
    return "".join(
        chr(byte) if byte in _PATH_SAFE_BYTES else f"%{byte:02X}"
        for byte in raw_path
    )


def _filesystem_path(repo: Path, raw_path: bytes) -> str | bytes:
    if os.name == "posix":
        return os.fsencode(repo) + b"/" + raw_path
    return os.fspath(repo / os.fsdecode(raw_path))


def _is_in_worktree_gitignore(repo: Path, source: bytes) -> bool:
    source_path = Path(os.fsdecode(source))
    candidate = source_path if source_path.is_absolute() else repo / source_path
    try:
        candidate.resolve().relative_to(repo.resolve())
    except ValueError:
        return False
    return candidate.name == ".gitignore" and candidate.is_file()


def _is_project_ignored(repo: Path, raw_path: bytes) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-z", "-v", "--no-index", "--stdin"],
        cwd=repo,
        input=raw_path + b"\0",
        check=False,
        capture_output=True,
    )
    if result.returncode == 1:
        return False
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    fields = [field for field in result.stdout.split(b"\0") if field]
    if len(fields) != 4:
        raise ValueError("unexpected git check-ignore output")
    source, _, pattern, matched_path = fields
    if matched_path != raw_path:
        raise ValueError("git check-ignore matched an unexpected path")
    return not pattern.startswith(b"!") and _is_in_worktree_gitignore(repo, source)


def _reject_relevant_special_entries(repo: Path) -> None:
    def scan(directory: bytes, relative: bytes) -> None:
        with os.scandir(directory) as entries:
            for entry in entries:
                name = entry.name
                raw_name = name if isinstance(name, bytes) else os.fsencode(name)
                if raw_name == b".git":
                    continue
                raw_path = raw_name if not relative else relative + b"/" + raw_name
                try:
                    entry_stat = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    encoded_path = _encode_path(raw_path)
                    message = f"filesystem entry vanished at {encoded_path!r}"
                    raise ValueError(message) from None
                if stat.S_ISDIR(entry_stat.st_mode):
                    scan(os.path.join(directory, name), raw_path)
                elif not (
                    stat.S_ISREG(entry_stat.st_mode) or stat.S_ISLNK(entry_stat.st_mode)
                ) and not _is_project_ignored(repo, raw_path):
                    encoded_path = _encode_path(raw_path)
                    raise ValueError(f"unsupported file kind at {encoded_path!r}")

    scan(os.fsencode(repo), b"")


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


def _file_metadata(value: os.stat_result) -> tuple[int, ...]:
    metadata = (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
    )
    if os.name == "posix":
        return (*metadata, value.st_ctime_ns)
    return metadata


def _regular_file_snapshot(path: str | bytes) -> tuple[bool, str]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    if os.name == "posix":
        flags |= getattr(os, "O_NONBLOCK", 0)
    for _ in range(_READ_ATTEMPTS):
        try:
            before = os.lstat(path)
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(before.st_mode):
            continue
        before_metadata = _file_metadata(before)
        try:
            descriptor = os.open(path, flags)
        except OSError as error:
            if error.errno in {errno.ELOOP, errno.ENOENT, errno.ENOTDIR}:
                continue
            raise
        try:
            opened = os.fstat(descriptor)
            opened_metadata = _file_metadata(opened)
            if not stat.S_ISREG(opened.st_mode) or before_metadata != opened_metadata:
                continue
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            descriptor_after = os.fstat(descriptor)
            try:
                path_after = os.lstat(path)
            except FileNotFoundError:
                continue
            descriptor_after_metadata = _file_metadata(descriptor_after)
            path_after_metadata = _file_metadata(path_after)
            if (
                stat.S_ISREG(descriptor_after.st_mode)
                and stat.S_ISREG(path_after.st_mode)
                and opened_metadata == descriptor_after_metadata == path_after_metadata
            ):
                return bool(opened.st_mode & 0o111), sha256_bytes(b"".join(chunks))
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
        if raw_path not in index_modes:
            raise ValueError(f"untracked file vanished at {encoded_path!r}") from None
        return {
            "path": encoded_path,
            "state": "deleted",
            "kind": "missing",
            "executable": False,
            "sha256": _EMPTY_SHA256,
        }

    if stat.S_ISREG(path_stat.st_mode):
        executable, digest = _regular_file_snapshot(path)
        return {
            "path": encoded_path,
            "state": "present",
            "kind": "file",
            "executable": executable,
            "sha256": digest,
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
    _reject_relevant_special_entries(top_level)
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

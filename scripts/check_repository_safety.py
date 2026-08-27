from __future__ import annotations

import hashlib
import hmac
import os
import re
import stat
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class SafetyViolation(RuntimeError):
    """A Git index entry violates the public-repository boundary."""


MAX_BLOB_BYTES = 4 * 1024 * 1024
MAX_INDEX_BYTES = 64 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 30
SUPPORTED_MODES = frozenset({b"100644", b"100755", b"120000"})
FORBIDDEN_PATHS = (
    b".artifacts",
    b"records/local",
    b"releases/local",
    b"configs/providers/local",
)
ASSIGNMENT_PATTERN = re.compile(
    r"""(?imx)
    ^[ \t]*
    (?:export[ \t]+)?
    (?P<quote>["']?)
    (?P<name>
        (?:[A-Za-z][A-Za-z0-9]*[-_]){0,2}
        (?:
            api[-_]?key
            |client[-_]?secret
            |secret[-_]?access[-_]?key
            |secret
            |token
            |password
            |credential
            |private[-_]?key
            |access[-_]?key(?:[-_]?id)?
        )
    )
    (?P=quote)
    [ \t]*[:=][ \t]*
    (?P<value>
        "[^"\r\n]*"
        |'[^'\r\n]*'
        |[A-Za-z0-9_./+~=@:%-]+
    )
    [ \t]*,?[ \t]*(?:\#[^\r\n]*)?$
    """
)
STRUCTURED_ASSIGNMENT_PATTERN = re.compile(
    r'''(?ix)
    (?:(?<=\{)|(?<=,))
    [ \t\r\n]*
    (?P<quote>["']?)
    (?P<name>
        (?:[A-Za-z][A-Za-z0-9]*[-_]){0,2}
        (?:
            api[-_]?key
            |client[-_]?secret
            |secret[-_]?access[-_]?key
            |secret
            |token
            |password
            |credential
            |private[-_]?key
            |access[-_]?key(?:[-_]?id)?
        )
    )
    (?P=quote)
    [ \t\r\n]*:[ \t\r\n]*
    (?P<value>
        "(?:\\.|[^"\\\r\n])*"
        |'(?:\\.|[^'\\\r\n])*'
        |[A-Za-z0-9_./+~=@:%-]+
    )
    (?=[ \t\r\n]*(?:[,}\]#]|$))
    '''
)
SIGNATURE_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{36}(?![A-Za-z0-9])"),
    re.compile(r"(?<![A-Za-z0-9])github_pat_[A-Za-z0-9_]{50,}"),
    re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
    re.compile(r"(?i)\bBearer[ \t]+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(
        r"-----BEGIN (?:(?:RSA|EC|OPENSSH|DSA|ENCRYPTED) )?PRIVATE KEY-----"
    ),
    re.compile(r"-----BEGIN PGP " + r"PRIVATE KEY BLOCK-----"),
)
PLACEHOLDERS = frozenset(
    {
        "changeme",
        "dummy",
        "example",
        "must not be logged",
        "placeholder",
        "redacted",
        "replace-me",
        "replace_me",
        "short",
        "test-only",
        "test_only",
    }
)


@dataclass(frozen=True, slots=True)
class IndexEntry:
    mode: bytes
    oid: bytes
    path: bytes


def escape_path(path: bytes) -> str:
    """Return a reversible, single-line representation safe for CI diagnostics."""
    safe = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._/-"
    return "".join(
        chr(byte) if byte in safe else f"%{byte:02X}" for byte in path
    )


def repository_root(start: Path) -> Path:
    """Find the nearest worktree marker without consulting redirectable Git state."""
    try:
        current = start.absolute()
        if current.is_file():
            current = current.parent
    except OSError as error:
        raise SafetyViolation("unable to inspect candidate Git repository") from error

    for candidate in (current, *current.parents):
        marker = candidate / ".git"
        try:
            if marker.is_symlink():
                raise SafetyViolation("Git repository marker must not be a symlink")
            if marker.is_dir() or marker.is_file():
                return candidate
        except OSError as error:
            raise SafetyViolation("unable to inspect Git repository marker") from error
    raise SafetyViolation("no Git repository found from supplied path")


def trusted_git_environment() -> dict[str, str]:
    """Copy the process environment while removing every inherited GIT_* override."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _git_arguments(arguments: list[str]) -> list[str]:
    return [
        "git",
        "--no-pager",
        "--no-replace-objects",
        "--literal-pathspecs",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        *arguments,
    ]


def _git_process(
    root: Path,
    arguments: list[str],
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            _git_arguments(arguments),
            cwd=root,
            env=trusted_git_environment(),
            check=False,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise SafetyViolation("unable to read trusted Git repository state") from error


def _git_output(
    root: Path,
    arguments: list[str],
) -> bytes:
    result = _git_process(root, arguments)
    if result.returncode != 0:
        raise SafetyViolation("unable to read trusted Git repository state")
    return result.stdout


def _worktree_differs_from_index(root: Path) -> bool:
    result = _git_process(
        root,
        ["diff-files", "--quiet", "--ignore-submodules=none", "--"],
    )
    if result.returncode not in {0, 1}:
        raise SafetyViolation("unable to compare tracked worktree with Git index")
    return result.returncode == 1


def _malformed_index() -> SafetyViolation:
    return SafetyViolation("Git index file is malformed")


def _decode_v4_strip_count(
    snapshot: bytes,
    cursor: int,
    limit: int,
) -> tuple[int, int]:
    if cursor >= limit:
        raise _malformed_index()
    byte = snapshot[cursor]
    cursor += 1
    value = byte & 0x7F
    for _ in range(9):
        if not byte & 0x80:
            return value, cursor
        if cursor >= limit:
            raise _malformed_index()
        value += 1
        if value > (sys.maxsize >> 7):
            raise _malformed_index()
        byte = snapshot[cursor]
        cursor += 1
        value = (value << 7) + (byte & 0x7F)
    raise _malformed_index()


def _validate_index_bytes(snapshot: bytes, *, hash_name: str) -> None:
    """Validate a documented Git index and reject its fsmonitor extension."""
    if hash_name not in {"sha1", "sha256"}:
        raise SafetyViolation("Git returned an unsupported object format")
    hash_size = hashlib.new(hash_name).digest_size
    if len(snapshot) < 12 + hash_size:
        raise _malformed_index()

    payload = snapshot[:-hash_size]
    expected_checksum = snapshot[-hash_size:]
    actual_checksum = hashlib.new(hash_name, payload).digest()
    if not hmac.compare_digest(actual_checksum, expected_checksum):
        raise SafetyViolation("Git index checksum is invalid")
    if payload[:4] != b"DIRC":
        raise _malformed_index()

    version, entry_count = struct.unpack(">II", payload[4:12])
    if version not in {2, 3, 4}:
        raise SafetyViolation("Git index version is unsupported")
    fixed_size = 40 + hash_size + 2
    if entry_count > (len(payload) - 12) // (fixed_size + 1):
        raise _malformed_index()

    cursor = 12
    previous_path = b""
    for _ in range(entry_count):
        entry_start = cursor
        if cursor + fixed_size > len(payload):
            raise _malformed_index()
        cursor += 40 + hash_size
        flags = struct.unpack(">H", payload[cursor : cursor + 2])[0]
        cursor += 2
        if flags & 0x4000:
            if version == 2 or cursor + 2 > len(payload):
                raise _malformed_index()
            extended_flags = struct.unpack(">H", payload[cursor : cursor + 2])[0]
            if extended_flags & ~0x6000:
                raise _malformed_index()
            cursor += 2

        declared_name_length = flags & 0x0FFF
        if version == 4:
            strip_count, cursor = _decode_v4_strip_count(
                payload,
                cursor,
                len(payload),
            )
            if strip_count > len(previous_path):
                raise _malformed_index()
            name_end = payload.find(b"\0", cursor)
            if name_end < 0:
                raise _malformed_index()
            path = previous_path[: len(previous_path) - strip_count]
            path += payload[cursor:name_end]
            cursor = name_end + 1
            previous_path = path
        else:
            if declared_name_length < 0x0FFF:
                name_end = cursor + declared_name_length
                if name_end >= len(payload) or payload[name_end] != 0:
                    raise _malformed_index()
            else:
                name_end = payload.find(b"\0", cursor)
                if name_end < 0:
                    raise _malformed_index()
            path = payload[cursor:name_end]
            cursor = name_end + 1
            aligned_cursor = entry_start + (
                ((cursor - entry_start + 7) // 8) * 8
            )
            if (
                aligned_cursor > len(payload)
                or any(payload[cursor:aligned_cursor])
            ):
                raise _malformed_index()
            cursor = aligned_cursor

        if (
            declared_name_length < 0x0FFF
            and declared_name_length != len(path)
        ):
            raise _malformed_index()

    while cursor < len(payload):
        if cursor + 8 > len(payload):
            raise _malformed_index()
        signature = payload[cursor : cursor + 4]
        extension_size = struct.unpack(">I", payload[cursor + 4 : cursor + 8])[0]
        cursor += 8
        if extension_size > len(payload) - cursor:
            raise _malformed_index()
        if 0x61 <= signature[0] <= 0x7A:
            raise SafetyViolation("required index extension is unsupported")
        if signature == b"FSMN":
            raise SafetyViolation("unsafe fsmonitor index extension is forbidden")
        cursor += extension_size


def _index_file_path(root: Path) -> Path:
    output = _git_output(
        root,
        ["rev-parse", "--path-format=absolute", "--git-path", "index"],
    )
    if (
        not output.endswith(b"\n")
        or b"\0" in output
        or b"\n" in output[:-1]
    ):
        raise SafetyViolation("Git returned an invalid index path")
    path = Path(os.fsdecode(output[:-1]))
    if not path.is_absolute():
        raise SafetyViolation("Git returned a non-absolute index path")
    return path


def _read_index_file(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        if path.is_symlink():
            raise SafetyViolation("Git index file must not be a symlink")
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return b""
    except SafetyViolation:
        raise
    except OSError as error:
        raise SafetyViolation("unable to read Git index file") from error

    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise SafetyViolation("Git index must be a regular file")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            snapshot = handle.read(MAX_INDEX_BYTES + 1)
    except (OSError, SafetyViolation) as error:
        if isinstance(error, SafetyViolation):
            raise
        raise SafetyViolation("unable to read Git index file") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    if len(snapshot) > MAX_INDEX_BYTES:
        raise SafetyViolation("Git index exceeds safety size limit")
    return snapshot


def index_file_snapshot(root: Path) -> tuple[Path, str, bytes]:
    index_path = _index_file_path(root)
    object_format = _git_output(
        root,
        ["rev-parse", "--show-object-format"],
    ).strip()
    if object_format not in {b"sha1", b"sha256"}:
        raise SafetyViolation("Git returned an unsupported object format")
    hash_name = object_format.decode("ascii")
    snapshot = _read_index_file(index_path)
    if snapshot:
        _validate_index_bytes(snapshot, hash_name=hash_name)
    return index_path, hash_name, snapshot


def _tagged_index_paths(snapshot: bytes) -> list[tuple[bytes, bytes]]:
    if snapshot and not snapshot.endswith(b"\0"):
        raise SafetyViolation("Git returned malformed index flag output")
    tagged_paths: list[tuple[bytes, bytes]] = []
    for record in (item for item in snapshot.split(b"\0") if item):
        if len(record) < 3 or record[1:2] != b" ":
            raise SafetyViolation("Git returned malformed index flag entry")
        tag, path = record[:1], record[2:]
        if not path:
            raise SafetyViolation("Git returned an empty index flag path")
        tagged_paths.append((tag, path))
    return tagged_paths


def _reject_unsafe_index_flags(
    snapshot: bytes,
    *,
    reject_skip_worktree: bool,
) -> None:
    for tag, path in _tagged_index_paths(snapshot):
        lowercase = tag.lower() == tag and tag.upper() != tag
        if lowercase or (reject_skip_worktree and tag == b"S"):
            raise SafetyViolation(
                f"unsafe index comparison flag: {escape_path(path)}"
            )


def index_flag_snapshot(root: Path) -> bytes:
    assume_and_skip = _git_output(root, ["ls-files", "-v", "-z"])
    _reject_unsafe_index_flags(assume_and_skip, reject_skip_worktree=True)
    return assume_and_skip


def parse_index_snapshot(snapshot: bytes) -> list[IndexEntry]:
    """Parse one raw `git ls-files --stage -z` snapshot deterministically."""
    if snapshot and not snapshot.endswith(b"\0"):
        raise SafetyViolation("Git returned a malformed index snapshot")

    entries: list[IndexEntry] = []
    paths: set[bytes] = set()
    for record in (item for item in snapshot.split(b"\0") if item):
        header, separator, path = record.partition(b"\t")
        fields = header.split(b" ")
        if not separator or len(fields) != 3 or not path:
            raise SafetyViolation("Git returned a malformed index entry")
        mode, oid, stage = fields
        if stage != b"0":
            raise SafetyViolation("unmerged index entries are forbidden")
        if mode == b"160000":
            raise SafetyViolation(f"Gitlink is forbidden: {escape_path(path)}")
        if mode not in SUPPORTED_MODES:
            raise SafetyViolation(
                f"unsupported tracked mode for path: {escape_path(path)}"
            )
        if (
            len(oid) not in {40, 64}
            or not all(byte in b"0123456789abcdef" for byte in oid)
        ):
            raise SafetyViolation("Git returned an invalid object identity")
        components = path.split(b"/")
        if (
            path.startswith(b"/")
            or any(component in {b"", b".", b".."} for component in components)
        ):
            raise SafetyViolation("Git returned an invalid tracked path")
        if path in paths:
            raise SafetyViolation(f"duplicate index path: {escape_path(path)}")
        paths.add(path)
        entries.append(IndexEntry(mode=mode, oid=oid, path=path))
    return sorted(entries, key=lambda entry: entry.path)


def index_snapshot(root: Path) -> tuple[bytes, list[IndexEntry]]:
    raw = _git_output(root, ["ls-files", "--stage", "-z"])
    return raw, parse_index_snapshot(raw)


def _text_views(content: bytes) -> list[str]:
    views = [content.decode("utf-8", errors="ignore").lstrip("\ufeff")]
    if len(content) % 2 == 0 and b"\0" in content:
        for encoding in ("utf-16-le", "utf-16-be"):
            try:
                view = content.decode(encoding).lstrip("\ufeff")
            except UnicodeDecodeError:
                continue
            if view not in views:
                views.append(view)
    return views


def _placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").strip()
    lowered = normalized.casefold()
    if len(normalized) < 12 or lowered in PLACEHOLDERS:
        return True
    return bool(
        (normalized.startswith("<") and normalized.endswith(">"))
        or (normalized.startswith("${") and normalized.endswith("}"))
        or re.fullmatch(r"\$[A-Za-z_][A-Za-z0-9_]*", normalized)
        or re.fullmatch(r"(?i)(?:x+|0+|\*+)", normalized)
    )


def contains_credential(content: bytes) -> bool:
    """Detect credential assignments and high-confidence provider signatures."""
    for text in _text_views(content):
        if any(pattern.search(text) for pattern in SIGNATURE_PATTERNS):
            return True
        assignments = (
            *ASSIGNMENT_PATTERN.finditer(text),
            *STRUCTURED_ASSIGNMENT_PATTERN.finditer(text),
        )
        if any(not _placeholder(match.group("value")) for match in assignments):
            return True
    return False


def _forbidden_path(path: bytes) -> bool:
    return any(
        path == forbidden or path.startswith(forbidden + b"/")
        for forbidden in FORBIDDEN_PATHS
    )


def read_blob(root: Path, entry: IndexEntry) -> bytes:
    oid = entry.oid.decode("ascii")
    size_output = _git_output(root, ["cat-file", "-s", oid]).strip()
    if not size_output.isdigit():
        raise SafetyViolation("Git returned an invalid tracked blob size")
    size = int(size_output)
    if size > MAX_BLOB_BYTES:
        raise SafetyViolation(
            f"tracked blob exceeds safety size limit: {escape_path(entry.path)}"
        )
    content = _git_output(root, ["cat-file", "blob", oid])
    if len(content) != size:
        raise SafetyViolation("Git returned inconsistent tracked blob bytes")
    return content


def scan_entries(root: Path, entries: list[IndexEntry]) -> None:
    for entry in entries:
        if _forbidden_path(entry.path):
            raise SafetyViolation(
                f"forbidden tracked path: {escape_path(entry.path)}"
            )
        if contains_credential(read_blob(root, entry)):
            raise SafetyViolation(
                f"possible credential in tracked file: {escape_path(entry.path)}"
            )


def scan_repository(start: Path) -> None:
    """Scan immutable index blobs and reject concurrent or worktree divergence."""
    root = repository_root(start)
    index_file_before = index_file_snapshot(root)
    dirty_before = _worktree_differs_from_index(root)
    flags_before = index_flag_snapshot(root)
    raw_before, entries = index_snapshot(root)
    scan_entries(root, entries)
    raw_after, _ = index_snapshot(root)
    flags_after = index_flag_snapshot(root)
    dirty_after = _worktree_differs_from_index(root)
    index_file_after = index_file_snapshot(root)
    if (
        raw_before != raw_after
        or flags_before != flags_after
        or index_file_before != index_file_after
    ):
        raise SafetyViolation("Git index changed during scan")
    if dirty_before or dirty_after:
        raise SafetyViolation("tracked worktree differs from index")


def main() -> int:
    try:
        scan_repository(Path.cwd())
    except SafetyViolation as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        print("repository safety check failed", file=sys.stderr)
        return 1
    print("repository safety check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

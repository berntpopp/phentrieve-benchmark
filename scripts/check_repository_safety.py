from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path, PurePosixPath


class SafetyViolation(RuntimeError):
    """A tracked repository entry violates the public-repository boundary."""


FORBIDDEN_PARTS = (
    ".artifacts",
    "records/local",
    "releases/local",
    "configs/providers/local",
)
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        rb"(?i)(?:api[_-]?key|client[_-]?secret)\s*[:=]\s*['\"][^'\"]{12,}"
    ),
)


def _resolved_directory(root: Path) -> Path:
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise SafetyViolation("unable to resolve repository root") from error
    if not resolved.is_dir():
        raise SafetyViolation("repository root is not a directory")
    return resolved


def _relative_file(root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    try:
        if candidate.is_symlink():
            raise SafetyViolation("tracked path is a symlink")
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(root)
    except SafetyViolation:
        raise
    except (OSError, ValueError) as error:
        message = "tracked path is missing or outside repository"
        raise SafetyViolation(message) from error
    if not resolved.is_file():
        message = f"tracked path is not a regular file: {relative.as_posix()}"
        raise SafetyViolation(message)
    return relative


def _is_forbidden(relative: str) -> bool:
    return any(
        relative == forbidden or relative.startswith(f"{forbidden}/")
        for forbidden in FORBIDDEN_PARTS
    )


def check_paths(root: Path, paths: Sequence[Path]) -> None:
    """Reject unsafe tracked paths and possible credentials without exposing values."""
    resolved_root = _resolved_directory(root)
    for path in paths:
        relative_path = _relative_file(resolved_root, path)
        relative = relative_path.as_posix()
        if _is_forbidden(relative):
            raise SafetyViolation(f"forbidden tracked path: {relative}")
        try:
            content = (resolved_root / relative_path).read_bytes()
        except OSError as error:
            raise SafetyViolation(f"unable to read tracked file: {relative}") from error
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            raise SafetyViolation(f"possible secret in tracked file: {relative}")


def _git_output(root: Path, arguments: list[str]) -> bytes:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise SafetyViolation("unable to read Git tracked files") from error


def repository_root(start: Path) -> Path:
    output = _git_output(start, ["rev-parse", "--show-toplevel"])
    location = output.rstrip(b"\r\n")
    if not location or b"\0" in location:
        raise SafetyViolation("Git returned an invalid repository root")
    try:
        return _resolved_directory(Path(location.decode("utf-8")))
    except UnicodeDecodeError as error:
        raise SafetyViolation("Git returned a non-UTF-8 repository root") from error


def _tracked_relative_paths(root: Path) -> list[PurePosixPath]:
    output = _git_output(root, ["ls-files", "-z"])
    if output and not output.endswith(b"\0"):
        raise SafetyViolation("Git returned malformed tracked-file output")
    paths: list[PurePosixPath] = []
    for item in sorted(part for part in output.split(b"\0") if part):
        try:
            text = item.decode("utf-8")
        except UnicodeDecodeError as error:
            message = "Git returned a non-UTF-8 tracked filename"
            raise SafetyViolation(message) from error
        parts = text.split("/")
        if (
            not text
            or text.startswith(("/", "\\"))
            or "\\" in text
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise SafetyViolation("Git returned a tracked path outside repository")
        paths.append(PurePosixPath(*parts))
    return paths


def tracked_paths(root: Path) -> list[Path]:
    """Return Git-index paths rooted at the resolved repository top level."""
    top_level = repository_root(root)
    relative_paths = _tracked_relative_paths(top_level)
    return [top_level.joinpath(*path.parts) for path in relative_paths]


def main() -> int:
    try:
        paths = tracked_paths(Path.cwd())
        check_paths(repository_root(Path.cwd()), paths)
    except SafetyViolation as error:
        print(str(error), file=sys.stderr)
        return 1
    print("repository safety check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

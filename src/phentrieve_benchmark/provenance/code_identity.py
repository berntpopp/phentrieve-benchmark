import subprocess
from pathlib import Path

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes


def _git(repo: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def _entry(repo: Path, raw_path: bytes) -> dict[str, str]:
    relative = raw_path.decode("utf-8")
    path = repo / relative
    normalized_path = relative.replace("\\", "/")
    if path.is_file():
        return {
            "path": normalized_path,
            "path_bytes": raw_path.hex(),
            "state": "present",
            "sha256": sha256_bytes(path.read_bytes()),
        }
    return {
        "path": normalized_path,
        "path_bytes": raw_path.hex(),
        "state": "deleted",
        "sha256": sha256_bytes(b""),
    }


def code_sha256(repo: Path) -> str:
    head = _git(repo, "rev-parse", "HEAD").decode().strip()
    listed = _git(
        repo,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
    )
    raw_paths = sorted(item for item in listed.split(b"\0") if item)
    if len(raw_paths) != len(set(raw_paths)):
        raise ValueError("git listed a path more than once")

    entries = [_entry(repo, raw_path) for raw_path in raw_paths]
    payload = {
        "schema_version": "code-identity/v1",
        "head": head,
        "exclusion_policy": "gitignore/v1",
        "entries": entries,
    }
    return sha256_bytes(canonical_json_bytes(payload))

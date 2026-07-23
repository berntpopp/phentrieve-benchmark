import os
import subprocess
from pathlib import Path

import pytest

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.code_identity import code_sha256
from phentrieve_benchmark.provenance.digests import sha256_bytes

POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="requires POSIX paths")


def _git(repo: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def _initialized_repo(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.org")
    _git(repo, "config", "user.name", "Test")


def _file_entry(
    path: str, content: bytes, *, executable: bool = False
) -> dict[str, object]:
    return {
        "path": path,
        "state": "present",
        "kind": "file",
        "executable": executable,
        "sha256": sha256_bytes(content),
    }


def _expected_identity(repo: Path, entries: list[dict[str, object]]) -> str:
    payload = {
        "schema_version": "code-identity/v2",
        "head": _git(repo, "rev-parse", "HEAD").decode().strip(),
        "exclusion_policy": "repository-gitignore/v1",
        "path_encoding": "percent-encoded-git-path-bytes/v1",
        "entries": entries,
    }
    return sha256_bytes(canonical_json_bytes(payload))


def test_dirty_and_untracked_sources_change_code_identity(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    source = tmp_path / "src" / "module.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    clean = code_sha256(tmp_path)

    source.write_text("VALUE = 2\n", encoding="utf-8")
    dirty = code_sha256(tmp_path)
    (tmp_path / "new_config.yaml").write_text("enabled: true\n", encoding="utf-8")
    untracked = code_sha256(tmp_path)

    assert len({clean, dirty, untracked}) == 3


def test_ignored_artifacts_do_not_change_code_identity(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    (tmp_path / ".gitignore").write_text(".artifacts/\n", encoding="utf-8")
    (tmp_path / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    before = code_sha256(tmp_path)

    artifact = tmp_path / ".artifacts" / "sha256" / "ab" / ("a" * 64)
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"restricted data")

    assert code_sha256(tmp_path) == before


def test_head_only_change_changes_code_identity(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    (tmp_path / "seed.py").write_text("SEED = True\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    before = code_sha256(tmp_path)
    _git(tmp_path, "commit", "--allow-empty", "-m", "metadata only")

    assert code_sha256(tmp_path) != before


def test_tracked_deletion_has_exact_v2_entry_and_digest(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    source = tmp_path / "module.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    source.unlink()

    assert code_sha256(tmp_path) == _expected_identity(
        tmp_path,
        [
            {
                "path": "module.py",
                "state": "deleted",
                "kind": "missing",
                "executable": False,
                "sha256": sha256_bytes(b""),
            }
        ],
    )


def test_subdirectory_argument_hashes_repository_top_level(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    (tmp_path / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    assert code_sha256(nested) == code_sha256(tmp_path)


def test_repository_gitignore_is_the_only_untracked_exclusion_source(
    tmp_path: Path,
) -> None:
    _initialized_repo(tmp_path)
    (tmp_path / ".gitignore").write_text("project-ignored.py\n", encoding="utf-8")
    (tmp_path / "seed.py").write_text("SEED = True\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    before = code_sha256(tmp_path)

    global_exclude = tmp_path.parent / "global-excludes"
    global_exclude.write_text("global-ignored.py\n", encoding="utf-8")
    _git(tmp_path, "config", "core.excludesFile", str(global_exclude))
    git_dir = Path(_git(tmp_path, "rev-parse", "--git-dir").decode().strip())
    (tmp_path / git_dir / "info" / "exclude").write_text(
        "info-ignored.py\n", encoding="utf-8"
    )
    (tmp_path / "global-ignored.py").write_text("GLOBAL = True\n", encoding="utf-8")
    (tmp_path / "info-ignored.py").write_text("INFO = True\n", encoding="utf-8")
    after_external_excludes = code_sha256(tmp_path)
    (tmp_path / "project-ignored.py").write_text("PROJECT = True\n", encoding="utf-8")

    assert after_external_excludes != before
    assert code_sha256(tmp_path) == after_external_excludes


@POSIX_ONLY
def test_raw_byte_paths_are_portable_and_sorted_by_encoded_path(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    seed = tmp_path / "seed.py"
    seed.write_bytes(b"SEED = True\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    root_bytes = os.fsencode(tmp_path)
    with open(root_bytes + b"/a\xff.py", "wb") as handle:
        handle.write(b"INVALID = True\n")
    with open(root_bytes + b"/a0.py", "wb") as handle:
        handle.write(b"ASCII = True\n")

    assert code_sha256(tmp_path) == _expected_identity(
        tmp_path,
        [
            _file_entry("a%FF.py", b"INVALID = True\n"),
            _file_entry("a0.py", b"ASCII = True\n"),
            _file_entry("seed.py", b"SEED = True\n"),
        ],
    )


@POSIX_ONLY
def test_literal_backslash_and_nested_path_have_distinct_identities(
    tmp_path: Path,
) -> None:
    _initialized_repo(tmp_path)
    (tmp_path / "seed.py").write_text("SEED = True\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    literal = tmp_path / "a\\b"
    literal.write_bytes(b"VALUE = True\n")
    literal_identity = code_sha256(tmp_path)
    literal.unlink()
    nested = tmp_path / "a" / "b"
    nested.parent.mkdir()
    nested.write_bytes(b"VALUE = True\n")

    assert code_sha256(tmp_path) != literal_identity


@POSIX_ONLY
def test_broken_symlink_is_present_and_hashes_its_raw_target(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    seed = tmp_path / "seed.py"
    seed.write_bytes(b"SEED = True\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    os.symlink("missing-target", tmp_path / "link")

    assert code_sha256(tmp_path) == _expected_identity(
        tmp_path,
        [
            {
                "path": "link",
                "state": "present",
                "kind": "symlink",
                "executable": False,
                "sha256": sha256_bytes(b"missing-target"),
            },
            _file_entry("seed.py", b"SEED = True\n"),
        ],
    )


@POSIX_ONLY
def test_executable_mode_changes_regular_file_identity(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    source = tmp_path / "script.py"
    source.write_bytes(b"print('ok')\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    before = code_sha256(tmp_path)

    source.chmod(0o755)

    assert code_sha256(tmp_path) == _expected_identity(
        tmp_path,
        [_file_entry("script.py", b"print('ok')\n", executable=True)],
    )
    assert code_sha256(tmp_path) != before


@POSIX_ONLY
def test_unsupported_special_file_kind_fails_closed(tmp_path: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("mkfifo is unavailable")
    _initialized_repo(tmp_path)
    (tmp_path / "seed.py").write_bytes(b"SEED = True\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    os.mkfifo(tmp_path / "pipe")

    with pytest.raises(ValueError, match="unsupported file kind"):
        code_sha256(tmp_path)


@POSIX_ONLY
def test_gitlink_fails_closed_without_being_treated_as_deleted(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    (tmp_path / "seed.py").write_bytes(b"SEED = True\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    child = tmp_path / "child"
    child.mkdir()
    _initialized_repo(child)
    (child / "child.py").write_bytes(b"CHILD = True\n")
    _git(child, "add", ".")
    _git(child, "commit", "-m", "child")
    child_head = _git(child, "rev-parse", "HEAD").decode().strip()
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{child_head},sub")

    with pytest.raises(ValueError, match="gitlinks are not supported"):
        code_sha256(tmp_path)

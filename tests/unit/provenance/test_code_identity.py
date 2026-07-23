import subprocess
import unicodedata
from pathlib import Path

import pytest

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.code_identity import code_sha256
from phentrieve_benchmark.provenance.digests import sha256_bytes


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


def _expected_identity(repo: Path, entries: list[dict[str, str]]) -> str:
    payload = {
        "schema_version": "code-identity/v1",
        "head": _git(repo, "rev-parse", "HEAD").decode().strip(),
        "exclusion_policy": "gitignore/v1",
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


def test_tracked_deletion_uses_deleted_state_and_empty_digest(tmp_path: Path) -> None:
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
                "sha256": sha256_bytes(b""),
            }
        ],
    )


def test_untracked_entry_order_is_deterministic(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    (tmp_path / "seed.py").write_text("SEED = True\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    (tmp_path / "z.py").write_text("Z = True\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("A = True\n", encoding="utf-8")
    first = code_sha256(tmp_path)

    (tmp_path / "z.py").unlink()
    (tmp_path / "a.py").unlink()
    (tmp_path / "a.py").write_text("A = True\n", encoding="utf-8")
    (tmp_path / "z.py").write_text("Z = True\n", encoding="utf-8")

    assert code_sha256(tmp_path) == first


def test_normalized_path_collision_is_rejected(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    (tmp_path / "seed.py").write_text("SEED = True\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    composed = tmp_path / "café.py"
    decomposed = tmp_path / unicodedata.normalize("NFD", "café.py")
    composed.write_text("VALUE = 1\n", encoding="utf-8")
    decomposed.write_text("VALUE = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="normalized path collision"):
        code_sha256(tmp_path)

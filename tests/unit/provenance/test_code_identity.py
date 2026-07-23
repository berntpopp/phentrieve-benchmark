import subprocess
import unicodedata
from pathlib import Path

from phentrieve_benchmark.provenance.code_identity import code_sha256


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


def test_byte_distinct_normalized_filenames_do_not_collide(tmp_path: Path) -> None:
    _initialized_repo(tmp_path)
    (tmp_path / "seed.py").write_text("SEED = True\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    composed = tmp_path / "café.py"
    decomposed = tmp_path / unicodedata.normalize("NFD", "café.py")
    composed.write_text("VALUE = 1\n", encoding="utf-8")
    composed_identity = code_sha256(tmp_path)

    composed.unlink()
    decomposed.write_text("VALUE = 1\n", encoding="utf-8")

    assert code_sha256(tmp_path) != composed_identity

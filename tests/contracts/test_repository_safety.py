from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_repository_safety import (
    FORBIDDEN_PARTS,
    SafetyViolation,
    check_paths,
    tracked_paths,
)


def initialise_repository(root: Path) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)


def track(root: Path, path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    subprocess.run(["git", "add", "--", path.relative_to(root)], cwd=root, check=True)
    return path


def test_restricted_artifact_paths_are_rejected(tmp_path: Path) -> None:
    for forbidden in FORBIDDEN_PARTS:
        path = tmp_path / forbidden / "payload.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic", encoding="utf-8")

        with pytest.raises(SafetyViolation, match=forbidden.replace(".", r"\.")):
            check_paths(tmp_path, [path])


def test_source_file_without_secrets_is_allowed(tmp_path: Path) -> None:
    path = tmp_path / "src" / "module.py"
    path.parent.mkdir()
    path.write_text('MODEL = "general/nmt"\n', encoding="utf-8")

    check_paths(tmp_path, [path])


@pytest.mark.parametrize(
    "content",
    [
        b"-----BEGIN " + b"PRIVATE KEY-----\n",
        b"api" + b"_key = '0123456789ab'\n",
        b"client" + b"_secret: \"0123456789ab\"\n",
    ],
)
def test_secret_classes_are_rejected_without_echoing_contents(
    tmp_path: Path, content: bytes
) -> None:
    path = tmp_path / "src" / "settings.py"
    path.parent.mkdir()
    path.write_bytes(content)

    with pytest.raises(SafetyViolation) as error:
        check_paths(tmp_path, [path])

    assert "settings.py" in str(error.value)
    assert content.decode("ascii") not in str(error.value)


def test_secret_pattern_boundaries_allow_short_or_unquoted_examples(
    tmp_path: Path,
) -> None:
    path = tmp_path / "docs" / "example.md"
    path.parent.mkdir()
    path.write_bytes(
        b"api" + b"_key = 'short'\n" + b"client" + b"_secret = example\n"
    )

    check_paths(tmp_path, [path])


def test_non_utf8_binary_file_is_scanned_without_decoding(tmp_path: Path) -> None:
    path = tmp_path / "fixtures" / "binary.dat"
    path.parent.mkdir()
    path.write_bytes(b"\xff\xfe\x00\x81")

    check_paths(tmp_path, [path])


def test_tracked_paths_uses_the_git_index_from_the_repository_top_level(
    tmp_path: Path,
) -> None:
    initialise_repository(tmp_path)
    expected = track(tmp_path, tmp_path / "src" / "module.py", b"VALUE = 1\n")
    nested = tmp_path / "src" / "nested"
    nested.mkdir()

    assert tracked_paths(nested) == [expected]


def test_main_can_be_invoked_from_a_subdirectory(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, tmp_path / "src" / "module.py", b"VALUE = 1\n")
    nested = tmp_path / "src" / "nested"
    nested.mkdir()
    script = Path(__file__).parents[2] / "scripts" / "check_repository_safety.py"

    result = subprocess.run(
        [sys.executable, script],
        cwd=nested,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "repository safety check passed"


def test_tracked_paths_fails_closed_outside_a_git_repository(tmp_path: Path) -> None:
    with pytest.raises(SafetyViolation, match="Git"):
        tracked_paths(tmp_path)


def test_tracked_paths_rejects_malicious_git_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initialise_repository(tmp_path)

    def forged_git_output(
        root: Path, arguments: list[str]
    ) -> bytes:
        if arguments == ["rev-parse", "--show-toplevel"]:
            return str(tmp_path).encode("utf-8") + b"\n"
        return b"../outside.txt\0"

    monkeypatch.setattr(
        "scripts.check_repository_safety._git_output", forged_git_output
    )

    with pytest.raises(SafetyViolation, match="outside repository"):
        tracked_paths(tmp_path)


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("safe", encoding="utf-8")

    with pytest.raises(SafetyViolation, match="outside repository"):
        check_paths(tmp_path, [outside])

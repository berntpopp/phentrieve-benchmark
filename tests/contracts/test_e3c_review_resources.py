import json
import subprocess
import unicodedata
from collections import Counter
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).parents[2]
SELECTION = (
    ROOT
    / "datasets/e3c-de/selections/e3c-de-feasibility-30-v1.json"
)
REVIEW = (
    ROOT
    / "datasets/e3c-de/review/e3c-de-feasibility-30-v1"
)
EXPECTED_SNAPSHOT_SHA256 = (
    "680df333be1f0ea4805452daebef337f2a6dca3d080c03bb0fc825614b436fc5"
)


def _selected_cases() -> dict[str, str]:
    selection = json.loads(SELECTION.read_bytes())
    return {
        record["source_case_id"]: record["language"]
        for record in selection["records"]
    }


def _snapshot_sha256(files: list[Path]) -> str:
    entries = []
    for path in sorted(files):
        relative = path.relative_to(REVIEW).as_posix()
        content_sha256 = sha256(path.read_bytes()).hexdigest()
        entries.append(f"{relative}\0{content_sha256}\n".encode())
    return sha256(b"".join(entries)).hexdigest()


def test_review_snapshot_contains_exact_selected_texts() -> None:
    selected = _selected_cases()
    case_directories = {
        path.name: path for path in REVIEW.iterdir() if path.is_dir()
    }

    assert set(case_directories) == set(selected)
    assert Counter(selected.values()) == {"en": 10, "fr": 10, "es": 10}

    text_files = []
    for case_id, language in selected.items():
        case_directory = case_directories[case_id]
        expected_names = {
            f"source.{language}.txt",
            "nmt.de.txt",
            "tllm.de.txt",
        }
        files = {path.name: path for path in case_directory.iterdir()}
        assert set(files) == expected_names
        for path in files.values():
            body = path.read_bytes()
            text = body.decode("utf-8")
            assert text.strip()
            assert unicodedata.normalize("NFC", text) == text
            assert b"\r" not in body
            text_files.append(path)

    assert len(text_files) == 90
    assert _snapshot_sha256(text_files) == EXPECTED_SNAPSHOT_SHA256


def test_review_snapshot_is_pinned_to_lf_in_git_attributes() -> None:
    relative_path = (
        "datasets/e3c-de/review/e3c-de-feasibility-30-v1/"
        "EN100310/source.en.txt"
    )
    result = subprocess.run(
        ["git", "check-attr", "eol", "--", relative_path],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"{relative_path}: eol: lf\n"

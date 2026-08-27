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
ATTRIBUTION_BEGIN = "<!-- BEGIN E3C REPORT ATTRIBUTION -->"
ATTRIBUTION_END = "<!-- END E3C REPORT ATTRIBUTION -->"
EXPECTED_ATTRIBUTION_SHA256 = (
    "2501128fa5f9fc0678467910b97a837254e2488e87013aa9f50b90c959181136"
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


def _attribution_records(
    notice: str,
) -> dict[str, tuple[str, str, str, str]]:
    assert notice.count(ATTRIBUTION_BEGIN) == 1
    assert notice.count(ATTRIBUTION_END) == 1
    appendix = notice.split(ATTRIBUTION_BEGIN, maxsplit=1)[1].split(
        ATTRIBUTION_END,
        maxsplit=1,
    )[0]

    rows = []
    for line in appendix.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [
            cell.strip() for cell in line.strip().strip("|").split("|")
        ]
        assert len(cells) == 5
        case_id = cells[0].removeprefix("`").removesuffix("`")
        original_license = cells[4].removeprefix("`").removesuffix("`")
        assert cells[0] == f"`{case_id}`"
        assert cells[4] == f"`{original_license}`"
        rows.append(
            (
                case_id,
                (cells[1], cells[2], cells[3], original_license),
            )
        )

    records = dict(rows)
    assert len(records) == len(rows)
    return records


def _attribution_sha256(
    records: dict[str, tuple[str, str, str, str]],
) -> str:
    entries = []
    for case_id, fields in sorted(records.items()):
        entry = "\0".join((case_id, *fields)) + "\n"
        entries.append(entry.encode())
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


def test_review_snapshot_has_required_notice_and_no_extra_entries() -> None:
    selected = _selected_cases()
    assert {path.name for path in REVIEW.iterdir()} == {
        *selected,
        "README.md",
    }

    notice = (REVIEW / "README.md").read_text(encoding="utf-8")
    for required in (
        "unreviewed machine translations",
        "not establish clinical correctness",
        "must not be used for clinical decisions",
        "non-commercial scientific review",
        "CC BY-NC",
        "f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc",
        "https://github.com/hltfbk/E3C-Corpus/blob/"
        "f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc/README.md",
        "../../license-evidence.yaml",
        "`<variant>.de.txt`",
    ):
        assert required in notice


def test_review_snapshot_retains_original_report_attribution() -> None:
    selected = _selected_cases()
    notice = (REVIEW / "README.md").read_text(encoding="utf-8")
    for required in (
        "Every German `*.de.txt` file is an unreviewed "
        "machine-translated adaptation",
        "supplied original-report attribution and license metadata "
        "is retained verbatim",
    ):
        assert required in notice

    records = _attribution_records(notice)
    assert set(records) == set(selected)
    assert all(
        field and field == field.strip()
        for fields in records.values()
        for field in fields
    )
    assert Counter(fields[3] for fields in records.values()) == {
        "CC BY 4.0": 14,
        "CC BY": 6,
        "CC-BY": 10,
    }
    assert _attribution_sha256(records) == EXPECTED_ATTRIBUTION_SHA256

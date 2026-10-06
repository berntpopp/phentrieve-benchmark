import json
from pathlib import Path

import pytest

from phentrieve_benchmark.models.hpo_proposal import (
    MAX_EXCERPT_CHARS,
    PROPOSAL_PROVENANCE,
    ProposalRun,
    ProposalValidationReport,
)
from phentrieve_benchmark.provenance.digests import sha256_bytes

ROOT = Path(__file__).parents[2]
PROPOSALS = ROOT / "datasets/e3c-de/proposals"
PROHIBITED = {"text", "text_snippet"}


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value))
    return set()


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return []


def _runs() -> list[Path]:
    return sorted(path.parent for path in PROPOSALS.glob("*/run.json"))


@pytest.mark.parametrize("run_directory", _runs(), ids=lambda path: path.name)
def test_tracked_run_is_complete_bound_and_text_free(run_directory: Path) -> None:
    run_bytes = (run_directory / "run.json").read_bytes()
    run = ProposalRun.model_validate_json(run_bytes, strict=True)
    assert run_bytes == run.canonical_bytes()
    assert run.run_id == run_directory.name
    assert sha256_bytes((run_directory / "prompt.md").read_bytes()) == run.prompt_sha256

    validation_bytes = (run_directory / "validation.json").read_bytes()
    report = ProposalValidationReport.model_validate_json(validation_bytes, strict=True)
    assert validation_bytes == report.canonical_bytes()
    assert report.run_sha256 == sha256_bytes(run_bytes)

    batch_files = sorted(run_directory.glob("batch-*.json"))
    assert {digest.batch_id: digest.sha256 for digest in report.batches} == {
        path.stem: sha256_bytes(path.read_bytes()) for path in batch_files
    }
    # Exact file set: a stray file could carry report text into the repository.
    assert {path.name for path in run_directory.iterdir()} == {
        "prompt.md",
        "run.json",
        "validation.json",
        *(
            f"{batch.batch_id}{suffix}"
            for batch in run.batches
            for suffix in (".json", ".prompt.md")
        ),
    }
    for path in batch_files:
        payload = json.loads(path.read_bytes())
        assert payload["provenance"] == PROPOSAL_PROVENANCE
        assert not _keys(payload) & PROHIBITED
        assert max(map(len, _strings(payload)), default=0) <= MAX_EXCERPT_CHARS
    assert not _keys(json.loads(validation_bytes)) & PROHIBITED

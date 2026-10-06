# E3C Proposal Step Implementation Plan (Phase 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the uniform LLM proposal step: plan runs over the annotation corpus, hand each batch to a Claude subagent, archive the raw output, and validate it deterministically into offsets, merges, and listed rejections. Then run and evaluate a pilot.

**Architecture:** Pure modules do the logic: mention location with typography-tolerant matching, validation, run planning, and HPO lookup. A thin pipeline module reads the corpus from the artifact store and writes the run directory. Three CLI commands sit on top: `proposals prepare-run`, `proposals validate`, and `proposals hpo-lookup`. Full texts reach the subagents only through Git-ignored files under `.artifacts/proposals/`. The tracked run directory `datasets/e3c-de/proposals/<run_id>/` holds `prompt.md`, `run.json`, the rendered `batch-NN.prompt.md`, the unchanged `batch-NN.json` outputs, and `validation.json`. The German group works through the same code path. Until its translation reviews are accepted, the corpus contains no German documents, so a German run stops with an explicit pending message. The synthetic integration test exercises the German path end to end.

**Tech Stack:** Python 3.11+, Pydantic v2 (strict, frozen models), Typer CLI, pytest, uv, ruff, mypy (strict). Subagents run in Claude Code (Agent tool, model `sonnet` = `claude-sonnet-5-5`).

**Spec:** `docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md` §6 (and §3 for sequencing).
**Guideline:** `docs/annotation-guidelines/hpo-span-annotation.md` (R0–R6 apply to proposals).
**Previous plan:** `docs/superpowers/plans/2026-10-06-e3c-annotation-groups-and-corpus.md` (Phases 0–1, merged on `main`).
**Branch:** `agent/e3c-phase2-proposals` (created from `main` at `dfc864d`).

**Conventions used throughout**

- Run every command from the repository root `C:\Users\jan-p\Development\phentrieve-benchmark-local` with Git Bash.
- Tests: `uv run pytest <path> -v`. Lint: `uv run ruff check .`. Types: `uv run mypy`.
- Models follow the repo pattern `ConfigDict(extra="forbid", frozen=True, strict=True)` and expose `canonical_bytes()` via `canonical_json_bytes`.
- Write typographic characters in Python source as `\u` escapes (ruff `RUF001` flags ambiguous literals).
- Test files need unique basenames across directories (no `__init__.py` in test folders).
- Do not add AI co-authorship trailers to commits.
- If ruff only reports import ordering (`I001`) or line length in new code, fix it with `uv run ruff check --fix <file>` or by wrapping lines. Do not change behaviour.

## Decisions taken for this plan

- **HPO lookup (decided 2026-10-06):** subagents may call `proposals hpo-lookup`. It searches labels and synonyms of the pinned `hp.obo` `v2026-06-23`. It is a reference, not a hint from UMLS, E3C, or Phase 0. The validator still checks every ID.
- **Model (decided 2026-10-06):** the pilot runs on Sonnet 5.5 (`claude-sonnet-5-5`) to see whether it is good enough. The model ID is a CLI option, so switching models needs no code change.
- **Merge key (decided 2026-10-06):** spec §6.2 merges proposals with "the same HPO ID and status". The key here is (HPO ID, assertion, experiencer, temporality, **verbalized**). Without `verbalized`, a measurement (R6) merged with a worded mention of the same term would inherit `verbalized = true` and leak into single-term derivation.
- **Batch-level errors are fatal (decided 2026-10-06):** these include unparseable JSON, a wrong envelope, missing, unknown, or duplicate reports, a hash mismatch, and an over-long string. Validation collects these errors for all batches and stops with one `ProposalBatchError`. The affected outputs are deleted and their batches dispatched again; failed attempts are not kept, but their number is recorded in the runbook. Only proposal- and mention-level problems become listed rejections. This way every run document has exactly one entry in `validation.json`.
- **Excerpt limit (decided 2026-10-06):** batch files are tracked in the public repository, and the E3C texts are CC BY-NC. The prompt asks for contexts of at most 120 characters. Any string in a batch file longer than 300 characters (`MAX_EXCERPT_CHARS`), whether context, phrase, or note, is a batch-level error, so such a file is never committed. A contract test checks this for tracked runs.
- **Hashes from committed blobs:** this machine has `core.autocrlf=true`, so working-tree bytes differ from the committed blob. `prepare-run` reads the guideline and the prompt template with `git show <commit>:<path>`. `guideline_sha256` and `prompt_sha256` are therefore the hashes of the committed bytes, and `prompt.md` is a copy of that blob.
- **Rendered batch prompts are tracked:** the exact prompt for each batch (template plus paths, document IDs, and hashes, but no report text) is written as `batch-NN.prompt.md` into the run directory (spec §6.3 "the exact prompt used").
- **Texts as one file per document:** the Read tool truncates lines longer than 2,000 characters, and E3C texts have lines of up to about 4,000. The prompt therefore tells subagents to read texts with `cat`. Each text sits in its own file, so a single `cat` stays well below the Bash output limit.
- **`occurrence` ordering:** whole-word matches are counted first, then matches inside longer words. The prompt describes this ordering in the same words.
- **No restriction to HP:0000118 (decided 2026-10-06; superseded the same day after the pilots, see "Changes after the plan was written"):** the lookup and the validator accept every active term. The physician review catches out-of-scope terms, and the pilot shows whether this is a problem.
- **Permissions:** the user runs Claude Code in auto mode, which should cover the subagents' `uv run`, `cat`, and file writes. The single-batch pilot shows this. No permission settings are changed by this plan.
- **Pilot size:** one report per original language and length stratum gives 9 reports. The spec says "about eight", so this fits.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/phentrieve_benchmark/models/hpo_proposal.py` | Run, batch-output, and validation-report models |
| `src/phentrieve_benchmark/proposals/__init__.py` | Package marker |
| `src/phentrieve_benchmark/proposals/locate.py` | Typography normalization with offset maps; mention location |
| `src/phentrieve_benchmark/proposals/validate.py` | Pure validation of a run's batch outputs |
| `src/phentrieve_benchmark/proposals/run.py` | Pilot selection, document selection, batching, prompt rendering |
| `src/phentrieve_benchmark/ontology/hpo_lookup.py` | Label/synonym search over the pinned OBO |
| `src/phentrieve_benchmark/pipeline/proposals.py` | Read corpus from the store; write and validate run directories |
| `src/phentrieve_benchmark/cli.py` | `proposals prepare-run`, `proposals validate`, `proposals hpo-lookup` |
| `configs/prompts/hpo-span-proposal-v1.md` | Versioned prompt template |
| `tests/fixtures/hpo.py` | Add `proposal_hpo_obo()` fixture |
| `tests/unit/models/test_hpo_proposal.py` | Model tests |
| `tests/unit/proposals/test_proposal_locate.py` | Locator tests |
| `tests/unit/proposals/test_proposal_validate.py` | Validator tests |
| `tests/unit/proposals/test_proposal_run_planning.py` | Planning tests |
| `tests/unit/ontology/test_hpo_lookup.py` | Lookup tests |
| `tests/integration/test_proposal_run.py` | Synthetic end-to-end run incl. German document |
| `tests/unit/test_cli_proposals.py` | CLI tests |
| `tests/contracts/test_proposal_prompt.py` | Tracked prompt renders and names the guideline |
| `tests/contracts/test_tracked_proposal_runs.py` | Tracked runs are complete, bound, and text-free |
| `.gitattributes` | Keep proposal run files byte-exact |
| `datasets/e3c-de/proposals/README.md` | Runbook and pilot results |
| `datasets/e3c-de/README.md`, `docs/project-checklist.md` | Pointers and status |

---

### Task 1: Proposal models

**Files:**
- Create: `src/phentrieve_benchmark/models/hpo_proposal.py`
- Test: `tests/unit/models/test_hpo_proposal.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/models/test_hpo_proposal.py
import json
from datetime import date

import pytest

from phentrieve_benchmark.models.hpo_proposal import (
    PROPOSAL_PROVENANCE,
    BatchDocument,
    ProposalBatch,
    ProposalBatchOutput,
    ProposalRun,
    ProposedAnnotation,
)


def _document(document_id: str) -> BatchDocument:
    return BatchDocument(
        document_id=document_id,
        document_sha256="a" * 64,
        source_case_id=document_id.upper(),
        annotation_language="en",
    )


def _run(*batches: ProposalBatch) -> ProposalRun:
    return ProposalRun(
        run_id="pilot-v1",
        run_date=date(2026, 10, 7),
        model_id="claude-sonnet-5-5",
        corpus_manifest_sha256="1" * 64,
        documents_sha256="2" * 64,
        hpo_release="v2026-06-23",
        ontology_sha256="3" * 64,
        prompt_sha256="4" * 64,
        guideline_path="docs/annotation-guidelines/hpo-span-annotation.md",
        guideline_commit="5" * 40,
        guideline_sha256="6" * 64,
        batches=batches,
    )


def test_run_round_trips_through_canonical_json() -> None:
    run = _run(ProposalBatch(batch_id="batch-01", documents=(_document("d1"),)))
    assert ProposalRun.model_validate_json(run.canonical_bytes(), strict=True) == run


def test_run_rejects_a_document_in_two_batches() -> None:
    with pytest.raises(ValueError, match="more than one batch"):
        _run(
            ProposalBatch(batch_id="batch-01", documents=(_document("d1"),)),
            ProposalBatch(batch_id="batch-02", documents=(_document("d1"),)),
        )


def test_run_rejects_duplicate_batch_ids() -> None:
    with pytest.raises(ValueError, match="duplicate batch"):
        _run(
            ProposalBatch(batch_id="batch-01", documents=(_document("d1"),)),
            ProposalBatch(batch_id="batch-01", documents=(_document("d2"),)),
        )


def test_run_id_must_be_a_safe_directory_name() -> None:
    run = _run(ProposalBatch(batch_id="batch-01", documents=(_document("d1"),)))
    payload = run.model_dump(mode="json")
    payload["run_id"] = "../x"
    with pytest.raises(ValueError):
        ProposalRun.model_validate_json(json.dumps(payload), strict=True)


def test_batch_output_requires_the_provenance_notice() -> None:
    payload = {
        "schema_version": "e3c-hpo-proposal-batch/v1",
        "provenance": "gold",
        "run_id": "pilot-v1",
        "batch_id": "batch-01",
        "reports": [],
    }
    with pytest.raises(ValueError):
        ProposalBatchOutput.model_validate_json(json.dumps(payload), strict=True)
    payload["provenance"] = PROPOSAL_PROVENANCE
    assert ProposalBatchOutput.model_validate_json(json.dumps(payload), strict=True)


@pytest.mark.parametrize(
    ("field", "value"),
    [("experiencer", "unknown"), ("temporality", "future"), ("assertion", "yes")],
)
def test_proposed_annotation_uses_guideline_r3_values(field: str, value: str) -> None:
    payload: dict[str, object] = {
        "proposal_id": "p001",
        "hpo_id": "HP:0001945",
        "hpo_label": "Fever",
        "assertion": "present",
        "experiencer": "patient",
        "temporality": "current",
        "verbalized": True,
        "mentions": [{"phrase": "Fieber", "context": "hohem Fieber"}],
        "note": None,
    }
    assert ProposedAnnotation.model_validate_json(json.dumps(payload), strict=True)
    payload[field] = value
    with pytest.raises(ValueError):
        ProposedAnnotation.model_validate_json(json.dumps(payload), strict=True)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/models/test_hpo_proposal.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phentrieve_benchmark.models.hpo_proposal'`.

- [ ] **Step 3: Implement the models**

```python
# src/phentrieve_benchmark/models/hpo_proposal.py
"""Models for the LLM proposal step.

Proposals are machine generated, not review data, and not gold. A run lists
its batches; each batch output is the unchanged subagent JSON; the validation
report resolves offsets, merges, and rejections deterministically.
"""

from datetime import date
from enum import StrEnum
from typing import Any, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes
from phentrieve_benchmark.selection.groups import AnnotationLanguage

PROPOSAL_PROVENANCE: Final = "machine generated, not review data, not gold"
# Longest string allowed anywhere in a tracked batch output (licence: excerpts only).
MAX_EXCERPT_CHARS: Final = 300
Provenance = Literal["machine generated, not review data, not gold"]
Assertion = Literal["present", "absent", "uncertain"]
ProposalExperiencer = Literal["patient", "family_member", "other"]
ProposalTemporality = Literal["current", "historical"]
_RUN_ID = r"^[a-z0-9][a-z0-9-]{0,62}$"
_BATCH_ID = r"^batch-[0-9]{2,}$"
_HPO_ID = r"^HP:[0-9]{7}$"


class BatchDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    document_id: str = Field(min_length=1)
    document_sha256: Sha256Hex
    source_case_id: str = Field(min_length=1)
    annotation_language: AnnotationLanguage


class ProposalBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str = Field(pattern=_BATCH_ID)
    documents: tuple[BatchDocument, ...] = Field(min_length=1)


class ProposalRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-hpo-proposal-run/v1"] = "e3c-hpo-proposal-run/v1"
    run_id: str = Field(pattern=_RUN_ID)
    run_date: date
    model_id: str = Field(min_length=1)
    corpus_manifest_sha256: Sha256Hex
    documents_sha256: Sha256Hex
    hpo_release: str = Field(pattern=r"^v[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    ontology_sha256: Sha256Hex
    prompt_sha256: Sha256Hex
    guideline_path: str = Field(min_length=1)
    guideline_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    guideline_sha256: Sha256Hex
    batches: tuple[ProposalBatch, ...] = Field(min_length=1)
    # German reports of the selection left out because their review is pending.
    pending_review: tuple[str, ...] = ()

    @model_validator(mode="after")
    def batches_are_disjoint(self) -> Self:
        batch_ids = [batch.batch_id for batch in self.batches]
        if len(batch_ids) != len(set(batch_ids)):
            raise ValueError("duplicate batch ID")
        document_ids = [
            document.document_id
            for batch in self.batches
            for document in batch.documents
        ]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("a document appears in more than one batch slot")
        return self

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))


class ProposalMention(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    phrase: str = Field(min_length=1)
    context: str = Field(min_length=1)
    occurrence: int | None = Field(default=None, ge=1)


class ProposedAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    proposal_id: str = Field(pattern=r"^p[0-9]{3,}$")
    hpo_id: str = Field(pattern=_HPO_ID)
    hpo_label: str = Field(min_length=1)
    assertion: Assertion
    experiencer: ProposalExperiencer
    temporality: ProposalTemporality
    verbalized: bool
    mentions: tuple[ProposalMention, ...] = Field(min_length=1)
    note: str | None = None


class ReportOutput(BaseModel):
    """One report of a batch output; annotations are checked one by one."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    document_id: str = Field(min_length=1)
    document_sha256: Sha256Hex
    annotations: tuple[Any, ...]


class ProposalBatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-hpo-proposal-batch/v1"]
    provenance: Provenance
    run_id: str
    batch_id: str
    reports: tuple[ReportOutput, ...]


class RejectionReason(StrEnum):
    INVALID_SCHEMA = "invalid_schema"
    DUPLICATE_PROPOSAL_ID = "duplicate_proposal_id"
    UNKNOWN_HPO_ID = "unknown_hpo_id"
    OBSOLETE_HPO_ID = "obsolete_hpo_id"
    NO_VALID_MENTIONS = "no_valid_mentions"
    PHRASE_NOT_TRIMMED = "phrase_not_trimmed"
    CONTEXT_NOT_FOUND = "context_not_found"
    CONTEXT_NOT_UNIQUE = "context_not_unique"
    PHRASE_NOT_IN_CONTEXT = "phrase_not_in_context"
    PHRASE_NOT_UNIQUE_IN_CONTEXT = "phrase_not_unique_in_context"
    OCCURRENCE_OUT_OF_RANGE = "occurrence_out_of_range"
    OVERLAPPING_MENTION = "overlapping_mention"


class Rejection(BaseModel):
    """A rejected proposal (no mention index) or mention (with index)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str
    document_id: str
    proposal_id: str | None
    mention_index: int | None = Field(default=None, ge=0)
    reason: RejectionReason
    detail: str


class LabelWarning(BaseModel):
    """The proposed label differs from the pinned label; the ID still counts."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str
    document_id: str
    proposal_id: str
    hpo_id: str
    proposed_label: str
    pinned_label: str | None


class ResolvedMention(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_proposal_id: str
    mention_index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    phrase: str = Field(min_length=1)


class ValidatedProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    proposal_id: str
    source_proposal_ids: tuple[str, ...] = Field(min_length=1)
    hpo_id: str = Field(pattern=_HPO_ID)
    hpo_label: str
    assertion: Assertion
    experiencer: ProposalExperiencer
    temporality: ProposalTemporality
    verbalized: bool
    mentions: tuple[ResolvedMention, ...] = Field(min_length=1)
    notes: tuple[str, ...]


class DocumentProposals(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str
    document_id: str
    document_sha256: Sha256Hex
    proposals: tuple[ValidatedProposal, ...]


class BatchDigest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    batch_id: str
    sha256: Sha256Hex


class ValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    documents: int
    proposals_received: int
    proposals_rejected: int
    validated_proposals: int
    mentions_evaluated: int
    mentions_rejected: int
    validated_mentions: int
    rejections_by_reason: dict[str, int]


class ProposalValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-hpo-proposal-validation/v1"] = (
        "e3c-hpo-proposal-validation/v1"
    )
    provenance: Provenance = PROPOSAL_PROVENANCE
    run_id: str
    run_sha256: Sha256Hex
    corpus_manifest_sha256: Sha256Hex
    hpo_release: str
    ontology_sha256: Sha256Hex
    batches: tuple[BatchDigest, ...]
    documents: tuple[DocumentProposals, ...]
    rejections: tuple[Rejection, ...]
    warnings: tuple[LabelWarning, ...]
    summary: ValidationSummary

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/models/test_hpo_proposal.py -v`
Expected: 8 passed.

- [ ] **Step 5: Lint and type check**

Run: `uv run ruff check src/phentrieve_benchmark/models/hpo_proposal.py tests/unit/models/test_hpo_proposal.py && uv run mypy`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/phentrieve_benchmark/models/hpo_proposal.py tests/unit/models/test_hpo_proposal.py
git commit -m "feat: add models for the HPO proposal step"
```

---

### Task 2: Mention locator with typography-tolerant matching

**Files:**
- Create: `src/phentrieve_benchmark/proposals/__init__.py` (empty)
- Create: `src/phentrieve_benchmark/proposals/locate.py`
- Test: `tests/unit/proposals/test_proposal_locate.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/proposals/test_proposal_locate.py
import pytest

from phentrieve_benchmark.models.hpo_proposal import RejectionReason
from phentrieve_benchmark.proposals.locate import (
    LocatedSpan,
    MentionLocationError,
    locate_mention,
    normalize_typography,
)


def _locate(
    text: str, phrase: str, context: str, occurrence: int | None = None
) -> LocatedSpan:
    return locate_mention(
        normalize_typography(text),
        phrase=phrase,
        context=context,
        occurrence=occurrence,
    )


def _reason(
    text: str, phrase: str, context: str, occurrence: int | None = None
) -> RejectionReason:
    with pytest.raises(MentionLocationError) as caught:
        _locate(text, phrase, context, occurrence)
    return caught.value.reason


def test_normalization_maps_typography_and_collapses_whitespace() -> None:
    normalized = normalize_typography("a\u00a0 \u201eb\u201c\u2013c")
    assert normalized.value == 'a "b"-c'
    assert normalized.starts == (0, 1, 3, 4, 5, 6, 7)
    assert normalized.ends == (1, 3, 4, 5, 6, 7, 8)


def test_exact_phrase_resolves_to_original_offsets() -> None:
    text = "Die Schwellung ging mit hohem Fieber einher."
    span = _locate(text, "Fieber", "mit hohem Fieber einher")
    assert (span.start, span.end) == (text.index("Fieber"), text.index("Fieber") + 6)


def test_typography_differences_are_tolerated_and_spans_stay_verbatim() -> None:
    text = "Temperatur 39,5\u00a0\u00b0C \u2013 \u201ehohes Fieber\u201c."
    span = _locate(text, "39,5 \u00b0C", 'Temperatur 39,5 \u00b0C - "hohes')
    assert text[span.start : span.end] == "39,5\u00a0\u00b0C"
    span = _locate(text, "hohes Fieber", '"hohes Fieber"')
    assert text[span.start : span.end] == "hohes Fieber"


def test_whole_word_match_takes_precedence() -> None:
    text = "She reported headache and ache in the back."
    span = _locate(text, "ache", "headache and ache in")
    assert span.start == text.index("and ache") + 4


def test_in_word_matches_count_after_whole_words() -> None:
    text = "She reported headache and ache in the back."
    span = _locate(text, "ache", "headache and ache in", occurrence=2)
    assert span.start == text.index("headache") + 4


def test_occurrence_selects_among_repeated_matches() -> None:
    text = "Fever on day one, fever on day three, fever on day five."
    context = "fever on day three, fever on day five"
    span = _locate(text, "fever", context, occurrence=2)
    assert span.start == text.index("fever on day five")
    assert (
        _reason(text, "fever", context)
        is RejectionReason.PHRASE_NOT_UNIQUE_IN_CONTEXT
    )
    assert (
        _reason(text, "fever", context, occurrence=3)
        is RejectionReason.OCCURRENCE_OUT_OF_RANGE
    )


@pytest.mark.parametrize(
    ("text", "phrase", "context", "reason"),
    [
        ("Hohes Fieber.", "Fieber", "kein Fieber", RejectionReason.CONTEXT_NOT_FOUND),
        ("Fieber. Fieber.", "Fieber", "Fieber", RejectionReason.CONTEXT_NOT_UNIQUE),
        (
            "mit hohem Fieber einher",
            "Husten",
            "hohem Fieber",
            RejectionReason.PHRASE_NOT_IN_CONTEXT,
        ),
        (
            "Hohes Fieber.",
            " Fieber",
            "Hohes Fieber",
            RejectionReason.PHRASE_NOT_TRIMMED,
        ),
    ],
)
def test_unlocatable_mentions_name_their_reason(
    text: str, phrase: str, context: str, reason: RejectionReason
) -> None:
    assert _reason(text, phrase, context) is reason
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/proposals/test_proposal_locate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phentrieve_benchmark.proposals'`.

- [ ] **Step 3: Implement the locator**

Create an empty `src/phentrieve_benchmark/proposals/__init__.py`, then:

```python
# src/phentrieve_benchmark/proposals/locate.py
"""Locate proposed mentions in a document text.

Language models do not count characters reliably, so a mention is given as
two verbatim strings: the phrase and a short context that contains it.
Matching tolerates typography a model may alter (quotation marks, dashes,
non-breaking and repeated whitespace); offsets always refer to the original
text, so a stored span is the verbatim original.
"""

import unicodedata
from dataclasses import dataclass

from phentrieve_benchmark.models.hpo_proposal import RejectionReason

_TYPOGRAPHY = {
    "\u00ab": '"',
    "\u00bb": '"',
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u2039": "'",
    "\u203a": "'",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
}


@dataclass(frozen=True)
class NormalizedText:
    """Normalized text; normalized character i covers original [starts[i], ends[i])."""

    value: str
    starts: tuple[int, ...]
    ends: tuple[int, ...]


@dataclass(frozen=True)
class LocatedSpan:
    start: int
    end: int


class MentionLocationError(ValueError):
    def __init__(self, reason: RejectionReason, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def normalize_typography(text: str) -> NormalizedText:
    characters: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    index = 0
    while index < len(text):
        character = text[index]
        if character.isspace():
            end = index + 1
            while end < len(text) and text[end].isspace():
                end += 1
            characters.append(" ")
            starts.append(index)
            ends.append(end)
            index = end
            continue
        characters.append(_TYPOGRAPHY.get(character, character))
        starts.append(index)
        ends.append(index + 1)
        index += 1
    return NormalizedText("".join(characters), tuple(starts), tuple(ends))


def _normalized(value: str) -> str:
    return normalize_typography(unicodedata.normalize("NFC", value)).value


def _positions(haystack: str, needle: str, start: int, end: int) -> list[int]:
    positions: list[int] = []
    position = haystack.find(needle, start, end)
    while position != -1:
        positions.append(position)
        position = haystack.find(needle, position + 1, end)
    return positions


def _whole_word(haystack: str, start: int, end: int) -> bool:
    before = haystack[start - 1] if start > 0 else ""
    after = haystack[end] if end < len(haystack) else ""
    return not before.isalnum() and not after.isalnum()


def locate_mention(
    text: NormalizedText, *, phrase: str, context: str, occurrence: int | None
) -> LocatedSpan:
    """Return original offsets of the phrase inside its unique context.

    Candidates are ordered whole-word matches first, then matches inside
    longer words. Without `occurrence` the phrase must have exactly one
    candidate of the first kind present; `occurrence` (1-based) indexes the
    ordered candidates.
    """
    if phrase != phrase.strip():
        raise MentionLocationError(
            RejectionReason.PHRASE_NOT_TRIMMED,
            "phrase has leading or trailing whitespace",
        )
    needle_context = _normalized(context)
    contexts = _positions(text.value, needle_context, 0, len(text.value))
    if not contexts:
        raise MentionLocationError(
            RejectionReason.CONTEXT_NOT_FOUND, "context does not occur in the text"
        )
    if len(contexts) > 1:
        raise MentionLocationError(
            RejectionReason.CONTEXT_NOT_UNIQUE,
            f"context occurs {len(contexts)} times in the text",
        )
    context_start = contexts[0]
    context_end = context_start + len(needle_context)
    needle_phrase = _normalized(phrase)
    matches = _positions(text.value, needle_phrase, context_start, context_end)
    if not matches:
        raise MentionLocationError(
            RejectionReason.PHRASE_NOT_IN_CONTEXT,
            "phrase does not occur in its context",
        )
    whole_words = [
        position
        for position in matches
        if _whole_word(text.value, position, position + len(needle_phrase))
    ]
    in_words = [position for position in matches if position not in whole_words]
    candidates = whole_words + in_words
    if occurrence is None:
        preferred = whole_words or in_words
        if len(preferred) > 1:
            raise MentionLocationError(
                RejectionReason.PHRASE_NOT_UNIQUE_IN_CONTEXT,
                f"phrase occurs {len(preferred)} times in its context; "
                "set occurrence",
            )
        chosen = preferred[0]
    else:
        if occurrence > len(candidates):
            raise MentionLocationError(
                RejectionReason.OCCURRENCE_OUT_OF_RANGE,
                f"occurrence {occurrence} exceeds {len(candidates)} matches",
            )
        chosen = candidates[occurrence - 1]
    last = chosen + len(needle_phrase) - 1
    return LocatedSpan(start=text.starts[chosen], end=text.ends[last])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/proposals/test_proposal_locate.py -v`
Expected: 10 passed.

- [ ] **Step 5: Lint and type check**

Run: `uv run ruff check src/phentrieve_benchmark/proposals tests/unit/proposals && uv run mypy`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/phentrieve_benchmark/proposals tests/unit/proposals/test_proposal_locate.py
git commit -m "feat: locate proposed mentions with typography-tolerant matching"
```

---

### Task 3: HPO lookup over the pinned release

**Files:**
- Modify: `tests/fixtures/hpo.py`
- Create: `src/phentrieve_benchmark/ontology/hpo_lookup.py`
- Test: `tests/unit/ontology/test_hpo_lookup.py`

- [ ] **Step 1: Add the proposal HPO fixture**

Append to `tests/fixtures/hpo.py`:

```python
def proposal_hpo_obo() -> bytes:
    return b"""format-version: 1.4
ontology: hp

[Term]
id: HP:0001945
name: Fever
synonym: "Pyrexia" EXACT []
synonym: "Hyperthermia" RELATED []
alt_id: HP:0009998

[Term]
id: HP:0002013
name: Vomiting
synonym: "Emesis" EXACT []

[Term]
id: HP:0002019
name: Constipation

[Term]
id: HP:0012735
name: Cough

[Term]
id: HP:0002373
name: Febrile seizure (within the age range of 3 months to 6 years)
synonym: "Febrile convulsion" EXACT []

[Term]
id: HP:0003326
name: Myalgia
synonym: "Muscle pain" EXACT []

[Term]
id: HP:0002829
name: Arthralgia
synonym: "Joint pain" EXACT []

[Term]
id: HP:0009999
name: Obsolete fever variant
is_obsolete: true
replaced_by: HP:0001945
"""
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/unit/ontology/test_hpo_lookup.py
from hashlib import sha256

from phentrieve_benchmark.ontology.hpo import load_hpo_index
from phentrieve_benchmark.ontology.hpo_lookup import read_lookup_entries, search_hpo
from tests.fixtures.hpo import proposal_hpo_obo

_ENTRIES = read_lookup_entries(proposal_hpo_obo())


def _ids(query: str, limit: int = 15) -> list[str]:
    return [match.entry.hpo_id for match in search_hpo(_ENTRIES, query, limit=limit)]


def test_fixture_is_a_valid_strict_hpo_index() -> None:
    body = proposal_hpo_obo()
    index = load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )
    assert index.alternate_to_primary["HP:0009998"] == "HP:0001945"


def test_reads_labels_synonyms_and_obsolete_flags() -> None:
    fever = next(entry for entry in _ENTRIES if entry.hpo_id == "HP:0001945")
    assert fever.label == "Fever"
    assert fever.synonyms == ("Pyrexia", "Hyperthermia")
    assert not fever.obsolete
    obsolete = next(entry for entry in _ENTRIES if entry.hpo_id == "HP:0009999")
    assert obsolete.obsolete


def test_text_search_skips_obsolete_terms() -> None:
    assert _ids("fever") == ["HP:0001945"]


def test_synonym_match_reports_the_synonym() -> None:
    (match,) = search_hpo(_ENTRIES, "muscle pain")
    assert match.entry.hpo_id == "HP:0003326"
    assert match.matched == "Muscle pain"


def test_all_tokens_must_match_and_accents_fold() -> None:
    assert _ids("F\u00e9brile convulsion") == ["HP:0002373"]
    assert _ids("joint fever") == []


def test_exact_label_ranks_before_partial_matches() -> None:
    assert _ids("pain") == ["HP:0002829", "HP:0003326"]
    assert _ids("pain", limit=1) == ["HP:0002829"]


def test_id_query_returns_the_term_even_if_obsolete() -> None:
    (match,) = search_hpo(_ENTRIES, " HP:0009999 ")
    assert match.entry.obsolete
    assert match.matched == "Obsolete fever variant"
```

`"pain"` matches "Joint pain" and "Muscle pain" at the same position rank, so the shorter name wins: "Joint pain" (`HP:0002829`, 10 characters) comes before "Muscle pain" (`HP:0003326`, 11 characters).

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/ontology/test_hpo_lookup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phentrieve_benchmark.ontology.hpo_lookup'`.

- [ ] **Step 4: Implement the lookup**

```python
# src/phentrieve_benchmark/ontology/hpo_lookup.py
"""Search the pinned HPO release by label, synonym, or ID.

A lookup aid for the proposal subagents. It reads OBO term stanzas directly
(fast enough for repeated CLI calls); the validator still checks every
proposed ID against the strict HPO index.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

_HPO_ID = re.compile(r"HP:[0-9]{7}", re.ASCII)
_SYNONYM = re.compile(r'^synonym: "((?:[^"\\]|\\.)*)"')


@dataclass(frozen=True)
class HpoLookupEntry:
    hpo_id: str
    label: str
    synonyms: tuple[str, ...]
    obsolete: bool


@dataclass(frozen=True)
class HpoLookupMatch:
    entry: HpoLookupEntry
    matched: str


def _entry(lines: list[str]) -> HpoLookupEntry | None:
    hpo_id = next((line[4:] for line in lines if line.startswith("id: ")), None)
    label = next((line[6:] for line in lines if line.startswith("name: ")), None)
    if hpo_id is None or label is None or _HPO_ID.fullmatch(hpo_id) is None:
        return None
    synonyms = tuple(
        match.group(1).replace('\\"', '"')
        for line in lines
        if (match := _SYNONYM.match(line)) is not None
    )
    return HpoLookupEntry(
        hpo_id=hpo_id,
        label=label,
        synonyms=synonyms,
        obsolete="is_obsolete: true" in lines,
    )


def read_lookup_entries(ontology_bytes: bytes) -> tuple[HpoLookupEntry, ...]:
    entries: list[HpoLookupEntry] = []
    stanza: list[str] | None = None
    for line in (*ontology_bytes.decode("utf-8").splitlines(), "[End]"):
        if line.startswith("["):
            if stanza is not None and (entry := _entry(stanza)) is not None:
                entries.append(entry)
            stanza = [] if line == "[Term]" else None
        elif stanza is not None:
            stanza.append(line)
    return tuple(entries)


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )


def search_hpo(
    entries: Sequence[HpoLookupEntry], query: str, *, limit: int = 15
) -> tuple[HpoLookupMatch, ...]:
    """Return active terms whose label or a synonym contains every query word.

    An exact HPO ID returns that term, obsolete or not. Ranking: exact name,
    then names starting with the query, then other matches; shorter names
    first; HPO ID breaks ties.
    """
    stripped = query.strip()
    if _HPO_ID.fullmatch(stripped):
        return tuple(
            HpoLookupMatch(entry=entry, matched=entry.label)
            for entry in entries
            if entry.hpo_id == stripped
        )
    folded_query = _fold(stripped)
    tokens = folded_query.split()
    if not tokens:
        return ()
    ranked: list[tuple[tuple[int, int], str, HpoLookupMatch]] = []
    for entry in entries:
        if entry.obsolete:
            continue
        best: tuple[tuple[int, int], str] | None = None
        for name in (entry.label, *entry.synonyms):
            folded = _fold(name)
            if not all(token in folded for token in tokens):
                continue
            if folded == folded_query:
                position = 0
            elif folded.startswith(folded_query):
                position = 1
            else:
                position = 2
            rank = (position, len(name))
            if best is None or rank < best[0]:
                best = (rank, name)
        if best is not None:
            ranked.append(
                (best[0], entry.hpo_id, HpoLookupMatch(entry=entry, matched=best[1]))
            )
    ranked.sort(key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in ranked[:limit])
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/ontology/test_hpo_lookup.py -v`
Expected: 7 passed.

- [ ] **Step 6: Lint, types, existing HPO tests**

Run: `uv run ruff check src/phentrieve_benchmark/ontology tests/unit/ontology tests/fixtures && uv run mypy && uv run pytest tests/unit/ontology -q`
Expected: no errors; all pass.

- [ ] **Step 7: Commit**

```bash
git add src/phentrieve_benchmark/ontology/hpo_lookup.py tests/unit/ontology/test_hpo_lookup.py tests/fixtures/hpo.py
git commit -m "feat: add HPO label and synonym lookup over the pinned release"
```

---

### Task 4: Deterministic validation of batch outputs

**Files:**
- Create: `src/phentrieve_benchmark/proposals/validate.py`
- Test: `tests/unit/proposals/test_proposal_validate.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/proposals/test_proposal_validate.py
import json
from datetime import date
from hashlib import sha256
from typing import Any

import pytest

from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.hpo_proposal import (
    MAX_EXCERPT_CHARS,
    PROPOSAL_PROVENANCE,
    BatchDocument,
    ProposalBatch,
    ProposalRun,
    ProposalValidationReport,
    RejectionReason,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex, load_hpo_index
from phentrieve_benchmark.proposals.validate import (
    ProposalBatchError,
    validate_proposal_run,
)
from tests.fixtures.hpo import proposal_hpo_obo

_GERMAN = Document.from_text(
    source_case_id="EN1",
    case_group_id="e3c:v2.0.0:EN1",
    document_id="e3c:v2.0.0:de:EN1:translated",
    language="de",
    translation_status=TranslationStatus.TRANSLATED,
    text=(
        "Die Schwellung ging mit hohem Fieber\u00a0einher. "
        "Diese Symptome waren nicht mit Erbrechen verbunden. "
        "Am dritten Tag erneut Fieber, Temperatur 39,5\u00a0\u00b0C."
    ),
)
_FIRST_FEVER = {"phrase": "Fieber", "context": "mit hohem Fieber einher"}
_SECOND_FEVER = {"phrase": "Fieber", "context": "erneut Fieber, Temperatur"}


def _index() -> HpoIndex:
    body = proposal_hpo_obo()
    return load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )


def _run() -> ProposalRun:
    return ProposalRun(
        run_id="test-run",
        run_date=date(2026, 10, 7),
        model_id="claude-sonnet-5-5",
        corpus_manifest_sha256="1" * 64,
        documents_sha256="2" * 64,
        hpo_release="v2026-06-23",
        ontology_sha256=sha256(proposal_hpo_obo()).hexdigest(),
        prompt_sha256="3" * 64,
        guideline_path="docs/annotation-guidelines/hpo-span-annotation.md",
        guideline_commit="4" * 40,
        guideline_sha256="5" * 64,
        batches=(
            ProposalBatch(
                batch_id="batch-01",
                documents=(
                    BatchDocument(
                        document_id=_GERMAN.document_id,
                        document_sha256=_GERMAN.document_sha256,
                        source_case_id="EN1",
                        annotation_language="de",
                    ),
                ),
            ),
        ),
    )


def _proposal(
    proposal_id: str = "p001",
    *,
    mentions: list[dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "proposal_id": proposal_id,
        "hpo_id": "HP:0001945",
        "hpo_label": "Fever",
        "assertion": "present",
        "experiencer": "patient",
        "temporality": "current",
        "verbalized": True,
        "mentions": mentions if mentions is not None else [_FIRST_FEVER],
        "note": None,
    }
    payload.update(overrides)
    return payload


def _output(reports: list[dict[str, Any]], **overrides: Any) -> bytes:
    payload: dict[str, Any] = {
        "schema_version": "e3c-hpo-proposal-batch/v1",
        "provenance": PROPOSAL_PROVENANCE,
        "run_id": "test-run",
        "batch_id": "batch-01",
        "reports": reports,
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False).encode()


def _report(annotations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "document_id": _GERMAN.document_id,
        "document_sha256": _GERMAN.document_sha256,
        "annotations": annotations,
    }


def _validate_outputs(outputs: dict[str, bytes]) -> ProposalValidationReport:
    return validate_proposal_run(
        run=_run(),
        run_sha256="6" * 64,
        batch_outputs=outputs,
        documents={_GERMAN.document_id: _GERMAN},
        hpo_index=_index(),
    )


def _validate(annotations: list[dict[str, Any]]) -> ProposalValidationReport:
    return _validate_outputs({"batch-01": _output([_report(annotations)])})


def _reasons(report: ProposalValidationReport) -> list[RejectionReason]:
    return [rejection.reason for rejection in report.rejections]


def test_valid_proposal_resolves_offsets_in_the_original_text() -> None:
    report = _validate([_proposal()])
    (document,) = report.documents
    (proposal,) = document.proposals
    (mention,) = proposal.mentions
    assert mention.start == _GERMAN.text.index("Fieber")
    assert _GERMAN.text[mention.start : mention.end] == "Fieber" == mention.phrase
    assert proposal.hpo_label == "Fever"
    assert report.rejections == ()


def test_measurement_span_keeps_the_original_spacing() -> None:
    report = _validate(
        [
            _proposal(),
            _proposal(
                "p002",
                verbalized=False,
                mentions=[
                    {"phrase": "39,5 \u00b0C", "context": "Temperatur 39,5 \u00b0C"}
                ],
            ),
        ]
    )
    proposals = report.documents[0].proposals
    assert len(proposals) == 2
    measurement = next(p for p in proposals if not p.verbalized)
    assert measurement.mentions[0].phrase == "39,5\u00a0\u00b0C"


def test_same_term_and_status_are_merged() -> None:
    report = _validate(
        [_proposal(), _proposal("p002", mentions=[_SECOND_FEVER], note="again")]
    )
    (proposal,) = report.documents[0].proposals
    assert proposal.proposal_id == "p001"
    assert proposal.source_proposal_ids == ("p001", "p002")
    assert [m.source_proposal_id for m in proposal.mentions] == ["p001", "p002"]
    assert proposal.notes == ("again",)


def test_different_status_stays_separate() -> None:
    report = _validate(
        [_proposal(), _proposal("p002", assertion="absent", mentions=[_SECOND_FEVER])]
    )
    assert len(report.documents[0].proposals) == 2


@pytest.mark.parametrize(
    ("hpo_id", "reason", "detail"),
    [
        ("HP:1234567", RejectionReason.UNKNOWN_HPO_ID, "not in the pinned"),
        ("HP:0009998", RejectionReason.UNKNOWN_HPO_ID, "alternate ID of HP:0001945"),
        ("HP:0009999", RejectionReason.OBSOLETE_HPO_ID, "obsolete"),
    ],
)
def test_invalid_hpo_ids_are_rejected(
    hpo_id: str, reason: RejectionReason, detail: str
) -> None:
    report = _validate([_proposal(hpo_id=hpo_id)])
    (rejection,) = report.rejections
    assert rejection.reason is reason
    assert detail in rejection.detail
    assert rejection.proposal_id == "p001"
    assert report.documents[0].proposals == ()


def test_schema_violation_is_rejected_with_the_proposal_id() -> None:
    report = _validate([_proposal(experiencer="unknown")])
    (rejection,) = report.rejections
    assert rejection.reason is RejectionReason.INVALID_SCHEMA
    assert rejection.proposal_id == "p001"
    assert "experiencer" in rejection.detail


def test_duplicate_proposal_id_is_rejected() -> None:
    report = _validate([_proposal(), _proposal(mentions=[_SECOND_FEVER])])
    assert _reasons(report) == [RejectionReason.DUPLICATE_PROPOSAL_ID]
    assert len(report.documents[0].proposals[0].mentions) == 1


def test_mention_rejection_keeps_the_rest_of_the_proposal() -> None:
    report = _validate(
        [_proposal(mentions=[_FIRST_FEVER, {"phrase": "Fieber", "context": "kein Fieber"}])]
    )
    (rejection,) = report.rejections
    assert rejection.reason is RejectionReason.CONTEXT_NOT_FOUND
    assert rejection.mention_index == 1
    assert len(report.documents[0].proposals[0].mentions) == 1


def test_proposal_without_located_mentions_is_rejected() -> None:
    report = _validate([_proposal(mentions=[{"phrase": "Fieber", "context": "kein Fieber"}])])
    assert _reasons(report) == [
        RejectionReason.CONTEXT_NOT_FOUND,
        RejectionReason.NO_VALID_MENTIONS,
    ]
    assert report.documents[0].proposals == ()


def test_overlapping_mentions_of_one_merged_proposal_are_rejected() -> None:
    report = _validate(
        [
            _proposal(
                mentions=[{"phrase": "hohem Fieber", "context": "mit hohem Fieber einher"}]
            ),
            _proposal("p002", mentions=[_FIRST_FEVER]),
        ]
    )
    (rejection,) = report.rejections
    assert rejection.reason is RejectionReason.OVERLAPPING_MENTION
    assert (rejection.proposal_id, rejection.mention_index) == ("p002", 0)
    (proposal,) = report.documents[0].proposals
    assert proposal.source_proposal_ids == ("p001", "p002")
    assert [m.phrase for m in proposal.mentions] == ["hohem Fieber"]


def test_label_mismatch_is_only_a_warning() -> None:
    report = _validate([_proposal(hpo_label="Pyrexia")])
    (warning,) = report.warnings
    assert (warning.proposed_label, warning.pinned_label) == ("Pyrexia", "Fever")
    assert len(report.documents[0].proposals) == 1


def test_summary_counts_add_up() -> None:
    report = _validate(
        [
            _proposal(mentions=[_FIRST_FEVER, {"phrase": "Fieber", "context": "kein Fieber"}]),
            _proposal("p002", mentions=[_SECOND_FEVER]),
            _proposal(
                "p003",
                hpo_id="HP:0002013",
                hpo_label="Vomiting",
                assertion="absent",
                mentions=[{"phrase": "Erbrechen", "context": "nicht mit Erbrechen verbunden"}],
            ),
            _proposal("p004", hpo_id="HP:1234567"),
        ]
    )
    summary = report.summary
    accepted_sources = sum(
        len(p.source_proposal_ids) for p in report.documents[0].proposals
    )
    assert summary.proposals_received == 4
    assert summary.proposals_received == summary.proposals_rejected + accepted_sources
    assert summary.validated_proposals == 2
    assert summary.mentions_evaluated == 4
    assert (
        summary.mentions_evaluated
        == summary.mentions_rejected + summary.validated_mentions
    )
    assert summary.rejections_by_reason == {
        "context_not_found": 1,
        "unknown_hpo_id": 1,
    }


def test_report_is_deterministic_and_binds_the_batch_bytes() -> None:
    first = _validate([_proposal()])
    second = _validate([_proposal()])
    assert first.canonical_bytes() == second.canonical_bytes()
    raw = _output([_report([_proposal()])])
    assert first.batches[0].sha256 == sha256(raw).hexdigest()


def test_wrong_document_hash_fails_the_batch() -> None:
    report = _report([])
    report["document_sha256"] = "0" * 64
    with pytest.raises(ProposalBatchError, match="does not match"):
        _validate_outputs({"batch-01": _output([report])})


def test_missing_report_fails_the_batch() -> None:
    with pytest.raises(ProposalBatchError, match="missing"):
        _validate_outputs({"batch-01": _output([])})


def test_missing_batch_output_fails_the_run() -> None:
    with pytest.raises(ProposalBatchError, match="batch outputs missing"):
        _validate_outputs({})


def test_wrong_provenance_fails_the_batch() -> None:
    with pytest.raises(ProposalBatchError, match="invalid batch output"):
        _validate_outputs({"batch-01": _output([_report([])], provenance="gold")})


_VALID_REPORT = _report([_proposal()])


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"{", "not valid JSON"),
        (
            _output([_VALID_REPORT, {**_VALID_REPORT, "document_id": "other"}]),
            r"unknown=\['other'\]",
        ),
        (_output([_VALID_REPORT, _VALID_REPORT]), "duplicate report"),
        (_output([_VALID_REPORT], batch_id="batch-09"), "output names"),
        (
            _output([_report([_proposal(note="x" * (MAX_EXCERPT_CHARS + 1))])]),
            f"exceed {MAX_EXCERPT_CHARS} characters",
        ),
    ],
)
def test_batch_level_defects_fail_the_batch(raw: bytes, message: str) -> None:
    with pytest.raises(ProposalBatchError, match=message):
        _validate_outputs({"batch-01": raw})


def test_extra_batch_output_fails_the_run() -> None:
    with pytest.raises(ProposalBatchError, match="not in the run"):
        _validate_outputs(
            {"batch-01": _output([_VALID_REPORT]), "batch-02": _output([])}
        )


def test_all_batch_errors_are_reported_together() -> None:
    english = Document.from_text(
        source_case_id="EN2",
        case_group_id="e3c:v2.0.0:EN2",
        document_id="e3c:v2.0.0:en:EN2:native",
        language="en",
        translation_status=TranslationStatus.NATIVE,
        text="Fever.",
    )
    second = ProposalBatch(
        batch_id="batch-02",
        documents=(
            BatchDocument(
                document_id=english.document_id,
                document_sha256=english.document_sha256,
                source_case_id="EN2",
                annotation_language="en",
            ),
        ),
    )
    run = _run().model_copy(update={"batches": (*_run().batches, second)})
    with pytest.raises(ProposalBatchError) as caught:
        validate_proposal_run(
            run=run,
            run_sha256="6" * 64,
            batch_outputs={"batch-01": b"{", "batch-02": b"["},
            documents={_GERMAN.document_id: _GERMAN, english.document_id: english},
            hpo_index=_index(),
        )
    assert "batch-01" in str(caught.value)
    assert "batch-02" in str(caught.value)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/proposals/test_proposal_validate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phentrieve_benchmark.proposals.validate'`.

- [ ] **Step 3: Implement the validator**

```python
# src/phentrieve_benchmark/proposals/validate.py
"""Validate archived proposal batches without changing them.

Batch-level defects (unparseable output, any string longer than
MAX_EXCERPT_CHARS, wrong envelope, missing or unknown reports, hash mismatch)
raise one ProposalBatchError naming every affected batch: those outputs are
discarded and dispatched again, so an over-long excerpt is never tracked.
Proposal- and mention-level defects are listed as rejections. Accepted
proposals with the same HPO ID, assertion, experiencer, temporality, and
verbalized flag are merged (guideline R5). `verbalized` is part of the key so
that a measurement (R6) never inherits the flag of a worded mention.
"""

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.hpo_proposal import (
    MAX_EXCERPT_CHARS,
    BatchDigest,
    DocumentProposals,
    LabelWarning,
    ProposalBatch,
    ProposalBatchOutput,
    ProposalRun,
    ProposalValidationReport,
    ProposedAnnotation,
    Rejection,
    RejectionReason,
    ReportOutput,
    ResolvedMention,
    ValidatedProposal,
    ValidationSummary,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex
from phentrieve_benchmark.proposals.locate import (
    LocatedSpan,
    MentionLocationError,
    NormalizedText,
    locate_mention,
    normalize_typography,
)
from phentrieve_benchmark.provenance.digests import sha256_bytes

_StatusKey = tuple[str, str, str, str, bool]
_Located = tuple[ProposedAnnotation, list[tuple[int, LocatedSpan]]]


class ProposalBatchError(ValueError):
    """A batch output cannot be validated at all; dispatch the batch again."""


@dataclass
class _ReportLog:
    batch_id: str
    document_id: str
    rejections: list[Rejection] = field(default_factory=list)
    warnings: list[LabelWarning] = field(default_factory=list)

    def reject(
        self,
        reason: RejectionReason,
        detail: str,
        *,
        proposal_id: str | None,
        mention_index: int | None = None,
    ) -> None:
        self.rejections.append(
            Rejection(
                batch_id=self.batch_id,
                document_id=self.document_id,
                proposal_id=proposal_id,
                mention_index=mention_index,
                reason=reason,
                detail=detail,
            )
        )


def _error_detail(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(str(part) for part in first["loc"])
    return f"{location}: {first['msg']}" if location else str(first["msg"])


def _proposal_id_of(item: Any) -> str | None:
    if isinstance(item, dict):
        value = item.get("proposal_id")
        if isinstance(value, str):
            return value
    return None


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return []


def parse_batch_output(
    raw: bytes, *, run_id: str, batch: ProposalBatch
) -> ProposalBatchOutput:
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProposalBatchError(f"{batch.batch_id}: not valid JSON") from error
    too_long = [s for s in _strings(parsed) if len(s) > MAX_EXCERPT_CHARS]
    if too_long:
        raise ProposalBatchError(
            f"{batch.batch_id}: {len(too_long)} strings exceed "
            f"{MAX_EXCERPT_CHARS} characters; discard the output and dispatch "
            "the batch again"
        )
    try:
        output = ProposalBatchOutput.model_validate_json(raw, strict=True)
    except ValidationError as error:
        raise ProposalBatchError(
            f"{batch.batch_id}: invalid batch output ({_error_detail(error)})"
        ) from error
    if output.run_id != run_id or output.batch_id != batch.batch_id:
        raise ProposalBatchError(
            f"{batch.batch_id}: output names run {output.run_id!r} "
            f"and batch {output.batch_id!r}"
        )
    expected = {document.document_id: document for document in batch.documents}
    reported = [report.document_id for report in output.reports]
    if len(reported) != len(set(reported)):
        raise ProposalBatchError(f"{batch.batch_id}: duplicate report")
    missing = sorted(set(expected) - set(reported))
    unknown = sorted(set(reported) - set(expected))
    if missing or unknown:
        raise ProposalBatchError(
            f"{batch.batch_id}: reports differ from the batch: "
            f"missing={missing} unknown={unknown}"
        )
    for report in output.reports:
        if report.document_sha256 != expected[report.document_id].document_sha256:
            raise ProposalBatchError(
                f"{batch.batch_id}: hash of {report.document_id} does not match "
                "the run"
            )
    return output


def _accepted_proposal(
    item: Any, *, seen: set[str], hpo_index: HpoIndex, log: _ReportLog
) -> ProposedAnnotation | None:
    try:
        proposal = ProposedAnnotation.model_validate_json(
            json.dumps(item), strict=True
        )
    except ValidationError as error:
        log.reject(
            RejectionReason.INVALID_SCHEMA,
            _error_detail(error),
            proposal_id=_proposal_id_of(item),
        )
        return None
    if proposal.proposal_id in seen:
        log.reject(
            RejectionReason.DUPLICATE_PROPOSAL_ID,
            "proposal ID already used in this report",
            proposal_id=proposal.proposal_id,
        )
        return None
    seen.add(proposal.proposal_id)
    term = hpo_index.terms.get(proposal.hpo_id)
    if term is None:
        primary = hpo_index.alternate_to_primary.get(proposal.hpo_id)
        detail = (
            f"alternate ID of {primary}"
            if primary is not None
            else "not in the pinned HPO release"
        )
        log.reject(
            RejectionReason.UNKNOWN_HPO_ID, detail, proposal_id=proposal.proposal_id
        )
        return None
    if term.obsolete:
        log.reject(
            RejectionReason.OBSOLETE_HPO_ID,
            "obsolete in the pinned HPO release",
            proposal_id=proposal.proposal_id,
        )
        return None
    if term.label is None or term.label.casefold() != proposal.hpo_label.casefold():
        log.warnings.append(
            LabelWarning(
                batch_id=log.batch_id,
                document_id=log.document_id,
                proposal_id=proposal.proposal_id,
                hpo_id=proposal.hpo_id,
                proposed_label=proposal.hpo_label,
                pinned_label=term.label,
            )
        )
    return proposal


def _locate_all(
    proposal: ProposedAnnotation, text: NormalizedText, log: _ReportLog
) -> list[tuple[int, LocatedSpan]]:
    located: list[tuple[int, LocatedSpan]] = []
    for index, mention in enumerate(proposal.mentions):
        try:
            span = locate_mention(
                text,
                phrase=mention.phrase,
                context=mention.context,
                occurrence=mention.occurrence,
            )
        except MentionLocationError as error:
            log.reject(
                error.reason,
                error.detail,
                proposal_id=proposal.proposal_id,
                mention_index=index,
            )
            continue
        located.append((index, span))
    return located


def _merged(
    members: list[_Located],
    *,
    document: Document,
    hpo_index: HpoIndex,
    log: _ReportLog,
) -> ValidatedProposal:
    accepted: list[ResolvedMention] = []
    for proposal, located in members:
        for index, span in located:
            if any(
                span.start < mention.end and mention.start < span.end
                for mention in accepted
            ):
                log.reject(
                    RejectionReason.OVERLAPPING_MENTION,
                    "overlaps another mention of the same term and status",
                    proposal_id=proposal.proposal_id,
                    mention_index=index,
                )
                continue
            accepted.append(
                ResolvedMention(
                    source_proposal_id=proposal.proposal_id,
                    mention_index=index,
                    start=span.start,
                    end=span.end,
                    phrase=document.text[span.start : span.end],
                )
            )
    first = members[0][0]
    label = hpo_index.terms[first.hpo_id].label
    return ValidatedProposal(
        proposal_id=first.proposal_id,
        source_proposal_ids=tuple(proposal.proposal_id for proposal, _ in members),
        hpo_id=first.hpo_id,
        hpo_label=label if label is not None else first.hpo_id,
        assertion=first.assertion,
        experiencer=first.experiencer,
        temporality=first.temporality,
        verbalized=first.verbalized,
        mentions=tuple(
            sorted(accepted, key=lambda mention: (mention.start, mention.end))
        ),
        notes=tuple(proposal.note for proposal, _ in members if proposal.note),
    )


def _validate_report(
    *,
    report: ReportOutput,
    document: Document,
    hpo_index: HpoIndex,
    log: _ReportLog,
) -> tuple[DocumentProposals, int]:
    """Return the document's validated proposals and its evaluated mentions."""
    text = normalize_typography(document.text)
    seen: set[str] = set()
    groups: dict[_StatusKey, list[_Located]] = {}
    evaluated = 0
    for item in report.annotations:
        proposal = _accepted_proposal(item, seen=seen, hpo_index=hpo_index, log=log)
        if proposal is None:
            continue
        evaluated += len(proposal.mentions)
        located = _locate_all(proposal, text, log)
        if not located:
            log.reject(
                RejectionReason.NO_VALID_MENTIONS,
                "no mention could be located",
                proposal_id=proposal.proposal_id,
            )
            continue
        key: _StatusKey = (
            proposal.hpo_id,
            proposal.assertion,
            proposal.experiencer,
            proposal.temporality,
            proposal.verbalized,
        )
        groups.setdefault(key, []).append((proposal, located))
    proposals = tuple(
        _merged(members, document=document, hpo_index=hpo_index, log=log)
        for members in groups.values()
    )
    return (
        DocumentProposals(
            batch_id=log.batch_id,
            document_id=document.document_id,
            document_sha256=document.document_sha256,
            proposals=proposals,
        ),
        evaluated,
    )


def validate_proposal_run(
    *,
    run: ProposalRun,
    run_sha256: str,
    batch_outputs: Mapping[str, bytes],
    documents: Mapping[str, Document],
    hpo_index: HpoIndex,
) -> ProposalValidationReport:
    if (
        hpo_index.release != run.hpo_release
        or hpo_index.ontology_sha256 != run.ontology_sha256
    ):
        raise ValueError("HPO index does not match the run")
    batch_ids = [batch.batch_id for batch in run.batches]
    missing = [batch_id for batch_id in batch_ids if batch_id not in batch_outputs]
    if missing:
        raise ProposalBatchError(f"batch outputs missing: {missing}")
    extra = sorted(set(batch_outputs) - set(batch_ids))
    if extra:
        raise ProposalBatchError(f"batch outputs not in the run: {extra}")
    parsed: list[ProposalBatchOutput] = []
    errors: list[str] = []
    for batch in run.batches:
        try:
            parsed.append(
                parse_batch_output(
                    batch_outputs[batch.batch_id], run_id=run.run_id, batch=batch
                )
            )
        except ProposalBatchError as error:
            errors.append(str(error))
    if errors:
        raise ProposalBatchError("; ".join(errors))
    results: list[DocumentProposals] = []
    rejections: list[Rejection] = []
    warnings: list[LabelWarning] = []
    received = 0
    evaluated = 0
    for batch, output in zip(run.batches, parsed, strict=True):
        for report in output.reports:
            document = documents.get(report.document_id)
            if document is None or document.document_sha256 != report.document_sha256:
                raise ValueError(
                    f"corpus document {report.document_id} is missing or differs "
                    "from the run"
                )
            log = _ReportLog(batch_id=batch.batch_id, document_id=document.document_id)
            result, count = _validate_report(
                report=report, document=document, hpo_index=hpo_index, log=log
            )
            results.append(result)
            rejections.extend(log.rejections)
            warnings.extend(log.warnings)
            received += len(report.annotations)
            evaluated += count
    validated = [proposal for result in results for proposal in result.proposals]
    summary = ValidationSummary(
        documents=len(results),
        proposals_received=received,
        proposals_rejected=sum(1 for r in rejections if r.mention_index is None),
        validated_proposals=len(validated),
        mentions_evaluated=evaluated,
        mentions_rejected=sum(1 for r in rejections if r.mention_index is not None),
        validated_mentions=sum(len(proposal.mentions) for proposal in validated),
        rejections_by_reason=dict(
            sorted(Counter(r.reason.value for r in rejections).items())
        ),
    )
    return ProposalValidationReport(
        run_id=run.run_id,
        run_sha256=run_sha256,
        corpus_manifest_sha256=run.corpus_manifest_sha256,
        hpo_release=run.hpo_release,
        ontology_sha256=run.ontology_sha256,
        batches=tuple(
            BatchDigest(batch_id=batch_id, sha256=sha256_bytes(batch_outputs[batch_id]))
            for batch_id in batch_ids
        ),
        documents=tuple(sorted(results, key=lambda result: result.document_id)),
        rejections=tuple(rejections),
        warnings=tuple(warnings),
        summary=summary,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/proposals/test_proposal_validate.py -v`
Expected: 26 passed.

- [ ] **Step 5: Lint and type check**

Run: `uv run ruff check src/phentrieve_benchmark/proposals tests/unit/proposals && uv run mypy`
Expected: no errors. Wrap any test line ruff reports as too long; do not change behaviour.

- [ ] **Step 6: Commit**

```bash
git add src/phentrieve_benchmark/proposals/validate.py tests/unit/proposals/test_proposal_validate.py
git commit -m "feat: validate proposal batches into offsets, merges, and rejections"
```

---

### Task 5: Run planning (pilot, selection, batches, prompt rendering)

**Files:**
- Create: `src/phentrieve_benchmark/proposals/run.py`
- Test: `tests/unit/proposals/test_proposal_run_planning.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/proposals/test_proposal_run_planning.py
from collections import Counter
from fractions import Fraction
from typing import Literal

import pytest

from phentrieve_benchmark.models.annotation_corpus import (
    AnnotationCorpusEntry,
    AnnotationCorpusManifest,
)
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.proposals.run import (
    pilot_case_ids,
    plan_batches,
    render_batch_prompt,
    select_run_entries,
)
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationGroupRecord,
    AnnotationLanguage,
)
from phentrieve_benchmark.selection.metrics import LengthStratum, Rational

_SOURCES: tuple[Literal["en", "fr", "es"], ...] = ("en", "fr", "es")


def _record(
    case_id: str,
    source: Literal["en", "fr", "es"],
    language: AnnotationLanguage,
    stratum: LengthStratum,
) -> AnnotationGroupRecord:
    return AnnotationGroupRecord(
        source_case_id=case_id,
        source_language=source,
        annotation_language=language,
        document_sha256=sha256_bytes(case_id.encode()),
        length_stratum=stratum,
        total_annotation_density=Rational.from_fraction(Fraction(1)),
    )


def _groups() -> AnnotationGroupManifest:
    records = [
        _record(f"{source.upper()}{stratum.value}{index}", source, source, stratum)
        for source in _SOURCES
        for stratum in LengthStratum
        for index in range(2)
    ]
    records += [
        _record(f"ENDE{index}", "en", "de", LengthStratum.SHORT) for index in range(2)
    ]
    return AnnotationGroupManifest(
        inventory_sha256="a" * 64, records=tuple(records), aggregate_sha256="b" * 64
    )


def _entry(record: AnnotationGroupRecord) -> AnnotationCorpusEntry:
    german = record.annotation_language == "de"
    return AnnotationCorpusEntry(
        source_case_id=record.source_case_id,
        annotation_language=record.annotation_language,
        document_id=f"doc:{record.annotation_language}:{record.source_case_id}",
        document_sha256=sha256_bytes(record.source_case_id.encode()),
        review_import_sha256="c" * 64 if german else None,
        translation_review_record_sha256="d" * 64 if german else None,
    )


def _corpus(
    groups: AnnotationGroupManifest, *, german_reviewed: bool = True
) -> AnnotationCorpusManifest:
    entries = [
        _entry(record)
        for record in groups.records
        if german_reviewed or record.annotation_language != "de"
    ]
    pending = () if german_reviewed else groups.case_ids("de")
    return AnnotationCorpusManifest(
        groups_sha256=sha256_bytes(groups.canonical_bytes()),
        native_documents_sha256="e" * 64,
        documents_sha256="f" * 64,
        entries=tuple(entries),
        pending_review=pending,
    )


def test_pilot_takes_one_report_per_original_language_and_stratum() -> None:
    groups = _groups()
    case_ids = pilot_case_ids(_corpus(groups), groups)
    strata = {r.source_case_id: r for r in groups.records}
    cells = Counter(
        (strata[case_id].annotation_language, strata[case_id].length_stratum)
        for case_id in case_ids
    )
    assert len(case_ids) == 9
    assert set(cells.values()) == {1}
    assert all(language != "de" for language, _ in cells)
    assert case_ids == pilot_case_ids(_corpus(groups), groups)


def test_pilot_rejects_a_corpus_from_another_group_manifest() -> None:
    groups = _groups()
    corpus = _corpus(groups).model_copy(update={"groups_sha256": "0" * 64})
    with pytest.raises(ValueError, match="different group manifest"):
        pilot_case_ids(corpus, groups)


def test_selection_filters_languages_and_sorts_by_language_and_case() -> None:
    entries = select_run_entries(
        _corpus(_groups()), languages=("fr", "de"), case_ids=None
    )
    assert [entry.source_case_id for entry in entries][:3] == [
        "ENDE0",
        "ENDE1",
        "FRlong0",
    ]
    assert {entry.annotation_language for entry in entries} == {"de", "fr"}


def test_selection_explains_pending_german_reports() -> None:
    corpus = _corpus(_groups(), german_reviewed=False)
    with pytest.raises(ValueError, match="2 German reports pending"):
        select_run_entries(corpus, languages=("de",), case_ids=None)


def test_selection_rejects_cases_outside_the_corpus() -> None:
    with pytest.raises(ValueError, match="not in the corpus"):
        select_run_entries(_corpus(_groups()), languages=None, case_ids=("XX1",))


def test_batches_have_the_requested_size_and_numbered_ids() -> None:
    entries = select_run_entries(_corpus(_groups()), languages=("en",), case_ids=None)
    batches = plan_batches(entries, batch_size=4)
    assert [batch.batch_id for batch in batches] == ["batch-01", "batch-02"]
    assert [len(batch.documents) for batch in batches] == [4, 2]


def test_prompt_rendering_fills_every_placeholder() -> None:
    template = "Run {run_id} {batch_id} -> {output_path}\n{documents}\n{run_id}"
    rendered = render_batch_prompt(
        template,
        run_id="pilot-v1",
        batch_id="batch-01",
        output_path="out.json",
        documents="1. doc",
    )
    assert rendered == "Run pilot-v1 batch-01 -> out.json\n1. doc\npilot-v1"


def test_prompt_template_must_contain_every_placeholder() -> None:
    with pytest.raises(ValueError, match="documents"):
        render_batch_prompt(
            "{run_id} {batch_id} {output_path}",
            run_id="r",
            batch_id="b",
            output_path="o",
            documents="d",
        )
```

`"FRlong0"` sorts before `"FRmedium0"` and `"FRshort0"` (plain string order), which is why it is the third entry.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/proposals/test_proposal_run_planning.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phentrieve_benchmark.proposals.run'`.

- [ ] **Step 3: Implement the planning functions**

```python
# src/phentrieve_benchmark/proposals/run.py
"""Plan a proposal run: which corpus documents, in which batches."""

from collections.abc import Collection, Sequence
from hashlib import sha256

from phentrieve_benchmark.models.annotation_corpus import (
    AnnotationCorpusEntry,
    AnnotationCorpusManifest,
)
from phentrieve_benchmark.models.hpo_proposal import BatchDocument, ProposalBatch
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationLanguage,
)
from phentrieve_benchmark.selection.metrics import LengthStratum

PILOT_SEED = "phentrieve-e3c-proposal-pilot-v1"
PILOT_LANGUAGES: tuple[AnnotationLanguage, ...] = ("en", "fr", "es")
PROMPT_PLACEHOLDERS = ("{run_id}", "{batch_id}", "{output_path}", "{documents}")


def _seeded(case_id: str) -> bytes:
    return sha256(f"{PILOT_SEED}\0{case_id}".encode()).digest()


def pilot_case_ids(
    corpus: AnnotationCorpusManifest, groups: AnnotationGroupManifest
) -> tuple[str, ...]:
    """One report per original language and length stratum, by seeded hash."""
    if corpus.groups_sha256 != sha256_bytes(groups.canonical_bytes()):
        raise ValueError("corpus was built from a different group manifest")
    strata = {record.source_case_id: record.length_stratum for record in groups.records}
    chosen: list[str] = []
    for language in PILOT_LANGUAGES:
        for stratum in LengthStratum:
            candidates = [
                entry.source_case_id
                for entry in corpus.entries
                if entry.annotation_language == language
                and strata[entry.source_case_id] is stratum
            ]
            if candidates:
                chosen.append(min(candidates, key=_seeded))
    return tuple(sorted(chosen))


def select_run_entries(
    corpus: AnnotationCorpusManifest,
    *,
    languages: Collection[AnnotationLanguage] | None,
    case_ids: Collection[str] | None,
) -> tuple[AnnotationCorpusEntry, ...]:
    entries = [
        entry
        for entry in corpus.entries
        if (languages is None or entry.annotation_language in languages)
        and (case_ids is None or entry.source_case_id in case_ids)
    ]
    if case_ids is not None:
        missing = set(case_ids) - {entry.source_case_id for entry in entries}
        if missing:
            raise ValueError(f"cases not in the corpus: {sorted(missing)}")
    if not entries:
        message = "no corpus document matches the selection"
        if (languages is None or "de" in languages) and corpus.pending_review:
            message += (
                f"; {len(corpus.pending_review)} German reports pending "
                "translation review"
            )
        raise ValueError(message)
    return tuple(
        sorted(
            entries,
            key=lambda entry: (entry.annotation_language, entry.source_case_id),
        )
    )


def plan_batches(
    entries: Sequence[AnnotationCorpusEntry], *, batch_size: int
) -> tuple[ProposalBatch, ...]:
    if batch_size < 1:
        raise ValueError("batch size must be positive")
    return tuple(
        ProposalBatch(
            batch_id=f"batch-{number:02d}",
            documents=tuple(
                BatchDocument(
                    document_id=entry.document_id,
                    document_sha256=entry.document_sha256,
                    source_case_id=entry.source_case_id,
                    annotation_language=entry.annotation_language,
                )
                for entry in entries[start : start + batch_size]
            ),
        )
        for number, start in enumerate(range(0, len(entries), batch_size), start=1)
    )


def render_batch_prompt(
    template: str,
    *,
    run_id: str,
    batch_id: str,
    output_path: str,
    documents: str,
) -> str:
    """Fill the batch placeholders; the template may contain literal JSON."""
    missing = [p for p in PROMPT_PLACEHOLDERS if p not in template]
    if missing:
        raise ValueError(f"prompt template lacks placeholders: {missing}")
    return (
        template.replace("{run_id}", run_id)
        .replace("{batch_id}", batch_id)
        .replace("{output_path}", output_path)
        .replace("{documents}", documents)
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/proposals/test_proposal_run_planning.py -v`
Expected: 8 passed.

- [ ] **Step 5: Lint and type check**

Run: `uv run ruff check src/phentrieve_benchmark/proposals tests/unit/proposals && uv run mypy`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/phentrieve_benchmark/proposals/run.py tests/unit/proposals/test_proposal_run_planning.py
git commit -m "feat: plan proposal runs with a stratified pilot and batches"
```

---

### Task 6: Run directories on disk, with a synthetic German end-to-end test

**Files:**
- Create: `src/phentrieve_benchmark/pipeline/proposals.py`
- Modify: `.gitattributes`
- Test: `tests/integration/test_proposal_run.py`

- [ ] **Step 1: Write the failing integration tests**

```python
# tests/integration/test_proposal_run.py
import json
from collections.abc import Collection
from datetime import date
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation_corpus import (
    AnnotationCorpusEntry,
    AnnotationCorpusManifest,
)
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.hpo_proposal import (
    PROPOSAL_PROVENANCE,
    ProposalRun,
    ProposalValidationReport,
)
from phentrieve_benchmark.ontology.hpo import load_hpo_index
from phentrieve_benchmark.pipeline.proposals import (
    GuidelineVersion,
    prepare_proposal_run,
    validate_run_directory,
)
from phentrieve_benchmark.provenance.canonical import canonical_jsonl_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationGroupRecord,
    AnnotationLanguage,
)
from phentrieve_benchmark.selection.metrics import LengthStratum, Rational
from tests.fixtures.hpo import proposal_hpo_obo

_TEMPLATE = b"Run {run_id}, batch {batch_id}.\nWrite {output_path}.\n\n{documents}\n"
_ENGLISH = Document.from_text(
    source_case_id="EN1",
    case_group_id="e3c:v2.0.0:EN1",
    document_id="e3c:v2.0.0:en:EN1:native",
    language="en",
    translation_status=TranslationStatus.NATIVE,
    text="Fever and cough.",
)
_GERMAN = Document.from_text(
    source_case_id="EN2",
    case_group_id="e3c:v2.0.0:EN2",
    document_id="e3c:v2.0.0:de:EN2:translated",
    language="de",
    translation_status=TranslationStatus.TRANSLATED,
    text="Kein Fieber, aber \u201eHusten\u201c seit\u00a0zwei Tagen.",
)


def _groups() -> AnnotationGroupManifest:
    def record(
        case_id: str, language: AnnotationLanguage
    ) -> AnnotationGroupRecord:
        return AnnotationGroupRecord(
            source_case_id=case_id,
            source_language="en",
            annotation_language=language,
            document_sha256=sha256_bytes(case_id.encode()),
            length_stratum=LengthStratum.SHORT,
            total_annotation_density=Rational.from_fraction(Fraction(1)),
        )

    return AnnotationGroupManifest(
        inventory_sha256="a" * 64,
        records=(record("EN1", "en"), record("EN2", "de")),
        aggregate_sha256="b" * 64,
    )


def _corpus(store: ArtifactStore, *, german_reviewed: bool = True) -> str:
    documents = (_ENGLISH, _GERMAN) if german_reviewed else (_ENGLISH,)
    documents_sha256 = store.put_bytes(
        canonical_jsonl_bytes(
            [document.model_dump(mode="json") for document in documents],
            identity_key="document_id",
        )
    )
    entries = [
        AnnotationCorpusEntry(
            source_case_id="EN1",
            annotation_language="en",
            document_id=_ENGLISH.document_id,
            document_sha256=_ENGLISH.document_sha256,
        )
    ]
    if german_reviewed:
        entries.append(
            AnnotationCorpusEntry(
                source_case_id="EN2",
                annotation_language="de",
                document_id=_GERMAN.document_id,
                document_sha256=_GERMAN.document_sha256,
                review_import_sha256="e" * 64,
                translation_review_record_sha256="f" * 64,
            )
        )
    manifest = AnnotationCorpusManifest(
        groups_sha256=sha256_bytes(_groups().canonical_bytes()),
        native_documents_sha256="d" * 64,
        documents_sha256=documents_sha256,
        entries=tuple(entries),
        pending_review=() if german_reviewed else ("EN2",),
    )
    return store.put_bytes(manifest.canonical_bytes())


def _prepare(
    tmp_path: Path,
    store: ArtifactStore,
    corpus_sha256: str,
    *,
    languages: Collection[AnnotationLanguage] | None = None,
) -> ProposalRun:
    return prepare_proposal_run(
        store=store,
        repository_root=tmp_path,
        corpus_manifest_sha256=corpus_sha256,
        groups=_groups(),
        run_id="synthetic-v1",
        model_id="claude-sonnet-5-5",
        run_date=date(2026, 10, 7),
        prompt_template=_TEMPLATE,
        guideline=GuidelineVersion(
            path="docs/annotation-guidelines/hpo-span-annotation.md",
            commit="1" * 40,
            sha256="2" * 64,
        ),
        hpo_release="v2026-06-23",
        ontology_sha256=sha256(proposal_hpo_obo()).hexdigest(),
        languages=languages,
        pilot=False,
        batch_size=1,
        run_directory=tmp_path / "datasets/e3c-de/proposals/synthetic-v1",
        input_directory=tmp_path / ".artifacts/proposals/synthetic-v1",
    )


def _annotation(
    proposal_id: str, hpo_id: str, label: str, assertion: str, phrase: str, context: str
) -> dict[str, Any]:
    return {
        "proposal_id": proposal_id,
        "hpo_id": hpo_id,
        "hpo_label": label,
        "assertion": assertion,
        "experiencer": "patient",
        "temporality": "current",
        "verbalized": True,
        "mentions": [{"phrase": phrase, "context": context}],
        "note": None,
    }


def _batch_output(
    batch_id: str, document: Document, annotations: list[dict[str, Any]]
) -> bytes:
    payload = {
        "schema_version": "e3c-hpo-proposal-batch/v1",
        "provenance": PROPOSAL_PROVENANCE,
        "run_id": "synthetic-v1",
        "batch_id": batch_id,
        "reports": [
            {
                "document_id": document.document_id,
                "document_sha256": document.document_sha256,
                "annotations": annotations,
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode()


def test_german_report_goes_end_to_end_from_corpus_to_validation(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    run = _prepare(tmp_path, store, _corpus(store))
    run_directory = tmp_path / "datasets/e3c-de/proposals/synthetic-v1"
    assert [batch.documents[0].document_id for batch in run.batches] == [
        _GERMAN.document_id,
        _ENGLISH.document_id,
    ]
    batch_input = tmp_path / ".artifacts/proposals/synthetic-v1/batch-01"
    assert (batch_input / "EN2.txt").read_bytes() == _GERMAN.text.encode()
    prompt = (run_directory / "batch-01.prompt.md").read_text(encoding="utf-8")
    assert "Write datasets/e3c-de/proposals/synthetic-v1/batch-01.json." in prompt
    assert ".artifacts/proposals/synthetic-v1/batch-01/EN2.txt" in prompt
    assert _GERMAN.document_sha256 in prompt
    assert _GERMAN.text not in prompt
    assert (run_directory / "prompt.md").read_bytes() == _TEMPLATE
    assert (run_directory / "run.json").read_bytes() == run.canonical_bytes()
    assert run.pending_review == ()

    outputs = {
        "batch-01": _batch_output(
            "batch-01",
            _GERMAN,
            [
                _annotation(
                    "p001", "HP:0001945", "Fever", "absent", "Fieber", "Kein Fieber, aber"
                ),
                _annotation(
                    "p002", "HP:0012735", "Cough", "present", "Husten",
                    '"Husten" seit zwei Tagen',
                ),
            ],
        ),
        "batch-02": _batch_output(
            "batch-02",
            _ENGLISH,
            [_annotation("p001", "HP:0001945", "Fever", "present", "Fever", "Fever and")],
        ),
    }
    for batch_id, raw in outputs.items():
        (run_directory / f"{batch_id}.json").write_bytes(raw)

    body = proposal_hpo_obo()
    index = load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )
    report, digest = validate_run_directory(
        run_directory=run_directory, store=store, hpo_index=index
    )

    validation_bytes = (run_directory / "validation.json").read_bytes()
    assert digest == sha256_bytes(validation_bytes)
    assert (
        ProposalValidationReport.model_validate_json(validation_bytes, strict=True)
        == report
    )
    assert report.run_sha256 == sha256_bytes(run.canonical_bytes())
    assert report.rejections == ()
    german = next(d for d in report.documents if d.document_id == _GERMAN.document_id)
    cough = next(p for p in german.proposals if p.hpo_id == "HP:0012735")
    (mention,) = cough.mentions
    assert _GERMAN.text[mention.start : mention.end] == "Husten" == mention.phrase
    for batch_id, raw in outputs.items():
        assert (run_directory / f"{batch_id}.json").read_bytes() == raw


def test_existing_run_is_not_overwritten(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    corpus_sha256 = _corpus(store)
    _prepare(tmp_path, store, corpus_sha256)
    with pytest.raises(FileExistsError, match="synthetic-v1"):
        _prepare(tmp_path, store, corpus_sha256)


def test_german_run_stops_while_reviews_are_pending(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    corpus_sha256 = _corpus(store, german_reviewed=False)
    with pytest.raises(ValueError, match="1 German reports pending"):
        _prepare(tmp_path, store, corpus_sha256, languages=("de",))
    assert not (tmp_path / "datasets/e3c-de/proposals/synthetic-v1").exists()


def test_run_records_german_reports_left_out_as_pending(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    corpus_sha256 = _corpus(store, german_reviewed=False)
    run = _prepare(tmp_path, store, corpus_sha256, languages=("en", "de"))
    assert [batch.documents[0].source_case_id for batch in run.batches] == ["EN1"]
    assert run.pending_review == ("EN2",)


def test_validation_rejects_a_changed_prompt(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    _prepare(tmp_path, store, _corpus(store))
    run_directory = tmp_path / "datasets/e3c-de/proposals/synthetic-v1"
    (run_directory / "prompt.md").write_bytes(b"edited")
    body = proposal_hpo_obo()
    index = load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )
    with pytest.raises(ValueError, match=r"prompt\.md"):
        validate_run_directory(
            run_directory=run_directory, store=store, hpo_index=index
        )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/integration/test_proposal_run.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phentrieve_benchmark.pipeline.proposals'`.

- [ ] **Step 3: Implement the pipeline module**

```python
# src/phentrieve_benchmark/pipeline/proposals.py
"""Prepare and validate proposal runs on disk.

The run directory datasets/e3c-de/proposals/<run_id>/ is tracked in Git:
prompt.md (the committed template), run.json, batch-NN.prompt.md (the exact
prompt per batch; paths, IDs, and hashes, no report text), batch-NN.json (the
unchanged subagent output), and validation.json. Full texts for the
subagents are written only below the local artifact root.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation_corpus import AnnotationCorpusManifest
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.hpo_proposal import (
    ProposalBatch,
    ProposalRun,
    ProposalValidationReport,
)
from phentrieve_benchmark.ontology.hpo import HpoIndex
from phentrieve_benchmark.proposals.run import (
    pilot_case_ids,
    plan_batches,
    render_batch_prompt,
    select_run_entries,
)
from phentrieve_benchmark.proposals.validate import validate_proposal_run
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationLanguage,
)

PROPOSALS_DIRECTORY = Path("e3c-de/proposals")
PROMPT_TEMPLATE = Path("configs/prompts/hpo-span-proposal-v1.md")
GUIDELINE = Path("docs/annotation-guidelines/hpo-span-annotation.md")


@dataclass(frozen=True)
class GuidelineVersion:
    path: str
    commit: str
    sha256: str


def read_corpus(
    store: ArtifactStore, corpus_manifest_sha256: str
) -> tuple[AnnotationCorpusManifest, dict[str, Document]]:
    manifest = AnnotationCorpusManifest.model_validate_json(
        store.read_bytes(corpus_manifest_sha256), strict=True
    )
    documents: dict[str, Document] = {}
    for line in store.read_bytes(manifest.documents_sha256).splitlines():
        if line:
            document = Document.model_validate_json(line, strict=True)
            documents[document.document_id] = document
    return manifest, documents


def _display(path: Path, repository_root: Path) -> str:
    try:
        return path.resolve().relative_to(repository_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _write_batch_inputs(
    *,
    batch: ProposalBatch,
    run_id: str,
    template: str,
    documents: dict[str, Document],
    repository_root: Path,
    run_directory: Path,
    input_directory: Path,
) -> None:
    """Write the texts (local only) and the rendered prompt (tracked)."""
    batch_directory = input_directory / batch.batch_id
    batch_directory.mkdir(parents=True, exist_ok=True)
    listing: list[str] = []
    for number, entry in enumerate(batch.documents, start=1):
        text_path = batch_directory / f"{entry.source_case_id}.txt"
        text_path.write_bytes(documents[entry.document_id].text.encode("utf-8"))
        listing.append(
            f"{number}. document_id `{entry.document_id}`, "
            f"document_sha256 `{entry.document_sha256}`, "
            f"language `{entry.annotation_language}`, "
            f"text file `{_display(text_path, repository_root)}`"
        )
    prompt = render_batch_prompt(
        template,
        run_id=run_id,
        batch_id=batch.batch_id,
        output_path=_display(
            run_directory / f"{batch.batch_id}.json", repository_root
        ),
        documents="\n".join(listing),
    )
    (run_directory / f"{batch.batch_id}.prompt.md").write_bytes(
        prompt.encode("utf-8")
    )


def prepare_proposal_run(
    *,
    store: ArtifactStore,
    repository_root: Path,
    corpus_manifest_sha256: str,
    groups: AnnotationGroupManifest,
    run_id: str,
    model_id: str,
    run_date: date,
    prompt_template: bytes,
    guideline: GuidelineVersion,
    hpo_release: str,
    ontology_sha256: str,
    languages: Collection[AnnotationLanguage] | None,
    pilot: bool,
    batch_size: int,
    run_directory: Path,
    input_directory: Path,
) -> ProposalRun:
    """Write run.json, prompt.md, the batch prompts, and the local texts.

    `prompt_template` and `guideline.sha256` must come from the committed
    blobs, not the working tree (line endings differ under core.autocrlf).
    """
    if run_directory.exists():
        raise FileExistsError(f"proposal run {run_id} already exists")
    corpus, documents = read_corpus(store, corpus_manifest_sha256)
    case_ids = pilot_case_ids(corpus, groups) if pilot else None
    entries = select_run_entries(corpus, languages=languages, case_ids=case_ids)
    german_selected = not pilot and (languages is None or "de" in languages)
    run = ProposalRun(
        run_id=run_id,
        run_date=run_date,
        model_id=model_id,
        corpus_manifest_sha256=corpus_manifest_sha256,
        documents_sha256=corpus.documents_sha256,
        hpo_release=hpo_release,
        ontology_sha256=ontology_sha256,
        prompt_sha256=sha256_bytes(prompt_template),
        guideline_path=guideline.path,
        guideline_commit=guideline.commit,
        guideline_sha256=guideline.sha256,
        batches=plan_batches(entries, batch_size=batch_size),
        pending_review=corpus.pending_review if german_selected else (),
    )
    template = prompt_template.decode("utf-8")
    run_directory.mkdir(parents=True)
    (run_directory / "prompt.md").write_bytes(prompt_template)
    (run_directory / "run.json").write_bytes(run.canonical_bytes())
    for batch in run.batches:
        _write_batch_inputs(
            batch=batch,
            run_id=run_id,
            template=template,
            documents=documents,
            repository_root=repository_root,
            run_directory=run_directory,
            input_directory=input_directory,
        )
    return run


def validate_run_directory(
    *, run_directory: Path, store: ArtifactStore, hpo_index: HpoIndex
) -> tuple[ProposalValidationReport, str]:
    """Validate a run's batch outputs and write validation.json.

    Batch files are only read. Returns the report and the SHA-256 of the
    canonical validation.json bytes.
    """
    run_bytes = (run_directory / "run.json").read_bytes()
    run = ProposalRun.model_validate_json(run_bytes, strict=True)
    if sha256_bytes((run_directory / "prompt.md").read_bytes()) != run.prompt_sha256:
        raise ValueError("prompt.md differs from the prompt recorded in run.json")
    corpus, documents = read_corpus(store, run.corpus_manifest_sha256)
    if corpus.documents_sha256 != run.documents_sha256:
        raise ValueError("corpus documents differ from the run")
    outputs = {
        path.stem: path.read_bytes()
        for path in sorted(run_directory.glob("batch-*.json"))
    }
    report = validate_proposal_run(
        run=run,
        run_sha256=sha256_bytes(run_bytes),
        batch_outputs=outputs,
        documents=documents,
        hpo_index=hpo_index,
    )
    payload = report.canonical_bytes()
    (run_directory / "validation.json").write_bytes(payload)
    return report, sha256_bytes(payload)
```

- [ ] **Step 4: Keep run files byte-exact in Git**

Append to `.gitattributes`:

```
/datasets/e3c-de/proposals/*/** -text
```

(Run files are bound by SHA-256 in `run.json` and `validation.json`; line-ending conversion would break those bindings. The pattern covers run directories only, not the runbook README.)

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/test_proposal_run.py -v`
Expected: 5 passed.

- [ ] **Step 6: Lint, types, full suite**

Run: `uv run ruff check . && uv run mypy && uv run pytest -q`
Expected: all clean and passing.

- [ ] **Step 7: Commit**

```bash
git add src/phentrieve_benchmark/pipeline/proposals.py tests/integration/test_proposal_run.py .gitattributes
git commit -m "feat: prepare and validate proposal run directories"
```

---

### Task 7: Prompt template v1

**Files:**
- Create: `configs/prompts/hpo-span-proposal-v1.md`
- Test: `tests/contracts/test_proposal_prompt.py`

- [ ] **Step 1: Write the failing contract test**

```python
# tests/contracts/test_proposal_prompt.py
from pathlib import Path

from phentrieve_benchmark.models.hpo_proposal import (
    MAX_EXCERPT_CHARS,
    PROPOSAL_PROVENANCE,
)
from phentrieve_benchmark.pipeline.proposals import GUIDELINE, PROMPT_TEMPLATE
from phentrieve_benchmark.proposals.run import render_batch_prompt

ROOT = Path(__file__).parents[2]


def test_prompt_template_renders_and_names_its_inputs() -> None:
    template = (ROOT / PROMPT_TEMPLATE).read_text(encoding="utf-8")
    rendered = render_batch_prompt(
        template,
        run_id="pilot-v1",
        batch_id="batch-01",
        output_path="datasets/e3c-de/proposals/pilot-v1/batch-01.json",
        documents="1. document",
    )
    assert "{" + "run_id}" not in rendered
    assert GUIDELINE.as_posix() in rendered
    assert PROPOSAL_PROVENANCE in rendered
    assert "proposals hpo-lookup" in rendered
    assert "e3c-hpo-proposal-batch/v1" in rendered
    assert "120 characters" in rendered
    assert f"{MAX_EXCERPT_CHARS} characters" in rendered
    assert "relative to the repository root" in rendered
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/contracts/test_proposal_prompt.py -v`
Expected: FAIL with `FileNotFoundError` for `configs/prompts/hpo-span-proposal-v1.md`.

- [ ] **Step 3: Write the prompt template**

Create `configs/prompts/hpo-span-proposal-v1.md` with exactly this content:

````markdown
# HPO span proposals for E3C reports (prompt v1)

You propose HPO annotations for clinical case reports. Your output is
machine generated, not review data, and not gold: a physician reviews every
proposal later in an annotation editor.

## Read first

1. Read the annotation guideline
   `docs/annotation-guidelines/hpo-span-annotation.md` completely. Rules
   R0-R6 decide what you annotate, which term you choose, where a span starts
   and ends, and which status you record. R7 does not concern you.
2. Then read each report text listed under "This batch" below. Read every
   text with Bash, for example `cat "<text file>"`; the Read tool truncates
   long lines.

All paths in this prompt are relative to the repository root, which is your
working directory. Where a tool needs an absolute path (for example to write
the output file), prepend the repository root.

Use nothing else. Do not open other files under `datasets/`, earlier
proposal runs, E3C annotations, UMLS mappings, or the Phase 0 feasibility
files, and do not search the web. Proposals must come from the text alone.

## Finding HPO terms

Every `hpo_id` must be an active term of HPO release v2026-06-23. Look terms
up with

    uv run phentrieve-benchmark proposals hpo-lookup "<english term>" ["<another term>" ...]

The lookup searches English labels and synonyms, so translate the finding
into English medical wording first. Pass several queries in one call.
`hpo-lookup HP:0001945` shows the label of an ID. Copy `hpo_label` from the
lookup output. Never invent an ID; if no term fits, do not annotate the
finding. Choose the most specific term the text supports (R1).

## What to propose

Per report, list every phenotypic finding the guideline asks for (R0),
whatever its status: negated, uncertain, historical, family members, and
other persons included.

- One proposal per HPO term and status. The status is the combination of
  `assertion`, `experiencer`, `temporality`, and `verbalized`. Put every
  occurrence with the same status into the same proposal as further mentions
  (R5). An occurrence with a different status is a separate proposal.
- `assertion`: `present`, `absent`, or `uncertain` (R3).
- `experiencer`: `patient`, `family_member`, or `other` (R3).
- `temporality`: `current` or `historical` (R3).
- `verbalized`: `false` only for a pathological measurement the text does
  not interpret (R6); otherwise `true`.
- `note`: `null`, or one short English sentence when a choice is not
  obvious.

## How to give a mention

A mention is located by two strings copied verbatim from the text:

- `phrase`: the span by R2 and R4, the shortest contiguous phrase that
  expresses the term, without negation or hedging cues. When several terms
  share wording (R4), each of them gets the same whole construction as its
  phrase.
- `context`: a short excerpt of the text, at most 120 characters, that
  contains the phrase and occurs exactly once in the whole text. A clause
  around the phrase is usually enough; lengthen it only to make it unique.

Copy both exactly, including case, accents, and punctuation. Quotation
marks, dashes, and runs of spaces may differ; nothing else may.

If the phrase occurs more than once inside its context, add
`"occurrence": n`. Matches are counted whole words first, then matches inside
longer words: for "ache" in "headache and ache", the whole word "ache" is
occurrence 1 and the "ache" inside "headache" is occurrence 2. Prefer a
context in which the phrase occurs only once.

Mentions of one proposal must not overlap.

No string anywhere in your output (phrase, context, note) may be longer than
300 characters. The texts are licensed for non-commercial use and your
output is published, so it must contain short excerpts only. A file with a
longer string is discarded as a whole.

## Output

Write exactly one file, `{output_path}`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "{run_id}",
  "batch_id": "{batch_id}",
  "reports": [
    {
      "document_id": "<document_id from the list below>",
      "document_sha256": "<document_sha256 from the list below>",
      "annotations": [
        {
          "proposal_id": "p001",
          "hpo_id": "HP:0001945",
          "hpo_label": "Fever",
          "assertion": "present",
          "experiencer": "patient",
          "temporality": "current",
          "verbalized": true,
          "mentions": [
            {"phrase": "Fieber", "context": "mit hohem Fieber einher"}
          ],
          "note": null
        }
      ]
    }
  ]
}
```

- One entry in `reports` per document below, in the listed order, with its
  `document_id` and `document_sha256` copied exactly. A report without
  findings has `"annotations": []`.
- `proposal_id` is `p001`, `p002`, ... within each report.
- Write no other file and change no file. When done, reply with one line
  per report (document ID and number of proposals), then list every file
  you read and every command you ran.

## This batch

Run `{run_id}`, batch `{batch_id}`.

{documents}
````

- [ ] **Step 4: Run the contract test**

Run: `uv run pytest tests/contracts/test_proposal_prompt.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add configs/prompts/hpo-span-proposal-v1.md tests/contracts/test_proposal_prompt.py
git commit -m "feat: add versioned HPO span proposal prompt v1"
```

---

### Task 8: CLI commands `proposals prepare-run`, `validate`, `hpo-lookup`

**Files:**
- Modify: `src/phentrieve_benchmark/cli.py`
- Modify: `tests/unit/test_cli_pipeline.py:77-88`
- Test: `tests/unit/test_cli_proposals.py`

- [ ] **Step 1: Write the failing CLI tests**

```python
# tests/unit/test_cli_proposals.py
import subprocess
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from phentrieve_benchmark import cli
from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.hpo_proposal import (
    BatchDocument,
    ProposalBatch,
    ProposalRun,
    ProposalValidationReport,
    ValidationSummary,
)
from phentrieve_benchmark.proposals.validate import ProposalBatchError
from phentrieve_benchmark.selection.groups import AnnotationGroupManifest
from tests.fixtures.hpo import proposal_hpo_obo


def _run() -> ProposalRun:
    return ProposalRun(
        run_id="full-v1",
        run_date=date(2026, 10, 7),
        model_id="claude-sonnet-5-5",
        corpus_manifest_sha256="1" * 64,
        documents_sha256="2" * 64,
        hpo_release="v2026-06-23",
        ontology_sha256="3" * 64,
        prompt_sha256="4" * 64,
        guideline_path="docs/annotation-guidelines/hpo-span-annotation.md",
        guideline_commit="5" * 40,
        guideline_sha256="6" * 64,
        batches=(
            ProposalBatch(
                batch_id="batch-01",
                documents=(
                    BatchDocument(
                        document_id="d1",
                        document_sha256="7" * 64,
                        source_case_id="EN1",
                        annotation_language="en",
                    ),
                ),
            ),
        ),
    )


def _message(output: str) -> str:
    return " ".join(output.replace("\u2502", " ").split())


def test_prepare_run_rejects_pilot_with_languages() -> None:
    invocation = CliRunner().invoke(
        cli.app,
        [
            "proposals", "prepare-run", "pilot-v1",
            "--corpus", "a" * 64,
            "--model-id", "claude-sonnet-5-5",
            "--pilot", "--language", "en",
        ],
    )
    assert invocation.exit_code == 2
    assert "selects its own reports" in _message(invocation.stderr)


def test_prepare_run_delegates_with_pinned_inputs(
    tmp_path: Path, monkeypatch: Any
) -> None:
    dataset_root = tmp_path / "datasets"
    groups_path = dataset_root / cli._E3C_GROUPS
    groups_path.parent.mkdir(parents=True)
    groups_path.write_bytes(
        AnnotationGroupManifest(
            inventory_sha256="e" * 64, records=(), aggregate_sha256="f" * 64
        ).canonical_bytes()
    )
    blobs = {
        "docs/annotation-guidelines/hpo-span-annotation.md": b"# guideline\n",
        "configs/prompts/hpo-span-proposal-v1.md": b"template",
    }
    context = type(
        "Context",
        (),
        {
            "repository_root": tmp_path,
            "dataset_root": dataset_root,
            "artifact_root": tmp_path / "artifacts",
            "store": object(),
            "clock": lambda self: datetime(2026, 10, 7, 8, 0, tzinfo=UTC),
        },
    )()
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: context)
    monkeypatch.setattr(
        cli, "_committed_blob", lambda root, path: ("c" * 40, blobs[path.as_posix()])
    )
    monkeypatch.setattr(
        cli,
        "_pinned_hpo_sha256",
        lambda *_: (type("Recipe", (), {"release": "v2026-06-23"})(), "d" * 64),
    )
    calls: list[dict[str, Any]] = []

    def fake_prepare(**kwargs: Any) -> ProposalRun:
        calls.append(kwargs)
        return _run()

    monkeypatch.setattr(cli, "prepare_proposal_run", fake_prepare)

    invocation = CliRunner().invoke(
        cli.app,
        [
            "proposals", "prepare-run", "full-v1",
            "--corpus", "a" * 64,
            "--model-id", "claude-sonnet-5-5",
            "--language", "en", "--language", "fr",
        ],
    )

    assert invocation.exit_code == 0, invocation.exception
    (call,) = calls
    assert call["languages"] == ("en", "fr")
    assert call["pilot"] is False
    assert call["batch_size"] == 10
    assert call["run_date"] == date(2026, 10, 7)
    assert call["guideline"].commit == "c" * 40
    assert call["guideline"].sha256 == sha256(b"# guideline\n").hexdigest()
    assert call["ontology_sha256"] == "d" * 64
    assert call["prompt_template"] == b"template"
    assert call["run_directory"] == dataset_root / "e3c-de/proposals/full-v1"
    assert call["input_directory"] == tmp_path / "artifacts/proposals/full-v1"
    assert invocation.stdout.startswith(
        "run_id=full-v1 documents=1 batches=1 pending_review=0 "
    )


def _git(root: Path, *arguments: str) -> None:
    identity = ["-c", "user.name=test", "-c", "user.email=test@example.org"]
    subprocess.run(
        ["git", *identity, *arguments],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_committed_blob_returns_the_commit_and_committed_bytes(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "prompt.md").write_bytes(b"line one\nline two\n")
    _git(tmp_path, "add", "prompt.md")
    _git(tmp_path, "commit", "-q", "-m", "add prompt")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert cli._committed_blob(tmp_path, Path("prompt.md")) == (
        head,
        b"line one\nline two\n",
    )


def test_committed_blob_rejects_uncommitted_changes(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "prompt.md").write_bytes(b"one\n")
    _git(tmp_path, "add", "prompt.md")
    _git(tmp_path, "commit", "-q", "-m", "add prompt")
    (tmp_path / "prompt.md").write_bytes(b"two\n")
    with pytest.raises(typer.BadParameter, match="uncommitted changes"):
        cli._committed_blob(tmp_path, Path("prompt.md"))
    with pytest.raises(typer.BadParameter, match="not committed"):
        cli._committed_blob(tmp_path, Path("missing.md"))


def test_validate_reports_batch_errors_and_exits_nonzero(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(cli, "_pinned_hpo_index", lambda *_: object())

    def fail(**_: Any) -> None:
        raise ProposalBatchError("batch-02: reports differ from the batch")

    monkeypatch.setattr(cli, "validate_run_directory", fail)
    invocation = CliRunner().invoke(
        cli.app,
        ["proposals", "validate", "pilot-v1", "--artifact-root", str(tmp_path)],
    )
    assert invocation.exit_code == 1
    assert "batch-02" in invocation.stderr


def test_validate_reports_other_errors_without_a_traceback(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(cli, "_pinned_hpo_index", lambda *_: object())

    def fail(**_: Any) -> None:
        raise ValueError("prompt.md differs from the prompt recorded in run.json")

    monkeypatch.setattr(cli, "validate_run_directory", fail)
    invocation = CliRunner().invoke(
        cli.app,
        ["proposals", "validate", "pilot-v1", "--artifact-root", str(tmp_path)],
    )
    assert invocation.exit_code == 1
    assert invocation.stderr.startswith("error=prompt.md differs")


def test_validate_prints_the_summary(tmp_path: Path, monkeypatch: Any) -> None:
    report = ProposalValidationReport(
        run_id="pilot-v1",
        run_sha256="1" * 64,
        corpus_manifest_sha256="2" * 64,
        hpo_release="v2026-06-23",
        ontology_sha256="3" * 64,
        batches=(),
        documents=(),
        rejections=(),
        warnings=(),
        summary=ValidationSummary(
            documents=9,
            proposals_received=120,
            proposals_rejected=4,
            validated_proposals=110,
            mentions_evaluated=150,
            mentions_rejected=6,
            validated_mentions=144,
            rejections_by_reason={},
        ),
    )
    monkeypatch.setattr(cli, "_pinned_hpo_index", lambda *_: object())
    monkeypatch.setattr(
        cli, "validate_run_directory", lambda **_: (report, "f" * 64)
    )
    invocation = CliRunner().invoke(
        cli.app,
        ["proposals", "validate", "pilot-v1", "--artifact-root", str(tmp_path)],
    )
    assert invocation.exit_code == 0, invocation.exception
    assert invocation.stdout == (
        f"validation_sha256={'f' * 64} documents=9 proposals=120 "
        "rejected_proposals=4 validated_proposals=110 mentions=150 "
        "rejected_mentions=6 warnings=0\n"
    )


def test_hpo_lookup_prints_matches_per_query(
    tmp_path: Path, monkeypatch: Any
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    digest = store.put_bytes(proposal_hpo_obo())
    monkeypatch.setattr(cli, "_pinned_hpo_sha256", lambda *_: (object(), digest))
    invocation = CliRunner().invoke(
        cli.app,
        [
            "proposals", "hpo-lookup", "muscle pain", "HP:0009999", "nothing",
            "--artifact-root", str(tmp_path),
        ],
    )
    assert invocation.exit_code == 0, invocation.exception
    assert invocation.stdout == (
        "# muscle pain\n"
        "HP:0003326\tMyalgia\tsynonym: Muscle pain\n"
        "# HP:0009999\n"
        "HP:0009999\tObsolete fever variant\tobsolete\n"
        "# nothing\n"
        "(no match)\n"
    )
```

In `tests/unit/test_cli_pipeline.py`, inside `test_pipeline_command_groups_are_exposed`, add `"proposals",` to the tuple after `"map-hpo",`.

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/unit/test_cli_proposals.py -v`
Expected: FAIL. The first test exits with code 2 because there is no `proposals` command; the others fail on `AttributeError` for `_pinned_hpo_sha256`/`_pinned_hpo_index`.

- [ ] **Step 3: Add the commands**

In `src/phentrieve_benchmark/cli.py`:

1. Extend the `typing` import to `from typing import Annotated, Literal, cast`.
2. Add imports (merge into existing import statements where the module is already imported):

```python
from phentrieve_benchmark.ontology.hpo import (
    HpoIndex,
    HpoSourceRecipe,
    load_hpo_index,
    load_hpo_source_recipe,
)
from phentrieve_benchmark.ontology.hpo_lookup import read_lookup_entries, search_hpo
from phentrieve_benchmark.pipeline.map_hpo import load_or_acquire_hpo, map_hpo_e3c
from phentrieve_benchmark.pipeline.proposals import (
    GUIDELINE,
    PROMPT_TEMPLATE,
    PROPOSALS_DIRECTORY,
    GuidelineVersion,
    prepare_proposal_run,
    validate_run_directory,
)
from phentrieve_benchmark.proposals.validate import ProposalBatchError
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import AnnotationLanguage
```

3. Register the sub-app next to the others:

```python
proposals_app = typer.Typer(no_args_is_help=True)
```

and

```python
app.add_typer(proposals_app, name="proposals")
```

4. Add below `attribution_e3c_command`:

```python
_HPO_RECIPE = Path("configs/ontologies/hpo-v2026-06-23.yaml")
_ANNOTATION_LANGUAGES = ("de", "en", "fr", "es")


def _pinned_hpo_sha256(
    artifact_root: Path, store: ArtifactStore
) -> tuple[HpoSourceRecipe, str]:
    recipe = load_hpo_source_recipe(_HPO_RECIPE).value
    return recipe, load_or_acquire_hpo(
        recipe, artifact_root=artifact_root, store=store
    )


def _pinned_hpo_index(artifact_root: Path, store: ArtifactStore) -> HpoIndex:
    recipe, ontology_sha256 = _pinned_hpo_sha256(artifact_root, store)
    return load_hpo_index(
        store.read_bytes(ontology_sha256),
        release=recipe.release,
        ontology_sha256=ontology_sha256,
    )


def _committed_blob(repository_root: Path, path: Path) -> tuple[str, bytes]:
    """Return the last commit of a clean file and its committed bytes.

    The committed blob is used instead of the working-tree file because
    line endings differ under core.autocrlf.
    """

    def git(*arguments: str) -> bytes:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=True,
            capture_output=True,
        ).stdout

    posix = path.as_posix()
    if git("status", "--porcelain", "--", posix).strip():
        raise typer.BadParameter(f"{posix} has uncommitted changes")
    commit = git("log", "-1", "--format=%H", "--", posix).decode().strip()
    if not commit:
        raise typer.BadParameter(f"{posix} is not committed")
    return commit, git("show", f"{commit}:{posix}")


@proposals_app.command("prepare-run")
def prepare_proposal_run_command(
    run_id: str,
    corpus: Annotated[str, typer.Option("--corpus")],
    model_id: Annotated[str, typer.Option("--model-id")],
    language: Annotated[list[str] | None, typer.Option("--language")] = None,
    pilot: Annotated[bool, typer.Option("--pilot")] = False,
    batch_size: Annotated[int, typer.Option("--batch-size", min=1)] = 10,
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    """Plan a proposal run and write the subagent prompts and texts.

    --corpus is the corpus_sha256 printed by build-corpus. Without --language
    and --pilot, every corpus document is included. --pilot picks one report
    per original language and length stratum.
    """
    if pilot and language:
        raise typer.BadParameter(
            "--pilot selects its own reports", param_hint="--language"
        )
    unknown = sorted(set(language or ()) - set(_ANNOTATION_LANGUAGES))
    if unknown:
        raise typer.BadParameter(
            f"unknown annotation languages: {unknown}", param_hint="--language"
        )
    languages = (
        cast(tuple[AnnotationLanguage, ...], tuple(language)) if language else None
    )
    context = _pipeline_context(dataset_root, artifact_root)
    recipe, ontology_sha256 = _pinned_hpo_sha256(context.artifact_root, context.store)
    guideline_commit, guideline_bytes = _committed_blob(
        context.repository_root, GUIDELINE
    )
    guideline = GuidelineVersion(
        path=GUIDELINE.as_posix(),
        commit=guideline_commit,
        sha256=sha256_bytes(guideline_bytes),
    )
    _, prompt_template = _committed_blob(context.repository_root, PROMPT_TEMPLATE)
    groups = AnnotationGroupManifest.model_validate_json(
        (context.dataset_root / _E3C_GROUPS).read_bytes(), strict=True
    )
    input_directory = context.artifact_root / "proposals" / run_id
    try:
        run = prepare_proposal_run(
            store=context.store,
            repository_root=context.repository_root,
            corpus_manifest_sha256=corpus,
            groups=groups,
            run_id=run_id,
            model_id=model_id,
            run_date=context.clock().date(),
            prompt_template=prompt_template,
            guideline=guideline,
            hpo_release=recipe.release,
            ontology_sha256=ontology_sha256,
            languages=languages,
            pilot=pilot,
            batch_size=batch_size,
            run_directory=context.dataset_root / PROPOSALS_DIRECTORY / run_id,
            input_directory=input_directory,
        )
    except (FileExistsError, FileNotFoundError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    documents = sum(len(batch.documents) for batch in run.batches)
    typer.echo(
        f"run_id={run.run_id} documents={documents} "
        f"batches={len(run.batches)} pending_review={len(run.pending_review)} "
        f"inputs={input_directory}"
    )


@proposals_app.command("validate")
def validate_proposal_run_command(
    run_id: str,
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    """Validate the archived batch outputs of a run and write validation.json."""
    store = ArtifactStore(artifact_root.resolve() / "objects")
    hpo_index = _pinned_hpo_index(artifact_root.resolve(), store)
    try:
        report, validation_sha256 = validate_run_directory(
            run_directory=dataset_root.resolve() / PROPOSALS_DIRECTORY / run_id,
            store=store,
            hpo_index=hpo_index,
        )
    except ProposalBatchError as error:
        typer.echo(f"batch_error={error}", err=True)
        raise typer.Exit(1) from error
    except (FileNotFoundError, ValueError) as error:
        typer.echo(f"error={error}", err=True)
        raise typer.Exit(1) from error
    summary = report.summary
    typer.echo(
        f"validation_sha256={validation_sha256} documents={summary.documents} "
        f"proposals={summary.proposals_received} "
        f"rejected_proposals={summary.proposals_rejected} "
        f"validated_proposals={summary.validated_proposals} "
        f"mentions={summary.mentions_evaluated} "
        f"rejected_mentions={summary.mentions_rejected} "
        f"warnings={len(report.warnings)}"
    )


@proposals_app.command("hpo-lookup")
def hpo_lookup_command(
    queries: Annotated[list[str], typer.Argument()],
    limit: Annotated[int, typer.Option("--limit", min=1)] = 15,
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    """Search the pinned HPO release by English label, synonym, or ID."""
    store = ArtifactStore(artifact_root.resolve() / "objects")
    _, ontology_sha256 = _pinned_hpo_sha256(artifact_root.resolve(), store)
    entries = read_lookup_entries(store.read_bytes(ontology_sha256))
    for query in queries:
        typer.echo(f"# {query}")
        matches = search_hpo(entries, query, limit=limit)
        if not matches:
            typer.echo("(no match)")
        for match in matches:
            parts = [match.entry.hpo_id, match.entry.label]
            if match.matched != match.entry.label:
                parts.append(f"synonym: {match.matched}")
            if match.entry.obsolete:
                parts.append("obsolete")
            typer.echo("\t".join(parts))
```

- [ ] **Step 4: Run the CLI tests**

Run: `uv run pytest tests/unit/test_cli_proposals.py tests/unit/test_cli_pipeline.py -v`
Expected: all pass (8 tests in `test_cli_proposals.py`).

- [ ] **Step 5: Lint, types, full suite**

Run: `uv run ruff check . && uv run mypy && uv run pytest -q`
Expected: all clean and passing. mypy checks only `src` and `scripts`, so the test files need no `type: ignore` comments. `ruff --fix` does not wrap long lines; wrap any E501 line by hand.

- [ ] **Step 6: Smoke-test the lookup on the real release (local, no paid call)**

Run: `uv run phentrieve-benchmark proposals hpo-lookup "fever" "febrile seizure" HP:0001945`
Expected: `HP:0001945\tFever` is the first line under `# fever`; the `# febrile seizure` block lists `HP:0002373`; the ID query prints one line. The local `hp.obo` is in `.artifacts/source-locks/`, so no download happens.

- [ ] **Step 7: Commit**

```bash
git add src/phentrieve_benchmark/cli.py tests/unit/test_cli_proposals.py tests/unit/test_cli_pipeline.py
git commit -m "feat: add proposals prepare-run, validate, and hpo-lookup commands"
```

---

### Task 9: Contract test for tracked runs and the runbook

**Files:**
- Create: `tests/contracts/test_tracked_proposal_runs.py`
- Create: `datasets/e3c-de/proposals/README.md`
- Modify: `datasets/e3c-de/README.md`

- [ ] **Step 1: Write the contract test**

```python
# tests/contracts/test_tracked_proposal_runs.py
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
    batch_ids = {batch.batch_id for batch in run.batches}
    assert {path.stem for path in batch_files} == batch_ids
    assert {
        path.name.removesuffix(".prompt.md")
        for path in run_directory.glob("batch-*.prompt.md")
    } == batch_ids
    for path in batch_files:
        payload = json.loads(path.read_bytes())
        assert payload["provenance"] == PROPOSAL_PROVENANCE
        assert not _keys(payload) & PROHIBITED
        assert max(map(len, _strings(payload)), default=0) <= MAX_EXCERPT_CHARS
    assert not _keys(json.loads(validation_bytes)) & PROHIBITED
```

Run: `uv run pytest tests/contracts/test_tracked_proposal_runs.py -v`
Expected: `1 skipped` (empty parameter set; no tracked run yet). It becomes active with the pilot in Task 10.

- [ ] **Step 2: Write the runbook**

Create `datasets/e3c-de/proposals/README.md`:

````markdown
# HPO span proposals

> **Machine generated, not review data, not gold.** Every file below this
> directory is LLM output or its deterministic validation. A physician
> reviews each proposal in the annotation editor before anything enters gold.

Design: [`docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md`](../../../docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md) §6.
Rules applied by the subagents: [`docs/annotation-guidelines/hpo-span-annotation.md`](../../../docs/annotation-guidelines/hpo-span-annotation.md) (R0-R6).
Prompt template: [`configs/prompts/hpo-span-proposal-v1.md`](../../../configs/prompts/hpo-span-proposal-v1.md).

## Run layout

Each run lives in `<run_id>/`:

| File | Content |
|---|---|
| `prompt.md` | the committed prompt template (SHA-256 in `run.json`) |
| `run.json` | model ID, run date, corpus manifest hash, HPO release, guideline path, commit, and blob hash, batches with document IDs and hashes, German reports left out as pending |
| `batch-NN.prompt.md` | the exact prompt given to the subagent of that batch (paths, IDs, hashes; no report text) |
| `batch-NN.json` | the unchanged subagent output |
| `validation.json` | resolved offsets, merges, rejections with reasons, label warnings, summary; canonical JSON, so its file hash is its canonical hash (recorded in the table below) |

Files are stored byte-exact (`-text` in `.gitattributes`). Batch outputs
hold only short phrases, context excerpts, and notes: any string longer than
300 characters makes validation fail for that batch, the output is discarded
and the batch dispatched again, so such a file is never committed. This fits
the non-commercial scientific-use assumption recorded in
[`../license-evidence.yaml`](../license-evidence.yaml) and
[`../LICENSES.md`](../LICENSES.md). Full texts for the subagents are written
only to `.artifacts/proposals/<run_id>/` (Git-ignored).

## Procedure

Run every step in the main checkout, not in a Git worktree: the corpus, the
object store, and the HPO source lock live in its `.artifacts/`.

1. Build the corpus (refresh verified stages first if the code changed):

   ```bash
   uv run phentrieve-benchmark acquire e3c
   uv run phentrieve-benchmark normalize e3c
   uv run phentrieve-benchmark build-corpus e3c [--review-import SHA ...]
   ```

   Note the printed `corpus_sha256`.

2. Prepare a run (guideline and prompt template must be committed):

   ```bash
   uv run phentrieve-benchmark proposals prepare-run <run_id> \
     --corpus <corpus_sha256> --model-id <model id> \
     [--pilot | --language de --language en ...] [--batch-size 10]
   ```

3. Dispatch one Claude Code subagent per batch (Agent tool,
   `subagent_type: general-purpose`, `model` matching `--model-id`). The
   prompt is the content of `datasets/e3c-de/proposals/<run_id>/batch-NN.prompt.md`,
   passed verbatim. Run up to five batches in parallel. Each subagent ends
   its reply with the files it read and the commands it ran: reject the
   batch (delete its output, dispatch again) if it opened anything under
   `datasets/` other than its own output, for example E3C annotations,
   mappings, or `annotation-feasibility/`.

4. Validate:

   ```bash
   uv run phentrieve-benchmark proposals validate <run_id>
   ```

   `batch_error=...` (exit code 1) lists every batch output that cannot be
   validated at all: invalid JSON, a string over 300 characters, wrong
   envelope, missing or unknown report, or hash mismatch. Delete those
   `batch-NN.json` files and dispatch the same prompts again; failed attempts
   are not kept, but count them for the table below. Proposal- and
   mention-level problems never stop validation; they are listed in
   `validation.json` with a reason.

5. Add the run to the table below and commit the run directory.

Reproducibility: subagent runs have no pinned temperature or seed and cannot
be regenerated identically. Validation, editor packages, and import are
deterministic functions of the archived batch outputs.

## German group

German reports enter the corpus only with an accepted translation review.
Until then `prepare-run --language de` stops with "N German reports pending
translation review". Once reviews are imported, rebuild the corpus with
`--review-import` and prepare a separate run, for example `de-v1`, with
`--language de`. A run may cover part of the German group; a later run covers
the rest.

## Runs

| Run | Model | Documents | Re-dispatched batches | `validation_sha256` | Status |
|---|---|---:|---:|---|---|
````

- [ ] **Step 3: Link the runbook from the dataset README**

In `datasets/e3c-de/README.md`, add after item 6 of "Analysis reading path":

```markdown
7. [`proposals/README.md`](proposals/README.md) - LLM proposal runs
   (machine generated, not gold), their validation, and the runbook.
```

- [ ] **Step 4: Verify and commit**

Run: `uv run pytest tests/contracts -q && uv run ruff check .`
Expected: all pass (the new contract test is skipped).

```bash
git add tests/contracts/test_tracked_proposal_runs.py datasets/e3c-de/proposals/README.md datasets/e3c-de/README.md
git commit -m "docs: add proposal runbook and tracked-run contract test"
```

---

### Task 10: Pilot run with Sonnet 5.5 (real data, local, no paid API)

This task runs the real pipeline. Subagents run inside Claude Code; no API key or paid provider call is involved.

Run it in the **main checkout** (`C:\Users\jan-p\Development\phentrieve-benchmark-local`), not in a worktree: the E3C snapshot, the object store, and `.artifacts/source-locks/hp-v2026-06-23.obo` exist only there. If Tasks 1–9 were implemented in a worktree, merge that branch into `agent/e3c-phase2-proposals` in the main checkout first. The user runs Claude Code in auto mode, so the subagent's `uv run`, `cat`, and file writes should need no confirmation. If prompts do appear, the user confirms them; do not change permission settings.

**Files:**
- Create (generated): `datasets/e3c-de/proposals/pilot-v1/` (`prompt.md`, `run.json`, `batch-01.prompt.md`, `batch-01.json`, `validation.json`)
- Modify: `datasets/e3c-de/proposals/README.md`

- [ ] **Step 1: Refresh verified stages and build the corpus**

```bash
uv run phentrieve-benchmark acquire e3c
uv run phentrieve-benchmark normalize e3c
uv run phentrieve-benchmark build-corpus e3c
```

Expected: the last line reads `corpus_sha256=<hash> de=0 en=63 fr=61 es=61 pending_review=61`. Copy `<hash>`.

- [ ] **Step 2: Prepare the pilot**

```bash
uv run phentrieve-benchmark proposals prepare-run pilot-v1 \
  --corpus <hash> --model-id claude-sonnet-5-5 --pilot
```

Expected: `run_id=pilot-v1 documents=9 batches=1 pending_review=0 inputs=...`. Check that `datasets/e3c-de/proposals/pilot-v1/run.json` lists 3 EN, 3 FR, and 3 ES documents.

- [ ] **Step 3: Dispatch the subagent**

Read `datasets/e3c-de/proposals/pilot-v1/batch-01.prompt.md`. Dispatch one Agent with `subagent_type: "general-purpose"`, `model: "sonnet"`, `description: "HPO proposals pilot-v1 batch-01"`, and the file content verbatim as `prompt`. Wait for the completion notification. Then check:
- `datasets/e3c-de/proposals/pilot-v1/batch-01.json` exists;
- `git status --short -- src tests configs docs datasets` shows nothing except the new run directory (the subagent changed no other file);
- the files the subagent lists as read are the guideline, its own text files under `.artifacts/proposals/pilot-v1/batch-01/`, and nothing else under `datasets/`. Otherwise delete the output and dispatch again (runbook step 3).

- [ ] **Step 4: Validate**

Run: `uv run phentrieve-benchmark proposals validate pilot-v1`
Expected: one `validation_sha256=... documents=9 ...` line. On `batch_error=...`, follow runbook step 4: delete the batch file, dispatch again, and validate again. Count the re-dispatches.

- [ ] **Step 5: Evaluate the pilot**

From `validation.json`:
- rejection rate for proposals (`proposals_rejected / proposals_received`) and mentions (`mentions_rejected / mentions_evaluated`), and `rejections_by_reason`;
- the number of label warnings.

Quality spot check, with the main session reading the texts via `cat` from `.artifacts/proposals/pilot-v1/batch-01/`: for three reports (one per language), compare the validated proposals with the text against R0–R6. Count obvious misses, wrong terms (including terms outside Phenotypic abnormality, which R0 excludes), wrong spans (R2/R4), wrong status (R3), and R6 misuse.

- [ ] **Step 6: Record the pilot result**

Append a row to the "Runs" table in `datasets/e3c-de/proposals/README.md`, with the number of re-dispatched batches from Step 4 and the `validation_sha256` printed there:

```markdown
| `pilot-v1` | `claude-sonnet-5-5` | 9 | <re-dispatches> | `<validation_sha256>` | pilot; see below |
```

Then add a section `## Pilot pilot-v1` with: the date, the dispatch attempts, the summary counts and rejection rates from Step 5, rejections by reason, the spot-check findings per report (short), and a verdict on whether Sonnet 5.5 is good enough. Write facts only and keep it in English.

- [ ] **Step 7: Verify and commit**

Run: `uv run pytest tests/contracts/test_tracked_proposal_runs.py -v`
Expected: 1 passed (`pilot-v1`).

```bash
git add datasets/e3c-de/proposals
git commit -m "data: add proposal pilot run pilot-v1 (Sonnet 5.5)"
```

- [ ] **Step 8: Stop and report to the user**

Present the pilot numbers and findings. Ask for an explicit decision; do not continue without it:
- full run with Sonnet 5.5 and prompt v1 (Task 11), or
- prompt revision: a new `configs/prompts/hpo-span-proposal-v2.md`, the `PROMPT_TEMPLATE` constant updated, a new pilot `pilot-v2`, or
- a second pilot with another model (for example `--model-id claude-opus-5-5`, Agent `model: "opus"`, run `pilot-v1-opus`).

If the spot check found terms outside Phenotypic abnormality, mention it. Restricting the lookup to HP:0000118 was deferred on 2026-10-06 and can be reconsidered then.

---

### Task 11: Full run for the original-language groups (only after explicit confirmation)

Do not start this task without the user's explicit go from Task 10 Step 8. The German group follows later in its own run (runbook, section "German group").

**Files:**
- Create (generated): `datasets/e3c-de/proposals/full-v1/`
- Modify: `datasets/e3c-de/proposals/README.md`, `docs/project-checklist.md`

- [ ] **Step 1: Prepare**

Use the confirmed model and prompt. With Sonnet 5.5 and prompt v1:

```bash
uv run phentrieve-benchmark proposals prepare-run full-v1 \
  --corpus <hash> --model-id claude-sonnet-5-5 \
  --language en --language fr --language es
```

Expected: `run_id=full-v1 documents=185 batches=19 pending_review=0 ...` (`pending_review` is 0 because German is not selected).

- [ ] **Step 2: Dispatch in waves**

Dispatch batches `batch-01` to `batch-19` in waves of up to five parallel Agents, configured and checked as in Task 10 Step 3, each with the content of its own `batch-NN.prompt.md`. After each wave, confirm the expected `batch-NN.json` files exist.

- [ ] **Step 3: Validate and handle batch errors**

Run: `uv run phentrieve-benchmark proposals validate full-v1`
For a `batch_error`, follow runbook step 4 for every batch it lists, then validate again until it succeeds. Count the re-dispatches.

- [ ] **Step 4: Record, verify, commit**

Add the `full-v1` row (re-dispatches, `validation_sha256`) and the summary counts to the runbook. In `docs/project-checklist.md`, under the item "Einheitlichen Vorschlagsschritt für alle 246 Texte durchführen", add the sub-bullet below. It is in German to match the file:

```markdown
  - Stand: Lauf `full-v1` für EN/FR/ES (185 Berichte) validiert; deutsche
    Gruppe folgt nach ihrem Übersetzungsreview als eigener Lauf.
```

Run: `uv run pytest -q && uv run ruff check . && uv run mypy`
Expected: all pass.

```bash
git add datasets/e3c-de/proposals docs/project-checklist.md
git commit -m "data: add proposal run full-v1 for the original-language groups"
```

---

## Self-Review Notes

- Spec §6.1 (batches of about ten; input text, language, ID, hash; versioned prompt; guideline version; no UMLS/E3C/Phase 0 inputs) → Tasks 5, 6, 7 (prompt forbids other sources), 8.
- §6.1 output schema and phrase/context location → Task 1 (`ProposedAnnotation`, `ProposalBatchOutput`), Task 7.
- §6.2 checks: ID/hash binding → Task 4 (`parse_batch_output`), Task 6 (corpus documents hash); active HPO term, label informational → Task 4 (rejections; label only warns); allowed axis values → Task 1 (Literals per R3); context unique and phrase in context with offsets → Task 2; typography tolerance with verbatim spans → Task 2; `occurrence` with whole-word precedence → Task 2; non-overlapping mentions → Task 4; listed rejections, nothing repaired → Task 4; merge by HPO ID and status → Task 4 (key includes `verbalized`, decided 2026-10-06).
- §6.3 traceability: `prompt.md` and guideline hash from committed blobs (Task 8 `_committed_blob`), guideline commit, `run.json` fields, rendered `batch-NN.prompt.md`, raw `batch-NN.json` with provenance, `validation.json` with canonical hash (file is canonical; hash recorded in the runbook table) → Tasks 6, 8, 9 (contract), `.gitattributes` keeps bytes exact.
- §6.3 short excerpts only → Task 4 (any string over `MAX_EXCERPT_CHARS` is a batch error, so the file is never committed), Task 7 (prompt limit 120), Task 9 (contract test).
- Review of 2026-10-06 (code verified by running it; all findings addressed): CRLF-independent hashes, excerpt limit on tracked files, tracked batch prompts, main-checkout and path notes for Tasks 10–11, RUF043, `occurrence` ordering, collected batch errors, CLI error handling, batch-level and `_committed_blob` tests, `pending_review` in `run.json`, file-read listing by subagents, re-dispatch counts, narrower `.gitattributes`. Not adopted: HP:0000118 restriction (decided against), checking the Agent model alias against `model_id` (the alias is set by the operator in the same step), pydantic-version independence of rejection `detail` strings (pinned by `uv.lock`). Package references to run/batch/proposal ID are Phase 3; the IDs exist here (`run_id`, `batch_id`, `proposal_id`, `source_proposal_ids`).
- §6.3 reproducibility statement → runbook (Task 9).
- §6.4 pilot (about eight reports, original languages, mixed lengths; German only synthetic; full run only after confirmation; pilot kept as own run) → Task 5 (`pilot_case_ids`), Task 6 (German integration test), Tasks 10–11.
- §9 validator tests (each rejection reason, offsets, merge, no input mutation) → Tasks 2, 4, 6 (batch files unchanged after validation).
- German support without reviewed texts: `select_run_entries` explains pending reports when nothing else is selected; otherwise `run.json` records them in `pending_review` and `prepare-run` prints their count; `prepare-run --language de` works unchanged once the corpus holds German documents.
- Names used across tasks: `PROPOSAL_PROVENANCE`, `MAX_EXCERPT_CHARS`, `ProposalRun`, `ProposalBatch`, `BatchDocument`, `ProposalBatchOutput`, `ProposedAnnotation`, `RejectionReason`, `ProposalValidationReport`, `ValidationSummary`, `normalize_typography`, `locate_mention`, `read_lookup_entries`, `search_hpo`, `validate_proposal_run`, `ProposalBatchError`, `pilot_case_ids`, `select_run_entries`, `plan_batches`, `render_batch_prompt`, `GuidelineVersion`, `prepare_proposal_run`, `validate_run_directory`, `PROPOSALS_DIRECTORY`, `PROMPT_TEMPLATE`, `GUIDELINE`, `_pinned_hpo_sha256`, `_pinned_hpo_index`, `_committed_blob`.

---

## Changes after the plan was written (2026-10-06)

Tasks 1-10 are done. The code blocks above are the plan as written; the
implementation differs where reviews and the pilots led to changes. The
runbook `datasets/e3c-de/proposals/README.md` holds the pilot results.

Review-driven changes in Tasks 1-9:

- Models: `ResolvedMention` rejects `end <= start`; the counts of
  `ValidationSummary` are non-negative.
- Locator: the whole-word check requires a boundary only on a side where
  the phrase's own edge character is alphanumeric.
- Lookup: queries and names are compared as word runs, so punctuation,
  hyphens, and apostrophes do not block a match.
- Validator: JSON keys over 300 characters and duplicate JSON keys are batch
  errors.
- Pipeline: paths outside the repository root are refused; the contract test
  requires the exact file set of a run directory.
- CLI: `hpo-lookup` writes UTF-8.

Changes after the pilots:

- Prompt v2 and v3 (`configs/prompts/`); `PROMPT_TEMPLATE` points to v3.
- `prepare-run --case` selects reports by source case ID.
- `proposals hpo-lookup` lists only terms under *Phenotypic abnormality* in
  text search and marks other terms on a lookup by ID. The validator rejects
  a proposal with a term outside that branch (`hpo_id_not_phenotypic`). This
  supersedes the decision "No restriction to HP:0000118".
- `proposals validate` removes an earlier `validation.json` before it runs.
  Expected failures of the three commands are reported without a traceback.
- Guideline R0, R3, and R5 carry three clarifications (hedged findings are
  `uncertain`; back-references are not occurrences; a normal finding is not
  a negated phenotype).
- Task 10 Step 3 should use `git status --short --untracked-files=all`.
- Task 11: the 27 piloted reports keep their pilot outputs as proposals; the
  full run covers the remaining 158 reports with `--case`, not all 185.

# E3C Annotation Groups and Corpus Implementation Plan (Phases 0–1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the superseded Excel annotation path, split all 246 E3C reports into four annotation groups, retarget the translation review export to the German group, and build the annotation corpus artifact that holds every report in its annotation language.

**Architecture:** A pure, deterministic split function over the tracked text-free inventory writes a tracked group manifest. The existing translation review export gains a case filter. A new corpus builder combines verified native documents with accepted translation review records into one `documents` JSONL artifact plus a text-free corpus manifest in the content-addressed store. German reports without an accepted review are listed as pending and never use unreviewed text.

**Tech Stack:** Python 3.11+, Pydantic v2 (strict, frozen models), Typer CLI, pytest, uv, ruff, mypy (strict).

**Spec:** `docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md` (§4, §5).
**Later plans:** Phase 2 (proposal step), Phase 3 (editor packages), Phase 4 (format v2 and import) get their own plans after this one is done.

**Conventions used throughout**

- Run every command from the repository root `C:\Users\jan-p\Development\phentrieve-benchmark-local` with Git Bash.
- Tests: `uv run pytest <path> -v`. Lint: `uv run ruff check .`. Types: `uv run mypy`.
- Models follow the repo pattern `ConfigDict(extra="forbid", frozen=True, strict=True)` and expose `canonical_bytes()` via `canonical_json_bytes`.
- Do not add AI co-authorship trailers to commits.
- If ruff only reports import ordering (`I001`) or line length in new code, fix it with `uv run ruff check --fix <file>` or by wrapping lines; do not change behaviour.

---

## File Structure

| File | Responsibility |
|---|---|
| `datasets/e3c-de/annotation-feasibility/make_annotation_review.py` | **Delete** (superseded Excel annotation workbook) |
| `datasets/e3c-de/annotation-feasibility/README.md`, `datasets/e3c-de/README.md` | Mark workbook generator and staged strategy as superseded |
| `pyproject.toml` | Exclude `scripts/build_editor_packages.py` from coverage |
| `src/phentrieve_benchmark/selection/groups.py` | Group models and deterministic split |
| `tests/unit/selection/test_annotation_groups.py` | Unit tests for the split |
| `src/phentrieve_benchmark/cli.py` | Commands `select e3c-groups`, export options `--variant`/`--groups`, command `build-corpus e3c` |
| `datasets/e3c-de/selections/e3c-annotation-groups-v1.json` | Tracked, text-free group manifest (generated) |
| `tests/contracts/test_tracked_annotation_groups.py` | Contract test for the tracked manifest |
| `src/phentrieve_benchmark/pipeline/translation_review.py` | `case_ids` filter in `export_translation_review` |
| `tests/unit/pipeline/test_translation_review_export.py` | Tests for the case filter |
| `src/phentrieve_benchmark/models/annotation_corpus.py` | Corpus manifest models |
| `src/phentrieve_benchmark/pipeline/annotation_corpus.py` | Corpus builder |
| `tests/unit/pipeline/test_annotation_corpus.py` | Unit tests for the corpus builder |
| `src/phentrieve_benchmark/pipeline/prepare.py` | Extract `verified_e3c_normalization` helper |

---

### Task 1: Commit the design documents

**Files:**
- Add: `docs/annotation-guidelines/hpo-span-annotation.md`
- Add: `docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md`
- Add: `docs/superpowers/plans/2026-10-06-e3c-annotation-groups-and-corpus.md`
- Modify: `docs/project-checklist.md`

**Done** in commit `0de08b3` on branch `agent/e3c-multilingual-annotation`.

---

### Task 2: Remove the superseded Excel annotation workbook

**Files:**
- Delete: `datasets/e3c-de/annotation-feasibility/make_annotation_review.py`
- Modify: `datasets/e3c-de/annotation-feasibility/README.md`
- Modify: `datasets/e3c-de/README.md:51-55`

- [ ] **Step 1: Confirm the current lint failure comes only from the script**

Run: `uv run ruff check . 2>&1 | tail -1`
Expected: `Found 31 errors.`

- [ ] **Step 2: Delete the script**

```bash
git rm datasets/e3c-de/annotation-feasibility/make_annotation_review.py
```

- [ ] **Step 3: Update the probe README**

In `datasets/e3c-de/annotation-feasibility/README.md`, insert directly below the first heading:

```markdown
> **Superseded (2026-10-06).** This probe remains as comparison data. Its
> recommendation of a span-free document-level gold and the Excel review
> workbook generator are replaced by span-based annotation in four language
> groups; see
> [`docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md`](../../../docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md).
```

Then delete the section that describes the review workbook generator (the paragraphs that explain how to run `make_annotation_review.py` and its outputs). Keep the probe results, the CUI triage, and the preserved-file hash table unchanged.

- [ ] **Step 4: Update the dataset README reading path**

In `datasets/e3c-de/README.md`, replace item 3 of "Analysis reading path":

```markdown
3. [`annotation-feasibility/README.md`](annotation-feasibility/README.md) -
   Phase 0 feasibility probe: do the consensus terms survive the German
   translation (Part A) and triage of the most frequent unresolved CUIs
   (Part B). Kept as comparison data; superseded as a working plan.
```

and add a new last item:

```markdown
6. [`../../docs/annotation-guidelines/hpo-span-annotation.md`](../../docs/annotation-guidelines/hpo-span-annotation.md) -
   span annotation rules for all four annotation groups.
```

- [ ] **Step 5: Verify lint, references, and contract tests**

Run: `uv run ruff check .`
Expected: `All checks passed!`

Run: `git grep -n "make_annotation_review" -- . ':!docs/superpowers' ':!docs/project-checklist.md'`
Expected: no output. (The checklist item naming the script is ticked in Task 9.)

Run: `uv run pytest tests/contracts -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add datasets/e3c-de/annotation-feasibility/README.md datasets/e3c-de/README.md
git commit -m "chore: remove superseded Excel annotation workbook generator"
```

---

### Task 3: Remove the coverage gate and exclude the editor script

The script and its mypy override were already committed in `8c7364a`.
Coverage is reported but no longer enforced (decided 2026-10-06; it was
already at 88 % and failing the 90 % gate before this plan).

**Files:**
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml:35`

- [ ] **Step 0: Remove the gate**

In `.github/workflows/ci.yml`, delete the line `          --cov-fail-under=90`
(keep `--cov-report=term-missing` as the last argument).

- [ ] **Step 1: Add the coverage exclusion**

Append to `pyproject.toml`:

```toml
# Runs only in the Ontocurator overlay environment; not measured in CI.
[tool.coverage.run]
omit = ["scripts/build_editor_packages.py"]
```

- [ ] **Step 2: Verify lint and types**

Run: `uv run ruff check scripts/build_editor_packages.py && uv run mypy`
Expected: ruff `All checks passed!`; mypy `Success: no issues found`.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml .github/workflows/ci.yml
git commit -m "ci: report coverage without a gate; exclude editor builder"
```

---

### Task 4: Deterministic split into annotation groups

**Files:**
- Create: `src/phentrieve_benchmark/selection/groups.py`
- Test: `tests/unit/selection/test_annotation_groups.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/selection/test_annotation_groups.py
import json
from collections import Counter
from fractions import Fraction

import pytest

from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.e3c import canonical_e3c_inventory_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    assign_annotation_groups,
    load_e3c_inventory,
)
from phentrieve_benchmark.selection.metrics import (
    E3cInventoryRecord,
    LengthStratum,
    Rational,
)

_PREFIX = {"en": "EN", "fr": "FR", "es": "ES"}


def _record(language: str, stratum: LengthStratum, index: int) -> E3cInventoryRecord:
    tokens = {
        LengthStratum.SHORT: 100,
        LengthStratum.MEDIUM: 300,
        LengthStratum.LONG: 500,
    }[stratum] + index
    case_id = f"{_PREFIX[language]}{stratum.value}{index:02d}"
    return E3cInventoryRecord(
        source_case_id=case_id,
        language=language,
        document_sha256=sha256_bytes(case_id.encode()),
        codepoint_count=tokens * 4,
        whitespace_token_count=tokens,
        sentence_count=1,
        annotation_counts=(("EVENT", index + 1),),
        total_annotation_density=Rational.from_fraction(
            Fraction((index + 1) * 100, tokens)
        ),
        marker_counts=(),
        marker_densities=(),
        length_stratum=stratum,
        warnings=(),
    )


def _inventory(per_stratum: int = 7) -> list[E3cInventoryRecord]:
    return [
        _record(language, stratum, index)
        for language in ("en", "fr", "es")
        for stratum in LengthStratum
        for index in range(per_stratum)
    ]


def test_split_is_deterministic_and_order_independent() -> None:
    records = _inventory()
    first = assign_annotation_groups(records)
    second = assign_annotation_groups(list(reversed(records)))
    assert first.canonical_bytes() == second.canonical_bytes()


def test_every_report_is_assigned_exactly_once() -> None:
    records = _inventory()
    manifest = assign_annotation_groups(records)
    assert len(manifest.records) == len(records)
    assert {record.source_case_id for record in manifest.records} == {
        record.source_case_id for record in records
    }


def test_about_a_quarter_of_each_language_goes_to_german() -> None:
    manifest = assign_annotation_groups(_inventory())
    for language in ("en", "fr", "es"):
        german = [
            record
            for record in manifest.records
            if record.source_language == language
            and record.annotation_language == "de"
        ]
        assert len(german) in {21 // 4, 21 // 4 + 1}
    others = Counter(
        record.annotation_language
        for record in manifest.records
        if record.annotation_language != "de"
    )
    assert set(others) == {"en", "fr", "es"}


def test_german_share_covers_every_length_stratum() -> None:
    manifest = assign_annotation_groups(_inventory())
    for language in ("en", "fr", "es"):
        for stratum in LengthStratum:
            assert any(
                record.source_language == language
                and record.length_stratum is stratum
                and record.annotation_language == "de"
                for record in manifest.records
            )


def test_manifest_binds_the_inventory_and_lists_group_case_ids() -> None:
    records = _inventory()
    manifest = assign_annotation_groups(records)
    assert manifest.inventory_sha256 == sha256_bytes(
        canonical_e3c_inventory_bytes(records)
    )
    german = manifest.case_ids("de")
    assert german == tuple(sorted(german))
    assert len(german) + sum(
        len(manifest.case_ids(language)) for language in ("en", "fr", "es")
    ) == len(records)


def test_duplicate_inventory_identity_is_rejected() -> None:
    record = _record("en", LengthStratum.SHORT, 0)
    with pytest.raises(ValueError, match="duplicate"):
        assign_annotation_groups([record, record])


def test_annotation_language_must_be_german_or_source() -> None:
    manifest = assign_annotation_groups(_inventory())
    payload = manifest.model_dump(mode="json")
    payload["records"][0]["annotation_language"] = (
        "fr" if payload["records"][0]["source_language"] != "fr" else "en"
    )
    with pytest.raises(ValueError, match="German or the source language"):
        AnnotationGroupManifest.model_validate_json(json.dumps(payload), strict=True)


def test_inventory_round_trips_from_canonical_bytes() -> None:
    records = _inventory()
    loaded = load_e3c_inventory(canonical_e3c_inventory_bytes(records))
    assert {record.source_case_id for record in loaded} == {
        record.source_case_id for record in records
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/selection/test_annotation_groups.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phentrieve_benchmark.selection.groups'`.

- [ ] **Step 3: Implement the split**

```python
# src/phentrieve_benchmark/selection/groups.py
"""Deterministic split of the E3C inventory into four annotation groups.

Every report is annotated in exactly one language: German (machine-translated)
or its original language. Per source language, reports are sorted by length
stratum, annotation density, and a seeded hash; every fourth report, starting
at a seeded offset, goes to German. This spreads the German share evenly over
length and density without a search.
"""

from collections.abc import Iterable
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes
from phentrieve_benchmark.selection.e3c import canonical_e3c_inventory_bytes
from phentrieve_benchmark.selection.metrics import (
    E3cInventoryRecord,
    LengthStratum,
    Rational,
)

GROUP_SEED = "phentrieve-e3c-annotation-groups-v1"
_SOURCE_LANGUAGES: tuple[Literal["en", "fr", "es"], ...] = ("en", "fr", "es")
_STRATUM_ORDER = {
    LengthStratum.SHORT: 0,
    LengthStratum.MEDIUM: 1,
    LengthStratum.LONG: 2,
}
_GROUP_COUNT = 4


class AnnotationGroupRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_case_id: str = Field(min_length=1)
    source_language: Literal["en", "fr", "es"]
    annotation_language: Literal["de", "en", "fr", "es"]
    document_sha256: Sha256Hex
    length_stratum: LengthStratum
    total_annotation_density: Rational

    @model_validator(mode="after")
    def is_german_or_source(self) -> Self:
        if self.annotation_language not in {"de", self.source_language}:
            raise ValueError(
                "annotation language must be German or the source language"
            )
        return self


class AnnotationGroupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-annotation-groups/v1"] = (
        "e3c-annotation-groups/v1"
    )
    selection_id: Literal["e3c-annotation-groups-v1"] = (
        "e3c-annotation-groups-v1"
    )
    inventory_sha256: Sha256Hex
    algorithm_id: Literal["e3c-stratified-systematic/v1"] = (
        "e3c-stratified-systematic/v1"
    )
    selection_seed: str = GROUP_SEED
    records: tuple[AnnotationGroupRecord, ...]
    aggregate_sha256: Sha256Hex

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def case_ids(self, annotation_language: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                record.source_case_id
                for record in self.records
                if record.annotation_language == annotation_language
            )
        )


def _seeded(value: str) -> bytes:
    return sha256(f"{GROUP_SEED}\0{value}".encode()).digest()


def load_e3c_inventory(payload: bytes) -> tuple[E3cInventoryRecord, ...]:
    return tuple(
        TypeAdapter(list[E3cInventoryRecord]).validate_json(payload, strict=True)
    )


def assign_annotation_groups(
    inventory: Iterable[E3cInventoryRecord],
) -> AnnotationGroupManifest:
    records = list(inventory)
    inventory_bytes = canonical_e3c_inventory_bytes(records)
    assigned: list[AnnotationGroupRecord] = []
    for language in _SOURCE_LANGUAGES:
        ordered = sorted(
            (record for record in records if record.language == language),
            key=lambda record: (
                _STRATUM_ORDER[record.length_stratum],
                record.total_annotation_density.fraction(),
                _seeded(record.source_case_id),
            ),
        )
        offset = int.from_bytes(_seeded(language), "big") % _GROUP_COUNT
        for index, record in enumerate(ordered):
            annotation_language: Literal["de", "en", "fr", "es"] = (
                "de" if index % _GROUP_COUNT == offset else language
            )
            assigned.append(
                AnnotationGroupRecord(
                    source_case_id=record.source_case_id,
                    source_language=language,
                    annotation_language=annotation_language,
                    document_sha256=record.document_sha256,
                    length_stratum=record.length_stratum,
                    total_annotation_density=record.total_annotation_density,
                )
            )
    output = tuple(
        sorted(
            assigned,
            key=lambda record: (record.source_language, record.source_case_id),
        )
    )
    aggregate = sha256_bytes(
        canonical_json_bytes([record.model_dump(mode="json") for record in output])
    )
    return AnnotationGroupManifest(
        inventory_sha256=sha256_bytes(inventory_bytes),
        records=output,
        aggregate_sha256=aggregate,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/selection/test_annotation_groups.py -v`
Expected: 8 passed.

- [ ] **Step 5: Lint and type check**

Run: `uv run ruff check src/phentrieve_benchmark/selection/groups.py tests/unit/selection/test_annotation_groups.py && uv run mypy`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/phentrieve_benchmark/selection/groups.py tests/unit/selection/test_annotation_groups.py
git commit -m "feat: split E3C reports into four annotation groups"
```

---

### Task 5: Command `select e3c-groups` and the tracked group manifest

**Files:**
- Modify: `src/phentrieve_benchmark/cli.py`
- Create (generated): `datasets/e3c-de/selections/e3c-annotation-groups-v1.json`
- Test: `tests/contracts/test_tracked_annotation_groups.py`

- [ ] **Step 1: Write the failing contract test**

```python
# tests/contracts/test_tracked_annotation_groups.py
import json
from collections import Counter
from pathlib import Path

from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    assign_annotation_groups,
    load_e3c_inventory,
)

ROOT = Path(__file__).parents[2]
INVENTORY = ROOT / "datasets/e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json"
GROUPS = ROOT / "datasets/e3c-de/selections/e3c-annotation-groups-v1.json"
PROHIBITED = {"text", "text_snippet", "prompt", "credential", "timestamp"}


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value))
    return set()


def test_tracked_groups_are_reproducible_from_the_tracked_inventory() -> None:
    inventory_bytes = INVENTORY.read_bytes()
    groups_bytes = GROUPS.read_bytes()
    expected = assign_annotation_groups(load_e3c_inventory(inventory_bytes))
    assert groups_bytes == expected.canonical_bytes()
    manifest = AnnotationGroupManifest.model_validate_json(groups_bytes, strict=True)
    assert manifest.inventory_sha256 == sha256_bytes(inventory_bytes)


def test_tracked_groups_have_the_agreed_sizes_and_no_text() -> None:
    manifest = AnnotationGroupManifest.model_validate_json(
        GROUPS.read_bytes(), strict=True
    )
    assert len(manifest.records) == 246
    german = Counter(
        record.source_language
        for record in manifest.records
        if record.annotation_language == "de"
    )
    assert german["en"] == 21
    assert german["fr"] in {20, 21}
    assert german["es"] in {20, 21}
    assert not _keys(json.loads(GROUPS.read_bytes())) & PROHIBITED
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/contracts/test_tracked_annotation_groups.py -v`
Expected: FAIL with `FileNotFoundError` for `e3c-annotation-groups-v1.json`.

- [ ] **Step 3: Add the command**

In `src/phentrieve_benchmark/cli.py`, add `from collections import Counter` to the imports, add

```python
from phentrieve_benchmark.selection.groups import (
    assign_annotation_groups,
    load_e3c_inventory,
)
```

and below `select_e3c_command`:

```python
_E3C_INVENTORY = Path("e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json")
_E3C_GROUPS = Path("e3c-de/selections/e3c-annotation-groups-v1.json")


@select_app.command("e3c-groups")
def select_e3c_groups_command(
    dataset_root: DatasetRoot = Path("datasets"),
) -> None:
    """Split all E3C reports into the four annotation groups."""
    manifest = assign_annotation_groups(
        load_e3c_inventory((dataset_root / _E3C_INVENTORY).read_bytes())
    )
    destination = dataset_root / _E3C_GROUPS
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(manifest.canonical_bytes())
    summary = _group_summary(
        record.annotation_language for record in manifest.records
    )
    typer.echo(f"destination={destination} {summary}")


def _group_summary(languages: Iterable[str]) -> str:
    counts = Counter(languages)
    return " ".join(
        f"{language}={counts[language]}" for language in ("de", "en", "fr", "es")
    )
```

Add `from collections.abc import Iterable` to the imports of `cli.py`.

- [ ] **Step 4: Generate the tracked manifest**

Run: `uv run phentrieve-benchmark select e3c-groups`
Expected: `destination=datasets/e3c-de/selections/e3c-annotation-groups-v1.json de=61 en=63 fr=61 es=61` (verified against the tracked inventory: German = 21 EN + 20 FR + 20 ES).

- [ ] **Step 5: Run the contract test and the full suite**

Run: `uv run pytest tests/contracts/test_tracked_annotation_groups.py -v`
Expected: 2 passed.

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/phentrieve_benchmark/cli.py tests/contracts/test_tracked_annotation_groups.py datasets/e3c-de/selections/e3c-annotation-groups-v1.json
git commit -m "feat: publish E3C annotation group manifest"
```

---

### Task 6: Translation review export for the German group

**Files:**
- Modify: `src/phentrieve_benchmark/pipeline/translation_review.py:171-247`
- Modify: `src/phentrieve_benchmark/cli.py` (`export_e3c_review_workbook_command`)
- Test: `tests/unit/pipeline/test_translation_review_export.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/pipeline/test_translation_review_export.py`:

```python
def test_export_can_be_restricted_to_listed_cases(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    tllm, _ = _manifests(store)

    export_sha256 = export_translation_review(
        store=store,
        tllm_manifest=tllm,
        destination=tmp_path / "review.xlsx",
        review_policy_id="medical-review-v1",
        case_ids=("FR2", "EN1"),
    )

    export = TranslationReviewExport.model_validate_json(
        store.read_bytes(export_sha256), strict=True
    )
    assert [case.source_case_id for case in export.cases] == ["EN1", "FR2"]


def test_export_rejects_listed_cases_missing_from_the_manifest(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    tllm, _ = _manifests(store)

    with pytest.raises(ValueError, match="lacks cases"):
        export_translation_review(
            store=store,
            tllm_manifest=tllm,
            destination=tmp_path / "review.xlsx",
            review_policy_id="medical-review-v1",
            case_ids=("EN1", "XX9"),
        )


def test_export_rejects_nmt_comparison_for_case_lists(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    tllm, nmt = _manifests(store)

    with pytest.raises(ValueError, match="NMT comparison"):
        export_translation_review(
            store=store,
            tllm_manifest=tllm,
            destination=tmp_path / "review.xlsx",
            review_policy_id="medical-review-v1",
            nmt_manifest=nmt,
            case_ids=("EN1",),
        )
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_translation_review_export.py -v -k "listed or case_lists"`
Expected: FAIL with `TypeError: export_translation_review() got an unexpected keyword argument 'case_ids'`.

- [ ] **Step 3: Implement the filter**

In `src/phentrieve_benchmark/pipeline/translation_review.py`, add `Collection` to the existing `from collections.abc import ...` line (or create that line if absent). Change the signature and the start of `export_translation_review`:

```python
def export_translation_review(
    *,
    store: ArtifactStore,
    tllm_manifest: TranslationManifest,
    destination: Path,
    review_policy_id: str,
    nmt_manifest: TranslationManifest | None = None,
    source_language: str | None = None,
    case_ids: Collection[str] | None = None,
) -> str:
    """Store a canonical review export and write its Excel review workbook."""
    all_records = _records_by_case(
        tllm_manifest,
        model="general/translation-llm",
        variant="TLLM",
    )
    if case_ids is not None:
        if nmt_manifest is not None:
            raise ValueError("NMT comparison is not supported for case lists")
        missing = set(case_ids) - all_records.keys()
        if missing:
            raise ValueError(f"TLLM manifest lacks cases: {sorted(missing)}")
        all_records = {
            case_id: record
            for case_id, record in all_records.items()
            if case_id in case_ids
        }
    tllm_records = _filter_language(
        all_records,
        source_language=source_language,
        variant="TLLM",
    )
```

Leave the rest of the function unchanged.

- [ ] **Step 4: Run the export tests**

Run: `uv run pytest tests/unit/pipeline/test_translation_review_export.py -v`
Expected: all pass (existing and new).

- [ ] **Step 5: Add CLI options**

In `src/phentrieve_benchmark/cli.py`, add the import

```python
from phentrieve_benchmark.selection.groups import AnnotationGroupManifest
```

(merge it into the existing `selection.groups` import) and replace `export_e3c_review_workbook_command` with:

```python
@review_workbook_app.command("export-e3c")
def export_e3c_review_workbook_command(
    destination: Path,
    include_nmt: Annotated[bool, typer.Option("--include-nmt")] = False,
    language: SourceLanguage = None,
    variant: Variant = "tllm",
    groups: Annotated[Path | None, typer.Option("--groups")] = None,
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    """Export a translation review workbook.

    With --groups, only the German annotation group of that manifest is
    exported; use it together with --variant tllm-full.
    """
    context = _pipeline_context(dataset_root, artifact_root)
    tllm_manifest = _resolve_review_translation_manifest(
        context=context, variant=variant
    )
    nmt_manifest = (
        _resolve_review_translation_manifest(context=context, variant="nmt")
        if include_nmt
        else None
    )
    case_ids = (
        AnnotationGroupManifest.model_validate_json(
            groups.read_bytes(), strict=True
        ).case_ids("de")
        if groups is not None
        else None
    )
    export_sha256 = export_translation_review(
        store=context.store,
        tllm_manifest=tllm_manifest,
        destination=destination.resolve(),
        review_policy_id=_TRANSLATION_REVIEW_POLICY_ID,
        nmt_manifest=nmt_manifest,
        source_language=language,
        case_ids=case_ids,
    )
    exported = [
        record
        for record in tllm_manifest.records
        if (language is None or record.source_language == language)
        and (case_ids is None or record.source_case_id in case_ids)
    ]
    typer.echo(f"export_sha256={export_sha256} cases={len(exported)}")
```

- [ ] **Step 6: Run CLI tests, lint, and types**

The existing CLI test asserts the exact keyword arguments passed to
`export_translation_review`. In `tests/unit/test_cli_pipeline.py`, inside
`test_review_workbook_export_resolves_tllm_and_omits_nmt_by_default`, add
`"case_ids": None,` to the expected keyword-argument dict (next to
`"source_language"`).

Run: `uv run pytest tests/unit/test_cli_pipeline.py tests/contracts/test_translation_review_workbook.py -v && uv run ruff check . && uv run mypy`
Expected: all pass, no lint or type errors.

- [ ] **Step 7: Commit**

```bash
git add src/phentrieve_benchmark/pipeline/translation_review.py src/phentrieve_benchmark/cli.py tests/unit/pipeline/test_translation_review_export.py tests/unit/test_cli_pipeline.py
git commit -m "feat: export translation review for the German annotation group"
```

---

### Task 7: Annotation corpus models and builder

**Files:**
- Create: `src/phentrieve_benchmark/models/annotation_corpus.py`
- Create: `src/phentrieve_benchmark/pipeline/annotation_corpus.py`
- Test: `tests/unit/pipeline/test_annotation_corpus.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/pipeline/test_annotation_corpus.py
import json
from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation_corpus import AnnotationCorpusManifest
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.translation_review import (
    ClinicalChange,
    ClinicalChangeCategory,
    TranslationReviewDecision,
    TranslationReviewImportEntry,
    TranslationReviewImportManifest,
    TranslationReviewRecord,
)
from phentrieve_benchmark.pipeline.annotation_corpus import build_annotation_corpus
from phentrieve_benchmark.provenance.canonical import canonical_jsonl_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationGroupRecord,
)
from phentrieve_benchmark.selection.metrics import LengthStratum, Rational

_TEXTS = {
    "EN1": ("en", "Fever and cough."),
    "EN2": ("en", "No vomiting."),
    "FR1": ("fr", "Fièvre."),
}


def _native(case_id: str) -> Document:
    language, text = _TEXTS[case_id]
    return Document.from_text(
        source_case_id=case_id,
        case_group_id=f"e3c:v2.0.0:{case_id}",
        document_id=f"e3c:v2.0.0:{language}:{case_id}:native",
        language=language,
        translation_status=TranslationStatus.NATIVE,
        text=text,
    )


def _groups(german: set[str]) -> AnnotationGroupManifest:
    records = tuple(
        AnnotationGroupRecord(
            source_case_id=case_id,
            source_language=language,  # type: ignore[arg-type]
            annotation_language="de" if case_id in german else language,  # type: ignore[arg-type]
            document_sha256=_native(case_id).document_sha256,
            length_stratum=LengthStratum.SHORT,
            total_annotation_density=Rational.from_fraction(Fraction(1)),
        )
        for case_id, (language, _) in sorted(_TEXTS.items())
    )
    return AnnotationGroupManifest(
        inventory_sha256="a" * 64, records=records, aggregate_sha256="b" * 64
    )


def _store_native(store: ArtifactStore) -> str:
    return store.put_bytes(
        canonical_jsonl_bytes(
            [_native(case_id).model_dump(mode="json") for case_id in _TEXTS],
            identity_key="document_id",
        )
    )


def _review(
    store: ArtifactStore,
    case_id: str,
    *,
    decision: TranslationReviewDecision,
    proposed: str,
) -> str:
    native = _native(case_id)
    tllm_sha = store.put_bytes(b"Fieber und Husten (TLLM).")
    proposed_sha = store.put_bytes(proposed.encode())
    changed = decision is not TranslationReviewDecision.ACCEPTED_UNCHANGED
    clinical = decision in {
        TranslationReviewDecision.QUESTION,
        TranslationReviewDecision.REJECTED,
    }
    record = TranslationReviewRecord(
        export_sha256="c" * 64,
        source_case_id=case_id,
        source_language=native.language,  # type: ignore[arg-type]
        target_language="de",
        source_text_sha256=native.document_sha256,
        tllm_text_sha256=tllm_sha if changed else proposed_sha,
        proposed_text_sha256=proposed_sha,
        reviewer_id="reviewer-1",
        reviewer_qualification="physician",
        reviewed_languages="en,de",
        review_date=date(2026, 10, 6),
        review_policy_id="e3c:translation-review/v1",
        decision=decision,
        clinical_change=ClinicalChange.PRESENT if clinical else ClinicalChange.NONE,
        clinical_change_category=(
            ClinicalChangeCategory.TERMINOLOGY if clinical else None
        ),
        clinical_change_rationale="Begriff falsch." if clinical else None,
    )
    record_sha = store.put_bytes(record.canonical_bytes())
    manifest = TranslationReviewImportManifest(
        export_sha256="c" * 64,
        entries=(
            TranslationReviewImportEntry(
                source_case_id=case_id,
                record_sha256=record_sha,
                review_record_sha256="d" * 64,
                proposed_text_sha256=proposed_sha,
                diff_sha256="e" * 64,
            ),
        ),
    )
    return store.put_bytes(manifest.canonical_bytes())


def _load(store: ArtifactStore, digest: str) -> AnnotationCorpusManifest:
    return AnnotationCorpusManifest.model_validate_json(
        store.read_bytes(digest), strict=True
    )


def _documents(
    store: ArtifactStore, manifest: AnnotationCorpusManifest
) -> dict[str, Document]:
    return {
        document.source_case_id: document
        for document in (
            Document.model_validate_json(line, strict=True)
            for line in store.read_bytes(manifest.documents_sha256).splitlines()
            if line
        )
    }


def test_original_groups_use_native_documents(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    digest = build_annotation_corpus(
        store=store,
        groups=_groups(german=set()),
        native_documents_sha256=_store_native(store),
        review_import_sha256s=(),
    )
    manifest = _load(store, digest)
    documents = _documents(store, manifest)
    assert set(documents) == {"EN1", "EN2", "FR1"}
    assert documents["FR1"] == _native("FR1")
    assert manifest.pending_review == ()


def test_german_report_without_accepted_review_is_pending(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    rejected = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.REJECTED,
        proposed="Fieber und Husten (TLLM).",
    )
    digest = build_annotation_corpus(
        store=store,
        groups=_groups(german={"EN1"}),
        native_documents_sha256=_store_native(store),
        review_import_sha256s=(rejected,),
    )
    manifest = _load(store, digest)
    assert manifest.pending_review == ("EN1",)
    assert "EN1" not in _documents(store, manifest)


def test_german_report_uses_the_accepted_reviewed_text(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    accepted = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.ACCEPTED_CORRECTED,
        proposed="Fieber und Husten.",
    )
    digest = build_annotation_corpus(
        store=store,
        groups=_groups(german={"EN1"}),
        native_documents_sha256=_store_native(store),
        review_import_sha256s=(accepted,),
    )
    manifest = _load(store, digest)
    document = _documents(store, manifest)["EN1"]
    assert document.text == "Fieber und Husten."
    assert document.language == "de"
    assert document.translation_status is TranslationStatus.TRANSLATED
    assert document.document_id == "e3c:v2.0.0:de:EN1:translated"
    assert document.case_group_id == "e3c:v2.0.0:EN1"
    entry = next(e for e in manifest.entries if e.source_case_id == "EN1")
    assert entry.review_import_sha256 == accepted
    assert entry.document_sha256 == sha256_bytes(b"Fieber und Husten.")


def test_case_accepted_in_two_imports_is_rejected(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    first = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.ACCEPTED_CORRECTED,
        proposed="Fieber und Husten.",
    )
    second = _review(
        store,
        "EN1",
        decision=TranslationReviewDecision.ACCEPTED_CORRECTED,
        proposed="Fieber, Husten.",
    )
    with pytest.raises(ValueError, match="more than one review import"):
        build_annotation_corpus(
            store=store,
            groups=_groups(german={"EN1"}),
            native_documents_sha256=_store_native(store),
            review_import_sha256s=(first, second),
        )


def test_group_manifest_must_match_native_documents(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    groups = _groups(german=set())
    payload = groups.model_dump(mode="json")
    payload["records"][0]["document_sha256"] = "f" * 64
    tampered = AnnotationGroupManifest.model_validate_json(
        json.dumps(payload), strict=True
    )
    with pytest.raises(ValueError, match="does not match the group manifest"):
        build_annotation_corpus(
            store=store,
            groups=tampered,
            native_documents_sha256=_store_native(store),
            review_import_sha256s=(),
        )


def test_corpus_is_deterministic(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    native = _store_native(store)
    first = build_annotation_corpus(
        store=store,
        groups=_groups(german=set()),
        native_documents_sha256=native,
        review_import_sha256s=(),
    )
    second = build_annotation_corpus(
        store=store,
        groups=_groups(german=set()),
        native_documents_sha256=native,
        review_import_sha256s=(),
    )
    assert first == second
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/unit/pipeline/test_annotation_corpus.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phentrieve_benchmark.models.annotation_corpus'`.

- [ ] **Step 3: Implement the models**

```python
# src/phentrieve_benchmark/models/annotation_corpus.py
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class AnnotationCorpusEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_case_id: str = Field(min_length=1)
    annotation_language: Literal["de", "en", "fr", "es"]
    document_id: str = Field(min_length=1)
    document_sha256: Sha256Hex
    review_import_sha256: Sha256Hex | None = None
    review_record_sha256: Sha256Hex | None = None

    @model_validator(mode="after")
    def german_entries_cite_their_review(self) -> Self:
        cites_review = (
            self.review_import_sha256 is not None
            and self.review_record_sha256 is not None
        )
        no_review = (
            self.review_import_sha256 is None and self.review_record_sha256 is None
        )
        if self.annotation_language == "de" and not cites_review:
            raise ValueError("German corpus entries must cite their review")
        if self.annotation_language != "de" and not no_review:
            raise ValueError("original-language entries have no translation review")
        return self


class AnnotationCorpusManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-annotation-corpus/v1"] = "e3c-annotation-corpus/v1"
    groups_sha256: Sha256Hex
    native_documents_sha256: Sha256Hex
    documents_sha256: Sha256Hex
    entries: tuple[AnnotationCorpusEntry, ...]
    pending_review: tuple[str, ...] = ()

    @field_validator("entries")
    @classmethod
    def sort_entries(
        cls, entries: tuple[AnnotationCorpusEntry, ...]
    ) -> tuple[AnnotationCorpusEntry, ...]:
        return tuple(sorted(entries, key=lambda entry: entry.source_case_id))

    @field_validator("pending_review")
    @classmethod
    def sort_pending(cls, pending: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(pending))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())
```

- [ ] **Step 4: Implement the builder**

```python
# src/phentrieve_benchmark/pipeline/annotation_corpus.py
"""Build the annotation corpus: every E3C report in its annotation language.

Original-language reports reuse the verified native documents. German
reports use only text from an accepted translation review; reports without
one are listed as pending and left out.
"""

from collections.abc import Sequence

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation_corpus import (
    AnnotationCorpusEntry,
    AnnotationCorpusManifest,
)
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.translation_review import (
    TranslationReviewDecision,
    TranslationReviewImportManifest,
    TranslationReviewRecord,
)
from phentrieve_benchmark.provenance.canonical import canonical_jsonl_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import AnnotationGroupManifest

_ACCEPTED = {
    TranslationReviewDecision.ACCEPTED_UNCHANGED,
    TranslationReviewDecision.ACCEPTED_CORRECTED,
}


def _read_documents(store: ArtifactStore, digest: str) -> dict[str, Document]:
    documents = (
        Document.model_validate_json(line, strict=True)
        for line in store.read_bytes(digest).splitlines()
        if line
    )
    return {document.source_case_id: document for document in documents}


def _accepted_reviews(
    store: ArtifactStore, review_import_sha256s: Sequence[str]
) -> dict[str, tuple[str, str, TranslationReviewRecord]]:
    accepted: dict[str, tuple[str, str, TranslationReviewRecord]] = {}
    for import_sha256 in review_import_sha256s:
        manifest = TranslationReviewImportManifest.model_validate_json(
            store.read_bytes(import_sha256), strict=True
        )
        for entry in manifest.entries:
            record = TranslationReviewRecord.model_validate_json(
                store.read_bytes(entry.record_sha256), strict=True
            )
            if record.decision not in _ACCEPTED:
                continue
            if entry.source_case_id in accepted:
                raise ValueError(
                    f"case {entry.source_case_id} is accepted in more than one "
                    "review import"
                )
            accepted[entry.source_case_id] = (
                import_sha256,
                entry.record_sha256,
                record,
            )
    return accepted


def _german_document(
    store: ArtifactStore, source: Document, record: TranslationReviewRecord
) -> Document:
    if record.source_text_sha256 != source.document_sha256:
        raise ValueError(
            f"review for {source.source_case_id} does not match the native source text"
        )
    version_prefix = source.case_group_id.rsplit(":", 1)[0]
    return Document.from_text(
        source_case_id=source.source_case_id,
        case_group_id=source.case_group_id,
        document_id=f"{version_prefix}:de:{source.source_case_id}:translated",
        language="de",
        translation_status=TranslationStatus.TRANSLATED,
        text=store.read_bytes(record.proposed_text_sha256).decode("utf-8"),
    )


def build_annotation_corpus(
    *,
    store: ArtifactStore,
    groups: AnnotationGroupManifest,
    native_documents_sha256: str,
    review_import_sha256s: Sequence[str],
) -> str:
    """Store the corpus documents and manifest; return the manifest hash."""
    native = _read_documents(store, native_documents_sha256)
    reviews = _accepted_reviews(store, review_import_sha256s)
    documents: list[Document] = []
    entries: list[AnnotationCorpusEntry] = []
    pending: list[str] = []
    for group_record in groups.records:
        case_id = group_record.source_case_id
        source = native.get(case_id)
        if source is None:
            raise ValueError(f"native document for {case_id} is missing")
        if source.document_sha256 != group_record.document_sha256:
            raise ValueError(
                f"native document for {case_id} does not match the group manifest"
            )
        if group_record.annotation_language != "de":
            documents.append(source)
            entries.append(
                AnnotationCorpusEntry(
                    source_case_id=case_id,
                    annotation_language=group_record.annotation_language,
                    document_id=source.document_id,
                    document_sha256=source.document_sha256,
                )
            )
            continue
        review = reviews.get(case_id)
        if review is None:
            pending.append(case_id)
            continue
        import_sha256, record_sha256, record = review
        document = _german_document(store, source, record)
        documents.append(document)
        entries.append(
            AnnotationCorpusEntry(
                source_case_id=case_id,
                annotation_language="de",
                document_id=document.document_id,
                document_sha256=document.document_sha256,
                review_import_sha256=import_sha256,
                review_record_sha256=record_sha256,
            )
        )
    documents_sha256 = store.put_bytes(
        canonical_jsonl_bytes(
            [document.model_dump(mode="json") for document in documents],
            identity_key="document_id",
        )
    )
    manifest = AnnotationCorpusManifest(
        groups_sha256=sha256_bytes(groups.canonical_bytes()),
        native_documents_sha256=native_documents_sha256,
        documents_sha256=documents_sha256,
        entries=tuple(entries),
        pending_review=tuple(pending),
    )
    return store.put_bytes(manifest.canonical_bytes())
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/pipeline/test_annotation_corpus.py -v`
Expected: 6 passed.

- [ ] **Step 6: Lint and type check**

Run: `uv run ruff check . && uv run mypy`
Expected: no errors. Remove any `type: ignore` that mypy reports as unused.

- [ ] **Step 7: Commit**

```bash
git add src/phentrieve_benchmark/models/annotation_corpus.py src/phentrieve_benchmark/pipeline/annotation_corpus.py tests/unit/pipeline/test_annotation_corpus.py
git commit -m "feat: build annotation corpus from native and reviewed German texts"
```

---

### Task 8: Command `build-corpus e3c`

**Files:**
- Modify: `src/phentrieve_benchmark/pipeline/prepare.py:422-454`
- Modify: `src/phentrieve_benchmark/cli.py`

- [ ] **Step 1: Extract the verified-normalization lookup**

In `src/phentrieve_benchmark/pipeline/prepare.py`, add above `select_e3c`:

```python
def verified_e3c_normalization(
    context: PipelineContext,
) -> tuple[StagePointer, NormalizationManifest]:
    """Return the verified E3C normalization for the current code identity."""
    source_recipe = load_source_recipe(
        _source_recipe_path("e3c", context.dataset_root)
    )
    target_recipe = _load_target_config("e3c", context.dataset_root)
    state = StageState(context.artifact_root / "state", context.store)
    source_pointer = state.reuse(
        stage="acquire",
        target="e3c",
        semantic_hashes={
            "recipe_sha256": source_recipe.sha256,
            "code_sha256": context.code_sha256,
        },
    )
    if source_pointer is None:
        raise ValueError("missing verified E3C acquisition")
    normalization_pointer = state.reuse(
        stage="normalize",
        target="e3c",
        semantic_hashes={
            "recipe_sha256": target_recipe.sha256,
            "source_snapshot_sha256": source_pointer.subject_sha256,
            "code_sha256": context.code_sha256,
        },
    )
    if normalization_pointer is None:
        raise ValueError("missing verified E3C normalization")
    normalization = NormalizationManifest.model_validate_json(
        context.store.read_bytes(normalization_pointer.subject_sha256),
        strict=True,
    )
    return normalization_pointer, normalization
```

Replace lines 425–454 of `select_e3c` (from `source_recipe = ...` through `normalization = NormalizationManifest...`) with:

```python
    target_recipe = _load_target_config("e3c", context.dataset_root)
    state = StageState(context.artifact_root / "state", context.store)
    normalization_pointer, normalization = verified_e3c_normalization(context)
```

If `StagePointer` is not yet imported in `prepare.py`, import it from `phentrieve_benchmark.pipeline.state`.

- [ ] **Step 2: Verify the refactor**

Run: `uv run pytest tests/integration tests/unit/test_cli_pipeline.py -v`
Expected: all pass (behaviour unchanged).

- [ ] **Step 3: Add the command**

In `src/phentrieve_benchmark/cli.py`, add imports:

```python
from phentrieve_benchmark.models.annotation_corpus import AnnotationCorpusManifest
from phentrieve_benchmark.pipeline.annotation_corpus import build_annotation_corpus
from phentrieve_benchmark.pipeline.prepare import verified_e3c_normalization
```

(merge the last one into the existing `pipeline.prepare` import), register the sub-app next to the others:

```python
build_corpus_app = typer.Typer(no_args_is_help=True)
app.add_typer(build_corpus_app, name="build-corpus")
```

and add:

```python
@build_corpus_app.command("e3c")
def build_e3c_corpus_command(
    review_import: Annotated[
        list[str] | None, typer.Option("--review-import")
    ] = None,
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    """Build the annotation corpus from the tracked group manifest."""
    context = _pipeline_context(dataset_root, artifact_root)
    _, normalization = verified_e3c_normalization(context)
    groups = AnnotationGroupManifest.model_validate_json(
        (context.dataset_root / _E3C_GROUPS).read_bytes(), strict=True
    )
    if groups.inventory_sha256 != normalization.inventory.sha256:
        raise typer.BadParameter(
            "group manifest was built from a different inventory",
            param_hint="--dataset-root",
        )
    corpus_sha256 = build_annotation_corpus(
        store=context.store,
        groups=groups,
        native_documents_sha256=normalization.documents.sha256,
        review_import_sha256s=tuple(review_import or ()),
    )
    manifest = AnnotationCorpusManifest.model_validate_json(
        context.store.read_bytes(corpus_sha256), strict=True
    )
    summary = _group_summary(
        entry.annotation_language for entry in manifest.entries
    )
    typer.echo(
        f"corpus_sha256={corpus_sha256} {summary} "
        f"pending_review={len(manifest.pending_review)}"
    )
```

`normalization.inventory` is optional in the model; if mypy flags it, guard with `if normalization.inventory is None: raise typer.BadParameter("E3C normalization has no inventory")`.

- [ ] **Step 4: Lint, types, full suite**

Run: `uv run ruff check . && uv run mypy && uv run pytest -q`
Expected: all clean and passing.

- [ ] **Step 5: Commit**

```bash
git add src/phentrieve_benchmark/pipeline/prepare.py src/phentrieve_benchmark/cli.py
git commit -m "feat: add build-corpus command for E3C"
```

---

### Task 9: Real-data run and documentation

**Files:**
- Modify: `docs/project-checklist.md`
- Modify: `datasets/e3c-de/README.md`

- [ ] **Step 1: Refresh the verified local stages (no paid calls)**

Verified pointers are bound to the code hash, so they must be republished after the code commits:

```bash
uv run phentrieve-benchmark acquire e3c
uv run phentrieve-benchmark normalize e3c
```

Expected: each prints one `stage=... subject_sha256=...` line.

- [ ] **Step 2: Build the corpus without reviews**

Run: `uv run phentrieve-benchmark build-corpus e3c`
Expected: `corpus_sha256=<hash> de=0 en=63 fr=61 es=61 pending_review=61` (exact numbers follow the tracked group manifest; `de` is 0 and `pending_review` equals the German group size).

- [ ] **Step 3: Export the German review workbook**

Run:

```bash
uv run phentrieve-benchmark review-workbook export-e3c \
  .artifacts/review-workbooks/e3c-de-group-translation-review.xlsx \
  --variant tllm-full \
  --groups datasets/e3c-de/selections/e3c-annotation-groups-v1.json
```

Expected: `export_sha256=<hash> cases=<German group size>`. Open the workbook once to confirm the rows are the German group.

- [ ] **Step 4: Document**

In `datasets/e3c-de/README.md`, add after the UMLS mapping paragraph:

```markdown
All 246 reports are split into four annotation groups (German, English,
French, Spanish) by `uv run phentrieve-benchmark select e3c-groups`; the
tracked, text-free result is `selections/e3c-annotation-groups-v1.json`.
`uv run phentrieve-benchmark build-corpus e3c [--review-import SHA ...]`
builds the annotation corpus: original-language reports as native
documents, German reports only from accepted translation reviews. German
reports without one are listed as pending. The translation review for the
German group is exported with
`review-workbook export-e3c --variant tllm-full --groups selections/e3c-annotation-groups-v1.json`.
```

In `docs/project-checklist.md`, tick the split item and the workbook export retarget item, and tick the Phase 0 cleanup item (`make_annotation_review.py` deleted, README updated).

- [ ] **Step 5: Verify and commit**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all pass.

```bash
git add datasets/e3c-de/README.md docs/project-checklist.md
git commit -m "docs: record annotation groups and corpus build"
```

---

## Self-Review Notes

- Spec §4 (cleanup) → Tasks 2, 3. §5.1 (split) → Tasks 4, 5. §5.2 (corpus, reviewed-only German text, pending list) → Tasks 7, 8. §5.3 (review retarget) → Task 6, run in Task 9. §7 coverage exclusion → Task 3.
- Local `.artifacts` cleanup is intentionally deferred to after Phase 3 (spec §4).
- Names used across tasks: `assign_annotation_groups`, `load_e3c_inventory`, `AnnotationGroupManifest.case_ids`, `build_annotation_corpus`, `AnnotationCorpusManifest`, `verified_e3c_normalization`, `_E3C_GROUPS`.

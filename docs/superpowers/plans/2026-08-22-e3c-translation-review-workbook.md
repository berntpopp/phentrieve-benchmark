# E3C Translation Review Workbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export the 30-case E3C TLLM snapshot to a safe two-sheet Excel review workbook and import completed workbooks into immutable, canonical review artifacts.

**Architecture:** Focused Pydantic models define export, review-record, diff, and import manifests. A workbook module owns the Excel profile and parsing; a pipeline module resolves translation artifacts, validates all rows, stores content-addressed objects, and publishes the import manifest last. Thin Typer commands expose export and import without making Excel canonical.

**Tech Stack:** Python 3.11+, Pydantic 2, openpyxl 3.1, Typer, pytest, existing canonical JSON/text and `ArtifactStore` utilities.

**Spec:** `docs/superpowers/specs/2026-08-22-e3c-translation-review-workbook-design.md`

## Global Constraints

- Workbook sheets are exactly `Anleitung` and `Review`.
- TLLM is primary; `NMT-Vergleich` exists only for an export manifest that includes NMT.
- Workbook cells are an editing interface; canonical JSON and UTF-8 artifacts are authoritative.
- Normalize reviewed text with existing `canonical_text_bytes`; never trim implicitly.
- Validate the entire workbook before publishing the import manifest.
- Preserve all source, TLLM, and NMT artifact bytes.
- HPO review remains out of scope.
- Do not add macros, formulas, external links, or a third sheet.

---

### Task 1: Canonical translation-review models

**Files:**
- Create: `src/phentrieve_benchmark/models/translation_review.py`
- Create: `tests/unit/models/test_translation_review.py`

**Interfaces:**
- Produces: `TranslationReviewExport`, `TranslationReviewExportCase`, `TranslationReviewRecord`, `TranslationReviewDiff`, `TranslationReviewImportEntry`, and `TranslationReviewImportManifest`.
- Produces: `TranslationReviewDecision`, `ClinicalChange`, and `ClinicalChangeCategory` enums.
- Produces: `TranslationReviewRecord.review_record() -> ReviewRecord`.
- Consumes: existing `ReviewRecord`, `canonical_json_bytes`, `canonical_text_bytes`, and SHA-256 types.

- [ ] **Step 1: Write failing model tests**

Create tests that instantiate one accepted-unchanged row and assert canonical identity and generic-gate mapping:

```python
def test_translation_review_record_has_deterministic_gate_projection() -> None:
    record = _record(
        decision=TranslationReviewDecision.ACCEPTED_UNCHANGED,
        proposed_text_sha256="3" * 64,
        clinical_change=ClinicalChange.NONE,
    )

    assert record.sha256() == sha256_bytes(record.canonical_bytes())
    gate = record.review_record()
    assert gate.review_id == f"translation-review:{record.sha256()}"
    assert gate.review_kind is ReviewKind.BILINGUAL
    assert gate.subject_sha256 == "3" * 64
    assert gate.manual_requirement is ManualReviewRequirement.REQUIRED
    assert gate.manual_status is ManualReviewStatus.ACCEPTED
```

Add parametrized tests for all five allowed decision-table rows and rejected constructions for every other combination. Test unique case IDs and ordered import entries.

- [ ] **Step 2: Run the tests and verify failure**

Run:

```powershell
uv run pytest tests/unit/models/test_translation_review.py -q
```

Expected: collection fails because `translation_review` does not exist.

- [ ] **Step 3: Implement enums and strict frozen models**

Implement these controlled values exactly:

```python
class TranslationReviewDecision(StrEnum):
    ACCEPTED_UNCHANGED = "unverändert akzeptiert"
    ACCEPTED_CORRECTED = "korrigiert akzeptiert"
    QUESTION = "Rückfrage"
    REJECTED = "abgelehnt"


class ClinicalChange(StrEnum):
    NONE = "keine"
    PRESENT = "vorhanden"


class ClinicalChangeCategory(StrEnum):
    OMISSION = "Auslassung"
    ADDITION = "Hinzufügung"
    ASSERTION = "Negation oder Aussagesicherheit"
    VALUE = "Zahl oder Einheit"
    ANATOMY = "Anatomie oder Lateralität"
    TERMINOLOGY = "Terminologie"
    SOURCE = "Quellproblem"
```

Use schema versions `translation-review-export/v1`, `translation-review-record/v1`, `unified-text-diff/v1`, and `translation-review-import/v1`. Every model is `extra="forbid"`, frozen, and strict. Implement `canonical_bytes()` and `sha256()` using existing provenance utilities.

The record validator enforces the spec decision table. Its `review_record()` maps both accepted decisions to `accepted`, question to `changes_requested`, and rejected to `rejected`; it uses `review_kind=bilingual`, `manual_requirement=required`, and `review_id=f"translation-review:{self.sha256()}"`.

- [ ] **Step 4: Run model tests**

Run:

```powershell
uv run pytest tests/unit/models/test_translation_review.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit canonical models**

```powershell
git add -- src/phentrieve_benchmark/models/translation_review.py tests/unit/models/test_translation_review.py
git commit -m "feat: define E3C translation review artifacts"
```

---

### Task 2: Deterministic text diffs and workbook profile

**Files:**
- Create: `src/phentrieve_benchmark/review/translation_text.py`
- Create: `src/phentrieve_benchmark/review/translation_workbook.py`
- Create: `tests/unit/review/test_translation_text.py`
- Create: `tests/unit/review/test_translation_workbook.py`

**Interfaces:**
- Consumes: Task 1 models.
- Produces: `unified_text_diff(tllm: str, reviewed: str) -> TranslationReviewDiff`.
- Produces: `WorkbookCase` dataclass with case ID, language, source text, TLLM text, and optional NMT text.
- Produces: `write_review_workbook(destination: Path, export: TranslationReviewExport, cases: tuple[WorkbookCase, ...]) -> None`.
- Produces: `read_review_workbook(source: Path) -> ParsedReviewWorkbook` with metadata and parsed row values only; canonical validation remains in Task 3.

- [ ] **Step 1: Write failing canonical-diff tests**

Cover NFC equivalence, CRLF-to-LF conversion, no trimming, fixed labels, and no timestamps:

```python
def test_unified_diff_normalizes_newlines_and_unicode() -> None:
    result = unified_text_diff("Cafe\u0301\r\n", "Café\nBefund\n")
    assert result.payload == (
        "--- tllm\n"
        "+++ reviewed\n"
        "@@ -1 +1,2 @@\n"
        " Café\n"
        "+Befund\n"
    )
```

- [ ] **Step 2: Run canonical-diff test and verify failure**

Run:

```powershell
uv run pytest tests/unit/review/test_translation_text.py -q
```

Expected: import failure for the missing module.

- [ ] **Step 3: Implement `unified_text_diff`**

Decode `canonical_text_bytes` back to text, call `difflib.unified_diff` with `fromfile="tllm"`, `tofile="reviewed"`, `n=3`, and `lineterm="\n"`, then store the joined payload in `TranslationReviewDiff`.

- [ ] **Step 4: Write failing workbook writer/reader tests**

Create a two-case export fixture and assert:

```python
workbook = load_workbook(output)
assert workbook.sheetnames == ["Anleitung", "Review"]
review = workbook["Review"]
assert review.freeze_panes == "A2"
assert [cell.value for cell in review[1]] == EXPECTED_HEADERS
assert review["E2"].value == "TLLM eins"
assert review["A2"].protection.locked is True
assert review["E2"].protection.locked is False
assert review.protection.sheet is True
```

Test the optional NMT header both absent and present, all controlled validation lists, selectable locked cells, text date format, wrapped/top-aligned text, and rejection before export when any cell exceeds 32,767 UTF-16 code units.

- [ ] **Step 5: Run workbook tests and verify failure**

Run:

```powershell
uv run pytest tests/unit/review/test_translation_workbook.py -q
```

Expected: import failure for the missing workbook module.

- [ ] **Step 6: Implement the two-sheet workbook writer**

Use openpyxl only. Put read-only export metadata and unlocked reviewer fields in fixed cells on `Anleitung`. Write the exact German headers from the spec on `Review`, prefill final text from TLLM, add list validations, protect immutable cells, enable filtering and locked-cell selection, and save through a same-directory temporary `.xlsx` followed by `os.replace`.

- [ ] **Step 7: Implement the workbook parser**

Require `.xlsx`, exactly two sheets, exact headers for the manifest profile, string metadata, and string row values. Load once with `data_only=False`, reject any cell whose `data_type == "f"`, and inspect the ZIP relationship/content-type names to reject VBA or external-link parts. Return parsed values without publishing artifacts.

- [ ] **Step 8: Run workbook and diff tests**

Run:

```powershell
uv run pytest tests/unit/review/test_translation_text.py tests/unit/review/test_translation_workbook.py -q
```

Expected: all tests pass.

- [ ] **Step 9: Commit workbook mechanics**

```powershell
git add -- src/phentrieve_benchmark/review/translation_text.py src/phentrieve_benchmark/review/translation_workbook.py tests/unit/review/test_translation_text.py tests/unit/review/test_translation_workbook.py
git commit -m "feat: add E3C translation review workbook profile"
```

---

### Task 3: Export service bound to published translation artifacts

**Files:**
- Create: `src/phentrieve_benchmark/pipeline/translation_review.py`
- Create: `tests/unit/pipeline/test_translation_review_export.py`

**Interfaces:**
- Consumes: Task 1 models, Task 2 workbook writer, `ArtifactStore`, and published TLLM/NMT `TranslationManifest` values.
- Produces: `export_translation_review(*, store: ArtifactStore, tllm_manifest: TranslationManifest, destination: Path, review_policy_id: str, nmt_manifest: TranslationManifest | None = None) -> str`, returning export-manifest SHA-256.

- [ ] **Step 1: Write failing export-service tests**

Build two translation manifests in an `ArtifactStore`. Assert that the export manifest orders cases by `(source_language, source_case_id)`, binds full source/TLLM hashes, includes NMT only when requested, and that the workbook cell text exactly matches store bytes.

Add failures for mismatched selection IDs, case sets, source hashes, and source languages across TLLM/NMT.

- [ ] **Step 2: Run export-service tests and verify failure**

Run:

```powershell
uv run pytest tests/unit/pipeline/test_translation_review_export.py -q
```

Expected: import failure for the missing service.

- [ ] **Step 3: Implement export resolution and manifest storage**

Resolve every referenced artifact through `store.read_bytes`, decode strict UTF-8, construct `TranslationReviewExport`, store its canonical bytes, and pass the resulting export ID plus workbook cases to `write_review_workbook`. Do not copy hashes from workbook input.

- [ ] **Step 4: Run export-service tests**

Run:

```powershell
uv run pytest tests/unit/pipeline/test_translation_review_export.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit export service**

```powershell
git add -- src/phentrieve_benchmark/pipeline/translation_review.py tests/unit/pipeline/test_translation_review_export.py
git commit -m "feat: export E3C translation review workbooks"
```

---

### Task 4: Transactional workbook import

**Files:**
- Modify: `src/phentrieve_benchmark/pipeline/translation_review.py`
- Create: `tests/unit/pipeline/test_translation_review_import.py`

**Interfaces:**
- Consumes: `read_review_workbook`, Task 1 models, `unified_text_diff`, and authoritative export manifests in `ArtifactStore`.
- Produces: `import_translation_review(*, store: ArtifactStore, workbook_path: Path) -> str`, returning the import-manifest SHA-256.

- [ ] **Step 1: Write failing happy-path import test**

Export a two-case workbook, fill reviewer metadata, leave one case unchanged, correct the other, and assert:

```python
manifest_sha256 = import_translation_review(
    store=store,
    workbook_path=workbook_path,
)
manifest = TranslationReviewImportManifest.model_validate_json(
    store.read_bytes(manifest_sha256), strict=True
)
assert [entry.source_case_id for entry in manifest.entries] == ["EN1", "FR1"]
assert store.read_bytes(manifest.entries[1].proposed_text_sha256) == (
    "Korrigierter Text\n".encode()
)
```

Assert a second import returns the same manifest SHA-256.

- [ ] **Step 2: Run happy-path test and verify failure**

Run:

```powershell
uv run pytest tests/unit/pipeline/test_translation_review_import.py::test_import_publishes_canonical_review_manifest -q
```

Expected: failure because the import function is missing.

- [ ] **Step 3: Implement full prevalidation**

Resolve the export ID from the store; compare immutable cells to canonical source/TLLM/NMT text; require NMT column presence iff the manifest includes NMT; validate exact case set, reviewer metadata, text lengths, and every decision-table combination. Collect all validation errors as `WorkbookValidationError` items containing sheet, row, case ID, field, and message. Raise once before any `put_bytes` call.

- [ ] **Step 4: Write failing rejection tests**

Parametrize tampered source/TLLM/NMT, missing/extra/duplicate case, bad date, policy mismatch, empty final text, invalid enum, every forbidden decision combination, extra sheet, formula, macro/external link fixture, and UTF-16 length overflow. Assert no import manifest is returned and error messages identify row and field.

- [ ] **Step 5: Run rejection tests and verify failure**

Run:

```powershell
uv run pytest tests/unit/pipeline/test_translation_review_import.py -q
```

Expected: failures identify unimplemented validation branches.

- [ ] **Step 6: Implement manifest-last publication**

After successful prevalidation, store canonical proposed text, record, generic `ReviewRecord` projection, and diff bytes. Construct ordered entries pairing case IDs and object hashes, then store `TranslationReviewImportManifest.canonical_bytes()` last. Return its hash. No mutable `latest` pointer is created.

- [ ] **Step 7: Add write-failure and semantic-revision tests**

Inject a store that raises on an intermediate `put_bytes`, assert no import-manifest bytes were stored, then retry with the normal store and assert success. Change only workbook formatting and assert identical identity; change reviewer comment and assert a distinct import manifest while the old manifest remains readable.

- [ ] **Step 8: Run all import tests**

Run:

```powershell
uv run pytest tests/unit/pipeline/test_translation_review_import.py -q
```

Expected: all tests pass.

- [ ] **Step 9: Commit import service**

```powershell
git add -- src/phentrieve_benchmark/pipeline/translation_review.py tests/unit/pipeline/test_translation_review_import.py
git commit -m "feat: import E3C translation review workbooks"
```

---

### Task 5: CLI integration and documentation

**Files:**
- Modify: `src/phentrieve_benchmark/cli.py`
- Modify: `tests/unit/test_cli_pipeline.py`
- Create: `tests/contracts/test_translation_review_workbook.py`
- Modify: `datasets/e3c-de/translations/README.md`
- Modify: `docs/project-checklist.md`

**Interfaces:**
- Consumes: Task 3 and Task 4 services.
- Produces: `review-workbook export-e3c OUTPUT.xlsx [--include-nmt]` and `review-workbook import-e3c INPUT.xlsx` CLI commands.

- [ ] **Step 1: Write failing CLI tests**

Add a Typer subgroup and assert export passes resolved TLLM/NMT manifests, destination, and policy ID to the service. Assert import prints only the resulting import-manifest SHA-256 and a concise case/status count. Confirm `--include-nmt` defaults false.

- [ ] **Step 2: Run CLI tests and verify failure**

Run:

```powershell
uv run pytest tests/unit/test_cli_pipeline.py -q
```

Expected: failures because `review-workbook` is unknown.

- [ ] **Step 3: Implement thin CLI commands**

Resolve the existing published TLLM pointer by recipe hash. Resolve NMT only when requested. Call the pipeline services; do not duplicate workbook or validation logic in `cli.py`. Use existing dataset/artifact-root options.

- [ ] **Step 4: Add a repository contract test**

The contract test exports the real tracked 30-case snapshot into a temporary store/workbook fixture, then verifies exactly 30 rows, exactly two sheets, default NMT omission, preserved UTF-8 text, and no modification to tracked snapshot bytes.

- [ ] **Step 5: Update operator documentation**

Document the two commands, the reviewer workflow, TLLM default, optional NMT flag, internal-only boundary, and that canonical import artifacts—not `.xlsx`—feed later stages. Mark the workbook design/implementation items complete in the checklist without marking manual medical review complete.

- [ ] **Step 6: Run focused integration tests**

Run:

```powershell
uv run pytest tests/unit/models/test_translation_review.py tests/unit/review/test_translation_text.py tests/unit/review/test_translation_workbook.py tests/unit/pipeline/test_translation_review_export.py tests/unit/pipeline/test_translation_review_import.py tests/unit/test_cli_pipeline.py tests/contracts/test_translation_review_workbook.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Run quality gates**

Run:

```powershell
uv run ruff check src tests
uv run mypy
uv run pytest -q
```

Expected: ruff and mypy exit zero; the complete test suite passes with only documented platform skips.

- [ ] **Step 8: Commit CLI and documentation**

```powershell
git add -- src/phentrieve_benchmark/cli.py tests/unit/test_cli_pipeline.py tests/contracts/test_translation_review_workbook.py datasets/e3c-de/translations/README.md docs/project-checklist.md
git commit -m "feat: expose E3C translation review workflow"
```

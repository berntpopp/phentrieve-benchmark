# E3C Review Resources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track the selected 30 E3C source reports and the existing NMT and
Translation LLM German outputs as a minimal, case-oriented, explicitly
unreviewed scientific review snapshot.

**Architecture:** Copy exact bytes from the two verified local translation
views into one tracked directory per case. A contract test pins the selection,
layout, text normalization, and complete content digest. Existing licensing
evidence and repository documentation are updated so they accurately describe
the new explicit redistribution boundary.

**Tech Stack:** Python 3.11, pytest, Pydantic, YAML, PowerShell, Git

---

## File Structure

- Create `datasets/e3c-de/review/e3c-de-feasibility-30-v1/README.md`
  as the review snapshot's status, attribution, and usage notice.
- Create 30 case directories below
  `datasets/e3c-de/review/e3c-de-feasibility-30-v1/`, each containing one
  `source.<language>.txt`, one `nmt.de.txt`, and one `tllm.de.txt`.
- Create `tests/contracts/test_e3c_review_resources.py` to pin the exact case
  population, layout, normalization, and snapshot digest.
- Modify `src/phentrieve_benchmark/acquisition/recipes.py` to accept the
  explicit review-snapshot redistribution decision.
- Modify `tests/unit/acquisition/test_recipes.py` to cover the new decision.
- Modify `datasets/e3c-de/license-evidence.yaml` and
  `datasets/e3c-de/dataset.yaml` to record and pin the new decision.
- Modify `README.md`, `datasets/e3c-de/README.md`,
  `datasets/e3c-de/LICENSES.md`, and
  `datasets/e3c-de/translations/README.md` so none claims that all E3C text
  remains local-only.

### Task 1: Permit the Explicit Review-Snapshot License Decision

**Files:**

- Modify: `tests/unit/acquisition/test_recipes.py`
- Modify: `src/phentrieve_benchmark/acquisition/recipes.py:502-515`

- [ ] **Step 1: Add the failing license-evidence test**

Append this test to `tests/unit/acquisition/test_recipes.py`:

```python
def test_license_evidence_accepts_scientific_review_snapshot(
    tmp_path: Path,
) -> None:
    evidence_path = write(
        tmp_path / "license-evidence.yaml",
        f"""
schema_version: license-evidence/v1
source_id: e3c
repository_url: https://github.com/hltfbk/E3C-Corpus
source_commit: {"a" * 40}
license_id: LicenseRef-E3C-CC-BY-NC-version-unspecified
license_url: https://github.com/hltfbk/E3C-Corpus/blob/{"a" * 40}/README.md
access_date: 2026-07-24
upstream_statement: CC BY-NC without a version.
redistribution_decision: noncommercial_scientific_review_snapshot
derivative_work_notes: Selected review texts are redistributed.
unresolved_questions:
  - The CC BY-NC version remains unspecified.
""",
    )

    evidence = load_license_evidence(evidence_path)

    assert (
        evidence.value.redistribution_decision
        == "noncommercial_scientific_review_snapshot"
    )
```

- [ ] **Step 2: Run the focused test and confirm the schema rejects it**

Run:

```powershell
uv run pytest tests/unit/acquisition/test_recipes.py::test_license_evidence_accepts_scientific_review_snapshot -v
```

Expected: FAIL with a Pydantic literal validation error for
`redistribution_decision`.

- [ ] **Step 3: Widen the license-evidence decision literal**

In `LicenseEvidence` in
`src/phentrieve_benchmark/acquisition/recipes.py`, replace the current field
with:

```python
    redistribution_decision: Literal[
        "source_not_redistributed",
        "noncommercial_scientific_review_snapshot",
    ]
```

- [ ] **Step 4: Run the focused unit tests**

Run:

```powershell
uv run pytest tests/unit/acquisition/test_recipes.py -q
```

Expected: all tests in the file PASS.

- [ ] **Step 5: Commit the schema change**

Run:

```powershell
git add -- src/phentrieve_benchmark/acquisition/recipes.py tests/unit/acquisition/test_recipes.py
git commit -m "feat: record scientific review redistribution"
```

Expected: one commit containing only the model and its unit test.

### Task 2: Publish and Pin the Exact 30-Case Text Snapshot

**Files:**

- Create: `tests/contracts/test_e3c_review_resources.py`
- Create:
  `datasets/e3c-de/review/e3c-de-feasibility-30-v1/<case-id>/source.<language>.txt`
- Create:
  `datasets/e3c-de/review/e3c-de-feasibility-30-v1/<case-id>/nmt.de.txt`
- Create:
  `datasets/e3c-de/review/e3c-de-feasibility-30-v1/<case-id>/tllm.de.txt`

- [ ] **Step 1: Add the failing review-resource contract**

Create `tests/contracts/test_e3c_review_resources.py` with:

```python
import json
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
```

- [ ] **Step 2: Run the contract and confirm the package is absent**

Run:

```powershell
uv run pytest tests/contracts/test_e3c_review_resources.py -v
```

Expected: FAIL with `FileNotFoundError` for the missing review directory.

- [ ] **Step 3: Verify and copy the exact local view bytes**

Run this one-time PowerShell materialization from the repository root:

```powershell
$destination = 'datasets\e3c-de\review\e3c-de-feasibility-30-v1'
$nmtRoot = '.artifacts\views\e3c-de-nmt'
$tllmRoot = '.artifacts\views\e3c-de-tllm'

if (Test-Path -LiteralPath $destination) {
    throw "review destination already exists: $destination"
}

$nmtRows = @(Import-Csv (Join-Path $nmtRoot 'index.csv'))
$tllmRows = @{}
Import-Csv (Join-Path $tllmRoot 'index.csv') | ForEach-Object {
    $tllmRows[$_.source_case_id] = $_
}

if ($nmtRows.Count -ne 30 -or $tllmRows.Count -ne 30) {
    throw 'both translation views must contain exactly 30 cases'
}

New-Item -ItemType Directory -Path $destination | Out-Null
foreach ($nmt in $nmtRows) {
    $tllm = $tllmRows[$nmt.source_case_id]
    if ($null -eq $tllm) {
        throw "TLLM view is missing case $($nmt.source_case_id)"
    }
    if ($nmt.source_language -ne $tllm.source_language) {
        throw "source language differs for case $($nmt.source_case_id)"
    }

    $nmtSource = Join-Path $nmtRoot $nmt.source_path
    $tllmSource = Join-Path $tllmRoot $tllm.source_path
    $nmtSourceHash = (Get-FileHash -Algorithm SHA256 $nmtSource).Hash
    $tllmSourceHash = (Get-FileHash -Algorithm SHA256 $tllmSource).Hash
    if ($nmtSourceHash -ne $tllmSourceHash) {
        throw "source bytes differ for case $($nmt.source_case_id)"
    }

    $caseDirectory = Join-Path $destination $nmt.source_case_id
    New-Item -ItemType Directory -Path $caseDirectory | Out-Null
    Copy-Item -LiteralPath $nmtSource -Destination (
        Join-Path $caseDirectory "source.$($nmt.source_language).txt"
    )
    Copy-Item -LiteralPath (
        Join-Path $nmtRoot $nmt.translation_path
    ) -Destination (Join-Path $caseDirectory 'nmt.de.txt')
    Copy-Item -LiteralPath (
        Join-Path $tllmRoot $tllm.translation_path
    ) -Destination (Join-Path $caseDirectory 'tllm.de.txt')
}
```

Expected: 30 case directories and 90 text files are created. No source or
translation bytes are transformed.

- [ ] **Step 4: Run the contract and confirm the pinned snapshot**

Run:

```powershell
uv run pytest tests/contracts/test_e3c_review_resources.py -v
```

Expected: `test_review_snapshot_contains_exact_selected_texts` PASS.

- [ ] **Step 5: Stage the snapshot and run the index-based safety scan**

Run:

```powershell
git add -- datasets/e3c-de/review tests/contracts/test_e3c_review_resources.py
uv run python scripts/check_repository_safety.py
```

Expected: `repository safety check passed`.

- [ ] **Step 6: Commit the immutable review texts**

Run:

```powershell
git commit -m "data: publish unreviewed E3C translation snapshot"
```

Expected: one commit containing the 90 text files and their contract test.

### Task 3: Add Review Notices and Align Licensing Documentation

**Files:**

- Modify: `tests/contracts/test_e3c_review_resources.py`
- Create:
  `datasets/e3c-de/review/e3c-de-feasibility-30-v1/README.md`
- Modify: `datasets/e3c-de/license-evidence.yaml`
- Modify: `datasets/e3c-de/dataset.yaml:123`
- Modify: `README.md`
- Modify: `datasets/e3c-de/README.md`
- Modify: `datasets/e3c-de/LICENSES.md`
- Modify: `datasets/e3c-de/translations/README.md`

- [ ] **Step 1: Add the failing root-layout and notice contract**

Append this test to `tests/contracts/test_e3c_review_resources.py`:

```python
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
        "`<variant>.de.txt`",
    ):
        assert required in notice
```

- [ ] **Step 2: Run the notice contract and confirm it fails**

Run:

```powershell
uv run pytest tests/contracts/test_e3c_review_resources.py::test_review_snapshot_has_required_notice_and_no_extra_entries -v
```

Expected: FAIL because `README.md` is absent.

- [ ] **Step 3: Add the review-package README**

Create
`datasets/e3c-de/review/e3c-de-feasibility-30-v1/README.md` with:

```markdown
# E3C German translation review snapshot

This directory contains the 30 cases selected by
`e3c-de-feasibility-30-v1`. It makes the source reports and two unreviewed
machine translations directly available for non-commercial scientific review.

Each case directory contains:

- `source.<language>.txt`: the canonical E3C source report;
- `nmt.de.txt`: the German Google `general/nmt` output;
- `tllm.de.txt`: the German Google `general/translation-llm` output.

The general translation filename is `<variant>.de.txt`, so later variants can
be added without changing the case-oriented layout.

All translations are unreviewed machine translations. Automatic checks do not
establish clinical correctness: each current variant has 25 records marked
`ready_for_review` and 5 marked `automatic_check_failed`. Both statuses still
require bilingual or fachsprachliche review. These texts must not be used for
clinical decisions.

The source is the E3C Corpus at commit
`f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc`. Its upstream README declares
CC BY-NC without identifying a license version. This review snapshot follows
the project's documented working assumption that attributed, non-commercial
scientific review is permitted. Preserve the E3C attribution when sharing or
discussing these materials.

The files preserve the original machine outputs. Corrections, preferences, and
accepted benchmark texts will be recorded separately rather than overwriting
this snapshot.
```

- [ ] **Step 4: Update the machine-readable licensing decision**

Replace `datasets/e3c-de/license-evidence.yaml` with:

```yaml
schema_version: license-evidence/v1
source_id: e3c
repository_url: https://github.com/hltfbk/E3C-Corpus
source_commit: f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc
license_id: LicenseRef-E3C-CC-BY-NC-version-unspecified
license_url: https://github.com/hltfbk/E3C-Corpus/blob/f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc/README.md
access_date: 2026-07-24
upstream_statement: The upstream README declares CC BY-NC without a license version.
redistribution_decision: noncommercial_scientific_review_snapshot
derivative_work_notes: A selected 30-case snapshot of upstream source text and two unreviewed German machine translations is redistributed for non-commercial scientific review; the complete upstream corpus remains local.
unresolved_questions:
  - The upstream CC BY-NC version remains unspecified; redistribution relies on the project's documented non-commercial scientific-use assumption.
```

In `datasets/e3c-de/dataset.yaml`, replace
`license_evidence_sha256` with:

```yaml
license_evidence_sha256: c0c9445f60065dd0060612bc0f45e211cd55d3c804755eab6dd400ac9ec09868
```

- [ ] **Step 5: Make repository documentation consistent**

In the root `README.md`, replace the local-artifact paragraph with:

```markdown
Real source text, translations, provider responses, curation packets, and
restricted release bundles normally remain in Git-ignored local artifact
paths. The explicit exception is the tracked, unreviewed 30-case E3C German
translation review snapshot under `datasets/e3c-de/review/`.
```

In `datasets/e3c-de/README.md`, replace the two paragraphs that claim all
source text is local-only with:

```markdown
The immutable source is `hltfbk/E3C-Corpus` commit
`f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc`. Its ZIP is 233,811,002 bytes
with SHA-256
`04e06d0a153a8ea845b647459ab51eb2fed5007bdf450d441c1469f8719a2206`.
The recipe selects only Layer 1 XML: 84 English, 81 French, and 81 Spanish
documents. These are public upstream data. The complete source XML snapshot
and canonical generated artifacts remain under the Git-ignored `.artifacts/`
directory. An explicit 30-case snapshot containing selected canonical source
texts and both unreviewed German translation variants is tracked under
`review/` for non-commercial scientific review.

Only the text-free inventory and selection manifest are tracked for the full
corpus. Upstream licensing and the explicit review-snapshot redistribution
decision are recorded in `license-evidence.yaml` and `LICENSES.md`.
```

Replace `datasets/e3c-de/LICENSES.md` with:

```markdown
# E3C licensing evidence

The pinned upstream README states “CC BY-NC” but does not identify a version.
This repository therefore records
`LicenseRef-E3C-CC-BY-NC-version-unspecified` and does not infer CC BY-NC 4.0.

The complete acquired corpus remains in Git-ignored local artifacts. The
selected 30-case source and unreviewed German translation snapshot under
`review/` is redistributed for attributed, non-commercial scientific review
under the project's documented working assumption. The unspecified upstream
license version remains recorded rather than silently resolved.

The review snapshot is not an accepted benchmark release and must not be used
for clinical decisions.
```

After the first paragraph of the `Artifact boundary` section in
`datasets/e3c-de/translations/README.md`, insert:

```markdown
The exact 30-case source texts and both current unreviewed translation variants
are additionally tracked in the case-oriented `../review/` snapshot for
non-commercial scientific review. That review snapshot is not the canonical
artifact store and does not change translation identity or status.
```

- [ ] **Step 6: Run focused documentation and recipe contracts**

Run:

```powershell
uv run pytest tests/contracts/test_e3c_review_resources.py tests/contracts/test_dataset_recipes.py tests/contracts/test_dataset_documentation.py -q
```

Expected: all selected contract tests PASS.

- [ ] **Step 7: Stage and safety-check the documentation update**

Run:

```powershell
git add -- README.md datasets/e3c-de/README.md datasets/e3c-de/LICENSES.md datasets/e3c-de/translations/README.md datasets/e3c-de/license-evidence.yaml datasets/e3c-de/dataset.yaml datasets/e3c-de/review/e3c-de-feasibility-30-v1/README.md tests/contracts/test_e3c_review_resources.py
uv run python scripts/check_repository_safety.py
```

Expected: `repository safety check passed`.

- [ ] **Step 8: Commit the review notices and licensing evidence**

Run:

```powershell
git commit -m "docs: publish E3C review usage boundary"
```

Expected: one commit containing the review README, updated evidence and hash,
and consistent repository documentation.

### Task 4: Verify the Complete Repository

**Files:**

- Verify all files changed in Tasks 1-3.

- [ ] **Step 1: Run formatting and static analysis**

Run:

```powershell
uv run ruff check .
uv run mypy
```

Expected: both commands exit successfully with no errors.

- [ ] **Step 2: Run the complete test suite**

Run:

```powershell
uv run pytest
```

Expected: the full suite passes with only previously documented skips.

- [ ] **Step 3: Run the final immutable-index safety scan**

Run:

```powershell
uv run python scripts/check_repository_safety.py
```

Expected: `repository safety check passed`.

- [ ] **Step 4: Confirm the final repository state**

Run:

```powershell
git status --short --branch
git log -6 --oneline
```

Expected: a clean `agent/benchmark-data-pipeline` worktree, ahead of its
upstream by the new local commits until the user authorizes a push.

# Readable E3C Translation View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Materialize canonical E3C translation artifacts into a flat readable view automatically and through a recovery CLI command.

**Architecture:** A focused translation-view module validates and renders a supplied `TranslationManifest` and can resolve the current manifest from stage state. The translation pipeline calls the renderer after canonical publication; the CLI exposes the same resolver for rebuilds.

**Tech Stack:** Python 3.12, Typer, Pydantic, pytest, standard-library CSV and filesystem APIs.

---

### Task 1: Deterministic materializer

**Files:**
- Create: `src/phentrieve_benchmark/translation/view.py`
- Create: `tests/unit/translation/test_view.py`

- [ ] **Step 1: Write failing tests**

Create fixture artifacts and a one-record `TranslationManifest`, then assert
that `materialize_translation_view(...)` writes canonical source/translation
bytes, a stable `index.csv`, and an ownership marker; assert a second run is
identical and an unowned destination raises `ValueError`.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest tests/unit/translation/test_view.py -v`
Expected: FAIL because `translation.view` does not exist.

- [ ] **Step 3: Implement minimal renderer**

Implement:

```python
def materialize_translation_view(
    *, manifest: TranslationManifest, store: ArtifactStore, destination: Path
) -> TranslationViewResult:
    ...
```

Read all referenced objects through `ArtifactStore`, write files and CSV to a
temporary sibling directory, write `.phentrieve-translation-view.json`, reject
unowned existing destinations, then atomically replace the owned view.

- [ ] **Step 4: Verify tests**

Run: `uv run pytest tests/unit/translation/test_view.py -v`
Expected: PASS.

### Task 2: Pipeline and CLI integration

**Files:**
- Modify: `src/phentrieve_benchmark/pipeline/translate.py`
- Modify: `src/phentrieve_benchmark/cli.py`
- Modify: `tests/unit/pipeline/test_translate.py`
- Modify: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing integration tests**

Assert a successful `translate_e3c` call invokes materialization after state
publication, and expose `materialize translations e3c` with the standard
artifact root.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest tests/unit/pipeline/test_translate.py tests/unit/test_cli.py -v`
Expected: FAIL because automatic materialization and command are absent.

- [ ] **Step 3: Implement integration**

Call `materialize_translation_view` using `translated.manifest` and
`context.artifact_root / "views" / "e3c-de"` after publishing translation
state. Add nested Typer groups and a recovery command that prepares/resolves
the compatible manifest without calling Google.

- [ ] **Step 4: Verify tests**

Run: `uv run pytest tests/unit/pipeline/test_translate.py tests/unit/test_cli.py -v`
Expected: PASS.

### Task 3: Documentation and existing data

**Files:**
- Modify: `datasets/e3c-de/translations/README.md`

- [ ] **Step 1: Document automatic and recovery behavior**

Document `.artifacts/views/e3c-de`, flat filenames, `index.csv`, non-canonical
status, and `uv run phentrieve-benchmark materialize translations e3c`.

- [ ] **Step 2: Run focused and full verification**

Run: `uv run pytest tests/unit/translation/test_view.py tests/unit/pipeline/test_translate.py tests/unit/test_cli.py -v`
Expected: PASS.

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 3: Materialize existing translations**

Run: `uv run phentrieve-benchmark materialize translations e3c`
Expected: 30 source and 30 German translation files plus `index.csv`.

- [ ] **Step 4: Commit implementation**

Commit source, tests, documentation, and this plan; do not commit `.artifacts`.

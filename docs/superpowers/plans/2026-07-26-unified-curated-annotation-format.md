# Unified Curated Annotation Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement strict common curated-annotation, independent-review, deterministic review-merge, and explicit single-term derivation contracts for E3C, GSC, and CSC while preserving complete artifact and run provenance.

**Architecture:** Add three focused model modules plus pure cross-artifact validation/derivation functions. Existing normalized models remain unchanged. Deterministic artifacts carry semantic provenance; existing `RunManifest` and `ProvenanceRunLink` models link exact execution inputs, code, configuration, and outputs.

**Tech Stack:** Python 3.11+, Pydantic 2, RFC 8785 canonical JSON, SHA-256, pytest, Ruff, strict mypy.

## Global Constraints

- Do not generate GSC/CSC spans or German E3C annotations.
- Do not implement review sufficiency, majority, precedence, acceptance, or release policy.
- Preserve all existing serialized source contracts byte-for-byte.
- Use zero-based half-open Unicode code-point spans.
- Use strict frozen Pydantic models with `extra="forbid"`.
- All network and provider access remains outside this phase.

---

### Task 1: Curated annotation and derivation contracts

**Files:**
- Create: `src/phentrieve_benchmark/models/curated_annotation.py`
- Modify: `src/phentrieve_benchmark/models/__init__.py`
- Test: `tests/unit/models/test_curated_annotation.py`

**Interfaces:**
- Produces: `DocumentReference`, `OntologyReference`, `AnnotationReference`, typed derivation-source models, `DerivationActivity`, `CuratedAnnotation`, `CuratedAnnotationSet`, `curated_annotation_id`.
- Consumes: existing `EvidenceSpan`, `HpoRelease`, canonical JSON and SHA-256 helpers.

- [ ] **Step 1: Write failing contract tests**

Cover strict enums, canonical ordering/deduplication of spans, activities and sources, content-derived annotation IDs, multi-source E3C mapping provenance, logical set identity, canonical bytes/hash, and rejection of extra fields or wrong IDs.

- [ ] **Step 2: Verify RED**

Run:

```text
uv run pytest -q tests/unit/models/test_curated_annotation.py
```

Expected: import failure because the new model module does not exist.

- [ ] **Step 3: Implement minimal strict models**

Use discriminated `source_kind` variants and compute IDs from:

```python
payload = annotation.model_dump(mode="json", exclude={"annotation_id"})
identifier = "curated-ann-" + sha256_bytes(
    canonical_json_bytes(
        {"schema_version": "curated-annotation-id/v1", "annotation": payload}
    )
)
```

Canonicalize every set-like tuple with exact sort keys and reject duplicates.
Expose canonical bytes and SHA-256 on `CuratedAnnotationSet`.

- [ ] **Step 4: Verify GREEN**

Run the focused test, Ruff on touched files, and strict mypy on the model
module.

- [ ] **Step 5: Commit**

```text
git add src/phentrieve_benchmark/models tests/unit/models/test_curated_annotation.py
git commit -m "feat: add curated annotation contracts"
```

### Task 2: Cross-artifact curated provenance validation

**Files:**
- Create: `src/phentrieve_benchmark/curation/__init__.py`
- Create: `src/phentrieve_benchmark/curation/validation.py`
- Test: `tests/unit/curation/test_validation.py`

**Interfaces:**
- Produces: `CuratedDependencies`, `validate_curated_annotation_set`.
- Consumes: exact `Document`, `SourceAnnotationSet`, `AnnotationSet`,
  `RagHpoSourceAnnotationRecord`, `UmlsHpoMappingManifest`, and `HpoIndex`
  artifacts indexed by their declared SHA-256 values.

- [ ] **Step 1: Write failing validation tests**

Use synthetic documents, source annotations, RAG-HPO sidecars, mapping
manifests, and a miniature `HpoIndex`. Cover exact document/ontology binding,
span equality, HPO existence, direct-mapping candidate consistency,
source-HPO row consistency, revision resolution, manual bound-document
derivation, missing dependency failure, and preservation of obsolete HPO
proposals without implicit acceptance.

- [ ] **Step 2: Verify RED**

Run:

```text
uv run pytest -q tests/unit/curation/test_validation.py
```

Expected: import failure for `phentrieve_benchmark.curation.validation`.

- [ ] **Step 3: Implement typed dependency validation**

Use a focused `CuratedDependencies` dataclass containing exact typed mappings;
do not introduce a persisted universal registry. Resolve each source variant
with its variant-specific compound key and fail closed on missing or
contradictory records.

- [ ] **Step 4: Verify GREEN**

Run focused tests, then Task 1 and Task 2 tests together.

- [ ] **Step 5: Commit**

```text
git add src/phentrieve_benchmark/curation tests/unit/curation
git commit -m "feat: validate curated annotation provenance"
```

### Task 3: Independent review decisions and deterministic merge

**Files:**
- Create: `src/phentrieve_benchmark/models/review_decision.py`
- Create: `src/phentrieve_benchmark/review/__init__.py`
- Create: `src/phentrieve_benchmark/review/merge.py`
- Modify: `src/phentrieve_benchmark/models/__init__.py`
- Test: `tests/unit/models/test_review_decision.py`
- Test: `tests/unit/review/test_merge.py`

**Interfaces:**
- Produces: `DecisionReference`, `ReviewDecision`, `ReviewDecisionSet`,
  `review_decision_id`, `validate_review_decision_set`,
  `merge_review_decision_sets`.
- Consumes: exact curated annotation-set and earlier decision-set hashes.

- [ ] **Step 1: Write failing decision-model tests**

Cover namespaced reviewer/stage identifiers, human/tool actor kinds, sorted
nonempty scopes, `confirmed`/`rejected`/`changes_requested`, canonical UTC
timestamps, content-derived IDs, counterproposal and supersession references,
and rejection of a confirmed decision carrying a counterproposal.

- [ ] **Step 2: Verify RED**

Run the model test and confirm the missing-module failure.

- [ ] **Step 3: Implement review models and cross-artifact checks**

Validate target and superseded-decision resolution when dependencies are
provided. Counterproposals must resolve to the same document as the target.
Do not calculate an effective decision.

- [ ] **Step 4: Write failing merge tests**

Demonstrate that merge is associative, commutative, idempotent, canonical,
collapses exact duplicates, rejects ID/content collisions, retains
contradictions, and can merge without loading annotation targets.

- [ ] **Step 5: Verify RED and implement minimal merge**

Merge directly to `ReviewDecisionSet`; do not add `ReviewCollection`.

- [ ] **Step 6: Verify GREEN and commit**

Run both focused test modules, Ruff, and mypy, then commit:

```text
git add src/phentrieve_benchmark/models src/phentrieve_benchmark/review tests/unit/models/test_review_decision.py tests/unit/review
git commit -m "feat: add independent annotation reviews"
```

### Task 4: Explicit selection and deterministic single-term derivation

**Files:**
- Create: `src/phentrieve_benchmark/models/single_term.py`
- Create: `src/phentrieve_benchmark/derivation/__init__.py`
- Create: `src/phentrieve_benchmark/derivation/single_term.py`
- Modify: `src/phentrieve_benchmark/models/__init__.py`
- Test: `tests/unit/models/test_single_term.py`
- Test: `tests/unit/derivation/test_single_term.py`

**Interfaces:**
- Produces: `SingleTermSelectionRecord`, `SingleTermSelection`,
  `SingleTermRecord`, `SingleTermSet`, `single_term_id`,
  `derive_single_terms`.
- Consumes: dataset-level explicit selections, referenced curated annotation
  sets, exact documents, reviewed decision-set hashes, and one exact HPO index.

- [ ] **Step 1: Write failing selection/output model tests**

Cover selector identity, actor kind, method identity, canonical review hashes,
dataset-wide record ordering, canonical serialization, strict output fields,
and content-derived single-term IDs.

- [ ] **Step 2: Verify RED and implement minimal models**

Run the model test first, then add only the contracts needed by the expected
API.

- [ ] **Step 3: Write failing extraction tests**

Use two synthetic documents. Prove exact span slicing, copied-and-validated HPO
and context values, stable output independent of input mapping order, exact
ontology binding, and failure for empty/missing/out-of-range/duplicate spans,
wrong documents, missing reviews, or mismatched ontology.

- [ ] **Step 4: Verify RED and implement extraction**

The function recomputes every materialized output field from documents and
curated annotations. It does not inspect review outcomes or infer eligibility.

- [ ] **Step 5: Verify GREEN and commit**

Run focused tests, Ruff, and mypy, then commit:

```text
git add src/phentrieve_benchmark/models src/phentrieve_benchmark/derivation tests/unit/models/test_single_term.py tests/unit/derivation
git commit -m "feat: derive explicit single term records"
```

### Task 5: Provenance roles, documentation, and full verification

**Files:**
- Modify: `src/phentrieve_benchmark/models/pipeline.py`
- Modify: `src/phentrieve_benchmark/models/__init__.py`
- Modify: `docs/project-checklist.md`
- Test: `tests/unit/models/test_pipeline.py` or the nearest existing
  provenance-role contract test
- Test: `tests/contracts/test_dataset_documentation.py`

**Interfaces:**
- Produces: provenance subject roles for curated annotation sets, review
  decision sets, single-term selections, and single-term sets.
- Consumes: all outputs from Tasks 1–4.

- [ ] **Step 1: Write failing provenance-role test**

Prove the four new deterministic subject roles serialize exactly and are
accepted by `ProvenanceRunLink`.

- [ ] **Step 2: Verify RED and add minimal enum values**

Do not add pipeline stages, CLI commands, or provider behavior.

- [ ] **Step 3: Update the project checklist**

Record that the common format infrastructure and deterministic merge/extractor
are implemented, while actual E3C annotation, GSC/CSC span alignment, review
policies, and real single-term release data remain open.

- [ ] **Step 4: Run full verification**

```text
uv run pytest -q
uv run ruff check .
uv run mypy src
git diff --check
```

- [ ] **Step 5: Commit**

```text
git add src/phentrieve_benchmark/models docs/project-checklist.md tests
git commit -m "docs: record unified annotation infrastructure"
```

## Final review

- [ ] Confirm the worktree contains no unrelated changes.
- [ ] Review the full branch diff against the approved design.
- [ ] Confirm no code computes review sufficiency or release acceptance.
- [ ] Confirm every new deterministic output has canonical bytes and SHA-256.
- [ ] Push the completed commits to the existing draft PR branch after all
  verification passes.

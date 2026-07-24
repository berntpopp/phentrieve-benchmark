# E3C UMLS-to-HPO Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deterministically map all eligible E3C Layer 1 UMLS CUIs to candidates from HPO `v2026-06-23`, then publish a consistent 30-case subset and text-free statistics.

**Architecture:** Extend the existing strict HPO parser with an exact reverse UMLS index, keep mapping proposals in contracts distinct from accepted HPO annotations, and add an independent pipeline stage consuming existing E3C and HPO artifacts. Work is grouped into three implementation blocks with one coherent commit per block.

**Tech Stack:** Python 3.11+, Pydantic 2, Pronto, Typer, existing artifact/provenance pipeline, pytest, Ruff, mypy.

---

## Block 1: HPO UMLS cross-reference index

**Files:**

- Modify: `src/phentrieve_benchmark/ontology/hpo.py`
- Modify: `tests/fixtures/hpo.py`
- Modify: `tests/unit/ontology/test_hpo.py`

- [ ] **Write failing parser tests**

Add miniature OBO terms containing:

```text
[Term]
id: HP:0000001
name: Finding one
xref: UMLS:C0000001

[Term]
id: HP:0000002
name: Finding two
xref: UMLS:C0000001
xref: SNOMEDCT_US:123

[Term]
id: HP:0000003
name: Broken UMLS reference
xref: UMLS:not-a-cui
```

Test separately that:

- `C0000001` resolves to sorted primary IDs `HP:0000001` and `HP:0000002`;
- SNOMED and other namespaces do not enter the UMLS index;
- repeated identical `UMLS:C0000001` values on one term are rejected;
- malformed values beginning with `UMLS:` raise `HpoIndexError`; and
- candidate records retain label, obsolete, `replaced_by`, and `consider`.

Run:

```powershell
uv run pytest tests/unit/ontology/test_hpo.py -q
```

Expected before implementation: failures because `HpoIndex` has no
`umls_to_hpo` index.

- [ ] **Implement the strict reverse index**

Extend `HpoTermRecord` with:

```python
umls_cuis: tuple[str, ...]
```

Extend `HpoIndex` with:

```python
umls_to_hpo: Mapping[str, tuple[str, ...]]
```

Read `term.xrefs`, normalize their string identifiers, accept only
`UMLS:C[0-9]{7}`, reject malformed `UMLS:` claims and duplicate UMLS CUIs
within a term, then build a sorted immutable reverse index. Preserve all
existing HPO revision behavior.

- [ ] **Verify Block 1**

```powershell
uv run pytest tests/unit/ontology tests/unit/ontology/test_revision.py -q
uv run ruff check src/phentrieve_benchmark/ontology tests/unit/ontology tests/fixtures/hpo.py
uv run mypy
```

Expected: all commands pass.

- [ ] **Commit Block 1**

```powershell
git add src/phentrieve_benchmark/ontology/hpo.py tests/fixtures/hpo.py tests/unit/ontology
git commit -m "feat: index HPO UMLS cross-references"
```

## Block 2: Mapping contracts, classification, and selected view

**Files:**

- Create: `src/phentrieve_benchmark/models/mapping.py`
- Modify: `src/phentrieve_benchmark/models/__init__.py`
- Create: `src/phentrieve_benchmark/mapping/__init__.py`
- Create: `src/phentrieve_benchmark/mapping/e3c.py`
- Create: `tests/unit/models/test_mapping.py`
- Create: `tests/unit/mapping/test_e3c_mapping.py`

- [ ] **Write failing contract and mapping tests**

Use synthetic `Document` and `SourceAnnotationSet` records to cover:

```python
@pytest.mark.parametrize(
    ("cui", "candidate_ids", "obsolete", "expected"),
    [
        ("C0000001", ("HP:0000001",), (False,), "unique_active"),
        ("C0000001", ("HP:0000001", "HP:0000002"), (False, False), "ambiguous"),
        ("C0000009", (), (), "missing"),
        ("C0000003", ("HP:0000003",), (True,), "obsolete"),
        ("not-a-cui", (), (), "invalid"),
    ],
)
```

Also assert:

- non-`CLINENTITY` annotations produce no mapping record;
- repeated CUIs in separate annotations remain separate mapping records;
- evidence output contains positions and SHA-256 but no `text_snippet`;
- records and candidates are canonically sorted;
- duplicate mapping identities are rejected;
- selected records are an exact subset of complete records; and
- the selected view fails if any selected case is absent.

Run:

```powershell
uv run pytest tests/unit/models/test_mapping.py tests/unit/mapping/test_e3c_mapping.py -q
```

Expected before implementation: imports fail because the mapping modules do
not exist.

- [ ] **Implement immutable mapping contracts**

Define:

```python
class MappingClassification(StrEnum):
    UNIQUE_ACTIVE = "unique_active"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"
    OBSOLETE = "obsolete"
    INVALID = "invalid"


class MappingDecision(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"
```

Add strict frozen models for:

- `MappingEvidence(start_char, end_char, text_sha256)`;
- `HpoMappingCandidate(hpo_id, label, obsolete, replaced_by, consider)`;
- `UmlsHpoMappingRecord`;
- `UmlsHpoMappingSummary`; and
- `UmlsHpoMappingManifest`.

The manifest must have canonical byte/hash methods and validators for unique
record IDs, exact counts, sorted records, HPO release identity, normalization
identity, and optional selection identity.

- [ ] **Implement pure E3C mapping**

Implement functions that:

1. validate document/source-annotation-set links with the existing validator;
2. select only `CLINENTITY` annotations;
3. classify each source CUI using `HpoIndex.umls_to_hpo`;
4. hash source span text while retaining span offsets;
5. mark `unique_active` as `candidate` and every other class as
   `needs_review`;
6. create a complete manifest from all normalized E3C documents; and
7. derive a selected manifest only by filtering complete mapping records using
   the selected source case IDs.

Do not construct `Annotation` or `AnnotationSet` objects in this phase.

- [ ] **Verify Block 2**

```powershell
uv run pytest tests/unit/models/test_mapping.py tests/unit/mapping/test_e3c_mapping.py -q
uv run ruff check src/phentrieve_benchmark/models src/phentrieve_benchmark/mapping tests/unit/models tests/unit/mapping
uv run mypy
```

Expected: all commands pass.

- [ ] **Commit Block 2**

```powershell
git add src/phentrieve_benchmark/models src/phentrieve_benchmark/mapping tests/unit/models/test_mapping.py tests/unit/mapping
git commit -m "feat: classify E3C UMLS-to-HPO mappings"
```

## Block 3: Pipeline, CLI, documentation, and real mapping run

**Files:**

- Create: `datasets/e3c-de/mapping.yaml`
- Create: `datasets/e3c-de/mappings/README.md`
- Modify: `src/phentrieve_benchmark/models/pipeline.py`
- Modify: `src/phentrieve_benchmark/pipeline/state.py`
- Create: `src/phentrieve_benchmark/pipeline/map_hpo.py`
- Modify: `src/phentrieve_benchmark/cli.py`
- Create: `tests/unit/pipeline/test_map_hpo.py`
- Create: `tests/integration/test_map_hpo_pipeline.py`
- Modify: `tests/unit/test_cli_pipeline.py`
- Modify: `tests/contracts/test_dataset_recipes.py`
- Modify: `tests/contracts/test_dataset_documentation.py`
- Modify: `tests/contracts/test_tracked_dataset_outputs.py`
- Modify: `datasets/e3c-de/README.md`
- Modify: `docs/project-checklist.md`

- [ ] **Write failing pipeline and CLI tests**

Test an offline synthetic pipeline with a miniature ontology and E3C fixture:

- the complete manifest includes all eligible annotations;
- the selected manifest is an exact subset;
- outputs contain no source clinical text;
- input hash mismatches fail closed;
- HPO and E3C preparation states are required;
- the mapping stage is independently reusable;
- `map-hpo e3c` delegates once and prints only hashes/counts; and
- no Google, UMLS, or other network client is constructed.

Run:

```powershell
uv run pytest tests/unit/pipeline/test_map_hpo.py tests/integration/test_map_hpo_pipeline.py tests/unit/test_cli_pipeline.py -q
```

Expected before implementation: failures because the stage and command do not
exist.

- [ ] **Add pinned mapping recipe and pipeline stage**

The recipe records:

```yaml
schema_version: e3c-umls-hpo-mapping-recipe/v1
mapping_id: e3c-l1-umls-hpo-v2026-06-23-v1
method: hpo-umls-xref
hpo_release: v2026-06-23
hpo_recipe: ../../configs/ontologies/hpo-v2026-06-23.yaml
complete_population: all-e3c-l1
selected_population: e3c-de-feasibility-30-v1
```

Implement `map_hpo_e3c(context)` to resolve and verify:

- E3C acquisition and normalization state;
- E3C feasibility selection state;
- pinned HPO recipe and ontology object; and
- mapping recipe identity.

If the HPO object is absent, download the exact recipe URL to a bounded
staging file, enforce the declared maximum size, verify byte length and
SHA-256, then publish it to the artifact store. A failed download or checksum
never replaces an existing verified object and never produces mapping state.

Publish complete manifest, selected manifest, summary, run manifest,
provenance link, and reusable mapping-stage state. Extend closed stage/role
enums with `map_hpo` and `umls_hpo_mapping_manifest`.

- [ ] **Add CLI and documentation**

Expose:

```text
uv run phentrieve-benchmark map-hpo e3c
```

Document exact inputs, classifications, review boundary, text-free outputs,
and how the 30-case subset relates to the complete 246-document population.
Update the checklist only for work actually implemented and observed.

- [ ] **Verify offline before the real run**

```powershell
uv run pytest -q
uv run ruff check .
uv run mypy
git diff --check
```

Expected: all commands pass without network access.

- [ ] **Run the real deterministic mapping**

First refresh verified local inputs if needed:

```powershell
uv run phentrieve-benchmark prepare e3c
```

Then execute:

```powershell
uv run phentrieve-benchmark map-hpo e3c
```

Inspect complete and selected counts, classification totals, unique CUI count,
candidate totals, and confirm tracked manifests contain no clinical text.

- [ ] **Publish observed text-free outputs and commit Block 3**

Copy only deterministic text-free complete, selected, and summary artifacts
to `datasets/e3c-de/mappings/`, add contract assertions for their exact hashes
and counts, rerun the full verification commands, then commit:

```powershell
git add datasets/e3c-de src/phentrieve_benchmark tests docs/project-checklist.md
git commit -m "feat: publish E3C UMLS-to-HPO mapping"
```

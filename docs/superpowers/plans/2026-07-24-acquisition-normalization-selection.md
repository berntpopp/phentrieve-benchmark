# Acquisition, Normalization, and Selection Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to
> implement this plan task by task. Use `superpowers:test-driven-development`
> for every behavior change and `superpowers:verification-before-completion`
> before every completion claim.

**Goal:** Acquire the pinned E3C and RAG-HPO archives, normalize E3C Layer 1
and the CSC/GSC targets into canonical local artifacts, and create the
deterministic 30-report E3C feasibility selection.

**Architecture:** Extend the existing content-addressed artifact and provenance
foundation with strict recipe models, streaming acquisition, safe archive
inspection, source-specific adapters, exact selection arithmetic, and thin
stage orchestration. Network access is confined to acquisition. Source text and
workbooks stay under `.artifacts/`; only recipes, licensing evidence,
text-free inventories, selection manifests, and documentation are tracked.

**Tech stack:** Python 3.11+, Pydantic 2, Typer, RFC 8785, HTTPX, PyYAML,
defusedxml, openpyxl, pytest, Hypothesis, Ruff, and mypy.

**Authoritative design:**
`docs/superpowers/specs/2026-07-24-acquisition-normalization-selection-design.md`

## Global implementation rules

- Work only on `agent/benchmark-data-pipeline`.
- Preserve the existing strict/frozen Pydantic conventions.
- Write the failing test first, run it and observe the expected failure, then
  add the minimum implementation.
- Never put upstream clinical text, source workbooks, XML, archives, or raw
  annotation descriptions in Git.
- Test fixtures must be generated at runtime and clearly synthetic.
- Never allow normal CI to access the network.
- Every persisted deterministic object uses `canonical_json_bytes()` or
  `canonical_jsonl_bytes()` and has a stable schema version.
- Every source hash is a lowercase SHA-256; no branch, `latest`, redirect,
  fallback source, or zero digest is accepted.
- Run manifests may vary. Source-snapshot, normalization, inventory, and
  selection subjects must be byte-identical for identical semantic inputs.
- Run the repository safety scanner before every commit that adds dataset
  configuration, fixtures, generated inventory, or documentation.

---

### Task 1: Add the four bounded pipeline dependencies

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Add dependencies with bounded major versions**

Run:

```powershell
uv add "httpx>=0.28,<1" "PyYAML>=6,<7" "defusedxml>=0.7,<1" "openpyxl>=3.1,<4"
```

HTTPX is the only network client. PyYAML is used only through `safe_load`.
defusedxml is the only E3C XML entry point. openpyxl receives only a workbook
package that has already passed the independent ZIP-package validator.

- [ ] **Step 2: Verify lock and imports**

Run:

```powershell
uv lock --check
uv run python -c "import defusedxml, httpx, openpyxl, yaml"
uv run ruff check pyproject.toml
```

Expected: every command exits zero and `uv.lock` contains exact resolutions.

- [ ] **Step 3: Commit dependencies**

```powershell
git add pyproject.toml uv.lock
git commit -m "build: add data pipeline dependencies"
```

---

### Task 2: Stream local files into the artifact store

**Files:**

- Modify: `src/phentrieve_benchmark/artifacts/store.py`
- Modify: `tests/unit/artifacts/test_store.py`

- [ ] **Step 1: Write failing `put_file` tests**

Add tests covering:

- a multi-chunk file is published under its SHA-256 and can be read back;
- the source path is not modified;
- a supplied expected digest and byte length must both match;
- the method rejects a file that changes size or metadata while being read;
- an existing corrupt destination is rejected;
- publication remains atomic and temporary files are removed after failure.

The public signature is:

```python
def put_file(
    self,
    source: Path,
    *,
    expected_sha256: str | None = None,
    expected_byte_length: int | None = None,
    chunk_size: int = 1024 * 1024,
) -> tuple[str, int]:
    ...
```

- [ ] **Step 2: Observe the red test**

Run:

```powershell
uv run pytest tests/unit/artifacts/test_store.py -k put_file -v
```

Expected: FAIL because `ArtifactStore.put_file` does not exist.

- [ ] **Step 3: Implement bounded streaming publication**

Read `source` in binary chunks, calculate its digest and byte length, compare
the pre/post `stat()` identity and size, validate expected values, and publish
through the same atomic destination semantics as `put_bytes`. Do not load the
whole file into memory. A mismatch raises a new
`ArtifactIntegrityError(ValueError)`.

- [ ] **Step 4: Verify artifact behavior**

Run:

```powershell
uv run pytest tests/unit/artifacts/test_store.py -v
uv run ruff check src/phentrieve_benchmark/artifacts tests/unit/artifacts
uv run mypy
```

- [ ] **Step 5: Commit**

```powershell
git add src/phentrieve_benchmark/artifacts/store.py tests/unit/artifacts/test_store.py
git commit -m "feat: stream files into artifact storage"
```

---

### Task 3: Define source-annotation and deterministic stage contracts

**Files:**

- Create: `src/phentrieve_benchmark/models/source_annotation.py`
- Create: `src/phentrieve_benchmark/models/pipeline.py`
- Modify: `src/phentrieve_benchmark/models/__init__.py`
- Create: `tests/unit/models/test_source_annotation.py`
- Create: `tests/contracts/test_pipeline_manifests.py`

- [ ] **Step 1: Write failing source-annotation tests**

Test strict direct and JSON construction for these frozen models:

```text
SourceAttribute(namespace, name, value)
SourceRelationArgument(role, referenced_annotation_id)
SourceAnnotation(
  source_annotation_id,
  source_type,
  source_concept_id?,
  attributes,
  evidence_spans
)
SourceRelation(
  source_relation_id,
  source_type,
  arguments,
  attributes
)
SourceAnnotationSet(
  schema_version="source-annotation-set/v1",
  annotation_set_id,
  document_sha256,
  source_schema_id,
  annotations,
  relations
)
```

Require NFC strings, sorted set-like collections, no duplicate normalized
identities, no duplicate `(namespace, name)` attributes, and relation
arguments that reference an annotation in the same set. Reuse `EvidenceSpan`
and add `validate_source_annotation_set(document, annotation_set)` for document
hash and half-open evidence-span validation.

- [ ] **Step 2: Write failing deterministic-manifest tests**

Define and test these strict/frozen models:

```text
ArtifactReference(schema_id, sha256, byte_length, record_count?)
WarningCount(code, count)
SourceMember(path, sha256, byte_length)
SourceSnapshotManifest(
  schema_version="source-snapshot-manifest/v1",
  source_id,
  source_commit,
  recipe_sha256,
  archive_sha256,
  archive_byte_length,
  archive_format,
  members
)
NormalizationCount(language?, record_type, count)
NormalizationManifest(
  schema_version="normalization-manifest/v1",
  target_id,
  source_snapshot_sha256,
  recipe_sha256,
  adapter_id,
  code_sha256,
  documents,
  annotations?,
  source_annotations?,
  source_sidecar?,
  inventory,
  counts,
  warnings
)
ProvenanceSubjectRole(
  source_snapshot,
  normalization_manifest,
  selection_manifest
)
ProvenanceRunLink(
  schema_version="provenance-run-link/v1",
  subject_role,
  subject_sha256,
  run_manifest_sha256
)
```

Every set-like tuple sorts by its declared identity and rejects duplicates.
Paths are relative canonical POSIX paths. No deterministic model accepts
`run_id`, timestamp, host, environment, or run-manifest fields.

- [ ] **Step 3: Observe missing models**

Run:

```powershell
uv run pytest tests/unit/models/test_source_annotation.py tests/contracts/test_pipeline_manifests.py -v
```

Expected: collection fails because the modules do not exist.

- [ ] **Step 4: Implement and export the contracts**

Give every manifest:

```python
def canonical_bytes(self) -> bytes:
    return canonical_json_bytes(self.model_dump(mode="json"))

def sha256(self) -> str:
    return sha256_bytes(self.canonical_bytes())
```

Use closed ASCII identifier patterns for schema IDs, adapter IDs, warning
codes, source IDs, roles, and record types. Do not add generic arbitrary
metadata fields.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
uv run pytest tests/unit/models/test_source_annotation.py tests/contracts/test_pipeline_manifests.py -v
uv run ruff check src/phentrieve_benchmark/models tests/unit/models tests/contracts/test_pipeline_manifests.py
uv run mypy
```

Then:

```powershell
git add src/phentrieve_benchmark/models tests/unit/models/test_source_annotation.py tests/contracts/test_pipeline_manifests.py
git commit -m "feat: add source and stage artifact contracts"
```

---

### Task 4: Load strict source and target recipes

**Files:**

- Create: `src/phentrieve_benchmark/acquisition/__init__.py`
- Create: `src/phentrieve_benchmark/acquisition/recipes.py`
- Create: `tests/unit/acquisition/test_recipes.py`

- [ ] **Step 1: Write failing recipe tests**

The source recipe model contains:

```text
schema_version="source-recipe/v1"
source_id
repository_url
source_commit
source_tag?
archive(
  url,
  format,
  expected_byte_length,
  maximum_byte_length,
  sha256,
  expected_top_level_directory,
  maximum_member_count,
  maximum_member_bytes,
  maximum_expanded_bytes,
  maximum_compression_ratio
)
included_paths[]
ignored_path_prefixes[]
adapter_id
source_schema_id
adapter_contract
license_evidence_sha256
```

The target recipe model contains:

```text
schema_version="normalization-recipe/v1"
target_id
source_id
adapter_id
required_paths[]
expected_tables[]
expected_counts[]
hpo_release?
```

`adapter_contract` is a discriminated strict union. The E3C variant declares
the exact language/path/count table, Sofa type, structural token/sentence
types, six semantic entity types, four relation types, span fields, relation
argument fields, concept fields, and allowed source attributes. The RAG-HPO
variant declares the exact selected files and workbook-package limits. A
contract variant must match `source_id` and `adapter_id`.

The adjacent licensing record is also a strict model:

```text
LicenseEvidence(
  schema_version="license-evidence/v1",
  source_id,
  repository_url,
  source_commit,
  license_id,
  license_url,
  access_date,
  upstream_statement,
  redistribution_decision,
  derivative_work_notes,
  unresolved_questions
)
```

Test:

- only full lowercase 40-character commits are accepted;
- `latest`, branch URLs, absent/all-zero hashes, redirects, HTTP, fragments,
  query strings, userinfo, and non-codeload hosts are rejected;
- the commit embedded in the direct codeload URL must equal `source_commit`;
- exact length is positive and at most the maximum;
- allowed and ignored path rules cannot overlap;
- YAML aliases, duplicate keys, non-string keys, and multi-document YAML fail;
- strict Pydantic validation rejects coercive booleans/numbers;
- semantically equivalent YAML formatting has one canonical configuration
  hash;
- comments, mapping order, and line endings do not alter that hash.

- [ ] **Step 2: Observe the red test**

Run:

```powershell
uv run pytest tests/unit/acquisition/test_recipes.py -v
```

- [ ] **Step 3: Implement safe YAML and recipe identity**

Subclass `yaml.SafeLoader` only to reject duplicate mapping keys and aliases.
Accept exactly one document and require a top-level mapping. Validate through
Pydantic, then hash:

```python
canonical_json_bytes(recipe.model_dump(mode="json"))
```

Expose:

```python
def load_source_recipe(path: Path) -> LoadedRecipe[SourceRecipe]: ...
def load_target_recipe(path: Path) -> LoadedRecipe[NormalizationRecipe]: ...
def load_license_evidence(path: Path) -> LoadedRecipe[LicenseEvidence]: ...
```

`LoadedRecipe` contains only `value` and `sha256`.

- [ ] **Step 4: Verify and commit**

```powershell
uv run pytest tests/unit/acquisition/test_recipes.py -v
uv run ruff check src/phentrieve_benchmark/acquisition tests/unit/acquisition
uv run mypy
git add src/phentrieve_benchmark/acquisition tests/unit/acquisition
git commit -m "feat: validate immutable source recipes"
```

---

### Task 5: Download archives without redirects or partial publication

**Files:**

- Create: `src/phentrieve_benchmark/acquisition/downloader.py`
- Create: `tests/unit/acquisition/test_downloader.py`
- Create: `tests/fixtures/http_server.py`

- [ ] **Step 1: Build a local HTTP fixture and failing tests**

Use `ThreadingHTTPServer` on loopback only. Cover:

- a chunked successful response is streamed and published to `ArtifactStore`;
- missing `Content-Length` is allowed but the measured length must be exact;
- an incorrect `Content-Length`, archive size, or digest fails;
- 301, 302, 303, 307, and 308 all fail without following the target;
- connect/read timeout and interrupted transfer fail;
- maximum byte count is enforced before and during streaming;
- HTTP errors do not expose response bodies or credential-bearing headers;
- no partial artifact or staging file remains after failure.

The API is:

```python
@dataclass(frozen=True)
class DownloadedArchive:
    sha256: str
    byte_length: int

def download_archive(
    recipe: SourceRecipe,
    *,
    store: ArtifactStore,
    staging_root: Path,
    client: httpx.Client | None = None,
) -> DownloadedArchive:
    ...
```

- [ ] **Step 2: Observe the red test**

```powershell
uv run pytest tests/unit/acquisition/test_downloader.py -v
```

- [ ] **Step 3: Implement streaming HTTPX acquisition**

Use an HTTPX client with `follow_redirects=False`, bounded connect/read/write/
pool timeouts, no ambient authentication, and a fixed non-secret user agent.
Stream into a fresh file below `staging_root`, calculate size/digest while
reading, then call `ArtifactStore.put_file()` with both expected values. Always
remove the staging file in `finally`.

- [ ] **Step 4: Verify and commit**

```powershell
uv run pytest tests/unit/acquisition/test_downloader.py -v
uv run ruff check src/phentrieve_benchmark/acquisition tests/unit/acquisition tests/fixtures/http_server.py
uv run mypy
git add src/phentrieve_benchmark/acquisition/downloader.py tests/unit/acquisition/test_downloader.py tests/fixtures/http_server.py
git commit -m "feat: acquire pinned source archives"
```

---

### Task 6: Safely inspect archives and publish selected members

**Files:**

- Create: `src/phentrieve_benchmark/acquisition/archives.py`
- Create: `tests/unit/acquisition/test_archives.py`

- [ ] **Step 1: Write failing ZIP/TAR safety tests**

Generate archives in memory at test runtime. Cover:

- selected regular files become CAS artifacts and a sorted
  `SourceSnapshotManifest`;
- ignored prefixes are inspected but not published;
- absolute, drive-qualified, UNC, backslash, `..`, NUL, empty, NFC-colliding,
  and duplicate paths fail;
- ZIP symlinks and TAR links, devices, FIFOs, sockets, sparse/unsupported
  members fail;
- member count, individual size, declared expanded total, streamed expanded
  total, and compression ratio limits fail closed;
- the expected top-level directory and required selected paths are exact;
- a member whose streamed bytes differ from its declared size fails;
- no member is written as a normal extracted working-tree file.

Expose:

```python
def publish_source_snapshot(
    recipe: LoadedRecipe[SourceRecipe],
    archive: DownloadedArchive,
    *,
    store: ArtifactStore,
) -> SourceSnapshotManifest:
    ...
```

- [ ] **Step 2: Observe the red test**

```powershell
uv run pytest tests/unit/acquisition/test_archives.py -v
```

- [ ] **Step 3: Implement safe archive readers**

Normalize only `/`-separated NFC paths and reject backslashes. Validate every
archive member before opening any selected member. Count declared sizes for
all members. Stream only explicitly included members to temporary files and
then CAS. Build the deterministic manifest only after every selected path,
hash, length, and required inventory check succeeds.

- [ ] **Step 4: Verify and commit**

```powershell
uv run pytest tests/unit/acquisition/test_archives.py -v
uv run ruff check src/phentrieve_benchmark/acquisition tests/unit/acquisition
uv run mypy
git add src/phentrieve_benchmark/acquisition/archives.py tests/unit/acquisition/test_archives.py
git commit -m "feat: validate source archive contents"
```

---

### Task 7: Measure and commit the real immutable source locks

**Files:**

- Create: `datasets/e3c-de/dataset.yaml`
- Create: `datasets/e3c-de/license-evidence.yaml`
- Create: `datasets/e3c-de/LICENSES.md`
- Create: `datasets/raghpo/source.yaml`
- Create: `datasets/raghpo/license-evidence.yaml`
- Create: `datasets/raghpo/LICENSES.md`
- Create: `datasets/raghpo/csc/dataset.yaml`
- Create: `datasets/raghpo/gsc/dataset.yaml`
- Create: `tests/contracts/test_dataset_recipes.py`

- [ ] **Step 1: Download each real commit archive exactly once**

Use these direct, immutable URLs:

```text
https://codeload.github.com/hltfbk/E3C-Corpus/zip/f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc
https://codeload.github.com/PoseyPod/RAG-HPO/zip/080fc3a04c91ee45c8986076765f4d4b4f14ddd9
```

Run from the repository root:

```powershell
New-Item -ItemType Directory -Force -Path .artifacts/source-locks
curl.exe --fail --silent --show-error --proto '=https' --tlsv1.2 --max-redirs 0 --output .artifacts/source-locks/e3c.zip https://codeload.github.com/hltfbk/E3C-Corpus/zip/f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc
curl.exe --fail --silent --show-error --proto '=https' --tlsv1.2 --max-redirs 0 --output .artifacts/source-locks/raghpo.zip https://codeload.github.com/PoseyPod/RAG-HPO/zip/080fc3a04c91ee45c8986076765f4d4b4f14ddd9
Get-Item .artifacts/source-locks/e3c.zip, .artifacts/source-locks/raghpo.zip | Select-Object Name,Length
Get-FileHash -Algorithm SHA256 .artifacts/source-locks/e3c.zip, .artifacts/source-locks/raghpo.zip
```

Record the observed decimal byte lengths and lowercase SHA-256 digests
directly in the recipes. The committed recipes must never contain temporary
values or placeholder digests.

- [ ] **Step 2: Write failing recipe contract tests**

Tests load all four recipes and both licensing records and assert:

- exact commits and codeload URLs above;
- non-zero measured lengths and hashes;
- E3C includes only EN/FR/ES Layer 1 XML plus upstream licensing/README
  evidence and explicitly ignores other paths;
- RAG-HPO includes only `Test_Cases.csv`,
  `RAG-HPO Tests and Data Analysis copy.xlsx`, `README.md`, and `LICENSE`;
- E3C expected document counts are 84/81/81;
- E3C stores the exact official per-language counts for `CLINENTITY`, `EVENT`,
  `ACTOR`, `BODYPART`, `TIMEX3`, `RML`, `TIMEX3TimexLinkLink`,
  `RMLPERTAINSTOLink`, `EVENTTLINKLink`, and `EVENTALINKLink`;
- CSC table counts are 116/116/1,789 and GSC counts are 114/1,012;
- HPO context is exactly `v2026-06-23`;
- each recipe's `license_evidence_sha256` matches the canonical semantic hash
  of its adjacent evidence file.

The E3C count vectors in that exact type order are:

```text
en: 1024, 4885, 682, 968, 380, 480, 502, 541, 4350, 114
fr: 1327, 4312, 427, 659, 333, 508, 236, 474, 3848, 71
es: 1345, 4767, 319, 814, 383, 391, 604, 473, 4096, 92
```

- [ ] **Step 3: Write exact licensing evidence**

For E3C, record that the upstream README declares `CC BY-NC` without a version;
use a local `LicenseRef-E3C-CC-BY-NC-version-unspecified` identifier and do not
infer CC BY-NC 4.0. For RAG-HPO, record the repository's MIT license and
copyright notice. Both phase decisions are `source_not_redistributed`; only
text-free metadata is tracked. Include source URL, direct license/README URL,
commit, access date `2026-07-24`, derivative/redistribution notes, and the
deferred-release limitation.

- [ ] **Step 4: Validate the real locks with production code**

Run:

```powershell
uv run pytest tests/contracts/test_dataset_recipes.py -v
uv run python scripts/check_repository_safety.py
git status --short
```

Confirm that `.artifacts/source-locks` is absent from `git status`.

- [ ] **Step 5: Commit recipes and licensing evidence**

```powershell
git add datasets tests/contracts/test_dataset_recipes.py
git commit -m "data: lock E3C and RAG-HPO sources"
```

---

### Task 8: Canonicalize text and compose UTF-16 offset maps

**Files:**

- Create: `src/phentrieve_benchmark/normalization/__init__.py`
- Create: `src/phentrieve_benchmark/normalization/text.py`
- Create: `tests/unit/normalization/test_text.py`

- [ ] **Step 1: Write failing normalization-map tests**

Cover:

- NFC composition and CRLF/CR to LF;
- optional removal of exactly one declared terminal format newline;
- empty canonical clinical text rejection;
- UIMA UTF-16 offsets before/after a non-BMP character;
- a UTF-16 boundary inside a surrogate pair;
- a boundary inside an NFC composition cluster;
- a boundary between CR and LF;
- span conversion through both UTF-16 and canonicalization maps;
- the required invariant
  `canonical_text[start:end] == canonicalized_source_span`.

The API is:

```python
@dataclass(frozen=True)
class CanonicalTextMap:
    source_text: str
    canonical_text: str

    def utf16_span(self, begin: int, end: int) -> EvidenceSpan: ...

def canonicalize_source_text(
    source_text: str,
    *,
    remove_terminal_format_newline: bool,
) -> CanonicalTextMap:
    ...
```

- [ ] **Step 2: Observe the red test**

```powershell
uv run pytest tests/unit/normalization/test_text.py -v
```

Expected: collection fails because `normalization.text` does not exist.

- [ ] **Step 3: Implement stable boundary mapping**

Build the UTF-16 cumulative boundary table and reject offsets not present in
it. A code-point boundary is canonicalizable only when canonicalizing the two
halves independently and concatenating them produces the same canonical text;
this rejects boundaries inside normalization and CRLF clusters. Do not treat
Python indices as UIMA offsets.

- [ ] **Step 4: Verify and commit**

```powershell
uv run pytest tests/unit/normalization/test_text.py -v
uv run ruff check src/phentrieve_benchmark/normalization tests/unit/normalization
uv run mypy
git add src/phentrieve_benchmark/normalization tests/unit/normalization
git commit -m "feat: map source offsets to canonical text"
```

---

### Task 9: Normalize E3C Layer 1 XMI

**Files:**

- Create: `src/phentrieve_benchmark/normalization/contracts.py`
- Create: `src/phentrieve_benchmark/normalization/e3c.py`
- Create: `tests/fixtures/e3c.py`
- Create: `tests/unit/normalization/test_e3c.py`

- [ ] **Step 1: Generate structurally faithful synthetic XMI fixtures**

The runtime builder creates `cas:Sofa`, token, sentence, `CLINENTITY`, `EVENT`,
`ACTOR`, `BODYPART`, `TIMEX3`, `RML`, `TIMEX3TimexLinkLink`,
`RMLPERTAINSTOLink`, `EVENTTLINKLink`, and `EVENTALINKLink` elements. Include
one non-BMP character before an annotation and source-native attributes/CUI.
No real E3C text is stored in the fixture module.

- [ ] **Step 2: Write failing adapter tests**

Cover:

- language comes only from the exact English/French/Spanish Layer 1 path;
- `x-unspecified` Sofa metadata cannot change language;
- entity and relation registries emit exact source-native types;
- token/sentence/POS/WebAnno metadata remain structural;
- source annotations are not HPO `Annotation` objects;
- UMLS CUI and factuality attributes are preserved;
- relation arguments resolve inside the same set;
- UTF-16 spans survive non-BMP text and NFC/line-ending normalization;
- DTD, entity, external access, unknown custom types, malformed offsets,
  duplicate `(language, source_case_id)`, and wrong counts fail closed;
- stable IDs match the design and output is permutation-independent.

`NormalizedTarget` in `contracts.py` contains tuples of `Document`,
`SourceAnnotationSet` or `AnnotationSet`, optional source-sidecar rows, inventory
records, counts, and warnings. Its serializer stores clinical JSONL only in
`ArtifactStore`.

- [ ] **Step 3: Observe the red test**

```powershell
uv run pytest tests/unit/normalization/test_e3c.py -v
```

Expected: collection fails because the E3C adapter does not exist.

- [ ] **Step 4: Implement the strict adapter**

Parse only with `defusedxml.ElementTree`. Resolve declared namespaces and types
from the recipe registry. Select `cas:Sofa`, convert every boundary through
`CanonicalTextMap`, build the native `Document` and `SourceAnnotationSet`, then
validate all spans and references. Reject unknown semantic XMI elements rather
than silently skipping them.

- [ ] **Step 5: Verify and commit**

```powershell
uv run pytest tests/unit/normalization/test_e3c.py -v
uv run ruff check src/phentrieve_benchmark/normalization tests/unit/normalization tests/fixtures/e3c.py
uv run mypy
git add src/phentrieve_benchmark/normalization tests/unit/normalization/test_e3c.py tests/fixtures/e3c.py
git commit -m "feat: normalize E3C layer one"
```

---

### Task 10: Validate nested XLSX packages before cell parsing

**Files:**

- Create: `src/phentrieve_benchmark/normalization/workbook.py`
- Create: `tests/fixtures/raghpo.py`
- Create: `tests/unit/normalization/test_workbook.py`

- [ ] **Step 1: Write failing XLSX-package tests**

Generate workbooks at runtime and mutate their ZIP members for adversarial
cases. Cover:

- a minimal workbook with exact sheets is accepted;
- member-count, member-size, expanded-size, and compression-ratio limits;
- duplicate/NFC-colliding/unsafe member names;
- encrypted members;
- VBA, macros, ActiveX, OLE, embedded packages, external links, external
  relationships, connections, query tables, and external data;
- unsupported content types and relationship types;
- formulas in any used sheet;
- fuzzy, trimmed, or case-folded sheet-name matching is forbidden;
- `GSC Manual Annotations ` retains its trailing space.

Expose:

```python
@dataclass(frozen=True)
class WorkbookLimits:
    maximum_member_count: int
    maximum_member_bytes: int
    maximum_expanded_bytes: int
    maximum_compression_ratio: int

def open_validated_workbook(
    workbook_bytes: bytes,
    *,
    limits: WorkbookLimits,
) -> openpyxl.Workbook:
    ...
```

- [ ] **Step 2: Observe the red test**

```powershell
uv run pytest tests/unit/normalization/test_workbook.py -v
```

Expected: collection fails because the validated workbook reader does not
exist.

- [ ] **Step 3: Implement package validation**

Inspect ZIP central-directory metadata and every relationship/content-type XML
part before calling openpyxl. Then use:

```python
openpyxl.load_workbook(
    BytesIO(workbook_bytes),
    read_only=True,
    data_only=False,
    keep_links=False,
)
```

Reject formula cells while reading declared tables. Close the workbook in all
paths.

- [ ] **Step 4: Verify and commit**

```powershell
uv run pytest tests/unit/normalization/test_workbook.py -v
uv run ruff check src/phentrieve_benchmark/normalization tests/unit/normalization tests/fixtures/raghpo.py
uv run mypy
git add src/phentrieve_benchmark/normalization/workbook.py tests/unit/normalization/test_workbook.py tests/fixtures/raghpo.py
git commit -m "feat: validate source workbook packages"
```

---

### Task 11: Normalize CSC and GSC independently

**Files:**

- Create: `src/phentrieve_benchmark/normalization/raghpo.py`
- Modify: `src/phentrieve_benchmark/normalization/contracts.py`
- Create: `tests/unit/normalization/test_raghpo.py`

- [ ] **Step 1: Write failing CSC/GSC adapter tests**

Cover:

- UTF-8 CSV with or without BOM and RFC 4180 quoting;
- exact headers, sheet names, columns, and data-row counts;
- CSC CSV and `CSC Input` case IDs and canonical note hashes agree;
- CSC joins `Case` to exact `Patient ID`;
- GSC joins exact `(patient_id, ID)` to `(Patient ID, ID)`;
- boolean, float, blank, whitespace-padded, fuzzy, case-folded, or
  punctuation-normalized identifiers are rejected;
- strict integer IDs and NFC text IDs without surrounding whitespace or
  controls retain their exact value;
- constructed ID components use injective percent encoding and cannot collide
  when an upstream value contains punctuation;
- surrounding ASCII whitespace around one HPO ID is removed;
- a CSC comma cell yields two annotations and only ASCII comma splits;
- every result matches `HP:[0-9]{7}`;
- manual rows have empty `evidence_spans`;
- `hpo_description` is never searched in the note;
- the ignored `RagHpoSourceAnnotationRecord` preserves raw term,
  description, optional secondary ID/category, and derived annotation IDs;
- CSC and GSC outputs, hashes, warnings, and failures are independent;
- source rows, annotations, and output JSONL sort deterministically.

Add this strict/frozen sidecar model to `normalization/contracts.py`:

```text
RagHpoSourceAnnotationRecord(
  schema_version="raghpo-source-annotation-record/v1",
  source_row_id,
  source_case_id,
  secondary_id?,
  hpo_description,
  raw_hpo_term,
  category?,
  derived_annotation_ids
)
```

The first manual data row is ordinal 1. Its stable row ID is
`raghpo:<commit>:<target>:manual-row:000001`; later rows increment the
six-digit ordinal. Derived annotation IDs append `:hpo:01`, then `:hpo:02`.
CSC uses `Case` in its document and annotation-set IDs. GSC retains
`source_case_id=patient_id`, and both its document and annotation-set IDs
include the exact secondary `ID` so the composite join key cannot collide.

- [ ] **Step 2: Observe the red test**

```powershell
uv run pytest tests/unit/normalization/test_raghpo.py -v
```

Expected: collection fails because the RAG-HPO adapter does not exist.

- [ ] **Step 3: Implement tabular adapters**

Use `csv.DictReader(..., dialect="excel", strict=True)` after BOM-aware UTF-8
decoding. Use the validated workbook reader. Accept an upstream identifier only
when it is a non-boolean non-negative `int` or an NFC string with no leading/
trailing whitespace or controls; convert integers with canonical ASCII decimal
format. Do not accept floats. Preserve the exact accepted value in record
fields. For colon-delimited constructed IDs, percent-encode its NFC UTF-8 bytes
except ASCII letters, digits, `.`, `_`, and `-`. Create HPO `AnnotationSet`
objects with `v2026-06-23` but do not apply later revision policy.

- [ ] **Step 4: Verify and commit**

```powershell
uv run pytest tests/unit/normalization/test_raghpo.py -v
uv run ruff check src/phentrieve_benchmark/normalization tests/unit/normalization
uv run mypy
git add src/phentrieve_benchmark/normalization/raghpo.py tests/unit/normalization/test_raghpo.py
git commit -m "feat: normalize CSC and GSC sources"
```

---

### Task 12: Build the text-free E3C inventory and exact selection

**Files:**

- Create: `src/phentrieve_benchmark/selection/__init__.py`
- Create: `src/phentrieve_benchmark/selection/contracts.py`
- Create: `src/phentrieve_benchmark/selection/metrics.py`
- Create: `src/phentrieve_benchmark/selection/e3c.py`
- Create: `tests/unit/selection/test_metrics.py`
- Create: `tests/unit/selection/test_e3c.py`

- [ ] **Step 1: Write failing metric and rational-contract tests**

Define:

```text
Rational(numerator >= 0, denominator > 0)
LengthStratum(short, medium, long)
E3cInventoryRecord(
  source_case_id,
  language,
  document_sha256,
  codepoint_count,
  whitespace_token_count,
  sentence_count,
  annotation_counts,
  marker_counts,
  rational_densities,
  length_stratum,
  warnings
)
SelectionOverride(source_case_id, action, rationale, author_role, decision_date)
E3cSelectionRecord(language, stratum, source_case_id, metrics)
E3cSelectionManifest(
  schema_version="e3c-selection-manifest/v1",
  selection_id,
  inventory_sha256,
  algorithm_id,
  selection_seed,
  overrides,
  records,
  aggregate_sha256
)
```

Test `len(canonical_text.split())`, code-point count, annotation/marker counts,
reduced positive-denominator rationals, and boundaries 199/200/400/401.
Reject empty text and all binary-float inputs.

- [ ] **Step 2: Write failing selection tests**

Cover:

- exactly 10 EN, 10 FR, 10 ES;
- per language exactly 3 short, 4 medium, 3 long;
- insufficient strata fail without rebalancing;
- min-max scaling and centroid use `fractions.Fraction`;
- constant features scale to zero;
- squared Euclidean maximin behavior;
- ties use lexicographically compared raw SHA-256 digest bytes of
  `seed + NUL + source_case_id`;
- input permutation does not affect output bytes;
- includes preselect and consume their own stratum slot;
- excludes leave the pool before fill;
- unknown/conflicting/duplicate/excessive/insufficient overrides fail;
- the initial override list is empty;
- manifests contain no clinical text, float, timestamp, or run ID.

- [ ] **Step 3: Observe the red tests**

```powershell
uv run pytest tests/unit/selection -v
```

Expected: collection fails because the selection package does not exist.

- [ ] **Step 4: Implement inventory and `e3c-diversity-maximin/v1`**

Keep calculations as `int` and `Fraction`. Serialize every fraction as reduced
`Rational`. Never convert a selection value to `float`. Sort final records by
language order `en`, `fr`, `es`, then stratum order `short`, `medium`, `long`,
then source case ID.

- [ ] **Step 5: Verify and commit**

```powershell
uv run pytest tests/unit/selection -v
uv run ruff check src/phentrieve_benchmark/selection tests/unit/selection
uv run mypy
git add src/phentrieve_benchmark/selection tests/unit/selection
git commit -m "feat: select the E3C feasibility cohort"
```

---

### Task 13: Add stage state, provenance, and per-target orchestration

**Files:**

- Create: `src/phentrieve_benchmark/pipeline/__init__.py`
- Create: `src/phentrieve_benchmark/pipeline/state.py`
- Create: `src/phentrieve_benchmark/pipeline/prepare.py`
- Create: `tests/unit/pipeline/test_state.py`
- Create: `tests/integration/test_prepare_pipeline.py`

- [ ] **Step 1: Write failing state-cache tests**

An ignored state pointer is:

```text
.artifacts/state/<stage>/<target>/<semantic-key-sha256>.json
```

The semantic key contains exact recipe, source snapshot, adapter, code, input,
selection seed, and override identities relevant to that stage. Tests require:

- atomic pointer publication;
- pointer JSON contains only subject role/hash and all required semantic hashes;
- every referenced manifest and artifact is re-read and re-hashed before reuse;
- missing/corrupt/mismatched state recomputes rather than trusting filenames;
- a different code/config/input/seed/override never reuses output;
- deterministic subject bytes remain identical across reruns;
- separate `ProvenanceRunLink` objects can differ by run manifest.

- [ ] **Step 2: Write failing orchestration tests**

With fake network and generated source snapshots, assert:

```text
prepare e3c: acquire e3c -> normalize e3c -> select feasibility-30
prepare csc: acquire raghpo -> normalize csc
prepare gsc: acquire raghpo -> normalize gsc
```

CSC and GSC may run before E3C, reuse only the verified RAG-HPO snapshot, and
do not share normalized state or failure. `normalize` never calls a network
client. `select` never opens an archive. Each invoked command emits one
`RunManifest` and one `ProvenanceRunLink`, including a failed run with stable
error codes and no raw exception/source text.

- [ ] **Step 3: Observe the red tests**

```powershell
uv run pytest tests/unit/pipeline/test_state.py tests/integration/test_prepare_pipeline.py -v
```

Expected: collection fails because pipeline state and orchestration do not
exist.

- [ ] **Step 4: Implement thin stage services**

Expose:

```python
def acquire_target(source_id: Literal["e3c", "raghpo"], context: PipelineContext) -> StageResult: ...
def normalize_target(target_id: Literal["e3c", "csc", "gsc"], context: PipelineContext) -> StageResult: ...
def select_e3c(cohort: Literal["feasibility-30"], context: PipelineContext) -> StageResult: ...
def prepare_target(target_id: Literal["e3c", "csc", "gsc"], context: PipelineContext) -> tuple[StageResult, ...]: ...
```

`PipelineContext` owns trusted repository/dataset/artifact roots, store,
clock/run-ID providers, and code identity. Adapters receive bytes and recipes,
never the context or HTTP client.

- [ ] **Step 5: Verify and commit**

```powershell
uv run pytest tests/unit/pipeline tests/integration/test_prepare_pipeline.py -v
uv run ruff check src/phentrieve_benchmark/pipeline tests/unit/pipeline tests/integration
uv run mypy
git add src/phentrieve_benchmark/pipeline tests/unit/pipeline tests/integration/test_prepare_pipeline.py
git commit -m "feat: orchestrate independent dataset stages"
```

---

### Task 14: Expose stage commands and the explicit live smoke

**Files:**

- Modify: `src/phentrieve_benchmark/cli.py`
- Create: `tests/unit/test_cli_pipeline.py`

- [ ] **Step 1: Write failing Typer CLI tests**

Require these commands and exact target choices:

```text
phentrieve-benchmark acquire e3c
phentrieve-benchmark acquire raghpo
phentrieve-benchmark normalize e3c
phentrieve-benchmark normalize csc
phentrieve-benchmark normalize gsc
phentrieve-benchmark select e3c --cohort feasibility-30
phentrieve-benchmark prepare e3c
phentrieve-benchmark prepare csc
phentrieve-benchmark prepare gsc
phentrieve-benchmark smoke live-download
```

Test `--dataset-root` and `--artifact-root` with temporary paths, stable
text-free success output containing stage/subject hash/reused status, concise
stable error codes, invalid target rejection, and absence of source text/raw
exceptions. Monkeypatch stage services; CLI unit tests do not access network.

- [ ] **Step 2: Observe the red tests**

```powershell
uv run pytest tests/unit/test_cli_pipeline.py -v
```

Expected: tests fail because the new command groups are absent.

- [ ] **Step 3: Implement thin commands**

Use Typer sub-apps for `acquire`, `normalize`, `select`, `prepare`, and `smoke`.
The live smoke calls both real acquisitions, normalizes all three targets,
selects E3C, reruns the deterministic subjects, and compares subject hashes.
It never calls a provider, uploads artifacts, or runs from normal CI.

- [ ] **Step 4: Verify and commit**

```powershell
uv run pytest tests/unit/test_cli_pipeline.py -v
uv run phentrieve-benchmark --help
uv run ruff check src/phentrieve_benchmark/cli.py tests/unit/test_cli_pipeline.py
uv run mypy
git add src/phentrieve_benchmark/cli.py tests/unit/test_cli_pipeline.py
git commit -m "feat: expose dataset preparation commands"
```

---

### Task 15: Run real normalization, commit text-free outputs, and finish docs

**Files:**

- Create: `datasets/e3c-de/README.md`
- Create: `datasets/e3c-de/selection-policy.md`
- Create: `datasets/e3c-de/inventories/e3c-v2.0.0-l1-en-fr-es-v1.json`
- Create: `datasets/e3c-de/selections/e3c-de-feasibility-30-v1.json`
- Create: `datasets/raghpo/README.md`
- Create: `datasets/raghpo/csc/README.md`
- Create: `datasets/raghpo/gsc/README.md`
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/contracts/test_dataset_documentation.py`
- Create: `tests/contracts/test_tracked_dataset_outputs.py`

- [ ] **Step 1: Run the explicit real-source pipeline**

Run:

```powershell
uv run phentrieve-benchmark smoke live-download
uv run phentrieve-benchmark prepare csc
uv run phentrieve-benchmark prepare gsc
uv run phentrieve-benchmark prepare e3c
```

Verify reported subject hashes agree across the smoke rerun and separate
prepare calls. Confirm E3C counts 84/81/81, CSC rows 116 and 1,789 with 1,795
derived HPO annotations, and GSC rows 114 and 1,012 with 1,012 derived HPO
annotations. Inspect only text-free reports; do not print clinical records.

- [ ] **Step 2: Export only text-free canonical records**

Copy the verified E3C inventory and selection manifest from their CAS subjects
to the tracked paths named above. Before staging, assert:

- no `text`, `clinical_note`, `hpo_description`, `text_snippet`, prompt,
  credential, run ID, timestamp, host, or environment keys;
- inventory contains 246 unique `(language, source_case_id)` records;
- selection contains 30 unique cases with 10 per language and 3/4/3 strata;
- seed is `phentrieve-e3c-de-feasibility-30-v1`;
- algorithm is `e3c-diversity-maximin/v1`;
- overrides are exactly `[]`;
- the tracked bytes equal the canonical CAS bytes.

- [ ] **Step 3: Write failing documentation/output contract tests**

Tests require every README section specified in the design, verify source
pins/checksums/commands/counts/limitations, compare `LICENSES.md` with
`license-evidence.yaml`, validate inventory/selection schemas and hashes, and
scan tracked dataset files for prohibited clinical fields.

Normal CI remains offline. Add only the new offline unit/integration/contract
tests to the existing CI invocation; do not add the live smoke command to
`.github/workflows/ci.yml`.

- [ ] **Step 4: Complete target documentation**

Document:

- purpose, boundaries, source URLs and commits;
- exact archive sizes and SHA-256 values;
- commands and ignored artifact locations;
- source files/sheets/columns/counts;
- normalization and identifier rules;
- E3C UTF-16/NFC offsets and Layer 1-only policy;
- `len(canonical_text.split())` and short/medium/long thresholds;
- exact feature, rational scaling, maximin, seed, tie, and override rules;
- Bodypart as a proxy rather than true HPO organ-system coverage;
- CSC/GSC empty evidence spans and deferred HPO revision;
- no translation, mapping, review, provider, or release in this phase;
- local-only real-source artifacts and licensing limitations.

- [ ] **Step 5: Run the complete offline verification**

Run:

```powershell
uv sync --locked --all-groups
uv lock --check
uv run ruff check .
uv run mypy
uv run python scripts/check_repository_safety.py
uv run pytest --cov=phentrieve_benchmark --cov=scripts --cov-report=term-missing --cov-fail-under=90
uv run phentrieve-benchmark --help
git diff --check
git status --short
```

Expected:

- all offline tests and static checks pass;
- coverage remains at least 90%;
- repository safety passes;
- CLI lists all new commands;
- only the intended documentation, recipe, code, tests, inventory, and
  selection files are pending;
- no `.artifacts` path is tracked.

- [ ] **Step 6: Commit final outputs and documentation**

```powershell
git add README.md .github/workflows/ci.yml datasets tests/contracts/test_dataset_documentation.py tests/contracts/test_tracked_dataset_outputs.py
git commit -m "docs: publish prepared dataset metadata"
```

- [ ] **Step 7: Re-run final verification from clean Git state**

```powershell
uv run ruff check .
uv run mypy
uv run python scripts/check_repository_safety.py
uv run pytest --cov=phentrieve_benchmark --cov=scripts --cov-report=term-missing --cov-fail-under=90
git diff --check
git status --short
```

Expected: all commands exit zero and `git status --short` emits nothing.

The next phase may start UMLS-to-HPO mapping and HPO revision. It must consume
the immutable artifacts created here and must not modify these canonical source
or selection records in place.

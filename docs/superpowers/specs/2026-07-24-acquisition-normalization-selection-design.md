# Acquisition, Normalization, and Selection Design

## 1. Purpose

This phase turns pinned public E3C and RAG-HPO source archives into verified,
canonical local artifacts. It provides three independently executable dataset
targets:

- `e3c`;
- `csc`;
- `gsc`.

CSC and GSC share one acquired RAG-HPO source snapshot, but normalization,
artifacts, hashes, run manifests, and failure states remain separate. E3C is
acquired and normalized independently. The E3C target additionally produces
the first feasibility cohort containing 10 English, 10 French, and 10 Spanish
Layer 1 reports.

This phase does not translate text, revise HPO identifiers, map UMLS concepts
to HPO, or publish a dataset release.

## 2. Confirmed Scope

The implementation includes:

- real downloads of pinned public source archives;
- exact SHA-256 and size verification before extraction;
- safe archive extraction into ignored local storage;
- source-specific E3C and RAG-HPO adapters;
- complete normalization of the CSC and GSC targets;
- normalization of E3C Layer 1 for English, French, and Spanish only;
- a deterministic E3C feasibility selection of 30 reports;
- separate commands for acquisition, normalization, and selection;
- a per-target convenience command that orchestrates the required stages;
- offline CI tests using local fixtures;
- a separate explicit live-download smoke test;
- human-readable and machine-readable documentation for every target.

The following work is explicitly deferred:

- E3C Layer 2 and Layer 3;
- Italian and Basque E3C reports;
- the 90-report E3C pilot cohort;
- UMLS-to-HPO mapping;
- CSC/GSC HPO revision decisions;
- translation and translation review;
- annotation adaptation and review;
- public release construction.

## 3. Upstream Source Locks

### 3.1 E3C

The source is the official `hltfbk/E3C-Corpus` repository at tag `v2.0.0`,
currently resolving to commit:

```text
f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc
```

Only these paths are eligible:

```text
data_annotation/English/layer1/*.xml
data_annotation/French/layer1/*.xml
data_annotation/Spanish/layer1/*.xml
```

The adapter must observe exactly 84 English, 81 French, and 81 Spanish Layer 1
documents. Other languages and layers are ignored by an explicit path policy,
not by repository traversal accident.

### 3.2 RAG-HPO

RAG-HPO has no equivalent immutable dataset release. The source is therefore
locked to commit:

```text
080fc3a04c91ee45c8986076765f4d4b4f14ddd9
```

The pinned snapshot contains the benchmark inputs and alignment workbook,
including:

```text
Test_Cases.csv
RAG-HPO Tests and Data Analysis copy.xlsx
```

The recipe declares the exact workbook sheets and columns used for CSC and
GSC. Sheet and column discovery by fuzzy matching is forbidden. A later
upstream update requires a new recipe version, archive digest, adapter
contract, and regression fixtures.

### 3.3 Archive identity

Each recipe stores:

- canonical archive URL;
- tag or full 40-character commit;
- expected byte length or an explicit upper bound;
- exact archive SHA-256;
- archive format;
- expected top-level directory;
- allowed source paths;
- adapter and source-schema versions;
- licensing identity.

GitHub-generated archive URLs are never treated as identities by themselves.
The source commit and downloaded-byte SHA-256 jointly identify the acquired
snapshot. A recipe cannot contain `latest`, a branch name, a missing digest, or
an all-zero placeholder digest.

## 4. Repository Layout

Tracked dataset definitions use this structure:

```text
datasets/
├── e3c-de/
│   ├── dataset.yaml
│   ├── README.md
│   ├── LICENSES.md
│   └── selection-policy.md
└── raghpo/
    ├── source.yaml
    ├── README.md
    ├── LICENSES.md
    ├── csc/
    │   ├── dataset.yaml
    │   └── README.md
    └── gsc/
        ├── dataset.yaml
        └── README.md
```

This retains the existing single RAG-HPO source recipe while making CSC and
GSC independent dataset targets with separate target recipes and
documentation.

Implementation modules are separated by responsibility:

```text
src/phentrieve_benchmark/
├── acquisition/
│   ├── recipes.py
│   ├── downloader.py
│   └── archives.py
├── normalization/
│   ├── contracts.py
│   ├── e3c.py
│   └── raghpo.py
├── selection/
│   ├── contracts.py
│   ├── metrics.py
│   └── e3c.py
└── pipeline/
    └── prepare.py
```

Files remain focused: acquisition has no dataset parsing, adapters have no
network access, selection has no archive access, and orchestration contains no
source-specific parsing.

## 5. Commands and Execution Units

The CLI exposes:

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
```

`prepare csc` and `prepare gsc` reuse the same verified RAG-HPO source artifact
when its full identity matches. They never share normalized output artifacts.

`prepare e3c` performs acquisition, normalization, and the
`feasibility-30` selection. A `prepare all` command is not required in this
phase.

Every command:

- is independently restartable;
- emits a run manifest;
- records source, code, config, adapter, input, and output identities;
- reuses an artifact only when every semantic identity matches;
- fails closed rather than silently changing a source, target, or parser.

## 6. Acquisition

Downloads are streamed with:

- HTTPS only;
- bounded connect and read timeouts;
- a declared maximum byte count;
- incremental SHA-256 calculation;
- an atomic temporary file;
- no credential-bearing URL or header in logs;
- no automatic source fallback.

Redirects are allowed only for the declared GitHub archive flow and remain
HTTPS. A response exceeding its limit, a length mismatch, an interrupted
stream, or a digest mismatch is rejected before publication to the artifact
store.

Archive extraction:

- supports only the recipe-declared ZIP or TAR variant;
- rejects absolute paths, drive-qualified paths, `..`, NULs, duplicate
  normalized paths, links, devices, FIFOs, sockets, and unsupported members;
- applies total-file-count, per-file-size, and expanded-size limits;
- verifies the expected top-level directory and allowed source inventory;
- never writes outside a fresh ignored staging directory;
- publishes source bytes through the content-addressed artifact store only
  after complete validation.

Raw archives, staging directories, extracted files, and clinical text remain
under `.artifacts/`. They are never Git-tracked.

## 7. Normalization Contracts

### 7.1 Common outputs

Each target produces:

- canonical JSONL `Document` records;
- canonical JSONL `SourceAnnotationSet` records for E3C source-native
  annotations;
- canonical JSONL `AnnotationSet` records for source HPO annotations in CSC
  and GSC;
- a text-free source inventory;
- a text-free normalization manifest;
- a run manifest;
- a warnings summary using stable codes only.

Canonical JSONL uses stable record identities and the existing serialization
contract. Clinical text is stored only as a content-addressed artifact.

`SourceAnnotationSet` is introduced in this phase because E3C source
annotations are not yet HPO annotations. It contains the exact document hash,
source schema identity, and immutable source annotations. A source annotation
contains its upstream annotation ID, source-native type, optional source
concept identifier such as a UMLS CUI, assertion/factuality attributes, and
validated evidence spans. It cannot be used where the existing HPO
`AnnotationSet` is required. The later UMLS-to-HPO phase consumes
`SourceAnnotationSet` and produces a new HPO `AnnotationSet`.

The normalization manifest records:

- target ID and schema version;
- source recipe and archive identities;
- source-relative path identity;
- adapter and configuration identities;
- counts by language and record type;
- input and output artifact hashes;
- warning codes and counts;
- code identity;
- creation run identity.

### 7.2 Text normalization

Text normalization is limited to:

1. decoding with the source-declared encoding;
2. Unicode NFC normalization;
3. CRLF and CR conversion to LF;
4. removal of one terminal source-format newline only when the adapter
   contract declares it non-content.

Whitespace, punctuation, capitalization, and sentence boundaries are not
otherwise rewritten. If an operation changes character offsets, the adapter
must emit and validate an offset map. Source evidence spans must still satisfy:

```text
canonical_text[start_char:end_char] == text_snippet
```

### 7.3 E3C adapter

The E3C adapter:

- parses XML without DTDs, external entities, network access, or recovery mode;
- accepts only English, French, and Spanish Layer 1 paths;
- derives `source_case_id` from the canonical upstream filename stem;
- preserves source annotation identifiers and source-native annotation types;
- validates every span against canonical text;
- rejects duplicate case IDs, malformed offsets, unknown structural variants,
  and count mismatches;
- creates native-language `Document` records with
  `translation_status=native`;
- creates `SourceAnnotationSet` records rather than misclassifying UMLS and
  source-native annotations as HPO annotations.

E3C annotations remain source annotations. This phase does not claim that UMLS
concepts have already been mapped to HPO.

### 7.4 CSC and GSC adapters

The RAG-HPO adapter reads only recipe-declared files, workbook sheets, and
columns. It creates distinct CSC and GSC targets while retaining upstream case
identifiers.

For each target it:

- canonicalizes source text into native `Document` records;
- converts explicit HPO identifiers into `Annotation` records;
- preserves provided evidence spans when present and validates them;
- rejects malformed HPO IDs, duplicated case IDs, mismatched workbook rows,
  ambiguous case joins, and silently missing required columns;
- records source rows without HPO evidence as explicit warnings rather than
  inventing spans;
- uses the declared manuscript ontology context `v2026-06-23` without
  asserting that identifiers have passed the later HPO-revision policy.

CSC and GSC normalization is complete in this phase; HPO validity,
`alt_id`, replacement, ambiguity, and removal decisions belong to the
subsequent revision phase.

## 8. E3C Inventory and Length Measurement

The eligible inventory contains all and only the 246 EN/FR/ES Layer 1 reports.
For every case it records no clinical text, but includes:

- source case ID;
- language;
- canonical document SHA-256;
- Unicode code-point count;
- whitespace-token count;
- source sentence count when structurally explicit;
- counts for each source-native annotation type;
- annotation density per 100 whitespace tokens;
- event and factuality-complexity counts;
- Bodypart-marker count as a source-native proxy;
- length stratum;
- stable warning codes.

Whitespace-token count is:

```python
len(canonical_text.split())
```

Length strata are:

- `short`: fewer than 200 tokens;
- `medium`: 200 through 400 tokens inclusive;
- `long`: more than 400 tokens.

No upper-length exclusion is introduced. These thresholds follow the published
E3C grouping, but the pipeline computes them itself from canonical source text.

Bodypart markers are documented only as a source-native diversity proxy. This
phase does not report true HPO-based organ-system coverage.

## 9. Feasibility Selection

### 9.1 Cohort contract

`e3c-de-feasibility-30-v1` contains exactly:

- 10 English Layer 1 reports;
- 10 French Layer 1 reports;
- 10 Spanish Layer 1 reports.

Within each language, the target allocation is:

- 3 short;
- 4 medium;
- 3 long.

If a pinned source lacks enough eligible reports for a stratum, selection
fails. It does not silently rebalance strata.

### 9.2 Feature vector

Within each language and length stratum, selection uses a versioned feature
vector derived only from the text-free inventory:

- whitespace-token count;
- total annotation density;
- per-type density for `CLINENTITY`, `EVENT`, `ACTOR`, `BODYPART`, `TIMEX3`,
  and `RML` when present;
- number of distinct source annotation types;
- factuality and negation marker density;
- Bodypart-marker density.

Each numeric feature is min-max scaled within its language and stratum. When
all candidates share one value, the scaled feature is zero.

### 9.3 Deterministic diversity algorithm

For each language and stratum:

1. Calculate the scaled feature vector for every eligible case.
2. Choose the first case with the greatest Euclidean distance from the stratum
   centroid.
3. Repeatedly choose the case maximizing its minimum Euclidean distance to the
   already selected cases.
4. Resolve every tie by the ascending SHA-256 of
   `selection-seed + "\0" + source_case_id`.
5. Sort the final manifest records by language, stratum, and source case ID.

The recipe declares the fixed seed and algorithm ID. Repeating selection from
the same inventory must produce byte-identical canonical output.

### 9.4 Overrides

The selection configuration supports explicit include and exclude overrides.
Every override contains:

- source case ID;
- action;
- non-empty rationale;
- author role;
- decision date.

Overrides are applied before automatic slot filling and must preserve all
language and stratum counts. Conflicting, duplicated, unknown, or count-breaking
overrides fail. The first feasibility selection uses an empty override list.

The selection manifest contains only IDs, metrics, identities, seed,
algorithm version, overrides, and the final aggregate hash. It contains no
clinical text.

## 10. Documentation Contract

Every target README documents:

- purpose and target boundaries;
- upstream repository and exact source pin;
- archive checksum and acquisition command;
- expected source files, sheets, columns, and counts;
- normalization operations in order;
- adapter and schema versions;
- identifier construction;
- output artifacts and hashes;
- warnings and failure behavior;
- local artifact locations;
- reproducible commands;
- known limitations and deferred work.

`LICENSES.md` and the machine-readable recipe record:

- upstream links;
- exact release or commit;
- direct license reference;
- access date;
- redistribution and derivative-work statements;
- project distribution decision;
- unresolved licensing questions.

E3C `selection-policy.md` additionally documents:

- Layer 1-only eligibility;
- EN/FR/ES counts;
- token formula and thresholds;
- every selection feature;
- scaling and distance calculations;
- fixed seed and tie-breaking;
- override semantics;
- the Bodypart proxy limitation.

Generated text-free audit reports summarize counts, languages, length strata,
warnings, and hashes. Generated documentation never includes source text.

## 11. Error, Resume, and Idempotency Semantics

The phase fails closed for:

- digest or length mismatch;
- unsafe or unexpected archive content;
- missing required files, sheets, columns, or XML structure;
- unknown source schema;
- duplicate or unstable identities;
- source count mismatch;
- invalid Unicode decoding;
- span mismatch;
- malformed HPO identifiers;
- ambiguous CSC/GSC joins;
- incomplete normalization;
- incorrect selection counts or strata;
- conflicting overrides.

Failure never publishes an output as complete. Existing files alone do not
make work reusable.

Resume requires identical:

- source recipe and archive digest;
- target and adapter version;
- normalization or selection configuration;
- code identity;
- input artifact identities;
- selection seed and override identity where applicable.

## 12. Test Strategy

### 12.1 Offline CI

CI performs no external source download. It uses small, structurally faithful
fixtures and a local HTTP server to test:

- streaming download, timeouts, limits, and checksum validation;
- interrupted and corrupted downloads;
- safe ZIP and TAR extraction;
- traversal, link, duplicate-path, special-file, and expansion-limit rejection;
- strict recipe validation;
- E3C XML parsing and count contracts;
- RAG-HPO CSV/workbook sheet and column contracts;
- CSC/GSC separation;
- Unicode and line-ending normalization;
- span preservation and offset-map validation;
- deterministic IDs and canonical JSONL;
- inventory metric calculations;
- length thresholds at 199, 200, 400, and 401 tokens;
- deterministic selection and tie-breaking;
- empty and invalid override behavior;
- resume identity checks;
- documentation and licensing-file presence;
- repository safety and absence of tracked clinical fixtures.

Clinical fixture text is generated at test runtime or stored only in explicitly
approved synthetic fixture form that satisfies repository-safety policy.

### 12.2 Live-download smoke test

An explicit, non-default smoke command downloads the real pinned archives and:

- verifies the recipe digest and size;
- validates archive structure;
- confirms E3C Layer 1 counts of 84/81/81;
- confirms required RAG-HPO files, sheets, and columns;
- runs normalization into ignored artifacts;
- verifies deterministic rerun hashes.

It is excluded from normal CI and requires an explicit user invocation or
manual workflow dispatch. It performs no paid-provider call.

## 13. Acceptance Criteria

This phase is complete when:

1. E3C and RAG-HPO real archives can be acquired from immutable source pins and
   verified against committed SHA-256 values.
2. Acquisition output remains entirely under ignored artifact storage.
3. `normalize csc`, `normalize gsc`, and `normalize e3c` run independently.
4. CSC and GSC share only the verified source snapshot, not normalized state.
5. E3C normalization contains exactly 84 English, 81 French, and 81 Spanish
   Layer 1 reports and no other layer or language.
6. CSC and GSC produce separate canonical document and annotation artifacts.
7. The E3C inventory deterministically measures canonical text and source
   annotation complexity without storing text in its manifest.
8. `select e3c --cohort feasibility-30` produces exactly 10 cases per language
   and a 3/4/3 short/medium/long allocation per language.
9. The initial selection has no overrides and reruns byte-identically.
10. Every target contains complete recipe, usage, normalization, selection
    where applicable, limitation, and licensing documentation.
11. Offline CI passes without external downloads, credentials, or provider
    calls.
12. The explicit live smoke test validates real upstream structure and
    deterministic local output.

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

This phase does not translate text, map UMLS concepts to HPO, manually
adjudicate obsolete or ambiguous HPO replacements, or publish a dataset
release. It does audit the existing CSC/GSC HPO identifiers against one pinned
HPO release and creates a separate immutable revision artifact.

## 2. Confirmed Scope

The implementation includes:

- real downloads of pinned public source archives;
- exact SHA-256 and size verification before extraction;
- safe archive extraction into ignored local storage;
- source-specific E3C and RAG-HPO adapters;
- complete normalization of the CSC and GSC targets;
- normalization of E3C Layer 1 for English, French, and Spanish only;
- a deterministic E3C feasibility selection of 30 reports;
- a deterministic CSC/GSC HPO audit against release `v2026-06-23`;
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
- manual adjudication of obsolete, ambiguous, `consider`, or unknown HPO IDs;
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

The RAG-HPO source lock was inspected on 2026-07-24. The two required blobs are
ordinary Git blobs rather than Git LFS pointers; the CSV is 218,127 bytes and
the workbook is 369,741 bytes at the pinned commit.

The exact source tables are:

| Target | Sheet or file | Required columns | Data rows |
| --- | --- | --- | ---: |
| CSC | `Test_Cases.csv` | `Case`, `clinical_note` | 116 |
| CSC | `CSC Input` | `Case`, `clinical_note` | 116 |
| CSC | `CSC Manual Annotations` | `Patient ID`, `hpo_description`, `hpo_term` | 1,789 |
| GSC | `GSC Input` | `patient_id`, `ID`, `clinical_note` | 114 |
| GSC | `GSC Manual Annotations ` | `Patient ID`, `ID`, `hpo_description`, `hpo_term`, `Category` | 1,012 |

The trailing space in the upstream `GSC Manual Annotations ` sheet name is
intentional and part of the pinned source contract. The CSC CSV and `CSC Input`
sheet must agree on case IDs and canonical clinical-note hashes; disagreement
fails normalization. Header rows are not included in the data-row counts.

### 3.3 Archive identity

Each recipe stores:

- canonical archive URL;
- tag or full 40-character commit;
- exact expected byte length;
- a separate maximum download byte count;
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

Recipes use direct commit-addressed `https://codeload.github.com/...` archive
URLs. Acquisition does not follow HTTP redirects. The implementation phase
downloads each archive once, records its exact byte length and SHA-256 in the
recipe, and then proves that the committed lock reproduces before adapter work
begins.

## 4. Repository Layout

Tracked dataset definitions use this structure:

```text
datasets/
├── e3c-de/
│   ├── dataset.yaml
│   ├── README.md
│   ├── LICENSES.md
│   ├── license-evidence.yaml
│   ├── selection-policy.md
│   ├── inventories/
│   │   └── e3c-v2.0.0-l1-en-fr-es-v1.json
│   └── selections/
│       └── e3c-de-feasibility-30-v1.json
└── raghpo/
    ├── source.yaml
    ├── README.md
    ├── LICENSES.md
    ├── license-evidence.yaml
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
- emits a separate text-free provenance link from its deterministic subject
  artifact to that run manifest;
- records source, code, config, adapter, input, and output identities;
- reuses an artifact only when every semantic identity matches;
- fails closed rather than silently changing a source, target, or parser.

Parsed recipe values are validated by strict typed models. Configuration
identity is the canonical JSON hash of the validated semantic model, not a hash
of YAML formatting, comments, or mapping order.

## 6. Acquisition

Downloads are streamed with:

- HTTPS only;
- bounded connect and read timeouts;
- a declared maximum byte count;
- incremental SHA-256 calculation;
- an atomic temporary file;
- no credential-bearing URL or header in logs;
- no automatic source fallback.

Redirects are rejected because recipes use direct commit-addressed codeload
URLs. A response exceeding its limit, a length mismatch, an interrupted stream,
or a digest mismatch is rejected before publication to the artifact store.

Archive extraction:

- supports only the recipe-declared ZIP or TAR variant;
- rejects absolute paths, drive-qualified paths, `..`, NULs, duplicate
  normalized paths, links, devices, FIFOs, sockets, and unsupported members;
- applies total-file-count, per-file-size, and expanded-size limits;
- verifies the expected top-level directory and allowed source inventory;
- never writes outside a fresh ignored staging directory;
- publishes source bytes through the content-addressed artifact store only
  after complete validation.

Because XLSX is itself a ZIP package, workbook parsing independently enforces
member-count, per-member-size, total-expanded-size, path, duplicate-member, and
compression-ratio limits. It rejects encrypted members, macros, external
relationships, external data connections, and unsupported package parts before
reading workbook cells.

Raw archives, staging directories, extracted files, and clinical text remain
under `.artifacts/`. They are never Git-tracked.

Successful acquisition publishes a deterministic, text-free source-snapshot
manifest containing the recipe identity, source commit, archive byte length
and SHA-256, archive-format identity, and the sorted extracted member paths,
sizes, and hashes. It contains no run ID, timestamp, host, or environment
field. The acquisition run manifest and `ProvenanceRunLink` remain separate.

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
- a separate text-free provenance-run link;
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

The source-annotation contract is:

```text
SourceAnnotationSet
  annotation_set_id
  document_sha256
  source_schema_id
  annotations[]
  relations[]

SourceAnnotation
  source_annotation_id
  source_type
  source_concept_id?
  attributes[]
  evidence_spans[]

SourceRelation
  source_relation_id
  source_type
  arguments[]
  attributes[]

SourceAttribute
  namespace
  name
  value

SourceRelationArgument
  role
  referenced_annotation_id
```

All collections that are set-like are normalized and sorted by their declared
stable identity. Duplicate annotation, relation, attribute, and argument
identities fail. Relation arguments must reference annotations in the same
set. Attribute values preserve source semantics but remain in ignored
content-addressed artifacts, never tracked manifests or logs.

The normalization manifest records:

- target ID and schema version;
- source recipe and archive identities;
- source-relative path identity;
- adapter and configuration identities;
- counts by language and record type;
- input and output artifact hashes;
- warning codes and counts;
- code identity.

The normalization manifest is deterministic and contains no run ID, timestamp,
host, or environment field. Execution identity belongs only to the run
manifest and the separate linkage record, so identical reruns produce
byte-identical normalized artifacts and normalization manifests.

All stages use one linkage contract:

```text
ProvenanceRunLink
  schema_version = provenance-run-link/v1
  subject_role
  subject_sha256
  run_manifest_sha256
```

`subject_role` is a closed value such as `source-snapshot`,
`normalization-manifest`, or `selection-manifest`. Link records are execution
provenance and never participate in the deterministic subject identity.

### 7.2 Text normalization

Text normalization is limited to:

1. decoding with the source-declared encoding;
2. Unicode NFC normalization;
3. CRLF and CR conversion to LF;
4. removal of one terminal source-format newline only when the adapter
   contract declares it non-content.

An empty canonical clinical document is invalid. This also guarantees a
non-zero denominator for token-density features.

Whitespace, punctuation, capitalization, and sentence boundaries are not
otherwise rewritten. If an operation changes character offsets, the adapter
must emit and validate an offset map. Source evidence spans must still satisfy:

```text
canonical_text[start_char:end_char] == text_snippet
```

### 7.3 E3C adapter

The E3C adapter:

- parses the pinned WebAnno/UIMA XMI 2.0 structure without DTDs, external
  entities, network access, or recovery mode;
- accepts only English, French, and Spanish Layer 1 paths;
- derives language solely from the exact allowed source path, never from
  optional or `x-unspecified` XMI language metadata;
- derives `source_case_id` from the canonical upstream filename stem;
- preserves source annotation identifiers and source-native annotation types;
- validates every span against canonical text;
- rejects duplicate `(language, source_case_id)` identities, malformed offsets,
  unknown structural variants, and count mismatches;
- creates native-language `Document` records with
  `translation_status=native`;
- creates `SourceAnnotationSet` records rather than misclassifying UMLS and
  source-native annotations as HPO annotations.

The recipe contains an exact XMI type registry. Token and sentence elements
are structural inputs used for validation and metrics; generic POS,
dependency, and WebAnno metadata are not emitted as benchmark annotations.
The semantic output includes the declared E3C types `CLINENTITY`, `EVENT`,
`ACTOR`, `BODYPART`, `TIMEX3`, and `RML`, plus the declared temporal and
pertains-to relation types. An unknown semantic custom type fails until the
registry and adapter version are deliberately revised.

E3C identities are:

```text
source_case_id     = upstream XML filename stem
document_id        = e3c:v2.0.0:<language>:<source_case_id>:native
annotation_set_id  = e3c:v2.0.0:<language>:<source_case_id>:source:v1
```

E3C annotations remain source annotations. This phase does not claim that UMLS
concepts have already been mapped to HPO.

UIMA XMI offsets are UTF-16 code-unit offsets, while the benchmark contract
uses Unicode code-point offsets. The adapter therefore:

1. extracts the exact `cas:Sofa` string;
2. converts every UIMA boundary from UTF-16 code units to source Unicode
   code-point indices;
3. rejects a boundary inside a surrogate pair;
4. composes that map with the declared NFC and line-ending normalization map;
5. validates the resulting benchmark span against canonical text.

Treating UIMA offsets as Python string indices is forbidden and covered by
non-BMP regression fixtures.

### 7.4 CSC and GSC adapters

The RAG-HPO adapter reads only recipe-declared files, workbook sheets, and
columns. It creates distinct CSC and GSC targets while retaining upstream case
identifiers.

For each target it:

- parses `Test_Cases.csv` as UTF-8 with an optional BOM and RFC 4180 quoting;
- parses the XLSX package without formulas, macros, external links, or external
  data refresh;
- requires the exact table names, columns, and row counts declared in the
  source lock;
- canonicalizes source text into native `Document` records;
- converts explicit HPO identifiers into `Annotation` records;
- preserves provided evidence spans when present and validates them, but never
  invents a span by label or substring matching;
- rejects malformed HPO IDs, duplicated case IDs, mismatched workbook rows,
  ambiguous case joins, and silently missing required columns;
- records source rows without HPO evidence as explicit warnings rather than
  inventing spans;
- uses the declared manuscript ontology context `v2026-06-23` without
  asserting that identifiers have passed the later HPO-revision policy.

RAG-HPO identities retain the exact upstream identifiers. CSC has one
upstream `Case` identity. GSC identifies a document by the exact composite
`(patient_id, ID)` key while retaining `patient_id` as its source case:

```text
CSC source_case_id     = Case
CSC document_id        = raghpo:<source-commit>:csc:<Case>:native
CSC annotation_set_id  = raghpo:<source-commit>:csc:<Case>:hpo:v1

GSC source_case_id     = patient_id
GSC document_id        = raghpo:<source-commit>:gsc:<patient_id>:<ID>:native
GSC annotation_set_id  = raghpo:<source-commit>:gsc:<patient_id>:<ID>:hpo:v1
```

Each upstream value remains exact in its record field. When embedded into a
colon-delimited constructed ID, its NFC UTF-8 bytes use injective percent
encoding, so punctuation inside one component cannot create an ID collision.

CSC joins `Test_Cases.csv` and `CSC Input` on `Case`, then joins manual
annotations by exact `Patient ID`. GSC joins input and manual rows on the exact
composite key `(patient_id, ID)` / `(Patient ID, ID)`. IDs are converted from
their declared CSV/XLSX scalar representation only; fuzzy, case-insensitive,
or punctuation-insensitive joins are forbidden.

An `hpo_term` cell is split only on an ASCII comma, each component is stripped
of surrounding ASCII whitespace, and every component must then match
`HP:[0-9]{7}`. The pinned CSC sheet contains both whitespace-padded IDs and six
two-ID cells, so this lexical normalization is part of the source adapter
contract. One row with two IDs produces two deterministic `Annotation`
records. GSC cells currently contain one ID each.

The manual tables do not provide trustworthy character offsets. Their
annotations therefore have empty `evidence_spans`; the adapter does not search
`hpo_description` in clinical text. To preserve the complete pinned source
record without overloading the HPO model, each target also writes an ignored
canonical `RagHpoSourceAnnotationRecord` sidecar containing:

```text
source_row_id
source_case_id
secondary_id?
hpo_description
raw_hpo_term
category?
derived_annotation_ids[]
```

The sidecar may contain source text and remains content-addressed under
`.artifacts/`. Text-free manifests contain only its artifact hash, schema
identity, row count, and warning counts.

CSC and GSC source normalization remains immutable. Section 14 defines a
separate HPO audit and revision artifact; it never edits these source
annotation sets in place.

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

Each numeric feature is min-max scaled within its language and stratum using
exact rational arithmetic. Counts are integers; densities are stored as an
integer numerator and token-count denominator. When all candidates share one
value, the scaled feature is exactly zero. Binary floating-point values never
participate in selection or its manifest. All rational values are serialized
in reduced form with a non-negative numerator and a positive denominator.
The versioned feature schema defines the exact source types and attributes
counted for every marker feature; undeclared attributes never affect
selection.

### 9.3 Deterministic diversity algorithm

For each language and stratum:

1. Calculate the scaled feature vector for every eligible case.
2. Choose the first case with the greatest squared Euclidean distance from the
   stratum centroid.
3. Repeatedly choose the case maximizing its minimum squared Euclidean
   distance to the already selected cases.
4. Resolve every tie by the ascending SHA-256 of
   the UTF-8 bytes of `selection-seed + "\0" + source_case_id`, comparing the
   32 digest bytes lexicographically.
5. Sort the final manifest records by language, stratum, and source case ID.

The recipe declares the fixed seed and algorithm ID. Repeating selection from
the same inventory must produce byte-identical canonical output.

The first cohort uses:

```text
algorithm_id = e3c-diversity-maximin/v1
selection_seed = phentrieve-e3c-de-feasibility-30-v1
```

Distances are compared as exact fractions without calculating square roots.
The manifest stores raw integer metrics and rational numerator/denominator
pairs, never rounded selection scores.

### 9.4 Overrides

The selection configuration supports explicit include and exclude overrides.
Every override contains:

- source case ID;
- action;
- non-empty rationale;
- author role;
- decision date.

An included case must be eligible for its existing language and stratum, is
preselected, and consumes one slot in that stratum. An excluded case is removed
before automatic filling. The maximin algorithm fills the remaining slots
against the already included cases. Overrides must preserve all language and
stratum counts. Conflicting, duplicated, unknown, excessive-include, or
insufficient-pool overrides fail. The first feasibility selection uses an
empty override list.

The selection manifest contains only IDs, metrics, identities, seed,
algorithm version, overrides, and the final aggregate hash. It contains no
clinical text or volatile execution fields. The eligible inventory and
selection manifest are canonical tracked records; their run linkage remains a
separate ignored execution-provenance artifact.

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

`license-evidence.yaml` is the authoritative machine-readable licensing
record; the dataset recipe refers to its semantic hash. `LICENSES.md` is the
human-readable rendering and must agree with it.

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
- UTF-16-to-code-point conversion with non-BMP and invalid-surrogate-boundary
  fixtures;
- nested XLSX package limits and external-relationship rejection;
- deterministic IDs and canonical JSONL;
- deterministic source-snapshot, normalization, inventory, selection, and
  provenance-link contracts;
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
- verifies deterministic subject hashes on rerun while allowing run manifests
  and provenance links to differ.

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
6. E3C emits source-native `SourceAnnotationSet` artifacts without claiming
   that their concepts are already HPO annotations.
7. CSC and GSC produce separate canonical document, HPO annotation, and
   source-row sidecar artifacts.
8. The E3C inventory deterministically measures canonical text and source
   annotation complexity without storing text in its manifest.
9. `select e3c --cohort feasibility-30` produces exactly 10 cases per language
   and a 3/4/3 short/medium/long allocation per language.
10. The initial selection has no overrides and reruns byte-identically.
11. Deterministic subject manifests contain no volatile execution fields and
    link to separate run manifests only through `ProvenanceRunLink` records.
12. Every target contains complete recipe, usage, normalization, selection
    where applicable, limitation, and licensing documentation.
13. Offline CI passes without external downloads, credentials, or provider
    calls.
14. The explicit live smoke test validates real upstream structure and
    deterministic local output.
15. The exact HPO `v2026-06-23` asset is verified by size and SHA-256 before
    parsing.
16. Every CSC/GSC HPO identifier is classified as active, alternate,
    obsolete with replacement, obsolete ambiguous/unresolved, unknown, or
    invalid.
17. Active IDs remain unchanged, alternate IDs resolve deterministically to
    their primary active ID, and every other non-active status requires manual
    review without silently changing the source annotation.

## 14. Pinned HPO Audit and Revision

The ontology source is the official HPO release `v2026-06-23`. The pipeline
uses the release asset:

```text
URL:
https://github.com/obophenotype/human-phenotype-ontology/releases/download/v2026-06-23/hp.obo

byte_length:
11222341

sha256:
a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b
```

The release tag, asset URL, exact byte length, and SHA-256 are configuration.
`latest` is forbidden. A later HPO release creates a new audit and revision;
it never overwrites the `v2026-06-23` result.

The parsed index contains primary HPO IDs, labels, active/obsolete state,
`alt_id`, `replaced_by`, and `consider`. Duplicate primary IDs, one alternate
ID assigned to multiple terms, alternate/primary collisions, malformed HPO
IDs, and replacement cycles fail closed.

Each source annotation produces one immutable decision:

```text
HpoRevisionDecision
  source_annotation_id
  source_hpo_id
  ontology_release
  ontology_sha256
  status
  canonical_hpo_id?
  proposed_hpo_ids[]
  replacement_chain[]
  requires_manual_review
  reason_code
```

The closed statuses are:

- `active`: the primary ID is active; `canonical_hpo_id` equals the source ID;
- `alt_id`: the source ID uniquely identifies an active primary term and is
  deterministically canonicalized;
- `obsolete_replaced`: the obsolete term has exactly one explicit
  `replaced_by`; it is recorded as a proposal and requires manual review;
- `obsolete_ambiguous`: multiple `replaced_by` or any `consider` candidates
  require manual review;
- `obsolete_unresolved`: no replacement candidate exists;
- `unknown`: the well-formed HPO ID is absent from the pinned ontology;
- `invalid_format`: the value is not exactly `HP:[0-9]{7}`.

Only `active` and `alt_id` populate `canonical_hpo_id` automatically.
`replaced_by` and `consider` never silently alter the gold annotation. Source
descriptions may be retained in ignored curation packets but never drive an
automatic ID replacement.

The stage emits:

- ignored canonical decision JSONL for CSC and GSC separately;
- a deterministic text-free audit manifest with counts by target and status;
- an optional revised `AnnotationSet` containing only active and deterministically
  resolved alternate IDs;
- a separate run manifest and `ProvenanceRunLink`;
- a manual-curation queue for every decision whose
  `requires_manual_review=true`.

The HPO parser and audit are fully covered by offline synthetic fixtures.
The real HPO download and real CSC/GSC audit run only through the explicit
live-source workflow.

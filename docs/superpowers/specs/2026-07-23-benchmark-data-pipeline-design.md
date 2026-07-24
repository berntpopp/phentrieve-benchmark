# Phentrieve Benchmark Data Pipeline Design

**Status:** Approved design

**Date:** 2026-07-23

**Repository:** `berntpopp/phentrieve-benchmark`

## 1. Summary

This repository will build, curate, validate, and package benchmark datasets for
Phentrieve while preserving complete data provenance. It will initially cover:

- revision of the RAG-HPO CSC and GSC annotations against an explicitly pinned
  Human Phenotype Ontology (HPO) release;
- a German E3C Layer 1 parallel-text benchmark derived from English, French,
  and Spanish source reports;
- deterministic derivation of single-term benchmark records from accepted
  document annotations;
- release manifests and adapters for the existing Phentrieve benchmark input
  format.

The repository will not initially orchestrate Phentrieve inference or scoring.
That functionality remains in the Phentrieve manuscript branch until a later,
separately designed migration.

## 2. Scope

### 2.1 Goals

- Make every dataset version reproducible from pinned upstream sources.
- Keep source acquisition, text translation, concept mapping, target-language
  span adaptation, reviews, and human curation as separate stages.
- Track exact source, input, gold-standard, configuration, code, prompt,
  provider, model, and ontology identities.
- Prevent unapproved paid API calls.
- Prevent third-party text from entering the public Git repository before
  redistribution has been explicitly approved.
- Produce compact, observable, resumable pipeline runs.
- Export data in the format already consumed by Phentrieve.
- Preserve a clean future interface for benchmark-run orchestration without
  duplicating the current manuscript implementation.

### 2.2 Non-goals

- Running or scoring Phentrieve benchmarks in the first implementation.
- Treating translated E3C reports as native German clinical narratives.
- Publishing CSC, GSC, E3C, translations, or curated derivatives before the
  corresponding licensing decision is recorded.
- Automatically approving model-generated translations or annotations as gold
  data.
- Pooling native and translated E3C results into one headline score.
- Building a graphical curation application in the first implementation.
- Introducing DVC, DataLad, Snakemake, or Nextflow before the Git-native
  workflow proves insufficient.

## 3. Repository Boundaries

The public Git repository contains:

- Python source code and tests;
- schemas and validation rules;
- dataset recipes and selection manifests;
- prompts and provider configuration without secrets;
- mapping, annotation, curation, and release policies;
- text-free run records and content hashes;
- data cards and licensing evidence;
- public recipe bundles that reproduce restricted datasets locally.

The following remain local and ignored by Git until an explicit redistribution
decision permits publication:

- downloaded upstream datasets;
- normalized clinical text;
- generated translations;
- raw provider responses;
- actual curation packets;
- assembled restricted dataset bundles;
- credentials and local provider configuration.

The repository uses one local content-addressed artifact store under
`.artifacts/`. Artifact paths are derived from SHA-256 digests. Git-tracked
records refer to artifacts by digest and logical role, not by mutable local
filename.

The repository safety scanner enforces two narrow, automatable boundaries: it
rejects tracked entries under the declared local-only paths, and it rejects
high-confidence credential assignments and provider/key signatures. It scans
the immutable Git index blobs, not mutable working-tree files. This scanner is
not a semantic clinical-text or licensing classifier. Prevention of
third-party clinical text entering Git additionally depends on the artifact
layout, dataset licensing gates, review policy, and release eligibility checks.
The scanner also rejects index flags such as assume-unchanged and
skip-worktree that could hide tracked working-tree divergence. It validates the
bounded on-disk index structure and checksum at both scan boundaries and rejects
the `FSMN` extension, because some Git versions suppress its per-entry valid
bits in plumbing output when the built-in daemon is unavailable. Lowercase
required index extensions, including split-index `link` and sparse-index
`sdir`, are unsupported and fail closed so mandatory semantics cannot be hidden
outside the validated primary index. Every Git subprocess forces
`core.fsmonitor=false`, so a repository-local hook path is never executed.

## 4. Repository Structure

```text
phentrieve-benchmark/
├── configs/
│   ├── providers/
│   └── policies/
├── datasets/
│   ├── e3c-de/
│   │   ├── dataset.yaml
│   │   ├── selections/
│   │   ├── LICENSES.md
│   │   ├── license-evidence.yaml
│   │   └── README.md
│   └── raghpo/
│       ├── dataset.yaml
│       ├── csc/
│       ├── gsc/
│       ├── LICENSES.md
│       ├── license-evidence.yaml
│       └── README.md
├── docs/
│   ├── annotation-guidelines/
│   ├── data-cards/
│   └── superpowers/
├── records/
├── schemas/
├── src/phentrieve_benchmark/
│   ├── acquisition/
│   ├── annotation/
│   ├── curation/
│   ├── derivation/
│   ├── normalization/
│   ├── ontology/
│   ├── provenance/
│   ├── release/
│   ├── review/
│   └── translation/
├── tests/
│   ├── contracts/
│   ├── fixtures/
│   ├── integration/
│   └── unit/
├── .artifacts/
└── releases/
```

`datasets/e3c-de/dataset.yaml` is the single recipe for the E3C German
parallel-text dataset. `datasets/raghpo/dataset.yaml` is the single shared
recipe for CSC and GSC because they originate from the same upstream
repository and conversion workflow. Selection manifests are immutable records
of chosen case identifiers, not additional dataset configuration systems.

## 5. Dataset Scope and Selection

### 5.1 E3C

The eligible source pool consists of E3C v2.0 Layer 1 reports in English,
French, and Spanish:

- English: 84 reports;
- French: 81 reports;
- Spanish: 81 reports.

The first quality-focused feasibility selection contains 10 source reports per
language, for 30 source reports and 30 German translations. The proposed
German pilot selection contains 30 source reports per language, for 90 source
reports and 90 German translations. In the first implementation, every selected
English, French, or Spanish source report is translated into German only. A
five-language parallel panel is a possible later expansion and is not part of
this repository's initial acceptance criteria. The selection sizes originate
from the feasibility and pilot cohorts discussed in Phentrieve issue #313. The
pipeline itself supports all 246 eligible source reports.

Selection is deterministic and stratified by:

- source language;
- document length;
- phenotype annotation density;
- organ-system coverage;
- assertion and factuality complexity.

The selection command records the eligible source inventory, metric values,
selection algorithm version, fixed seed, selected identifiers, manual
overrides with rationale, and final selection hash. The proposed filenames are:

- `e3c-de-feasibility-30-v1.json`;
- `e3c-de-pilot-90-v1.json`, created only after feasibility review.

No selection manifest contains clinical text.

### 5.2 CSC and GSC

CSC and GSC retain their upstream document identifiers. The revised datasets
are separate subsets of one RAG-HPO recipe. Their initial ontology context is
HPO `v2026-06-23`, matching the current manuscript benchmark assets. Every
build requires an explicit HPO release; `latest` is rejected.

## 6. Core Data Model

Documents, annotation sets, and review decisions are separate immutable
artifacts.

```text
SourceCase
  ├── NativeDocument
  │     └── SourceAnnotationSet
  └── GermanDocument
        ├── TranslationReview
        └── GermanAnnotationSet
              └── AnnotationReview
```

### 6.1 Required identities

- `source_case_id`: unchanged upstream case identifier;
- `case_group_id`: stable identifier connecting a source report and its German
  translation;
- `document_id`: identifier for one exact language variant;
- `document_sha256`: SHA-256 of canonical document bytes;
- `annotation_set_id`: immutable annotation-set revision;
- `annotation_set_sha256`: canonical annotation-set hash;
- `review_id`: immutable identity of one automated, bilingual, annotation, or
  adjudication review;
- `review_sha256`: canonical review-artifact hash;
- `review_policy_id`: immutable identity of the policy that selected and
  evaluated the review;
- `selection_id`: immutable selected-cohort identity;
- `hpo_release`: exact HPO release tag;
- `source_language` and `target_language`;
- `translation_status`: `native` or `translated`;
- `automated_review_status`: `pending`, `passed`, `findings`, or `failed`;
- `manual_review_requirement`: `required` or `not_selected`;
- `manual_review_status`: `pending`, `accepted`, `changes_requested`,
  `rejected`, or `not_applicable`;
- `annotation_review_status`: `pending`, `accepted`, `changes_requested`, or
  `rejected`;
- `curation_status`: `pending`, `accepted`, or `rejected`.

Each annotation set refers to the exact `document_sha256` it annotates. If the
German text changes, annotations attached to the previous document hash remain
preserved but are no longer eligible for the current release until reviewed
against the new text. Review artifacts always identify the exact document or
annotation-set hash they evaluate and record the reviewer role without storing
credentials or other secrets.

### 6.2 Character spans

Spans use zero-based, half-open Unicode code-point offsets:

```text
start_char <= position < end_char
```

For every evidence span:

```text
document_text[start_char:end_char] == text_snippet
```

Normalization is limited to declared operations such as Unicode normalization
and line-ending normalization. Any operation that can change offsets emits an
offset map from source text to canonical text.

## 7. Pipeline Architecture

The pipeline exposes independently executable stages:

```text
acquire
→ select
→ normalize
→ map-umls-hpo
→ estimate-cost
→ translate
→ review-translation
→ adapt-annotations
→ review-annotations
→ curate
→ derive-terms
→ validate
→ release
```

### 7.1 Acquisition

Acquisition uses exact upstream release tags or commit SHAs and verifies
declared checksums. Mutable branch names and unversioned local downloads are
not valid release inputs. Downloaded content is written only to
`.artifacts/`.

### 7.2 Normalization

Source-specific adapters transform E3C and RAG-HPO records into the common
document and annotation contracts. The original source bytes, canonical bytes,
conversion code identity, conversion configuration, warnings, and output
hashes remain linked in provenance.

### 7.3 UMLS-to-HPO mapping

The primary mapping is built deterministically from `UMLS:` cross-references in
the pinned HPO OBO release. The pipeline does not redistribute UMLS
Metathesaurus files.

Mapping policy:

- include phenotypic findings;
- exclude diagnoses, procedures, drugs, body parts without a phenotypic
  finding, and other non-phenotypic concepts;
- retain the source CUI, source span, candidate HPO identifiers, mapping
  method, decision, and rationale;
- accept a unique exact CUI mapping only as a candidate until policy
  validation succeeds;
- route one-to-many, missing, obsolete, or semantically questionable mappings
  to human review;
- never infer a replacement solely from label similarity.

### 7.4 HPO revision

CSC/GSC identifiers are classified as:

- valid and unchanged;
- uniquely normalized through `alt_id`;
- uniquely replaced through an explicit ontology replacement relation;
- ambiguous;
- removed without replacement;
- invalid.

Only unique, explicit ontology replacements can be proposed
deterministically. Ambiguous, removed, and invalid identifiers require a human
decision.

### 7.5 Full-text translation

Full-text translation consumes canonical native documents and produces German
document artifacts. It does not read or modify annotations. Translation and
annotation adaptation therefore have independent identities and can be
repeated separately.

### 7.6 Translation review

Translation review evaluates the source document and German translation for:

- clinical meaning;
- negation and normal findings;
- uncertainty and factuality;
- experiencer and family history;
- temporality;
- laterality;
- numerical values and units;
- abbreviations;
- omissions and additions.

The default automated reviewer configuration uses `gpt-5.6-terra`. A
`gpt-5.6-sol` configuration is retained only for a measured comparison or a
stratified audit. Automated review produces proposals and findings, never a
gold-standard approval.

The feasibility phase uses a provisional risk-based human-review policy:

- every translation receives automated review;
- a deterministic, stratified sample of at least 20% receives manual bilingual
  domain review against the source text;
- sampling covers source language, document length, annotation density, and
  assertion and factuality complexity, with stratum boundaries pinned in the
  review policy;
- the reviewer must be qualified in both the source language and German and
  must record whether they act as a medical translator, bilingual clinical
  annotator, or physician;
- a meaning-changing defect involving phenotype identity, assertion,
  experiencer, temporality, laterality, numerical values, omission, or addition
  is critical and expands manual review to every remaining translation in the
  affected source-language and complexity stratum;
- review findings create corrected document artifacts and never overwrite the
  original translation.

The feasibility decision record reports the achieved manual and physician
review coverage, defect rates by stratum, expansion decisions, and the approved
manual-review policy for the pilot. Until that decision is recorded, the
pipeline must not describe unreviewed translations as individually medically
or physician validated.

### 7.7 Annotation adaptation

Concept mapping and target-language span adaptation are separate operations:

1. map the source UMLS concept to an HPO identifier;
2. translate and accept the German document text;
3. propose German spans using exact and normalized matching against the
   document and pinned German HPO terminology;
4. use an agentic proposal only for unresolved or ambiguous spans;
5. perform a blinded primary review of HPO identity, span, assertion,
   experiencer, and temporality against the German text without exposing
   Phentrieve outputs;
6. reconcile the primary review with source annotations and mapping proposals
   during a separate adjudication step;
7. accept through human curation.

Source spans remain evidence and are never mechanically projected and accepted
as German gold spans. Reviewers and adjudicators record separate identities and
decisions. Benchmark-system output is never visible during annotation, review,
adjudication, or curation.

### 7.8 Single-term derivation

Single-term records are derived only from accepted document annotations. Each
record retains:

- source document and annotation-set identities;
- exact German surface form;
- HPO identifier;
- assertion, experiencer, and temporality;
- derivation code and configuration hashes.

The derivation is deterministic and can be repeated without provider calls.

## 8. Provenance

Every stage emits a canonical run manifest containing:

- run identifier, stage, status, and timestamps;
- input and output artifact hashes;
- source repository, release tag or commit, and source checksums;
- pipeline repository commit, dirty-state indicator, and `code_sha256`;
- normalized configuration hash;
- prompt hash when applicable;
- provider, engine, requested model, returned model identity, endpoint class,
  and processing mode;
- HPO and mapping-resource identities;
- selected document identifiers and selection hash;
- retry and error summaries;
- input characters, input tokens, cached tokens, output tokens, and provider
  usage when available;
- pricing snapshot identity, estimated cost, and accrued estimated cost;
- licensing-evidence identity;
- package versions and operating environment.

Secrets, clinical text, provider credentials, raw endpoint query values, and
raw exceptions are excluded from Git-tracked manifests.

Corrections create new artifacts and annotation-set revisions. Existing
artifacts are never overwritten in place.

### 8.1 Code identity

`code_sha256` identifies the exact executable repository state using the
`code-identity/v2` canonical JSON payload. It resolves the supplied path, then
ascends to the nearest `.git` file or directory and validates that worktree, so
calling it from a subdirectory fingerprints the whole repository without
parsing newline-terminated Git path output. The payload contains `head`,
`exclusion_policy` set to
`repository-gitignore/v1`, `path_encoding` set to
`percent-encoded-git-path-bytes/v1`, and path-sorted `entries`.

Each entry contains exactly `path`, `state`, `kind`, `executable`, and
`sha256`. `path` is an injective ASCII percent encoding of the raw,
NUL-delimited bytes emitted by Git: ASCII letters, digits, `-`, `.`, `_`, and
`/` are literal, with `/` the only unescaped path separator; percent signs,
literal backslashes, and every other byte are encoded.
Entries are sorted by that final encoded path. `state` is `present` or
`deleted`; deleted tracked paths use `kind: missing`, `executable: false`, and
the SHA-256 of empty bytes. Present regular files use `kind: file`, bind their
executable bit, and hash their bytes. Present symlinks use `kind: symlink`,
`executable: false`, and hash the raw link-target bytes, so broken links are
not confused with deletions. An untracked path that disappears after Git has
enumerated it fails closed; only an indexed path may be represented as deleted.

Tracked files and relevant untracked files are enumerated with only repository
`.gitignore` rules, including nested `.gitignore` files. Git's global exclude
configuration and `.git/info/exclude` never affect this identity. Gitlinks,
merge-conflicted duplicate index paths, device files, FIFOs, sockets, and other
unsupported kinds fail closed rather than being represented as deletions.
Before Git enumeration, a raw, non-following filesystem scan also detects
FIFOs, sockets, devices, and other special entries Git may omit. It never
traverses `.git` metadata or symlink directories. A special entry is ignored
only when `git check-ignore` identifies a non-negated, in-worktree
`.gitignore` rule as its winning exclusion; global excludes and
`.git/info/exclude` never hide it.
Regular files are read through a non-following, non-blocking descriptor where
the platform supports those flags. Their digest and executable bit come from
the same validated descriptor snapshot. Path and descriptor identity, kind,
mode, size, mtime, and stable ctime where available are checked before and
after reading; a detectable concurrent mutation is retried a bounded number of
times and then fails closed. This is not an atomic multi-file snapshot.

Declared runtime paths, including `.git/`, `.artifacts/`, local credentials,
and generated run outputs, are excluded through project `.gitignore` rules.
The policy identifiers are included in the hash input. A dirty boolean alone
is never sufficient for cache reuse or resume.

### 8.2 Run and release manifests

Run manifests are execution records. They contain volatile fields such as run
identifiers, timestamps, retry events, and environment details and are not
expected to be byte-identical across repeated executions.

Release manifests are deterministic content records. They contain no volatile
execution fields or run-manifest digests. A separate text-free linkage record
maps a release-manifest digest to the contributing run-manifest digests; that
record is execution provenance and does not participate in the release semantic
identity. Repeating a deterministic build from identical inputs must produce
byte-identical dataset artifacts and a byte-identical release manifest.

### 8.3 Canonical serialization and aggregate hashes

Persisted JSON values are normalized to declared Unicode forms and serialized
with the JSON Canonicalization Scheme in RFC 8785. JSONL serializes each record
canonically, orders records by the schema-declared stable identity, uses UTF-8
with LF line endings, and ends with one newline. Schemas declare whether array
order is semantically significant; set-like arrays are sorted by their stable
identity before hashing.

Aggregate identities such as `source_sha256`, `input_sha256`, `gold_sha256`,
and `document_ids_sha256` are SHA-256 digests of canonical manifests containing
the schema version and a path-sorted list of logical roles, stable identifiers,
and component artifact digests. They are never hashes of directory traversal
order or mutable filenames.

## 9. Paid Operations and Cost Visibility

No checked-in configuration can pre-authorize paid calls.

`estimate-cost` performs no provider request. It calculates:

- Google translation cost from exact input character counts;
- LLM review cost from tokenizer-based input estimates, configured output
  bounds, and the pinned pricing snapshot;
- gross cost independently of account-specific free credits;
- a clearly labelled net estimate when an optional local credit configuration
  is supplied.

The normal `translate` or agentic-review command:

1. validates all inputs;
2. computes and displays the cost estimate;
3. displays provider, model, case count, and pricing source;
4. asks `Start paid run? [y/N]`;
5. makes no external call unless the user confirms interactively.

A non-interactive invocation of a paid stage exits without calling the
provider. Non-interactive paid automation is outside the first implementation.
All pre-run totals are labelled as estimates. Exact measured provider usage and
the resulting post-run cost are recorded when the provider exposes them.

Pre-run money is an exact, finite, non-negative `Decimal`, not a binary float.
Python callers provide `Decimal` values; JSON stores plain decimal strings.
The confirmation display uses the normalized exact decimal value rather than a
currency-specific rounded precision, so the displayed upper bound is never
understated. Prompt-displayed provider, model, stage, and pricing identifiers
use a conservative ASCII identifier charset. The authorization boundary calls
the confirmation callback only for `interactive is True` and approves only a
literal boolean `True`; a CLI adapter must turn its explicitly documented user
input into that boolean before calling the boundary.

## 10. Console and Logging Design

All code, schemas, configuration, documentation, prompts, CLI text, logs, and
commit messages are written in English.

Normal progress uses one compact updating line:

```text
translate en→de 18/30 | 60% | ok 18 fail 0 | $1.68/$2.83 | ETA 01:42
```

`--verbose` emits additional compact events only for:

- case and stage transitions;
- retries;
- warnings and failures;
- cache or resume hits;
- validation findings;
- measured character, token, duration, and cost updates.

Clinical text and credentials never appear in console output. Every run also
writes structured `events.jsonl` records for later analysis. `Ctrl+C` produces
an `incomplete` manifest and leaves validated artifacts resumable.

Structured event logging uses closed, field-specific schemas rather than
accepting generic metadata. The first implementation supports only
`case_complete`, with all three fields required: an opaque conservative-ASCII
`case_id` matching `synthetic-[1-9][0-9]*`, a strict non-negative integer
`duration_ms`, and `status` fixed to the reviewed lifecycle code `ok`. Unknown
event types and fields are rejected. Non-synthetic cases must use a fixed-form
digest field such as `case_id_sha256`, or another reviewed validated identifier
type in a new event schema. Every new event type requires a design review, an
explicit field schema, and event-specific tests before it can be emitted.
Caller containers are first snapshotted once into built-in values, then
semantic validation and canonical rendering complete before the event file is
opened.

## 11. Error and Resume Semantics

- Provider failures never become empty valid translations.
- Temporary failures use bounded exponential backoff.
- Permanent failures mark the affected artifact as failed.
- A provider or model is never silently replaced by a fallback.
- Outputs are written atomically.
- A partial run is explicitly `incomplete`.
- Resume requires identical source, input, code, prompt, model,
  configuration, and ontology fingerprints.
- Existing files alone are not evidence that work is reusable.
- An incomplete run cannot produce a releasable dataset.
- Raw exceptions remain in local diagnostic logs only; stable public error
  codes enter manifests.

### 11.1 Release eligibility

A dataset build is release-eligible only when all of the following are true:

- every contributing run is `complete`;
- source revisions, selection, configuration, code, prompts, providers, and
  ontology releases have valid immutable identities;
- all artifacts pass their schemas and cross-artifact integrity checks;
- every annotation set references the current document hash;
- every annotation set included in the release has `accepted` annotation-review
  and curation decisions; rejected candidates remain in provenance but are
  excluded from release payloads;
- every translation passes automated review with no unresolved critical
  finding;
- translations selected by the active manual-review policy have an `accepted`
  manual review, while non-selected translations are explicitly marked
  `not_selected` and the achieved coverage is recorded;
- the feasibility decision has approved the manual-review policy used for a
  pilot release;
- the release manifest is deterministic and all aggregate hashes verify;
- a public data release has a compatible `redistributable` licensing decision.

A local restricted bundle may be assembled without a `redistributable`
decision, but it must still satisfy every quality and integrity requirement and
must remain under a declared Git-ignored local bundle path. Release metadata
must state the achieved bilingual and physician review coverage and must not
imply individual medical validation for translations outside the manual sample.

## 12. Curation

Canonical source artifacts are immutable. Manual curation uses local,
schema-validated review packets:

```text
curation export
→ edit per-case JSON packets
→ curation import
→ validate decisions
→ create a new annotation-set revision
```

For CSC/GSC, packets highlight valid IDs, proposed explicit replacements,
ambiguous or removed IDs, missing spans, and span mismatches.

For E3C, translation and annotation packets remain separate. Each human
decision records curator identity, timestamp, previous value, chosen value,
decision type, and optional rationale.

## 13. Licensing Evidence and Publication Gates

Each dataset contains both human-readable and machine-readable licensing
evidence:

- `LICENSES.md`;
- `license-evidence.yaml`.

Evidence records:

- upstream dataset and repository links;
- exact source release or commit;
- direct license link;
- access date;
- declared license identifier or text;
- relevant publication links;
- known statements about redistribution, translation, and derived data;
- unresolved questions;
- project distribution decision;
- responsible reviewer and decision date.

Initial external references include:

- E3C v2.0 corpus and its CC BY-NC statement:
  <https://github.com/hltfbk/E3C-Corpus/tree/v2.0.0#data-distribution-and-licence>;
- RAG-HPO repository and MIT license:
  <https://github.com/PoseyPod/RAG-HPO> and
  <https://github.com/PoseyPod/RAG-HPO/blob/main/LICENSE>;
- RAG-HPO publication:
  <https://genomemedicine.biomedcentral.com/articles/10.1186/s13073-025-01521-w>;
- HPO downloads and UMLS cross-reference information:
  <https://human-phenotype-ontology.github.io/downloads.html>;
- UMLS licensing and access information:
  <https://www.nlm.nih.gov/databases/umls.html>.

A public release gate requires an explicit `redistributable` decision. Until
that decision exists, the pipeline can produce:

- a local restricted data bundle;
- a public recipe bundle with source references, checksums, transformations,
  schemas, and provenance but no protected text.

## 14. Release and Manuscript Handoff

A complete local data bundle contains:

```text
manifest.json
documents.jsonl
annotations.jsonl
terms.jsonl
phentrieve/annotations/*.json
DATA_CARD.md
LICENSES.md
```

The `phentrieve/annotations/` export uses the existing document-oriented
contract:

- `doc_id`;
- `language`;
- `full_text`;
- `annotations`;
- `hpo_id`;
- `assertion_status`;
- `evidence_spans`.

The manifest exposes `dataset_id`, `dataset_version`, `hpo_release`,
`source_sha256`, `input_sha256`, `gold_sha256`, `document_ids_sha256`,
selection identity, licensing identity, review-policy identity, and achieved
bilingual and physician review coverage.

Native E3C and German parallel-text variants retain distinct stratum labels.
Downstream benchmark software must not pool them into one headline score.

The manuscript repository consumes only immutable release manifests and
adapters. It remains responsible for inference, scoring, comparison, and
benchmark-result storage in the first implementation.

## 15. `hpo-translator` Integration

The private `berntpopp/hpo-translator` repository is suitable as a starting
point for translation engines and German HPO terminology, but not as the
benchmark pipeline itself.

It will remain responsible for:

- translation-engine implementations;
- preparation and translation of HPO terminology;
- provider-specific batching and transport.

This repository will remain responsible for:

- dataset acquisition and selection;
- full provenance and content identities;
- cost confirmation and run accounting;
- clinical full-text workflow;
- UMLS-to-HPO mapping;
- German span adaptation;
- reviews, human curation, validation, and releases.

Before direct integration, `hpo-translator` requires a separate hardening
change:

- fail closed instead of returning empty translations on provider errors;
- explicitly request and record the Google `general/nmt` model;
- split provider and local-model dependencies into optional extras;
- avoid eager imports of every engine;
- record source, input, configuration, model, code, and output hashes;
- expose character, token, and cost accounting hooks;
- replace existence-only resume checks with identity checks;
- add Google NMT behavior tests and continuous integration;
- publish a pinned tag or use an exact commit.

The currently inspected baseline is commit `c18ce8e`. The benchmark repository
will depend on a hardened tag or exact hardened commit, never on a mutable
branch.

## 16. Testing and Validation

The default test suite uses synthetic clinical text and makes no paid calls.

Required coverage includes:

- deterministic acquisition and checksum verification;
- stable selection from a fixed seed;
- UMLS-to-HPO mapping against a pinned miniature ontology;
- valid, obsolete, replaced, ambiguous, removed, and invalid HPO IDs;
- provider contracts with mocked responses;
- fail-closed provider behavior;
- exact character-based cost calculations;
- token-based review-cost estimates;
- compact progress and structured event output;
- annotation invalidation after document revision;
- Unicode half-open spans and exact snippets;
- separate translation and annotation reviews;
- deterministic stratified manual-review sampling and critical-defect
  expansion;
- prevention of medical-validation claims beyond achieved review coverage;
- interrupted-run resume behavior;
- distinct code hashes for different dirty working-tree states;
- rejection of incomplete releases;
- enforcement of the complete release-eligibility predicate;
- licensing gates and linked evidence;
- byte-identical repeated dataset and release-manifest builds while run
  manifests retain execution-specific fields;
- RFC 8785 serialization, stable JSONL ordering, and aggregate-hash fixtures;
- rejection of tracked local-only artifact paths and high-confidence
  credential signatures;
- licensing and release gates that prevent unapproved third-party text from
  entering public bundles.

Live provider tests are excluded from continuous integration and require the
same interactive cost display and confirmation as normal paid stages.

## 17. Technology Choices

- Python 3.11 or newer;
- `uv` for dependency and lockfile management;
- Typer for the CLI;
- Pydantic for internal models and configuration;
- JSON Schema for persisted artifact contracts;
- Ruff and mypy for static checks;
- pytest, Hypothesis, and snapshot tests;
- canonical UTF-8 JSON/JSONL with sorted keys and final newlines;
- SHA-256 for artifact and semantic identities;
- Git-native metadata without DVC in the first implementation.

## 18. Acceptance Criteria

The first implementation is complete when:

1. the public repository can run its full test suite without external data or
   paid services;
2. E3C, CSC, and GSC sources can be acquired from pinned revisions into the
   ignored artifact store;
3. the E3C feasibility selection can be generated reproducibly;
4. CSC/GSC HPO revision packets can be generated against HPO `v2026-06-23`;
5. clearly labelled approximate pre-run cost estimates are shown before any
   paid stage;
6. paid stages require an interactive confirmation and provide compact live
   progress and accrued-cost estimates;
7. translation, concept mapping, span adaptation, automated review, sampled
   bilingual review, annotation review, adjudication, and curation have
   independent identities;
8. a complete synthetic end-to-end run produces deterministic document,
   annotation, term, Phentrieve-adapter, data-card, license, and release-manifest
   outputs while preserving separate execution run manifests;
9. restricted real-data builds cannot be committed or released accidentally;
10. the manuscript workflow can identify a dataset solely from the exported
    release manifest and hashes.

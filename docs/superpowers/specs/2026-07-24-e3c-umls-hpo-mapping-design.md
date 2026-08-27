# E3C UMLS-to-HPO mapping

## Goal and scope

Build a deterministic mapping from E3C Layer 1 `CLINENTITY` UMLS CUIs to HPO
candidates using only `UMLS:` cross-references in the pinned official HPO
release `v2026-06-23`.

The mapping runs over all 246 normalized English, French, and Spanish Layer 1
documents. A second deterministic view contains only the 30 records selected
by `e3c-de-feasibility-30-v1`. The phase does not translate text, create
German evidence spans, accept final HPO annotations, query UMLS services, or
use label similarity.

## Inputs

The mapping consumes:

- normalized E3C `SourceAnnotationSet` records linked to their canonical
  source documents;
- only annotations with source type `CLINENTITY`;
- the annotation's unchanged `source_concept_id`;
- the pinned HPO `hp.obo` release `v2026-06-23`;
- the existing E3C feasibility selection for the 30-case view.

An eligible source concept must match `C` followed by seven decimal digits.
Other source annotation types are outside this mapping population rather than
failed mappings.

## HPO UMLS index

The existing strict HPO parser is extended to retain normalized `UMLS:C...`
cross-references for each HPO term. It builds an immutable reverse index from
each CUI to all primary HPO terms carrying that exact cross-reference.

The parser:

- accepts only exact `UMLS:C[0-9]{7}` cross-references for this index;
- ignores cross-references from other namespaces;
- excludes malformed values that claim the `UMLS:` namespace and retains
  them as deterministic ontology warnings;
- retains the primary HPO ID, label, active/obsolete state, `replaced_by`, and
  `consider` values for every candidate;
- sorts CUIs and candidates deterministically; and
- rejects duplicate CUI-to-HPO entries rather than silently multiplying them.

No alternate HPO identifier is introduced by the CUI index: candidates are
identified by their primary term stanza.

## Mapping classification

Every eligible `CLINENTITY` source annotation produces exactly one mapping
record with one of these classifications:

- `unique_active`: exactly one candidate exists and it is active;
- `ambiguous`: more than one candidate exists, regardless of active state;
- `missing`: the valid CUI has no candidate in the pinned HPO release;
- `obsolete`: exactly one candidate exists and it is obsolete;
- `invalid`: the source concept does not have the required CUI syntax.

`unique_active` means a deterministic mapping candidate, not a clinically
accepted annotation. `ambiguous`, `missing`, `obsolete`, and `invalid` always
require review. An obsolete candidate is never replaced automatically through
`replaced_by` or `consider`.

## Mapping records

Each text-free mapping record contains:

- schema version and stable mapping-record ID;
- source annotation-set ID and source annotation ID;
- source document hash;
- unchanged source CUI;
- source evidence span positions and a hash of each span text, not the text;
- sorted HPO candidates with primary ID, label, active/obsolete state,
  `replaced_by`, and `consider`;
- HPO release and ontology SHA-256;
- mapping method `hpo-umls-xref`;
- classification;
- decision status `candidate` or `needs_review`; and
- machine-readable rationale.

Labels are ontology metadata and may be retained in the text-free output.
Clinical report text and source span text are not stored in tracked mapping
manifests.

## Outputs

The pipeline creates three deterministic artifacts:

1. a complete mapping manifest for all 246 normalized E3C Layer 1 documents;
2. a selected mapping manifest containing records whose source documents
   belong to `e3c-de-feasibility-30-v1`; and
3. a summary containing document, annotation, unique-CUI, classification, and
   candidate counts.

The complete and selected manifests reference the exact normalization,
selection, ontology, configuration, and code identities. Repeated source CUIs
remain separate annotation records but are counted once in unique-CUI
statistics.

Tracked outputs under `datasets/e3c-de/mappings/` contain no clinical text.
Large intermediate inputs and the verified HPO file remain in `.artifacts/`.

## Pipeline and CLI

The independent command is:

```text
phentrieve-benchmark map-hpo e3c
```

It requires verified E3C acquisition, normalization, and selection state plus
the pinned verified HPO artifact. Missing or identity-mismatched inputs stop
the command without producing a successful mapping manifest.

The command prints only stable artifact identities and compact counts. It
performs no paid operation, requires no Google or UMLS credentials, and is
safe to test offline with synthetic E3C annotations and a miniature ontology.

## Review boundary

This phase proposes ontology identities only. It does not:

- accept `unique_active` candidates as final clinical annotations;
- resolve multiple candidates;
- replace obsolete terms;
- judge whether the source phrase truly expresses the proposed phenotype;
- project source spans into a German translation; or
- generate Single-Term benchmark cases.

Those decisions consume the mapping records in later curation and German
annotation phases.

## Error handling

The mapping fails closed when:

- a source annotation set refers to the wrong document hash;
- source evidence spans no longer match normalized source text;
- annotation or mapping identities are duplicated;
- HPO release or ontology hashes differ from the pinned recipe;
- duplicate valid UMLS cross-references occur within one HPO term;
- a selected case cannot be found in the complete mapping population; or
- manifest counts disagree with their records.

Missing HPO coverage for a valid CUI is a `missing` result, not a pipeline
failure. A malformed HPO UMLS cross-reference is excluded and reported as an
ontology warning rather than silently normalized.

## Testing

Offline tests cover:

- HPO parsing with zero, one, and multiple exact UMLS cross-references;
- malformed `UMLS:` cross-references;
- all five mapping classifications;
- repeated CUIs across independent source annotations;
- deterministic ordering and canonical hashes;
- full-population and selected-view consistency;
- exclusion of non-`CLINENTITY` annotations;
- absence of clinical text in tracked outputs;
- input identity failures; and
- CLI delegation without network access.

The real mapping run verifies the pinned HPO checksum before parsing and
publishes observed counts only after the implementation passes offline tests.

## Acceptance criteria

The phase is complete when:

- all 246 normalized E3C documents are considered;
- every eligible `CLINENTITY` annotation has exactly one mapping record;
- every record is classified by the closed policy above;
- no label-based or external mapping is performed;
- the selected 30-case view is an exact subset of the complete manifest;
- outputs are deterministic, text-free, and linked to pinned inputs;
- all non-`unique_active` mappings are explicitly reviewable; and
- offline tests, Ruff, and mypy pass.

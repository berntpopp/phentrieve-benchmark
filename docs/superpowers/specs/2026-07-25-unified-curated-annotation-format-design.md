# Unified Curated Annotation Format

**Status:** Agent-reviewed; pending user approval

**Date:** 2026-07-25

## 1. Goal

Define one immutable, canonical format for curated HPO annotations from E3C,
GSC, and CSC. The format must:

- preserve the exact document and HPO release being annotated;
- retain the derivation of every annotation from source records or earlier
  annotation proposals;
- support independent confirmations, rejections, change requests, and
  counterproposals from multiple reviewers and tools;
- combine review files deterministically without resolving disagreements; and
- provide an unambiguous basis for deterministic extraction of single-term
  records from explicit text spans.

This phase implements format infrastructure only. It does not align GSC/CSC
annotations to text, create German E3C annotations, define review sufficiency,
resolve review conflicts, or decide release eligibility.

## 2. Existing contracts and compatibility

The existing contracts keep their current meanings and remain byte-compatible:

- `Document` represents one exact canonical text.
- `SourceAnnotationSet` preserves E3C source annotations and relations.
- `AnnotationSet` preserves normalized RAG-HPO HPO assignments. Its empty
  evidence spans accurately represent the missing offsets in the workbook.
- `UmlsHpoMappingManifest` preserves E3C UMLS-to-HPO candidates.
- `RagHpoSourceAnnotationRecord` links normalized GSC/CSC annotations to
  workbook rows.
- `ReviewRecord` continues to describe the existing coarse workflow review
  state and is not silently repurposed.

No existing normalized artifact is rewritten or relabelled as curated gold
data. A new `CuratedAnnotationSet/v1` is the common downstream contract.

```text
E3C SourceAnnotationSet ─┐
UMLS-HPO mapping ────────┼──> CuratedAnnotationSet/v1
GSC/CSC AnnotationSet ───┤
RAG-HPO source sidecar ──┘
```

## 3. Character and identity rules

All evidence offsets remain zero-based, half-open Unicode code-point offsets:

```text
document.text[start_char:end_char] == text_snippet
```

Every curated annotation set binds to:

- one exact `document_sha256`;
- one exact `hpo_release`;
- one exact `ontology_sha256`; and
- immutable annotation content.

Cross-artifact references use both an artifact hash and an in-artifact record
ID. A record ID alone is never sufficient to identify a reviewed subject.

All persisted models use strict, closed schemas, canonical JSON, deterministic
tuple ordering, and SHA-256 identities following the repository's existing
canonicalization rules.

## 4. Curated annotation model

`CuratedAnnotationSet/v1` contains:

```text
CuratedAnnotationSet
├── schema_version = "curated-annotation-set/v1"
├── annotation_set_id
├── document_sha256
├── hpo_release
├── ontology_sha256
└── annotations[]
```

Each `CuratedAnnotation` contains:

```text
CuratedAnnotation
├── annotation_id
├── hpo_id
├── assertion
├── experiencer
├── temporality
├── evidence_spans[]
└── derivations[]
```

The initial closed values retain the semantics of the current common
`Annotation` model:

- `assertion`: `present`, `absent`, or `uncertain`;
- `experiencer`: `patient` or `other`;
- `temporality`: `current`, `historical`, or `future`.

The new model uses enums rather than unrestricted strings. Expansion requires
a schema revision or an explicitly backward-compatible enum addition with
tests.

Evidence spans use the existing `EvidenceSpan` contract. They are unique and
sorted by `(start_char, end_char, text_snippet)`. Empty evidence spans are
structurally valid because a GSC/CSC HPO assignment may be imported as a
curation proposal before later span annotation. Empty spans are not implicitly
eligible for single-term derivation.

Annotations are sorted by `annotation_id`. Annotation IDs must be unique
within a set. A changed HPO identity, span, assertion, experiencer, or
temporality creates a new annotation proposal with a new annotation ID; it
never mutates an immutable stored artifact.

## 5. Annotation derivation

Every curated annotation contains one or more
`AnnotationDerivationRecord/v1` values:

```text
AnnotationDerivationRecord
├── schema_version = "annotation-derivation-record/v1"
├── derivation_id
├── method
└── source: DerivationSourceReference
```

`DerivationSourceReference` is a strict tagged union. Each variant defines an
unambiguous lookup in an existing artifact:

```text
E3cSourceAnnotationReference
├── source_kind = "e3c_source_annotation"
├── source_annotations_sha256
├── source_annotation_set_id
└── source_annotation_id

UmlsHpoMappingReference
├── source_kind = "umls_hpo_mapping_record"
├── mapping_manifest_sha256
└── mapping_record_id

RagHpoSourceAnnotationReference
├── source_kind = "raghpo_source_annotation"
├── annotations_sha256
├── annotation_set_id
├── annotation_id
├── source_sidecar_sha256
└── source_row_id

CuratedAnnotationReference
├── source_kind = "curated_annotation"
└── annotation: AnnotationReference

DocumentReference
├── source_kind = "document"
├── documents_sha256
├── document_id
└── document_sha256
```

The E3C reference uses both set and annotation IDs because source annotation
IDs are local to a `SourceAnnotationSet`. The RAG-HPO reference binds both the
normalized HPO annotation and its workbook-sidecar row. The mapping reference
identifies one exact mapping record. The curated reference is the only
annotation-revision reference; there is no second `previous_annotation` field
that could contradict it. The document reference binds both the aggregate
document artifact and the exact document record and text identities.

`method` is one of:

- `direct_mapping`;
- `contextual_refinement`;
- `source_hpo`;
- `manual_annotation`; or
- `revision`.

`AnnotationReference` is:

```text
AnnotationReference
├── annotation_set_sha256
└── annotation_id
```

Derivations are unique and sorted by `derivation_id`. Derivation IDs must be
unique within an annotation. A revision uses method `revision` with a
`CuratedAnnotationReference` to the proposal being revised. A manual
annotation without another annotation source uses method `manual_annotation`
with a `DocumentReference`.

Derivation records describe origin, not review or acceptance. Reviewer
identity and decisions belong only in review artifacts.

## 6. Independent review decisions

Reviews are stored separately from annotations so a reviewer or tool can emit
a new immutable file without rewriting the annotation proposal.

`ReviewDecisionSet/v1` contains:

```text
ReviewDecisionSet
├── schema_version = "review-decision-set/v1"
├── decision_set_id
└── decisions[]
```

Each `ReviewDecision` contains:

```text
ReviewDecision
├── decision_id
├── target: AnnotationReference
├── reviewer_id
├── reviewer_role
├── review_kind
├── created_at
├── review_scope
├── outcome
├── review_stage
├── review_policy_id?
├── rationale?
└── counterproposal?
```

Reviewer metadata belongs to each decision so a materialized review
collection remains self-describing even when one file contains decisions from
multiple tools or reviewers. `reviewer_id` is an opaque, non-secret identity
or stable pseudonym. It must not contain credentials. `reviewer_role`
describes the capacity in which the review was performed.

`review_kind` is one of:

- `automated`;
- `bilingual`;
- `medical`;
- `annotation`; or
- `adjudication`.

`review_scope` is one of:

- `hpo_identity`;
- `evidence`;
- `assertion`;
- `context`; or
- `complete`.

`outcome` is one of:

- `accepted`;
- `rejected`;
- `changes_requested`.

`counterproposal`, when present, is an `AnnotationReference`. It may refer to
an annotation in another curated annotation set. A counterproposal is a new
immutable annotation, not replacement fields embedded in the review.

A counterproposal must bind to the same `document_sha256`, `hpo_release`, and
`ontology_sha256` as the reviewed target. It must contain a derivation with
method `revision` and a `CuratedAnnotationReference` back to that exact target.
This is referential integrity, not an acceptance rule.

The schema permits multiple independent decisions for the same annotation and
scope. It does not assign priority to reviewer kinds, count approvals, infer a
current status, or require particular outcome/counterproposal combinations.
Those are later review-policy concerns.

`created_at` is canonical UTC at whole-second precision, serialized exactly as
`YYYY-MM-DDTHH:MM:SSZ`. Decisions are unique and sorted by `decision_id`
within each `ReviewDecisionSet`.

```text
AnnotationReference
├── bilingual review: evidence accepted
├── medical review: HPO identity accepted
└── automated review: assertion changes requested
```

## 7. Deterministic collection of review files

Different reviewers and tools may create separate decision-set files.
`ReviewCollection/v1` materializes their deterministic union:

```text
ReviewDecisionSet A ─┐
ReviewDecisionSet B ─┼──> ReviewCollection/v1
ReviewDecisionSet C ─┘
```

The collection contains:

```text
ReviewCollection
├── schema_version = "review-collection/v1"
├── collection_id
├── annotation_set_sha256s[]
├── decision_set_sha256s[]
└── decisions[]
```

Collection rules:

1. Input annotation-set hashes and decision-set hashes are unique and sorted.
2. Decisions are sorted by `decision_id`.
3. Repeated byte-identical decisions with the same `decision_id` collapse to
   one materialized decision.
4. The same `decision_id` with different canonical content is an error.
5. Semantically similar decisions with different IDs remain independent.
6. Every target and counterproposal reference must resolve in the supplied
   curated annotation sets.
7. Different versions of an annotation remain distinct because their
   `annotation_set_sha256` values differ.
8. Conflicting outcomes remain side by side and are never resolved by the
   collector.

The collection hash is a pure function of canonical inputs. Repeating the
collection with the same files produces byte-identical output regardless of
input file order.

`collection_id` is generated, never supplied by the caller. It is
`review-collection-` followed by the SHA-256 of canonical JSON containing the
schema version plus the sorted annotation-set and decision-set hashes. The ID
is computed before serializing the collection and is not included in its own
identity payload.

## 8. Single-term derivation contract

This phase does not implement an acceptance policy. Therefore the extractor
does not inspect review counts or calculate whether an annotation is eligible.
It consumes an explicit, document-scoped `SingleTermSelection/v1`:

```text
SingleTermSelection
├── schema_version = "single-term-selection/v1"
├── selection_id
├── document_sha256
├── hpo_release
├── ontology_sha256
└── records[]
      ├── annotation: AnnotationReference
      └── evidence_span_index
```

Each selection record chooses exactly one evidence span of one exact curated
annotation. The selection is a policy output or manual input; defining how it
is produced is outside this phase. Records are unique and sorted by
`(annotation_set_sha256, annotation_id, evidence_span_index)`. Because curated
evidence spans have canonical ordering, the index is stable for an immutable
annotation set.

The deterministic extractor receives:

- the exact `Document`;
- all referenced `CuratedAnnotationSet` artifacts; and
- one `SingleTermSelection`.

For each selection record it validates:

- the annotation reference resolves;
- the referenced set binds to the supplied document hash;
- every referenced annotation set uses the selection's HPO release;
- every referenced annotation set uses the selection's ontology hash;
- the span index exists;
- the stored span matches the document exactly; and
- no `(annotation reference, span index)` pair is duplicated.

It emits `SingleTermSet/v1`:

```text
SingleTermSet
├── schema_version = "single-term-set/v1"
├── single_term_set_id
├── selection_sha256
├── document_sha256
├── hpo_release
├── ontology_sha256
└── records[]
      ├── single_term_id
      ├── annotation: AnnotationReference
      ├── evidence_span_index
      ├── hpo_id
      ├── assertion
      ├── experiencer
      ├── temporality
      ├── start_char
      ├── end_char
      └── term_text
```

`term_text` is always computed as
`document.text[start_char:end_char]`; it is never copied from an unverified
caller value. One selected span produces one single-term record. Discontinuous
or multi-span expressions require explicit selection of each independently
usable span; no synthetic joining rule is introduced.

Records and stable IDs are sorted deterministically by annotation-set hash,
annotation ID, and span index.

`single_term_id` is generated as `single-term-` plus the SHA-256 of canonical
JSON containing the annotation-set hash, annotation ID, and span index.
`single_term_set_id` is generated as `single-term-set-` plus the SHA-256 of
canonical JSON containing the schema version, selection hash, document hash,
HPO release, and ontology hash. Neither generated ID is included in its own
identity payload.

## 9. Validation boundaries

Pure model validation enforces local structure, closed values, ordering,
uniqueness, and digest syntax.

Full provenance validation requires an artifact registry keyed by SHA-256.
Every hash referenced by a typed derivation, annotation reference, decision
set, or selection must be present in that registry with the schema required by
the reference variant. Cross-artifact validators then enforce:

- curated evidence spans match the bound document;
- every typed derivation resolves through its variant-specific lookup key;
- review targets and counterproposals resolve;
- counterproposals match the target document, HPO release, and ontology
  identity and derive from the target;
- collection decision IDs do not collide;
- review collections contain exactly the union of their decision sets; and
- single-term outputs exactly match their document, selection, annotations,
  and HPO/context fields.

Parsing one model can validate only its local closed schema. A requested full
provenance validation without every referenced artifact in the registry fails
closed. Unresolved references, mismatched hashes, out-of-range spans, and
identifier collisions also fail closed. A disagreement between valid reviews
is data, not a validation failure.

## 10. Pipeline and tool boundary

This format phase provides pure read, validate, canonicalize, collect, and
derive functions. It does not add an interactive review interface.

A later review tool can:

```text
read CuratedAnnotationSet
→ display annotation and document context
→ write ReviewDecisionSet
→ optionally write a counterproposal CuratedAnnotationSet
→ combine independent files into ReviewCollection
```

Because review decisions contain exact annotation references, the tool cannot
silently apply a decision to a changed proposal.

## 11. Explicit non-goals

- No GSC/CSC span alignment.
- No German E3C annotation generation.
- No automatic promotion of UMLS-to-HPO candidates.
- No rule defining how many reviews are sufficient.
- No rule requiring bilingual, medical, or adjudication review.
- No majority vote or reviewer precedence.
- No effective `draft`, `accepted`, or `release-ready` status calculation.
- No automatic conversion of accepted reviews into a single-term selection.
- No review user interface.
- No release or publication operation.

## 12. Testing

Offline tests use synthetic documents and cover:

- compatibility of existing source models;
- strict curated annotation enums and canonical ordering;
- exact Unicode evidence-span validation;
- source derivations and revision references;
- independent decisions from multiple reviewer kinds;
- accepted, rejected, change-requested, and counterproposal records without
  policy evaluation;
- deterministic collection independent of file order;
- exact duplicate collapse and conflicting-ID rejection;
- retention of contradictory reviews;
- separation of reviews for different annotation-set hashes;
- unresolved target and counterproposal rejection;
- cross-document, cross-release, and non-derived counterproposal rejection;
- canonical whole-second UTC decision timestamps;
- explicit single-term span selection;
- exact term extraction from Unicode text;
- empty, missing, out-of-range, and duplicate span-selection failures;
- byte-identical canonical outputs and stable hashes; and
- Ruff, mypy, and the complete offline pytest suite.

## 13. Acceptance criteria

The format phase is complete when:

1. E3C, GSC, and CSC can all produce the same curated annotation contract
   without changing their existing normalized artifacts.
2. Every curated annotation can retain machine-verifiable source derivation.
3. Multiple people or tools can independently record scoped decisions against
   the exact same or different annotation revisions.
4. Rejections and change requests can reference immutable counterproposals.
5. Separate decision files combine deterministically and preserve unresolved
   disagreement.
6. No review-sufficiency or release policy is encoded.
7. An explicit span selection can be converted deterministically into exact
   single-term records.
8. All new contracts are strict, canonical, offline tested, and linked by
   SHA-256 identities.

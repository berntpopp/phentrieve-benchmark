# [Design] Span-first HPO annotation and review editor

Published on 2026-08-31 as https://github.com/berntpopp/phentrieve-benchmark/issues/3.
Local snapshot refreshed on 2026-09-13; issue last updated: 09/06/2026 12:00:19.
The GitHub issue is authoritative. The original draft filename is retained.

Editorial note (2026-09-13): the issue body below retains its earlier claim that
the ontology release is `latest`. Direct code inspection found that the server
stamps the release parsed from the supplied ontology; strict release validation
and content checksums remain missing. See the assessment for this correction.

For the subsequent local assessment, see [backend and storage assessment](hpo-annotation-editor-backend-assessment.md). That recommendation is not an accepted architecture decision.

## Status

Analysis and scoping. This issue collects what already exists, what the
editor must do, where the gaps are, and which decisions are still open. It
does not decide schema changes, migrations, or Phentrieve mappings.

Boundaries:

- Axis semantics come from #2. This issue does not redefine them.
- The Excel review workbooks for E3C stay in use in parallel; they are out of
  scope here.
- Legacy conversion and schema migration are benchmark pipeline work, not
  editor features.
- Pre-annotation (LLM or other tools) reaches the editor as proposal sets.
  Turning quotes into exact offsets is pipeline work; a proposal whose quote
  cannot be located arrives without a span.

## Purpose

One editor for producing and reviewing benchmark HPO annotations:

- **Span-first.** The default workflow anchors an annotation to evidence
  spans in the text. The editor steers toward spans.
- **Document-level remains possible.** An annotation without a span is a
  deliberate, secondary choice, not a separate mode. It uses the same model
  (zero or more evidence spans) and covers both new span-less annotations and
  legacy data without spans (GSC, CSC, document-level E3C proposals), which
  can be loaded, reviewed, and given spans later.

## What exists

### `hpo-span-annotator` (JohannKaspar/hpo-span-annotator, MIT)

Stdlib Python server plus vanilla ES-module UI, no build step. Roughly 3.4k
LOC Python, 2.4k LOC JS, ~146 tests, 8 commits.

Directly reusable:

- `ui/spans.js` — standalone span editor: overlapping, nested, and
  discontinuous spans; knows only text, offsets, and mention IDs; has an unused
  "suggestion" overlay channel that fits a review view.
- `search.py`, `lexical.py`, `hpo.py` — lexical, exact, ID, dense, and browse
  routes; server-side shuffled candidates stamped with `rank`, `display_pos`,
  and `found_via`.
- `events.py`, `store.py` — lookup/edit event log; atomic record writes.

Not reusable as-is:

- `ui/annotate.js` — the whole application in one module-level state
  singleton with full re-render; the search panel is not a component.
- Validation covers span offsets only. HPO IDs are regex-checked, not resolved
  against the ontology; `axes` is `dict[str, Any]` (the declared
  `AXIS_VALUES` are never used); marker spans are unchecked; records carry no
  schema version; the ontology release is `latest`, not pinned.
- The record key `(document, annotator)` and the per-annotator sync scoping
  assume one writer per record. A reviewer writing about another annotator's
  record breaks that invariant.
- No proposals, review decisions, reconciliation, or configurable axes; the
  three axes are hardcoded in both `model.py` and `axes.js`.

### Benchmark contracts (`CuratedAnnotationSet/v1`, `ReviewDecisionSet/v1`)

Already cover: immutable proposals with derivation provenance; scoped review
decisions (`confirmed`, `rejected`, `changes_requested`) with counterproposals
and `supersedes`; deterministic merge of independently written decision
files; strict Pydantic models and cross-artifact validators; pinned ontology
identity (release plus SHA-256).

Limits observed while checking editor needs (to be settled in #2 or a schema
issue, not here):

- `evidence_spans[]` is flat: several mentions and one discontinuous mention
  look the same.
- Annotation IDs are content-derived including spans, so attaching a span to a
  legacy annotation creates a new identity; #2 asks that it should not.
- Axis values differ from the #2 proposal (experiencer, temporality).
- There is no review outcome for reviewer uncertainty; the workbook uses
  "unsicher" for this.
- There is no field for a proposal's assessment or confidence (the workbook's
  "Einschätzung"); `DerivationActivity` records only method and agent.

## Requirements

Derived from the agreed editor direction and #2. Numbered for reference,
open to correction.

1. An annotation carries zero or more evidence spans. The span path is the
   default: selecting text is the primary way to create an annotation. Spans
   may be discontinuous, overlapping, or nested; one span may support several
   HPO terms.
2. Creating an annotation without a span is possible but a deliberate action,
   and span-less annotations are visibly distinguished. Legacy annotations
   without spans load the same way, can be reviewed, and can receive spans
   later.
3. Axes and permitted values come from the canonical schema (#2). Reviewer
   uncertainty is recorded separately from clinical `uncertain`.
4. Review: proposals (human- or tool-generated, e.g. LLM pre-annotation) are
   immutable; per proposal a reviewer can confirm, reject, or change
   (counterproposal), and can add annotations. Independent
   annotation hides proposals. Reconciliation shows independent results side
   by side and preserves the originals.
5. HPO lookup searches IDs, labels, and synonyms against the pinned ontology
   release. Query, route, shown candidates, rank, display position, and the
   selected term are recorded. Dense retrieval stays explicit and off by
   default for independent annotation. Transitive ancestor/descendant pairs
   trigger a warning, never an automatic change.
6. The server validates against the benchmark contracts and fails closed on
   unknown schema versions.
7. The editor reads and writes the current canonical contracts. Autosave may
   use a private mutable workspace; submission produces immutable artifacts.
   No legacy conversion or migration inside the editor.

## Gap table

| Requirement | `hpo-span-annotator` | Benchmark contracts | Gap |
| --- | --- | --- | --- |
| 1 span annotation | yes (`spans.js`) | flat `evidence_spans` | mention grouping not expressible |
| 2 span-less annotations (new or legacy) | no: terms require spans | yes: empty spans valid | create, display, and review span-less items as a secondary path |
| 3 axes from schema | 3 hardcoded, unvalidated | v1 enums, differ from #2 | single source of truth |
| 4 review and reconciliation | none (offline Jaccard report only) | decisions, counterproposals, merge | UI and workspace |
| 5 lookup with provenance | yes (`rank`, `display_pos`, `found_via`) | no field | where lookup provenance lives |
| 5 pinned ontology | `latest` | `OntologyReference` | load the pinned release |
| 5 hierarchy warning | browse route, no warning | term-existence checks only | small addition |
| 6 server validation | offsets only | strict models and validators | reuse the validators |
| 7 workspace vs submission | autosave per record | immutable artifacts | separate the two |

## Options

### Technical basis

- (a) Refactor `hpo-span-annotator` in place. Touches record model, store,
  export, merge, sync scoping, and the UI singleton; assess integration with
  benchmark validators rather than assuming validation must be duplicated.
- (b) Extract `spans.js`, the axis definitions, and the search/ontology
  backend into a new application built on the benchmark models. The search
  panel and the application shell would be written new; test `spans.js`
  compatibility with the chosen evidence and offset contracts.
- (c) Rewrite. Fallback only.

Option (b) is a promising path to strict validation and native contracts.
Its cost advantage remains a hypothesis to check with a prototype.

### Code location

Inside the `phentrieve_benchmark` package (validators and models at hand), in
the `hpo-span-annotator` repository (collaborator-owned, MIT), or a new
repository. Attribution and keeping `spans.js` in sync upstream apply in every
case.

### Contract version

Target v1 now and accept the limits listed above, or wait for the outcome of
#2 and a v2 before building persistence.

## Open questions

- Which contract limits must be resolved before the editor is useful, and
  which can wait?
- Where does lookup provenance belong: in the annotation set or in a linked
  event-log artifact?
- Is a profile concept needed at all, or is "axes from the schema version;
  spans preferred, span-less allowed as an explicit choice" sufficient?
- How should the UI make span-less creation a deliberate choice without
  blocking it (for example an explicit action plus a visible marker)?
- Do several annotators need to work from different machines, and how are
  their workspaces exchanged?
- How should reviewers add spans to imported legacy annotations in the same
  session, as already allowed by requirement 2?
- Where is the completeness of a partially annotated document recorded: in
  the workspace/task state or in the canonical artifact (v1 has no such
  field)?

## Out of scope

- Excel workbooks and their import.
- Schema migration and legacy conversion.
- Phentrieve mappings (`normal`, `family_history`).
- A profile-authoring framework.
- The editor calling an LLM itself. Consuming tool- or LLM-generated proposal
  sets is the review mode and in scope.

## Next steps

1. Correct or confirm the requirement list in this issue.
2. Settle axis semantics in #2.
3. Decide technical basis and code location. A small spike (load one
   `CuratedAnnotationSet/v1` with its document into a page using `spans.js`;
   no persistence) could inform the decision.
4. Open one implementation issue for the smallest useful editor, scoped after
   step 3.

## Deliverables

- [ ] Agreed requirement list
- [ ] Decision on technical basis and code location recorded
- [ ] Decision on contract version target recorded
- [ ] Follow-up implementation issue opened

## Editor implications of the schema refinement (2026-09-06; not yet accepted)

These are proposed refinements linked to the discussion in #2, not accepted new schema semantics or a decision to implement v2. Keep the span-first workflow and the deliberate span-less path.

### Annotation and evidence interactions

- Axes belong to the individual HPO annotation. The current editor attaches axes to a mention shared by its terms; this cannot express different assertions for terms using the same selected passage. Shared evidence must not force shared axes.
- Support repeated evidence mentions and discontinuous segments distinctly. Preserve cue/marker spans for assertion, experiencer, and time where the accepted contract permits them.
- Shared evidence needs explicit edit behavior. A candidate design uses set-local mention references and an action to detach evidence for one annotation. Editing a shared mention must clearly show which annotations are affected; reference versus copy semantics remain a #2 decision.
- Selecting text creates evidence and an annotation; additional evidence attaches to an existing annotation. Span-less creation remains explicit. Adding spans to imported annotations is already covered by requirement 2; decide the interaction rather than reopening whether it is supported.

### Workspace, submission, review, and completeness

- Autosave persists mutable working state; submission creates an immutable version. Stable annotation IDs can survive evidence edits if #2 adopts them, but reviews must continue to target exact versions.
- Changed content must not silently inherit earlier approval. Define how the UI shows which scopes need renewed review, including edits to shared evidence.
- Provide reviewer inability to decide separately from clinical uncertainty, subject to the accepted review contract. Show proposal assessments and derivation separately.
- Expose document-level completeness separately from per-annotation correctness. A document with zero findings must be completable. The persisted completeness assertion must bind to the reviewed document, scope, and submitted version; artifact ownership is decided with #2.
- Correctly annotated negative or family findings remain visible and reviewable. A versioned gold-policy preview may show inclusion/exclusion and reasons, but must not hide these annotations or turn gold exclusion into review rejection.

### Usability and technical compatibility

Keep HPO selection, assertion, and experiencer easy to reach. Time, resolution, statement context, and provenance can use a detail panel. Defaults must be visible and traceable, particularly for imported or temporally unspecified findings. Exact controls depend on the accepted #2 values.

Define offsets end to end: Python uses Unicode code points, while browser strings use UTF-16 code units. The existing editor's `check_offset_safe` rejects non-BMP text. Reusing `spans.js` therefore requires an explicit text restriction or a tested offset conversion; unchanged extraction is not yet established for general Unicode documents.

Component extraction remains a plausible option, not a demonstrated cheapest path. In-place refactoring could also call benchmark validators instead of duplicating them. Compare the options with a small prototype after agreeing its target contract.

Suggested prototype cases (not implementation authorization):

1. Load a span-less annotation and attach evidence.
2. Give two annotations shared evidence but different assertions; edit and detach that evidence.
3. Represent repeated mentions and a discontinuous mention separately, including cue spans.
4. Submit a version, review it, then modify evidence without silently carrying approval forward.
5. Complete a zero-finding document; show a correctly reviewed negative/family annotation outside positive gold.
6. Verify offsets with non-BMP characters according to the chosen offset policy.

Additional deliverables:

- [ ] Agree evidence-sharing and per-annotation axis interactions with #2.
- [ ] Define submission, renewed review, and document-completeness behavior.
- [ ] Record the offset convention and supported text policy.
- [ ] Use the prototype results to decide technical basis and contract target.

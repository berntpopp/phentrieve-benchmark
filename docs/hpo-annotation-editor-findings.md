# HPO annotation editor: findings and handoff

Initial findings: 2026-08-31. Updated: 2026-09-13.

This is a local handoff, not an accepted schema or architecture decision.
The issues below remain authoritative for their respective design discussions.
See the [backend and storage assessment](hpo-annotation-editor-backend-assessment.md)
for code evidence, validation checks, and the current reuse recommendation.

## Current state

- Benchmark schema discussion: https://github.com/berntpopp/phentrieve-benchmark/issues/2
- Editor design issue (analysis and scoping, span-first with document-level
  as secondary path): https://github.com/berntpopp/phentrieve-benchmark/issues/3
- No Phentrieve implementation issue has been published yet.
- Final axis semantics must be settled in benchmark issue #2 before Phentrieve
  crosswalks are implemented.

## Existing `hpo-span-annotator`

The existing editor is a strong span-focused starting point, not merely a demo.
It already supports:

- paint-first span annotation;
- overlapping, nested, and discontinuous spans;
- multiple HPO terms linked to one mention;
- assertion/context axes and separate marker spans;
- HPO lookup through lexical, exact, ID, dense, and hierarchy-browse routes;
- shuffled scored candidates plus `rank`, `display_pos`, and `found_via` logs;
- autosave, completion state, event logging, local storage, and optional private
  Hugging Face synchronization;
- multi-annotator export and basic agreement reporting.

It does not provide a real review workflow with immutable proposals,
accept/reject/change decisions, counterproposals, additions, or conflict
resolution. Its server validation is also weaker than the benchmark contracts.

## Editor direction and proposed structure

The editor remains **span-first**. Span-free document annotation is an added
capability/profile, not the new core or an MVP replacement for span annotation.

Preserve the existing span and search strengths while adding:

- versioned axis definitions; whether a separate profile concept is needed remains open;
- annotations with zero or more evidence mentions;
- review/reconciliation workflows;
- strict server-side validation;
- HPO autocomplete and hierarchy warnings;
- native benchmark annotation and review contracts.

A suitable conceptual model is:

```text
Annotation
  HPO term + axes + 0..n evidence mentions

Evidence mention
  1..n span segments + optional assertion/context cue spans
```

This represents span-free annotations, repeated mentions, discontinuous
mentions, overlapping mentions, and several HPO terms supported by one mention.

`hpo-span-annotator` is a source of reusable components. The current local
recommendation is a new application UI and benchmark-based persistence/review
model, with selective reuse of span/search components. This is not an accepted
architecture decision, and a cost advantage over in-place refactoring has not
been demonstrated by a prototype.

## Profiles and workflow

The profile bullets below are candidate design guidance if profiles are adopted,
not a decision to build a profile system.

- Keep profiles small: axes, allowed values, requiredness, span policy, and
  hierarchy policy.
- Start with built-in profiles; no general profile-authoring framework.
- Store a profile reference once per annotation set/work package, not per term.
- Annotation/editing and review are application modes, not separate workflow
  profile systems.
- Partially annotated is a task state, not a mode.
- Independent annotation must hide proposals to avoid confirmation bias.
- Assisted reconciliation happens afterward and preserves original proposals.
- Reviewer uncertainty is separate from clinical assertion `uncertain`.

## HPO lookup and hierarchy

- Autocomplete should search HPO IDs, preferred labels, and synonyms against a
  pinned ontology release.
- Lexical/exact/ID/browse lookup is appropriate for independent annotation.
- Dense/semantic retrieval can bias gold relative to Phentrieve; keep it
  explicit, logged, and disabled by default for independent annotation.
- Record query, route, shown candidates, true rank, display position, selected
  result, ontology version, and terminology-index identity.
- Warn about transitive ancestor/descendant relationships.
- Guideline: select the most specific active term supported by the text.
- Do not automatically delete, replace, or suppress parent terms.

## Benchmark format boundary

- Start from the current benchmark formats, but allow explicit evolutionary
  schema changes where requirements justify them.
- Do not reinterpret an existing schema version in place.
- The editor does not perform legacy conversion or schema migration.
- Migration is a separate benchmark pipeline/command and separate issue.
- The editor reads and writes the current supported canonical version and fails
  closed on unknown versions.
- A private mutable workspace format may support autosave; submission serializes
  immutable canonical artifacts.

Current `CuratedAnnotationSet/v1` has fixed axes and a flat `evidence_spans`
list. It cannot distinguish multiple mentions from one discontinuous mention.
Its content-derived annotation ID also changes when spans or derivations change.
The evidence model or axes decided in #2 may therefore require an explicit v2.

## Schema and Phentrieve

Proposed canonical axes under discussion:

- assertion: `present`, `absent`, `uncertain`;
- experiencer: patient/family context must be separated from assertion;
- temporality values and treatment of resolved findings remain open in #2.

The unaccepted refinement added to #2 on 2026-09-06 also proposes separate
resolution metadata, actual/hypothetical/generic statement context, explicit
handling of unavailable legacy metadata, and version-bound review/completeness.
Stable annotation identity, shared evidence semantics, and gold selection remain
open. Approved negative or family annotations need not enter positive gold.

Concrete Phentrieve inconsistency:

- export treats `normal` as an excluded abnormal feature;
- the Phentrieve benchmark adapter maps `normal` to `PRESENT`.

The schema issue should decide whether `normal` is a source-level label that
maps to canonical `absent` for an abnormal HPO feature. Only afterward should a
focused Phentrieve implementation issue be opened.

## Next steps

Issue #3 has been published and refined; the local issue snapshot has been
refreshed to include its 2026-09-06 additions.

1. Decide code location and the scope of a small reuse prototype.
2. Agree the structural contract: annotation versus evidence, shared evidence,
   stable identity versus immutable versions, and Unicode offsets.
3. Prototype span editing and search with versioned axis definitions. Final
   clinical axis values need not block this work.
4. Settle schema semantics and the submission/review contract before productive
   canonical submissions. Do not silently flatten richer evidence into v1.
5. Record the architecture decision and scope a focused implementation issue.

The editor UI can progress before final axis semantics. Configurable controls do
not remove structural persistence decisions or the need for a supported canonical
schema. No editor implementation is authorized or performed by this handoff.

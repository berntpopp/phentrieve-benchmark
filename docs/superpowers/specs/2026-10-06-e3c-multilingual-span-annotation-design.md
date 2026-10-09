# E3C Multilingual Span Annotation Design

**Status:** Draft for review

**Date:** 2026-10-06

## 1. Summary

The E3C Layer 1 corpus (246 reports: 84 English, 81 French, 81 Spanish) is
split into four annotation groups of roughly equal size: German
(machine-translated) and English, French, Spanish (original). Every report is
annotated in exactly one language. Annotation is span-based from the start,
follows [the span annotation guideline](../../annotation-guidelines/hpo-span-annotation.md),
and happens in the Ontocurator editor. Proposals come from one uniform LLM
step that sees only the text. Each group yields its own document-level gold
and its own single-term set; groups are never pooled.

This design replaces:

- the staged strategy of 2026-08-24 (span-free document-level gold first,
  spans later only for the single-term subset);
- the 30-case feasibility cohort as the working set. The 30 cases were an
  arbitrary size; their Phase 0 results remain comparison data;
- the Excel annotation workbook (`make_annotation_review.py`). Excel remains
  only for the translation review.

It returns to the span-based target-language annotation of the original
pipeline design (`2026-07-23-benchmark-data-pipeline-design.md`, §7.7) and
extends it to the original languages.

## 2. Goals and Non-goals

Goals:

- a fair, reproducible split of all 246 reports into four annotation groups;
- one reference corpus artifact that holds every report in its annotation
  language;
- proposals of uniform quality for every report, independent of the existing
  UMLS mapping, E3C annotations, and Phase 0 audit;
- full traceability from every gold annotation back to the raw proposal
  output;
- editor packages that enforce the guideline where the editor can;
- an import path from the editor export to validated benchmark artifacts.

Non-goals:

- a quality filter for unsuitable reports. It is planned for later and will
  be a separate, explicit selection step on top of the split. It runs before
  or after the physician review, but always before the benchmark analysis
  starts; excluded reports stay listed with a reason (decided 2026-10-06);
- semantic or automated translation review;
- span-level evaluation; scoring stays document-level by HPO ID;
- changes to the editor beyond profile configuration;
- proposing further occurrences of a marked phrase in the editor;
- mandatory double annotation. The original pipeline design required a
  blinded primary review and a separate adjudication step (§7.7 there).
  This design deliberately makes that optional (decided 2026-10-06): every
  package can be built without proposals (§7), so a blinded second
  annotation of a subset with adjudication and an agreement measure stays
  possible later without new tooling. Until then the gold rests on one
  physician review per report, and this limitation is reported with it.

## 3. Phases

| Phase | Content | Depends on |
|---|---|---|
| 0 | Cleanup: delete `make_annotation_review.py`, update READMEs | – |
| 1 | Split and annotation corpus | – |
| 2 | Proposal step: pilot, then full run | 1; German group reviewed |
| 3 | Editor packages per group | 2 |
| 4 | Curated format v2 and import adapter | 1 |

All five phases are implemented and tested end to end, on synthetic data and
on the pilot, before any human step begins (decided 2026-10-06). The human
steps (translation review of the German group, physician review in the
editor) are not part of this design and start only once the whole pipeline
stands. Running the proposal step for the German group requires its reviewed
texts; the code for it does not.

The first human step after the pipeline stands is a workflow pilot (decided
2026-10-06): two to three reports per original-language group go end to end
through editor, export, import, and gold v1 with a real reviewer before the
full annotation starts. The German group joins once its first texts are
reviewed. The pilot tests tooling and instructions; its annotations count as
regular gold if they pass review.

## 4. Phase 0: Cleanup

- Delete `datasets/e3c-de/annotation-feasibility/make_annotation_review.py`.
  Nothing imports it and no test covers it; all 31 current `ruff check .`
  errors come from it, so CI on `main` turns green again.
- Update `datasets/e3c-de/annotation-feasibility/README.md` and
  `datasets/e3c-de/README.md`: the probe data stays as comparison data; the
  workbook generator and the staged recommendation are marked as superseded
  with a link to this design.
- Local, Git-ignored files are deleted only after Phase 3 and after
  confirmation: `.artifacts/review-workbooks/e3c-en-annotation-review.*`,
  `hpo-lookup.json`, `.artifacts/editor-packages/editor-e3c-v2.zip`,
  `ui-check-2026-10-05/`.

## 5. Phase 1: Split and Annotation Corpus

### 5.1 Split

A new selection algorithm `e3c-annotation-groups/v1` assigns every report of
the verified inventory to one group:

- per source language, roughly a quarter of the reports go to the German
  group (about 21 English, 20 French, 20 Spanish); the rest stay in their
  original language. Resulting sizes are about DE 61, EN 63, FR 61, ES 61;
  exact equality is not required;
- stratification within each source language uses the existing length
  stratum and the E3C total annotation density from the inventory metrics;
- assignment is stratified systematic sampling: sort the language's reports
  by (length stratum, annotation density, seeded hash of the case ID), then
  assign every fourth report, starting at a seeded offset, to German. This
  spreads the German share evenly over length and density without a search;
- fixed seed `phentrieve-e3c-annotation-groups-v1`.

The output is a text-free manifest `e3c-annotation-groups-v1.json` under
`datasets/e3c-de/selections/`, analogous to the feasibility selection: one
record per report with source case ID, source language, annotation language,
the stratification metrics, and an aggregate hash. Its directory name keeps
`e3c-de` for continuity; the manifest itself covers all four languages.

### 5.2 Annotation corpus

A new stage materializes one `documents` artifact with exactly one
`Document` per report, in its annotation language:

- original group: the existing native document, unchanged;
- German group: a `Document` with `translation_status = translated`,
  `language = de`, `case_group_id` equal to the source case, and the fixed
  German text. Today no stage produces translated documents; this stage
  closes that gap.

The German text is the reviewed text from an accepted translation review
record (`unverändert akzeptiert` or `korrigiert akzeptiert`). An unreviewed
translation is never used. A German report without an accepted review is
left out of the corpus artifact until its review is accepted; the stage lists
such reports explicitly instead of failing silently. The stage records, per
German document, the review import manifest and record it came from. A later
correction produces a new corpus artifact; the old one stays valid for
annotations made against it (guideline R7).

This corpus artifact is the single reference for proposals, editor packages,
and curated annotation sets.

### 5.3 Translation review retarget

Every German text is reviewed before use (decided 2026-10-06). This replaces
the lean, risk-based review decided on 2026-08-24. The existing workbook was
designed for exactly this complete review: one row per case and a mandatory
decision per row. The export currently targets the 30-case selection and
must accept the German group of the split instead, with the `tllm-full`
translations as the reviewed variant. Workbook format and import are
otherwise unchanged.

## 6. Phase 2: Proposal Step

### 6.1 Execution

Claude subagents in Claude Code process the corpus in batches of about ten
reports. Input per report: the canonical text, its language, and its corpus
document ID and hash. Shared input per run: a versioned prompt file and the
guideline version. No UMLS candidates, E3C annotations, or Phase 0 results
are given.

The subagent applies the guideline (R0–R6) and returns, per report, a list of
proposed annotations:

```json
{
  "document_id": "...",
  "document_sha256": "...",
  "annotations": [
    {
      "proposal_id": "p001",
      "hpo_id": "HP:0001945",
      "hpo_label": "Fever",
      "assertion": "present",
      "experiencer": "patient",
      "temporality": "current",
      "verbalized": true,
      "mentions": [
        {"phrase": "Fieber", "context": "mit hohem Fieber einher"}
      ],
      "note": null
    }
  ]
}
```

A mention is located by two verbatim strings: `phrase`, the span by R2/R4,
and `context`, a short excerpt that contains the phrase exactly once and
occurs exactly once in the text. Language models do not count characters
reliably; the validator computes offsets.

Subagents may look terms up in the pinned release with
`proposals hpo-lookup` (labels and synonyms; added 2026-10-06). Text search
lists only terms under *Phenotypic abnormality*.

### 6.2 Deterministic validation

A pipeline command validates each batch output and never edits it:

- the document ID and hash match the corpus artifact;
- the HPO ID is an active term of the pinned release `v2026-06-23`; the label
  is informational and is not used to resolve IDs;
- the HPO ID lies under *Phenotypic abnormality* (HP:0000118), the branch
  guideline R0 covers (added 2026-10-06 after the pilots);
- assertion, experiencer, and temporality use the allowed values;
- each `context` occurs exactly once in the text and each `phrase` exactly
  once in its `context`; the resulting offsets are recorded;
- matching tolerates typography the model may alter (quotation marks,
  dashes, non-breaking and repeated spaces): both strings and the text are
  compared in a normalized form, and offsets are mapped back to the original
  text, so the stored span is always the verbatim original;
- a mention may carry an optional `occurrence` index (1-based) when the
  phrase occurs more than once in its context, for example "Schmerzen" in
  "Bauchschmerzen und Schmerzen"; whole-word matches take precedence over
  matches inside longer words;
- mentions of one proposal do not overlap.

Rejected proposals and mentions are listed with a reason in a validation
report; nothing is repaired silently. Proposals with the same HPO ID and
status in one report are merged into one proposal with several mentions
(R5).

### 6.3 Traceability

Each run is stored, tracked in Git, under
`datasets/e3c-de/proposals/<run_id>/`:

- `prompt.md`, the exact prompt used, and the guideline commit;
- `run.json`: model ID, run date, corpus artifact hash, batch list with the
  document IDs and hashes per batch;
- `batch-NN.json`: the unchanged subagent output, with provenance "machine
  generated, not review data, not gold";
- `validation.json`: the validator report with resolved offsets, merges, and
  rejections, plus its own canonical hash.

The outputs contain only short phrases and context excerpts, like the
existing Phase 0 files; this fits the documented non-commercial review
assumption in `license-evidence.yaml`. Every proposal in an editor package
references run, batch, and proposal ID.

Reproducibility: subagent runs have no pinned temperature or seed and cannot
be regenerated identically. What is reproducible is everything downstream of
the archived raw outputs: validation, packages, and import are deterministic
functions of the stored batches. Claims about the proposal step are limited
to that.

### 6.4 Pilot

Before the full run, a pilot of about eight reports from the three
original-language groups (mixed languages and lengths) is processed and
validated. German texts are not used before their review, so the German path
is exercised end to end only with synthetic data until then. The pilot shows
the rejection rate and proposal quality; the prompt is revised if needed. The full run starts only
after explicit confirmation. Pilot outputs are kept as their own run.

Status 2026-10-07: all 185 reports of the original-language groups have
validated proposals (2,242 proposals); the German group waits for its
translation review. Four pilots with 27 reports and a run of 60 further
reports were proposed by Sonnet subagents and revised by Opus subagents, the
60 after an Opus cross-read; the other 98 reports were proposed by Opus.
The cross-read is a check of Sonnet proposals: a cross-read of 92 Opus
reports found 8 clear points in 1,213 proposals, which were applied by
script, and Opus proposals get no further cross-read. Per report,
`datasets/e3c-de/proposals/current-proposals.json` names the run and the
steps. Results, measurements, and decisions are recorded in
`datasets/e3c-de/proposals/README.md`.

## 7. Phase 3: Editor Packages

`scripts/build_editor_packages.py` is rebuilt to produce one package per
annotation group:

- documents: the corpus documents of that group with their corpus IDs and
  text;
- proposals: the validated proposals of the latest confirmed run, as tool
  annotations with `source_refs` pointing to run, batch, case, and proposal
  ID (`run/batch/case/proposal`; raw proposal IDs restart in every report,
  decided 2026-10-08);
- one evidence mention per occurrence; the current builder's
  several-spans-as-segments behaviour is removed;
- profile: assertion, experiencer, and temporality required
  (`allow_empty=False`) with the values of guideline R3; new required axis `verbalization` with
  `verbalized`/`not_verbalized`; `evidence_policy` requiring evidence on
  completion;
- proposal axis values come from the proposal step;
- an option builds a package without any proposals, for blinded annotation
  (see the double-annotation note in §2);
- every package gets a text-free build record in
  `datasets/e3c-de/editor-packages/` (decided 2026-10-08): manifest hash,
  hash of `current-proposals.json`, runs, corpus manifests, guideline
  commits, profile hash, and ontology hash. An editor export names the
  manifest hash of its origin package, which ties it to the record. The
  build is deterministic, and the builder refuses a package whose content
  differs from its committed record; changed content gets a new package
  version in the package ID.

The builder stays a script in the Ontocurator overlay environment. Coverage
statistics are not a design driver; the script is excluded from the CI
coverage measurement instead of being split up for testability.

The GSC package keeps its current content.

## 8. Phase 4: Curated Format v2 and Import

### 8.1 `curated-annotation-set/v2`

v1 is not reinterpreted. v2 adds:

- the attribute values of guideline R3: experiencer `patient`,
  `family_member`, `other`; temporality `current`, `historical` (no
  `future`);
- `verbalized: bool` on each annotation (guideline R6);
- a derivation source kind `llm_proposal` referencing the proposal run's
  validation report hash and the proposal ID, and a derivation method for
  reviewed machine proposals. Validation checks that the referenced proposal
  belongs to the same corpus document.

Contiguous `EvidenceSpan`s and assertion values stay as in v1. The axis
values were settled on 2026-10-06 (guideline R3) and replace the open
proposals of issue #2 for this dataset; the issue is updated accordingly.

v2 is not a drop-in change: `curation/validation.py`,
`models/review_decision.py`, `review/merge.py`, and
`derivation/single_term.py` are typed against the v1 set and must accept v2
(or a common interface) in the same phase.

### 8.2 Import adapter

The adapter reads an editor export and produces a `ReviewDecisionSet` and a
v2 `CuratedAnnotationSet` per document:

- the export's document hash must equal the corpus document hash;
- multi-segment (discontinuous) mentions are rejected with a clear error
  (guideline R4);
- confirmed or changed annotations with the same HPO ID and status are merged
  into one annotation with several spans (R5); manual additions without a
  decision are imported as additions;
- the editor outcome `uncertain` maps to `changes_requested` and does not
  enter gold;
- `text_snippet` is computed from the corpus text; editor offsets are Unicode
  code points and match Python string indices;
- reviewer ID in `namespace:id` form, stage ID, scopes, and second-precision
  UTC timestamps come from an import configuration.

An end-to-end check of the editor on 2026-10-08 (two reviewers, three
languages, review and independent mode, package export) confirmed that an
export carries the origin package and its manifest hash, every decision with
outcome, note, and reviewer, and every annotation with its author and its
link to the proposal. It adds these points for the adapter:

- the editor stores the reviewer as the free text typed on its dashboard.
  The import configuration maps these editor IDs to the namespaced
  pseudonyms; an editor ID missing from the configuration is an error;
- the review timestamp is the submission time of the case (decided
  2026-10-08), truncated to seconds. Decisions have no timestamp of their
  own;
- the export's `origin_manifest_hash` must match a build record in
  `datasets/e3c-de/editor-packages/` (§7);
- the export contains neither the guideline version of the review round nor
  the editor software version. The guideline commit comes from the import
  configuration;
- a changed proposal arrives as a new annotation by the reviewer whose
  `source_refs` hold the proposal's annotation ID and version. Its mentions
  can be in another order than in the proposal, so mentions are compared and
  merged by span, not by position;
- a proposal that was copied without a change and then confirmed is exported
  together with its copy; the merge by HPO ID and status (R5) covers this.

The import also writes a text-free review statistics report per annotation
group (decided 2026-10-06): proposals confirmed unchanged, changed (term,
span, or axes), and rejected; gold annotations added by the reviewer without
a proposal; and the share of gold annotations that originate from a
proposal. This makes transparent how strongly the gold rests on the LLM
proposals. It does not replace double annotation: findings missed by both
the proposal and the reviewer, and anchoring effects, stay unmeasured.

### 8.3 Single-term derivation

The existing derivation takes an explicit, hand-built `SingleTermSelection`
whose records each point to one annotation span (`models/single_term.py`).
Two additions are needed:

- a selector that builds the selection from the accepted gold of one
  annotation group by the guideline criteria (assertion `present`,
  experiencer `patient`, span owned by one annotation, verbalized);
- merging candidates with identical phrase text and HPO ID across documents
  of one language. The current record ties a case to a single span, so the
  merged case keeps one representative span and lists the others as
  additional sources.

Per annotation group, the result is one single-term set.

### 8.4 Text corrections after annotation (guideline R7)

A German text corrected after annotation becomes a new corpus document. Its
existing annotations stay bound to the old version. The case is re-annotated
on the new version; proposals and earlier decisions may be shown as a
starting point. Automatic remapping of spans through the review diff is not
planned.

## 9. Testing

- Offline, synthetic fixtures as in the existing CI.
- Split: determinism, group sizes per language, stratum spread, stable
  manifest hash.
- Corpus: translated documents only from accepted reviews, unreviewed
  reports listed and left out, hash binding.
- Validator: each rejection reason, offset computation, merge by HPO ID and
  status, no mutation of input.
- v2 model and import: discontinuous rejection, merge, `uncertain` mapping,
  hash mismatch, review statistics counts.

## 10. Open Questions

- Scoring rules for each group, decided after annotation (2026-10-06). The
  annotation captures everything needed for both a present-only patient view
  and an assertion-aware view.
- Whether the pilot result justifies a second, independent proposal pass for
  comparison (not planned).
- Timing of the later quality filter relative to annotation.

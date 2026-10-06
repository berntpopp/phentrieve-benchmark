# HPO span annotation guideline

Status: draft rules agreed on 2026-10-06; not yet applied to any reviewed data.

Scope: texts this project annotates itself, currently E3C Layer 1. The 246
reports are split into four annotation groups of roughly equal size: German
(machine-translated) and English, French, Spanish (original). Every text is
annotated in exactly one language. The rules apply identically to all four
languages; examples are German. Adopted gold without spans (GSC, CSC) stays
document-level; span-free annotations remain possible as a deliberate
secondary choice.

This guideline revises the staged strategy of 2026-08-24, which planned a
span-free document-level gold first and spans later only for the single-term
subset. Annotation is now span-based from the start, and single-term cases are
derived directly from those spans; there is no separate span pass.

Original E3C annotations follow different span conventions (mostly the head
word; body parts are separate annotations) and a different terminology
(UMLS). They are not used as span proposals.

## Why spans and how they are used

- **Single-term task.** Phentrieve receives only the marked phrase as input
  (compare `tests/data/benchmarks/german/570terms_german.json` in the
  Phentrieve repository: `{"text": "Anasarka", "expected_hpo_ids": [...]}`).
  A span therefore has to be usable verbatim as such an input.
- **Full-text task.** Scoring stays document-level: the set of HPO IDs per
  document. Phentrieve also reports evidence offsets (`start_char`,
  `end_char`); complete spans keep a later span-level evaluation fair. Such an
  evaluation is not yet defined.

## Rules

### R0 What is annotated

Annotate phenotypic findings: signs, symptoms, and abnormal examination,
laboratory, or imaging findings. A diagnosis is annotated only where HPO
models it as a phenotypic abnormality (for example *Hypertension*, *Diabetes
mellitus*, *Systemic lupus erythematosus*). Other diagnoses, procedures,
treatments, and pathogens are not annotated themselves; annotate the findings
the text reports for them. Examples from the Phase 0 CUI triage:
"Tuberkulose" and "Metastasierung" are diagnoses or disease course without a
matching phenotype term. A suspected diagnosis ("Verdacht auf SLE") follows
the same rule with assertion `uncertain`.

Completeness:

- annotate every positive finding;
- annotate explicitly negated phenotypes ("kein Fieber");
- do not annotate normal findings without a phenotype reference ("Analtonus
  normal").

### R1 Term choice

Select the most specific active term of the pinned HPO release that the text
supports. Do not add ancestor terms for the same finding. Example:
"Fieberkrämpfe" is *Febrile seizure*, not *Fever* plus *Seizure*.

### R2 Span extent

Mark the shortest contiguous phrase that expresses the term on its own.

- Include modifiers that determine the term: "rezidivierendes Fieber" is
  *Recurrent fever*, so "rezidivierend" belongs to the span.
- Exclude everything else: negation and hedging cues, experiencer and time
  expressions, and the rest of the sentence.
- Contiguity takes precedence over minimality: words inside the phrase stay
  in the span even if they do not determine the term. "Schmerzen in der
  rechten Lendenregion" keeps "rechten".

Example: in "Diese Symptome waren nicht mit Erbrechen, Verstopfung …
verbunden." the span for *Vomiting* is "Erbrechen".

### R3 Status is an attribute, not part of the span

Assertion (`present`, `absent`, `uncertain`), experiencer, and temporality are
recorded on the annotation. "nicht mit Erbrechen" gives the span "Erbrechen"
on an annotation with assertion `absent`.

Experiencer `patient` is the index person of the report. In obstetric reports
the fetus or newborn is `other` ("gesundes Neugeborenes 2,9 kg").

### R4 Shared components

When several terms share a component of their wording, mark the whole
construction as one span and attach that same span to every term involved.
This covers an elided word part, a shared location, and a shared subject.
Discontinuous spans are not used.

Examples:

- "Muskel- und Gelenkschmerzen" is the span of both *Myalgia* and
  *Arthralgia* (elided word part).
- "Schwellung und Schmerzen in der rechten Lendenregion" is the span of both
  the swelling and the pain term (shared location).
- "Die Leber war vergrößert, hart und knotig" is the span of every liver term
  it expresses (shared subject).

A span shared by more than one term is never a single-term case.

### R5 All occurrences

Mark every occurrence that supports an annotation, not only the first or the
clearest one.

- All occurrences with the same status (assertion, experiencer, temporality)
  belong to one annotation.
- An occurrence with a different status forms a separate annotation. Example:
  "febril 39,5 °C" at admission and "fieberfrei" later give *Fever*/`present`
  and *Fever*/`absent`.
- How temporally sequenced findings count in the document-level gold is open
  in issue #2 and does not affect where spans are placed.

### R6 Findings that are not verbalized

A pathological measurement without an interpretation ("CRP 3,7 mg/dl",
"Hb 6,8 g/dl") is still assessed for the corresponding term.

- Only pathological values are annotated. A normal value ("Körpertemperatur
  37 °C") gives no annotation unless the text states it as a finding
  ("afebril").
- A measurement the text interprets is verbalized and not covered by R6:
  "erniedrigtes Serumalbumin (29 g/l)" is an ordinary annotation.
- The span covers the measurement.
- The annotation is marked as not verbalized (structured flag, see
  [Data model](#data-model)).
- Such annotations are excluded from single-term derivation.

### R7 Fixed text version

This rule applies to the German group; original texts are fixed by the
pinned E3C source.

Each case's German text is fixed before annotation starts. A translation
correction found during annotation creates a new text version; the case's
spans must then be re-anchored to that version. Annotation sets are bound to
the exact text through `document_sha256`, and validation rejects spans that do
not match the referenced text.

Spans are verbatim machine-translated text and become single-term inputs.
A span whose wording is unnatural or wrong German is reported as a
translation correction under this rule, not silently accepted.

## Single-term derivation

Single-term cases are derived from all four annotation groups, one
single-term set per language (decided 2026-10-06).

Only clear findings enter the single-term benchmark (decided 2026-10-06):
negated, uncertain, or non-patient findings are easier to derive and add
little value to that task.

Every span is a candidate when all of the following hold:

- the annotation has assertion `present` and experiencer `patient`;
- the span belongs to exactly one annotation (R4);
- the annotation is not marked as not verbalized (R6).

Spans are contiguous by construction (R4). Candidates with identical phrase
text and HPO ID are merged across all documents of the same language, so a
frequent phrase such as "Fieber" yields one single-term case.

## Data model

`CuratedAnnotationSet/v1` can represent the spans and status of R1–R5 and R7
without change, as checked in
`src/phentrieve_benchmark/models/curated_annotation.py` and
`src/phentrieve_benchmark/derivation/single_term.py`:

- each `EvidenceSpan` is contiguous, so several spans unambiguously mean
  several occurrences;
- assertion, experiencer, and temporality are annotation fields;
- two annotations may carry the same span;
- single-term selection already points to one span (`evidence_span_index`);
- `document_sha256` binds an annotation set to one text version.

Two things v1 cannot represent:

- **R6 marker.** It needs a new field on the annotation. The model forbids
  extra fields and an existing schema version is not reinterpreted in place,
  so this requires `curated-annotation-set/v2`.
- **Proposal origin.** Proposals come from a single LLM proposal step on the
  annotated text itself. No existing derivation source kind can reference
  such a proposal (`DerivationSourceReference` in
  `src/phentrieve_benchmark/models/curated_annotation.py`); in v1 the
  annotation can only be `manual_annotation` with a bound document, which
  drops its origin. The format design of 2026-07-25 explicitly excluded
  German E3C annotation generation.

German translations are also not yet benchmark `Document`s: no pipeline
stage produces documents with `translation_status = translated`, so an
annotation set on a German text has nothing to reference.

Known and unchanged: the content-derived annotation ID includes the spans, so
it changes when spans change.

## Open questions

- Scoring rule for the German gold: which combinations of assertion,
  experiencer, and temporality count as gold terms, including temporally
  sequenced findings (issue #2). The existing `positive_hpo_present_v1` is
  defined in the manuscript repository, not here.
- Definition of a span-level evaluation for the full-text task.

Not planned for now: editor support that proposes further occurrences of a
marked phrase (R5).

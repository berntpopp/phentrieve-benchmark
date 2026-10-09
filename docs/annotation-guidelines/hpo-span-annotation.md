# HPO span annotation guideline

Status: rules agreed on 2026-10-06, revised by the user decisions of
2026-10-09; not yet applied to any reviewed data. The decision history and
derived clarifications are in
[`hpo-span-annotation-decisions.md`](hpo-span-annotation-decisions.md).

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

Annotate findings the text explicitly describes: signs, symptoms, and
examination, laboratory, or imaging findings described as pathologically
altered. Do not derive findings from measurements, treatments, or clinical
reasoning (R1, R6).

Only active terms under *Phenotypic abnormality* (HP:0000118) of the pinned
HPO release v2026-06-23 are allowed. An explicitly named diagnosis is
annotated when a term in this branch describes it (for example
*Hypertension*, *Diabetes mellitus*, *Systemic lupus erythematosus*, or
*Tuberculosis infection*). A suspected diagnosis ("Verdacht auf SLE")
follows the same rule with assertion `uncertain`.

Procedures, treatments, and pathogens themselves are excluded, even when
HPO has a term for the procedure or treatment. Annotate explicitly described
pathological findings or consequences instead. "Ernährung über eine
Magensonde" gives no annotation; "needed 4 red cell packs" alone does not
establish a bleeding phenotype. Do not derive an infection from a pathogen
name or a disease from its treatment.

Infections, metastases, and test results follow the same text-bound term
choice as other findings (R1). A positive test is not automatically an
infection, and a negative test is not automatically an absent disease.
Annotate a test finding only when the text explicitly describes it as
pathologically altered and a permitted term fits; do not infer pathology
from vaccine-induced positivity or a result described as normal or not
clinically significant. An explicitly named and negated phenotype still
receives `absent`. A general term for an explicitly named metastatic lesion
may be used only if it describes that lesion without implying a primary
tumour or another unstated property. If no term fits, leave it unannotated.

Completeness (decided 2026-10-06): annotate every phenotypic finding in the
text, whoever it concerns and whatever its status. This includes negated
("kein Fieber"), suspected ("V. a. Lupus"), historical, family ("Mutter mit
Epilepsie"), and other-person findings ("Neugeborenes mit Ikterus" in a report
about the mother). Later evaluations of negation or experiencer are only
meaningful if these are annotated as completely as positive patient findings.

Not annotated:

- hypothetical or conditional statements ("Wiedervorstellung bei erneuten
  Krampfanfällen", "Risiko einer Niereninsuffizienz im Verlauf"): nothing has
  occurred;
- generic medical statements ("SLE kann zu Nierenbeteiligung führen"): no
  finding of a person;
- normal findings without a phenotype reference ("Analtonus normal"). A
  normal examination finding is not a negated phenotype (decided
  2026-10-06): "Milz nicht tastbar" gives no annotation, in particular not
  *Splenomegaly* with assertion `absent`. A finding the text itself names
  and negates ("keine Splenomegalie") is annotated as `absent`.

### R1 Term choice

Select the most specific permitted term that the marked phrase itself
expresses. Translation, synonyms, and equivalent clinical wording are
allowed; literal agreement with an HPO label is not required. Context
outside the span may establish assertion, experiencer, or temporality, but
must not make the HPO term more specific. For example, "pallor" is *Pallor*,
not *Anemic pallor* because a low haemoglobin value appears elsewhere.

If the phrase contains a qualification for which no suitable more specific
term exists, use the fitting general term. "Starke Bauchschmerzen" may be
annotated as *Abdominal pain* when no suitable severity-specific term is
available. Missing representation of a qualification is not a reason to
drop an otherwise matching finding.

Do not replace a diagnosis with individual components or consequences that
are not stated. "Dermatomyositis" alone does not give a substitute *Myositis*
annotation; excluded haemophilia does not give absent factor VIII or IX
activity. Do not infer an obstruction from imaging findings or choose a
term for a different measurement method. If no equivalent or fitting
general term describes the stated finding, leave it unannotated and record
the terminology gap in a review note.

Do not add ancestor terms for the same occurrence. "Fieberkrämpfe" is
*Febrile seizure*, not additional *Fever* and *Seizure* annotations. Separate
explicit general and specific occurrences are both annotated with the term
each phrase supports: "Nierentumor" and later "Nierenzellkarzinom" yield
separate general and specific annotations, even for the same lesion. Do not
attach the general phrase to the specific term using the other occurrence
as context. Explicitly worded collective and component findings are treated
in the same way; raw component values give no annotations (R6).

When no single term represents all explicitly named characteristics,
complementary terms may share the same span (R4). Do not add a redundant
ancestor of another term on that span.

### R2 Span extent

Mark the shortest contiguous phrase that expresses the term on its own.

- Include modifiers that determine the term: "rezidivierendes Fieber" is
  *Recurrent fever*, so "rezidivierend" belongs to the span.
- Exclude everything else: negation and hedging cues, experiencer and time
  expressions, and the rest of the sentence.
- Contiguity takes precedence over minimality: words inside the phrase stay
  in the span even if they do not determine the term. "Schmerzen in der
  rechten Lendenregion" keeps "rechten".
- A site-specific term needs its site in the span. "Distended" alone is not
  a span for *Abdominal distention*. Include the subject when needed to
  express the finding; retain unavoidable intervening words, including cues,
  under the contiguity rule. Record the status separately (R3).
- Drop leading or trailing words that do not determine the selected term.
  There is no guideline character limit: a complete construction takes
  precedence over a short span. A proposal format's excerpt limit is a
  tooling constraint, not permission to truncate the finding.

Example: in "Diese Symptome waren nicht mit Erbrechen, Verstopfung …
verbunden." the span for *Vomiting* is "Erbrechen".

### R3 Status is an attribute, not part of the span

Three attributes are recorded on the annotation (values decided 2026-10-06):

| Attribute | Values |
|---|---|
| Assertion | `present`, `absent`, `uncertain` |
| Experiencer | `patient`, `family_member`, `other` |
| Temporality | `current`, `historical` |

"nicht mit Erbrechen" gives the span "Erbrechen" on an annotation with
assertion `absent`. `uncertain` means the text expresses uncertainty; it never
means the annotator is unsure.

A finding or diagnosis the text only suggests is `uncertain` (decided
2026-10-06): "vereinbar mit", "spricht für", "Aspekt wie bei", and "Verdacht
auf" hedge the finding they introduce ("Histologie spricht für ein
Ganglioneurom"). A hedge on the cause or pathogen of a finding leaves the
finding itself `present` ("Pneumonie, vermutlich durch Pneumocystis").

- Experiencer `patient` is the index person of the report. `family_member`
  covers relatives ("Mutter mit Epilepsie"). Everyone else is `other`; in
  obstetric reports the fetus or newborn is `other` ("gesundes Neugeborenes
  2,9 kg"). There is no `unknown`: a finding without a named person in a case
  report concerns the patient.
- Temporality `current` is the reported episode, including findings without
  an explicit earlier time. `historical` requires an unambiguous reference to
  a time before that episode ("Krampfanfälle in der Kindheit"). Past tense
  and a section heading such as "Anamnese" alone do not establish
  `historical`: "bei Aufnahme bestand Fieber" is `current`. For chronic
  conditions, neither persistence nor resolution is assumed; without a clear
  earlier time reference use `current`. There is no `future` value (such
  statements are hypothetical and not annotated, see R0) and no `not_stated`.
- An explicitly resolved finding is `absent` at that occurrence. Earlier
  presence remains a separate `present` annotation (R5). Both states may
  belong to the current episode; `absent` does not mean `historical`.
- An explicitly stated suspicion is `uncertain`; an explicit later exclusion
  gives a separate `absent` annotation. A normal test result alone does not
  rule out a diagnosis. Judge hedging by the statement's meaning rather than
  a word list: "indicated" is not automatically uncertain. A hedge on the
  cause still leaves an explicitly established finding `present`.

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

Complementary terms may also share one span when no single term represents
all its explicitly named characteristics (decided 2026-10-09). For example,
"orales Plattenepithelkarzinom" may carry *Squamous cell carcinoma* and
*Neoplasm of the oral cavity* if no permitted term covers both type and
site. Each term must be supported by the phrase; neither may be a redundant
ancestor of the other. This span is also excluded from single-term cases.

### R5 All occurrences

Mark every occurrence that supports an annotation, not only the first or the
clearest one.

- All occurrences with the same HPO ID and status (assertion, experiencer,
  temporality) belong to one annotation.
- An occurrence with a different status forms a separate annotation. Example:
  "febril 39,5 °C" at admission and "fieberfrei" later give *Fever*/`present`
  and *Fever*/`absent`. "Das Fieber verschwand" also gives a separate
  *Fever*/`absent` occurrence, not a further `present` occurrence. Mark the
  finding phrase ("Fieber"); its disappearance determines the assertion.
- A purely referential expression is not an occurrence. Mark renewed
  wording when it names a finding and supports a permitted term on its own;
  an article or demonstrative alone is not a reason to omit it. "Diese
  Schmerzen" can support *Pain*, but cannot inherit a specific site from
  another sentence. "Diese Befunde" does not name a finding. A later general
  mention gets its own general term, not the earlier specific term (R1).
- An abbreviation counts only if it identifies the finding on its own.
  Do not use another occurrence's expansion to resolve an ambiguous
  abbreviation such as "CU" into a separate annotation.
- How temporally sequenced findings count in the document-level gold is open
  in issue #2 and does not affect where spans are placed.

### R6 Measurements require an explicit interpretation in the text

Annotate a measurement-based finding only when the text itself explicitly
classifies it as pathologically altered. This is a full-text annotation
task, not an interpretation of laboratory or other numeric values (decided
2026-10-09).

- "Hb 6,8 g/dl", "CRP 3,7 mg/dl", or "QTc 450 ms" alone gives no
  annotation. Neither an external reference nor a reference interval printed
  in the report permits the annotator to derive a finding from a number.
- "Anämie", "erniedrigtes Hämoglobin", "CRP erhöht", and "verlängerte
  QTc-Zeit" explicitly describe findings and must be annotated when a
  permitted HPO term fits.
- Use the shortest wording that expresses the interpreted finding, not a
  bare measurement: "erniedrigtes Serumalbumin (29 g/l)" gives the span
  "erniedrigtes Serumalbumin". Its later uninterpreted numeric value does
  not create a second annotation or occurrence.
- Explicitly named and negated phenotypes remain covered by R0/R3, including
  "keine Anämie" and "afebril". A normal numeric value alone gives no
  annotation.

The earlier rule admitting non-verbalized measurement findings is
superseded. All accepted E3C findings are now verbalized; a separate
non-verbalized category is not part of this guideline.

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
- the phrase itself supports the selected HPO term without context from
  elsewhere in the report (R1/R2).

All accepted findings are verbalized under R6. Historical findings remain
eligible when these criteria hold; temporality is not an exclusion rule.
Repeated phrase text associated with different HPO IDs is flagged for
review before release; it must not silently become contradictory test cases.

Spans are contiguous by construction (R4). Candidates with identical phrase
text and HPO ID are merged across all documents of the same language, so a
frequent phrase such as "Fieber" yields one single-term case.

## Data model

`CuratedAnnotationSet/v1` can represent the spans of R1–R5 and R7 without
change, as checked in
`src/phentrieve_benchmark/models/curated_annotation.py` and
`src/phentrieve_benchmark/derivation/single_term.py`:

- each `EvidenceSpan` is contiguous, so several spans unambiguously mean
  several occurrences;
- assertion, experiencer, and temporality are annotation fields;
- two annotations may carry the same span;
- single-term selection already points to one span (`evidence_span_index`);
- `document_sha256` binds an annotation set to one text version.

Two things v1 cannot represent:

- **Attribute values of R3.** v1 has experiencer `patient`/`other` and
  temporality `current`/`historical`/`future`. R3 adds `family_member` and
  drops `future`.
- **Proposal origin.** Proposals come from a single LLM proposal step on the
  annotated text itself. No existing derivation source kind can reference
  such a proposal (`DerivationSourceReference` in
  `src/phentrieve_benchmark/models/curated_annotation.py`); in v1 the
  annotation can only be `manual_annotation` with a bound document, which
  drops its origin. The format design of 2026-07-25 explicitly excluded
  German E3C annotation generation.

These changes still require `curated-annotation-set/v2`; v1 is not
reinterpreted in place. The former R6 marker is no longer a requirement for
E3C gold. Existing proposal schemas and editor packages still carry
`verbalized`/`verbalization`; their adaptation is pending. Existing raw
proposals, run records, and package build records remain historical evidence
under their recorded guideline versions, not accepted gold under this revision.

`pipeline/annotation_corpus.py` already creates German benchmark `Document`s
with `translation_status = translated` from accepted translation reviews.
The real German group still awaits those reviews. Curated format v2, the
editor import adapter, and automatic single-term selection are not yet
implemented. Rule revisions alone do not establish that old proposals meet
the new guideline; affected proposals need correction or physician review.

Known and unchanged: the content-derived annotation ID includes the spans, so
it changes when spans change.

## Open questions

- Scoring rules, decided later and not needed for annotation (2026-10-06).
  The dataset supports at least a present-only patient view (comparable to
  the existing `positive_hpo_present_v1` results on GSC/CSC, defined in the
  manuscript repository) and an assertion-aware view that matches HPO ID and
  assertion, since Phentrieve outputs an assertion per finding.
- Definition of a span-level evaluation for the full-text task.

Not planned for now: editor support that proposes further occurrences of a
marked phrase (R5).

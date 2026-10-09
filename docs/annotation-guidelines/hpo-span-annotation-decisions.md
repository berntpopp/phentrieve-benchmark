# HPO span annotation guideline: decisions and open questions

Status: discussion recorded on 2026-10-07; updated on 2026-10-09 with the
user decisions from the guided repository review and their operational
consequences. These changes have been incorporated into
[`hpo-span-annotation.md`](hpo-span-annotation.md), which remains the binding
text. This log records the history rather than defining a second guideline.

- Part A lists the decision history, by rule, with date and source. Rows
  marked superseded describe earlier decisions, not current requirements.
- Part B preserves ten questions raised under the earlier guideline and
  records their resolution. They come from the
  proposal runs on the 185 original-language E3C reports: the reports of the
  proposal and cross-read subagents and the 94 arguable points of the
  cross-read of `rest92-opus-v3`
  ([`datasets/e3c-de/proposal-crossreads/rest92-opus-v3/`](../../datasets/e3c-de/proposal-crossreads/rest92-opus-v3/)).
  Each question now has a dated decision or derived clarification. The
  descriptions headed "Earlier guideline" preserve the original problem.

The grouping of the 94 points into questions and the counts per question
were made by the main session and are approximate. The examples are machine
proposals, not review data.

Decisions on the proposal procedure (prompts, cross-reading, revisions) are
not listed here; they are in
[`datasets/e3c-de/proposals/README.md`](../../datasets/e3c-de/proposals/README.md).

## Part A: Decisions taken

"Draft" means: part of the draft rules agreed on 2026-10-06, without a
separate decision note in the guideline.

### Scope and method

| # | Decision | Date | Recorded in |
|---|---|---|---|
| A1 | Annotation is span-based from the start. This revises the staged strategy of 2026-08-24 (span-free gold first). Span-free annotation stays possible as a deliberate secondary choice. | 2026-10-06 | guideline, Scope |
| A2 | Every text is annotated in exactly one language; the rules are identical for German, English, French, and Spanish. | 2026-10-06 | guideline, Scope |
| A3 | Original E3C annotations are not used as span proposals (other span conventions, UMLS instead of HPO). | 2026-10-06 | guideline, Scope |
| A4 | A span must be usable verbatim as a single-term input for Phentrieve. Full-text scoring stays document-level. | draft | guideline, Why spans |
| A5 | Only active terms under *Phenotypic abnormality* (HP:0000118) of the pinned release v2026-06-23 can be proposed; the validator rejects other terms. This supersedes "no restriction to HP:0000118". Consequence: for example *Preeclampsia*, *Stillbirth*, and *Ectopic pregnancy* cannot be annotated. | 2026-10-06 | proposals README; proposal-step plan |

### R0 What is annotated

| # | Decision | Date | Recorded in |
|---|---|---|---|
| A6 | Annotated are phenotypic findings: signs, symptoms, and abnormal examination, laboratory, or imaging findings. | draft | R0 |
| A7 | A diagnosis is annotated only where HPO models it as a phenotypic abnormality (*Hypertension*, *Diabetes mellitus*, *Systemic lupus erythematosus*). Other diagnoses, procedures, treatments, and pathogens are not annotated themselves; the findings reported for them are. Earlier examples claimed "Tuberkulose" and "Metastasierung" had no matching phenotype term; those blanket exclusions are superseded by A45. | draft | R0 |
| A8 | A suspected diagnosis follows the same rule with assertion `uncertain`. | draft | R0 |
| A9 | Completeness: every phenotypic finding is annotated, whoever it concerns and whatever its status (negated, suspected, historical, family, other persons). | 2026-10-06 | R0 |
| A10 | Not annotated: hypothetical or conditional statements, generic medical statements, and normal findings without a phenotype reference. | draft | R0 |
| A11 | A normal examination finding is not a negated phenotype: "Milz nicht tastbar" gives no annotation. A finding the text names and negates ("keine Splenomegalie") is `absent`. | 2026-10-06 | R0 |

### R1 Term choice

| # | Decision | Date | Recorded in |
|---|---|---|---|
| A12 | The most specific active term the text supports is chosen. | draft | R1 |
| A13 | Earlier rule: no ancestor terms for the same finding ("Fieberkrämpfe" is *Febrile seizure*, not *Fever* plus *Seizure*). The blanket same-finding restriction is superseded by A39: it applies to one occurrence, not separate explicit general and specific phrases. | draft | R1 |

### R2 Span extent

| # | Decision | Date | Recorded in |
|---|---|---|---|
| A14 | The span is the shortest contiguous phrase that expresses the term on its own. | draft | R2 |
| A15 | Modifiers that determine the term belong to the span ("rezidivierendes Fieber" for *Recurrent fever*). | draft | R2 |
| A16 | Negation and hedging cues, experiencer and time expressions, and the rest of the sentence are excluded. | draft | R2 |
| A17 | Contiguity takes precedence over minimality: words inside the phrase stay in the span ("Schmerzen in der rechten Lendenregion" keeps "rechten"). | draft | R2 |

### R3 Status

| # | Decision | Date | Recorded in |
|---|---|---|---|
| A18 | Status is recorded as attributes, not in the span: assertion `present` / `absent` / `uncertain`, experiencer `patient` / `family_member` / `other`, temporality `current` / `historical`. | 2026-10-06 | R3 |
| A19 | `uncertain` means the text expresses uncertainty, never that the annotator is unsure. | draft | R3 |
| A20 | A finding or diagnosis the text only suggests is `uncertain` ("vereinbar mit", "spricht für", "Aspekt wie bei", "Verdacht auf"). A hedge on the cause or pathogen leaves the finding `present`. | 2026-10-06 | R3 |
| A21 | `patient` is the index person; relatives are `family_member`; everyone else is `other`, including the fetus or newborn in obstetric reports. There is no `unknown`: a finding without a named person concerns the patient. | draft | R3 |
| A22 | `current` is the reported episode, including findings without an explicit time; `historical` is a finding the text places before it. There is no `future` and no `not_stated`. | draft | R3 |
| A23 | Superseded by A41: whether a finding has resolved was not recorded. | draft | earlier R3 |

### R4 Shared components

| # | Decision | Date | Recorded in |
|---|---|---|---|
| A24 | When several terms share a component of their wording (elided word part, shared location, shared subject), the whole construction is one span attached to every term involved. Discontinuous spans are not used. | draft | R4 |
| A25 | A span shared by more than one term is never a single-term case. | draft | R4 |

### R5 All occurrences

| # | Decision | Date | Recorded in |
|---|---|---|---|
| A26 | Every occurrence that supports an annotation is marked. Occurrences with the same status belong to one annotation; an occurrence with a different status forms a separate annotation ("febril 39,5 °C" and later "fieberfrei" give *Fever* `present` and *Fever* `absent`). | draft | R5 |
| A27 | Earlier examples excluded "der Tumor", "diese Schmerzen", and "die Läsionen" as back-references. Clarified by A37/A39/A45: a renewed phrase counts when it independently names a finding; articles and demonstratives alone do not exclude it. | 2026-10-06 | earlier R5; revised R5 |

### Earlier R6: Findings that are not verbalized (superseded)

| # | Decision | Date | Recorded in |
|---|---|---|---|
| A28 | Superseded by A43: a pathological measurement without interpretation was annotated, marked as not verbalized; the span covered the measurement. Normal values gave no annotation unless stated as a finding ("afebril"). | draft | earlier R6 |
| A29 | A measurement the text interprets is an ordinary, verbalized annotation ("erniedrigtes Serumalbumin (29 g/l)"). | draft | R6 |
| A30 | Superseded by A43: a finding stated in words and its later measurement stayed two annotations (verbalized and not verbalized). | 2026-10-06 | proposals README, earlier Guideline clarifications |

### R7 and single-term derivation

| # | Decision | Date | Recorded in |
|---|---|---|---|
| A31 | German texts are fixed before annotation; a translation correction creates a new text version and spans are re-anchored. An unnatural or wrong German span is reported as a translation correction. | draft | R7 |
| A32 | Single-term cases are derived from all four groups, one set per language. | 2026-10-06 | Single-term derivation |
| A33 | Only clear findings enter the single-term benchmark: assertion `present`, experiencer `patient`, span belonging to exactly one annotation, not marked as not verbalized. | 2026-10-06 | Single-term derivation |

### Deliberately left open

| # | Topic | Date | Recorded in |
|---|---|---|---|
| A34 | Scoring rules are decided after annotation. | 2026-10-06 | Open questions |
| A35 | A span-level evaluation for the full-text task is not defined. | 2026-10-06 | Open questions |
| A36 | How temporally sequenced findings count in the document-level gold is open in issue #2 and does not affect span placement. | 2026-10-06 | R5 |

### Revision of 2026-10-09

Source for A37–A44: the user choices in the guided discussion of this
repository on 2026-10-09, now incorporated into the guideline. A45 records
operational consequences derived from those choices and the existing rules;
it is not a separately answered user question.

| # | Decision | Supersedes or clarifies | Recorded in |
|---|---|---|---|
| A37 | The marked phrase itself must support the HPO term. Context outside the span may determine axes, but cannot supply term specificity. | A12, A14 | R1, R2 |
| A38 | A fitting general term is allowed when a qualification has no suitable specific term. Synonyms and equivalent wording are allowed; individual disease components, consequences, and clinical inferences are not substitutes for a missing matching term. | A12 | R1 |
| A39 | Explicit general and specific occurrences of the same finding are both annotated with the term each phrase supports. Do not generate an extra ancestor for one occurrence. | A13, A26 | R1, R5 |
| A40 | Complementary terms may share a span when no single term covers all its explicitly named characteristics and neither term is a redundant ancestor of the other. Such spans are not single-term cases. | A24, A25 | R4 |
| A41 | Explicit disappearance gives a separate `absent` occurrence alongside earlier `present`. Explicit suspicion and later exclusion similarly give `uncertain` and `absent`; normal tests alone do not establish exclusion. | A23 (superseded), A26 | R3, R5 |
| A42 | `historical` requires an unambiguous time before the reported episode. Past tense or an anamnesis heading alone is insufficient; without a clear earlier reference use `current`, without assuming chronic persistence or resolution. | A22 | R3 |
| A43 | Only measurement findings explicitly classified as pathologically altered in the text are annotated. Numbers and reference intervals are not interpreted. Non-verbalized measurement annotations are excluded from E3C gold. | A28 and A30 (superseded), A29, A33 | R0, R6, Single-term derivation |
| A44 | Treatments and procedures themselves remain excluded even if HPO has a term. Explicit pathological findings or consequences are annotated without inferring them from treatment. | A7 | R0 |
| A45 | Apply the same text-bound scope to infection diagnoses, tests, and metastatic lesions. Renewed mentions must support their own term; span completeness takes priority over tooling excerpt limits. | A7 examples (superseded), A16, A17, A27 | R0, R2, R5; derived clarification |

A4 and A33 still describe the intended single-term task, with eligibility
made explicit by A37 and A40. A6 now requires explicitly described findings
under A43. A18–A21, A31–A32, and the open scoring questions A34–A36 remain.
Historical proposals may contain non-verbalized findings under A28/A30;
they are not retrospectively declared compliant with A43.

## Part B: Earlier questions and their resolutions

Overview. "Points" are arguable cross-read points of `rest92-opus-v3`.

| # | Question | Rules | Points |
|---|---|---|---:|
| Q1 | Infections, pathogen tests, serology | R0 | 11 |
| Q2 | Metastases | R0 | 2 |
| Q3 | Substitute and inferred terms | R0, R1 | about 22 |
| Q4 | Specificity taken from context | R1, R2, R5 | about 21 |
| Q5 | One finding at two levels | R1, R4 | 7 |
| Q6 | Back-reference or renewed mention | R5 | 9 |
| Q7 | Span edges, subjects, and long constructions | R2, R4 | 10 |
| Q8 | Past-history conditions: `historical` or `current` | R3 | 0 |
| Q9 | Resolved, excluded, and refuted findings; hedge words | R3, R5 | 3 |
| Q10 | Treatments with a term; borderline values | R0, R6 | 6 |

Three further points are plain term choices without a guideline question.
Q8 has no cross-read point; it shows in the first-pass proposals.

### Q1 Infections, pathogen tests, serology

Earlier guideline: R0 excludes pathogens and gives "Tuberkulose" as a diagnosis
without a matching phenotype term (A7). The pinned release has
*Tuberculosis infection* (HP:5210111), *Pulmonary tuberculosis*
(HP:0032262), and terms for single test results, so the example contradicts
the rule "annotate a diagnosis where HPO models it".

Where proposals diverge:

- Tuberculosis as a diagnosis: left out in most batches, proposed in
  `rest92-opus-v3` batch-08 (*Pulmonary tuberculosis*, *Mycobacterial
  meningitis*) and in ES100561; the cross-read asks for it in EN100605
  (`absent`) and EN100606 (`uncertain`).
- Positive pathogen tests: *Positive respiratory tract SARS-CoV-2
  coronavirus nucleic acid test* (EN100606, EN100705), *Positive
  Mycobacterium tuberculosis sputum culture* (EN100606), *Bacteremia* for
  N. meningitidis in peripheral blood (ES100832; verbalized in EN100655, not
  verbalized in FR100603).
- Serology: positive antibodies proposed for CMV, HSV, and VZV but not for
  rubella and LCMV in the same line (ES100417); negative hepatitis B
  serology left out next to three others that were proposed (FR100589);
  rubella positivity explained by vaccination.

Sub-questions:

- a. Is an infection diagnosis annotated when the release has a term for it,
  and is the R0 example replaced?
- b. Is a positive pathogen test an abnormal laboratory finding (annotate)
  or the pathogen itself (do not annotate)?
- c. Is a negative serology `absent` or a normal finding without annotation
  (compare A11)?
- d. Is a positivity the text explains as vaccine-induced or as not
  significant annotated?

Decision / derived clarification (2026-10-09; A37, A38, A43, A45):

An explicitly named infection diagnosis is annotated if a permitted HPO term
describes it. Remove the blanket tuberculosis exclusion. A test result is
annotated only when explicitly described as pathologically altered and a
matching permitted term exists. Do not derive infection from a positive
test, absent disease from a negative test, or pathology from vaccine-induced
or explicitly insignificant positivity. An explicitly named and negated
phenotype is still `absent`. This applies the general scope decisions; the
user did not separately vote on each serology example. Individual term
matches remain physician review cases.

### Q2 Metastases

Earlier guideline: "Metastasierung" is disease course without a matching
phenotype term (A7).

Where proposals diverge: metastases are left out in most batches. A
neoplasm term of the affected organ is proposed instead in batch-05
(*Neoplasm of the liver*, ES100634) and batch-10 (*Neoplasm of the skeletal
system* for "métastase osseuse", FR100994). The cross-read asks for
*Neoplasm of the liver* in EN101783 and asks to drop it in ES100634.

Options:

- a. No annotation for metastases.
- b. A neoplasm term of the named organ, `present`.
- c. As b, but only where the text describes the lesion itself (imaging,
  histology), not for the bare word "metastatic".

Decision / derived clarification (2026-10-09; A37, A38, A45):

There is no blanket exclusion or automatic organ-neoplasm substitution for
metastases. Apply R1: a permitted term must describe the explicitly named
lesion, possibly at a general level, without implying a primary tumour or
another unstated property. "Metastatic" alone does not establish a site.
If no fitting term exists, leave the finding unannotated and note the gap.
The user decided the general mapping policy, not the validity of each
example's proposed HPO term; those mappings remain physician review cases.

### Q3 Substitute and inferred terms

Earlier guideline: R1 asks for the most specific term the text supports (A12);
the prompt says "if no term fits, do not annotate the finding". Neither says
how far a term may be from the wording.

Two patterns:

- A diagnosis without its own term, replaced by a component: "dermatomyosite"
  as *Myositis* (FR100515, FR100517); "drépanocytose hétérozygote composite
  SC" as *HbS hemoglobin* plus *HbC hemoglobin* (FR100986); excluded
  "hémophilie" as *Reduced factor VIII activity* and *Reduced factor IX
  activity*, `absent` (FR100168); "hernie de Spiegel" as *Ventral hernia*
  (FR100996).
- A described finding that suggests a term the text does not name: dilated
  small-bowel loops with air-fluid levels as *Intestinal obstruction*
  (ES100840); "sin irritación peritoneal" as *Peritonitis* `absent`
  (ES100659, EN100399); "placa de necrosis en el colon sigmoide" as
  *Gastrointestinal infarctions* (ES100519); "reduced tracer uptake" on a
  technetium scan as *Reduced radioactive iodine uptake* (EN107021);
  "tumoración malar" as *Facial neoplasm* (ES100713); "émission d'écume" as
  *Excessive salivation* (FR100282).

Options:

- a. Strict: annotate only when the term or one of its synonyms matches
  what the text states; otherwise no annotation.
- b. Closest term allowed when it is an ancestor or component the text
  logically implies (myositis in dermatomyositis); no clinical inference
  from described findings.
- c. Closest term allowed in both patterns, with a note.

To consider: such spans are single-term inputs (A4). Under b and c the
phrase "dermatomyosite" becomes a single-term case for *Myositis*.

Decision (2026-10-09; A38):

The user chose strict text-bound matching, with an explicit qualification:
if no suitable term represents a qualification, use the fitting general
term rather than dropping the finding. This allows translation, synonyms,
and generalization of the stated finding, but not substituting unmentioned
disease components or inferred consequences. "Starke Bauchschmerzen" may
map to *Abdominal pain*; "dermatomyosite" alone is not a substitute
*Myositis* case. This is option a amended by the user's general-term rule,
not option b's component inference.

### Q4 Specificity taken from context

Earlier guideline: R1 asks for the most specific term "the text supports"
(A12); R2 asks that the span express the term on its own (A14). The two
pull apart when the specificity stands elsewhere in the text.

Where proposals diverge:

- More specific term from another sentence or a value: *Liver abscess* or
  *Bacterial liver abscess* because the aspirate grew bacteria (EN100399);
  *Pallor* or *Anemic pallor* with Hb 7,6 (ES100177); *Pituitary prolactin
  cell adenoma* or *Macroprolactinoma* with "30 mm" (FR100361); *Elevated
  circulating creatine kinase activity* or *Extremely elevated creatine
  kinase* at 300 times the upper limit (EN100029); *Pedal edema* or *Bipedal
  edema* (ES100519). In 12 of the 19 arguable term corrections the
  suggested term is a descendant of the proposed one.
- A later, more general mention of a finding already annotated with a
  specific term: "méningite" after bacterial meningitis (FR100361),
  "Osteoarthritis" without the knee (EN106233), "goiter" after multinodular
  goiter (EN100067), "fever" after low-grade fever. The proposals attach it
  to the specific annotation; the cross-read calls that an extra occurrence.

Sub-questions:

- a. May a term take its specificity from context outside the span, or must
  the span alone carry it?
- b. If context counts: does the span then grow to include the determining
  words (for example the value), or does it stay on the naming phrase?
- c. A later general mention: further occurrence of the specific annotation,
  a separate annotation with the general term (against A13), or not marked?

To consider: under a "context counts" rule, a span such as "pallor" becomes
a single-term case for *Anemic pallor*.

Decision (2026-10-09; A37, A39):

The user chose phrase-local specificity (option a: the span alone carries
the term). No specificity may be borrowed from another sentence or a
separate numeric value. A later general mention is annotated with its own
general term, not attached to the earlier specific term and not omitted.
The same rule applies to full-text annotation and single-term candidates.

### Q5 One finding at two levels

Earlier guideline: no ancestor terms for the same finding (A13). R4 allows one
span for several terms that share wording (A24).

Where proposals diverge:

- The text names a collective term and then lists the single values:
  "pancytopenia" plus leukocyte, haemoglobin, and platelet values
  (EN100372); "dyslipidémie" plus LDL and HDL values (FR100717);
  "hyper-transaminasémie" plus AST and ALT (FR100925). Proposals keep both
  levels; the cross-read asks to drop the collective term in two cases and
  the single terms in the third.
- The text names a lesion at two levels in different places: *Renal
  neoplasm* and *Renal cell carcinoma* (ES100079, ES100112), *Testicular
  neoplasm* with *Testicular teratoma* and *Testicular seminoma* (ES100050).
- No single term carries site and kind: "oral squamous cell carcinoma" as
  *Squamous cell carcinoma* alone or together with *Neoplasm of the oral
  cavity* on the same span (EN105114).

[`ancestor-pairs.json`](../../datasets/e3c-de/proposals/ancestor-pairs.json)
lists 103 such pairs in the current proposals; many of them are separate
findings.

Sub-questions:

- a. When the text names a collective term and its components, which level
  is annotated: the named collective term, the components, or both?
- b. When general and specific wording occur in different places for one
  lesion, are both mentions occurrences of the specific term (see Q4c)?
- c. May two terms from different branches share one span to cover site and
  kind?

Decision (2026-10-09; A39, A40, A43):

Both explicitly worded general and specific findings are annotated, with
the term supported by each occurrence. A named collective finding is
annotated; raw component measurements do not add annotations. Explicitly
worded pathological components are annotated in their own right. When no
single term covers explicitly named site and type, complementary terms may
share a span if neither is a redundant ancestor of the other. Such a span
is excluded from single-term derivation. No extra ancestor is generated for
the same occurrence.

### Q6 Back-reference or renewed mention

Earlier guideline: "der Tumor", "diese Schmerzen", "die Läsionen" are not
marked; "only a phrase that names the finding again is" (A27).

Where proposals diverge: a bare noun that repeats the finding's head word:
"both abscesses" after liver abscesses (EN100399), "lymphome" after B-cell
lymphoma (FR100439), "dyspnée" after exertional dyspnea (FR100517), "the
ulcerative lesion" (EN105114), "hematoma" at follow-up (EN107021). Also the
abbreviation in parentheses, "Colitis Ulcerosa (CU)" (ES100284).

Options:

- a. A repeated head word is an occurrence whenever it could stand as a
  term input by itself ("abscesses"), whatever article precedes it.
- b. A repeated head word with a definite article or demonstrative is a
  back-reference; without one it is an occurrence.
- c. Only wording that expresses the annotated term on its own counts
  (ties this question to Q4c).

Separate point: is an abbreviation an occurrence? It is a poor single-term
input.

Derived clarification (2026-10-09; A37, A39, A45):

Mark a renewed phrase when it identifies a finding on its own, using its
own supported term. Articles and demonstratives do not decide eligibility:
"diese Schmerzen" can support *Pain*, but cannot inherit an earlier
anatomical qualification. Pure references such as "diese Befunde" do not
count. An abbreviation counts only when it independently identifies the
finding; an ambiguous "CU" does not inherit the preceding expansion.
This follows the user's phrase-local and all-explicit-mentions decisions.

### Q7 Span edges, subjects, and long constructions

Earlier guideline: shortest contiguous phrase that expresses the term on its
own (A14); words inside the phrase stay (A17); cues are excluded (A16); a
shared construction is one span (A24).

Where proposals diverge:

- Edge words that do not determine the term: side, site, size, quality
  ("right lumbar region mass", "cellulite fronto-temporo pariétale",
  "pitting oedema"). The cross-read rates the same pattern as clear in some
  batches and arguable in others.
- Subject or site missing from the span of a site-specific term: "flexion
  was restricted" for *Limited knee flexion* (EN100156); "distended" for
  *Abdominal distention* (EN100376). Adding the subject makes the span a
  clause that can contain a negation word ("abdomen appeared neither tender
  nor distended").
- Hedging cue inside the span ("sugiriendo", ES100578).
- Shared constructions longer than the 120-character context of the
  proposal format: CRP, LDH, and ESR after "increased levels of" (EN100606).
- Long spans in general: 122 of 1,490 mentions in `rest92-opus-v3` are
  longer than 50 characters, the longest has 111.

Sub-questions:

- a. Are leading or trailing side, site, size, and quality words always
  dropped when they do not determine the term?
- b. Does a site-specific term need its site inside the span, even when the
  span then becomes a clause or contains a negation word? Or is the short
  predicate enough, with the consequence that it is not usable as a
  single-term input?
- c. Is there an upper bound for a span, and what applies to a shared
  construction (R4) that exceeds it?

Derived clarification (2026-10-09; A37, A45):

Use the shortest contiguous phrase that carries the selected term. Drop
non-determining words at its edges; retain unavoidable internal words under
the existing contiguity rule. A site-specific term requires the site inside
the span, even if that requires a subject and intervening words or cues;
axes are recorded separately. Do not use an isolated predicate with site
borrowed from context. There is no guideline character limit. Proposal
excerpt limits are tooling constraints that must be addressed in the
proposal workflow, not by truncating complete spans. These are operational
consequences, not a separately chosen user option.

### Q8 Past-history conditions: `historical` or `current`

Earlier guideline: `historical` is "a finding the text places before" the
reported episode (A22).

Where proposals diverge: chronic conditions listed under the past history
("antecedentes", "antécédents") are mostly recorded as `historical`:
hypertension, diabetes, COPD, hypercholesterolaemia, atrial fibrillation,
migraine (ES100659, ES100715, ES100819, batch-04). Ulcerative colitis is
`current` in batch-05. A negated history ("no history of X") is `absent`
and `historical` in batch-02.

Options:

- a. By section: everything named under the past history is `historical`.
- b. By persistence: a chronic condition that still exists is `current`;
  only events and conditions that have ended are `historical`.
- c. As a, but a condition the report treats as part of the present illness
  is `current`.

To consider: temporality is not a criterion of the single-term derivation
(A33); it matters for a temporality-aware evaluation and for issue #2.

Decision (2026-10-09; A42):

The user chose explicit time reference and corrected the initial
section-based option: `historical` only when the finding is unambiguously
placed before the reported episode. Past tense and an anamnesis heading
alone are insufficient. "Bei Aufnahme bestand Fieber" is `current`.
Without an explicit earlier reference use `current`; do not assume either
persistence or resolution of chronic conditions. This is not the original
option a (classifying everything in the past-history section as historical).

### Q9 Resolved, excluded, and refuted findings; hedge words

Earlier guideline: whether a finding has resolved is not recorded (A23). The R5
example nevertheless turns "fieberfrei" into *Fever* `absent` (A26). A
finding the text only suggests is `uncertain` (A20).

Where proposals diverge:

- Resolution: "seizures stopped" and "resolution of the pericardial
  effusion" are further mentions of the `present` annotation in batch-01
  and batch-02; "disparition de X" is a separate `absent` annotation in
  batch-08 and batch-09 (nuchal rigidity, myalgia, low back pain).
- A suspicion the work-up refutes: *Hemangioma* `uncertain` or `absent`
  after the authors reject it (ES100713); *Type I diabetes mellitus*
  `uncertain` or `absent` after a normal fasting glucose (FR100130).
- Hedge words not in the R3 list: "indicated" read as `present` in EN101783
  and "indicating" as `uncertain` in EN105551; "de aspecto esteatósico"
  (ES100832); "aparente" (ES100098).

Sub-questions:

- a. Is a statement that a finding has resolved a separate `absent`
  annotation, a further occurrence of the `present` one, or not marked?
  Does the answer differ between "X disappeared" and a negating term such
  as "fieberfrei"?
- b. Is a suspected finding that the report later rules out `absent`,
  `uncertain`, or both as two annotations?
- c. Which further wordings count as hedges ("indicate", "appearance of",
  "apparent")?

Decision (2026-10-09; A41):

The user chose separate states: an explicitly resolved finding gives
`absent`, alongside its earlier `present` occurrence. "X disappeared" and
"fieberfrei" follow the same rule. An explicit suspicion and later explicit
exclusion similarly remain separate `uncertain` and `absent` annotations;
normal test values alone do not establish exclusion. Hedge wording is
judged by the meaning of the statement, not a mechanical word list, and
uncertainty about a cause does not hedge an established finding. Scoring
temporally sequenced annotations remains open.

### Q10 Treatments with a term; borderline values

Earlier guideline: procedures and treatments are not annotated; the exception
for terms HPO models as phenotypes is stated only for diagnoses (A7). R6
covers "pathological" measurements without saying where pathological
begins (A28).

Where proposals diverge:

- Treatments, procedures, and their traces with an HPO term: *Nasogastric
  tube feeding* (ES100310), *Bleeding requiring red cell transfusion* for
  "needed 4 red cell packs" (EN100497), *Scarring* for a surgical scar
  (ES100797).
- Uninterpreted values at the edge of the reference range: blood pressure
  90/60 mmHg as *Hypotension* (EN100605), Hb 11,4 g/dl as *Anemia*
  (FR100092), QTc 450 ms as *Prolonged QTc interval* (FR100275), "osmotic
  gap was 45" (EN100376).

Sub-questions:

- a. Does the R0 exception extend to treatments and procedures for which
  the release has a term under *Phenotypic abnormality*?
- b. Which reference decides whether an uninterpreted value is
  pathological, and is a borderline value annotated?

Decision (2026-10-09; A43, A44):

The user excludes procedures and treatments even where HPO offers a term;
explicit pathological findings or consequences are annotated instead.
Treatment alone does not establish a phenotype. The user also chose a
stricter rule than the proposed report-reference option: only findings the
text itself explicitly classifies as pathologically altered may and must
be annotated. No numeric values are interpreted, including values with
reference intervals printed in the report. Therefore no external range or
borderline-value rule is needed, and the former non-verbalized measurement
category is superseded.

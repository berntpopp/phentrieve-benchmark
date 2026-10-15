# HPO span proposals for E3C reports (prompt v4)

You propose HPO annotations for clinical case reports. Your output is
machine generated, not review data, and not gold: a physician reviews every
proposal later in an annotation editor.

## Read first

1. Read the annotation guideline
   `docs/annotation-guidelines/hpo-span-annotation.md` completely. Rules
   R0-R6 decide what you annotate, which term you choose, where a span starts
   and ends, and which status you record. R7 concerns you only for German
   reports (see "German reports" below). Where this prompt and the guideline
   differ, the guideline wins.
2. Then read each report text listed under "This batch" below. Read every
   text with Bash, for example `cat "<text file>"`; the Read tool truncates
   long lines.

All paths in this prompt are relative to the repository root, which is your
working directory. Where a tool needs an absolute path (for example to write
the output file), prepend the repository root.

Use nothing else. Do not open other files under `datasets/`, earlier
proposal runs, E3C annotations, UMLS mappings, or the Phase 0 feasibility
files, and do not search the web. Proposals must come from the text alone.

## Finding HPO terms

Every `hpo_id` must be an active term of HPO release v2026-06-23. Look terms
up with

    uv run phentrieve-benchmark proposals hpo-lookup "<english term>" ["<another term>" ...]

The lookup searches English labels and synonyms, so translate the finding
into English medical wording first. Pass several queries in one call.
`hpo-lookup HP:0001945` shows the label of an ID. Copy `hpo_label` from the
lookup output. Never invent an ID; if no term fits, do not annotate the
finding. Choose the most specific term that the marked phrase itself
supports (R1). Context outside the phrase may decide the status, but never
makes the term more specific. When a qualification has no fitting specific
term, use the fitting general term. Do not substitute components,
consequences, or clinical inferences for a missing term; if nothing fits,
leave the finding out and list it in your reply.

The lookup matches words, not meaning. Before you settle for a general term
or drop a finding, try other wordings: synonyms, the technical and the lay
name, and the finding together with its site ("pancreatic tumor" rather than
"tumor").

The lookup lists only terms under *Phenotypic abnormality*, the branch the
guideline covers (R0). A lookup by ID marks a term outside it as "not a
phenotypic abnormality"; do not use such a term.

## What to propose

Per report, list every phenotypic finding the guideline asks for (R0),
whatever its status: negated, uncertain, historical, family members, and
other persons included.

Be complete. Go through each report sentence by sentence. Findings from the
history, the physical examination, specialised examinations (for example
eye, skin, or neurological), laboratory results, imaging, and histology all
count. A negated list gives one absent proposal per finding ("no A, B, or
C" gives three). When a report is drafted, read it once more and add every
finding you passed over.

What is not proposed:

- a bare measurement, even with a reference interval: "Hb 6,8 g/dl" gives
  nothing. Propose a measurement finding only when the text itself calls it
  pathological ("erniedrigtes Hämoglobin", "CRP erhöht"), and mark that
  wording, not the value (R6);
- procedures and treatments, even when HPO has a term for them, and
  findings inferred from a treatment, a pathogen name, or a test result the
  text does not call pathological (R0);
- hypothetical and generic statements, and normal findings the text does
  not name as a negated phenotype (R0).

For each proposal:

- One proposal per HPO term and status. The status is the combination of
  `assertion`, `experiencer`, and `temporality`. Put every occurrence with
  the same status into the same proposal as further mentions (R5). An
  occurrence with a different status is a separate proposal.
- Mark every place where the text names the finding again, also when it is
  worded differently (R5). A renewed mention counts only if its own wording
  supports the term: a later general mention ("diese Schmerzen") gets its
  own general term, and a mere reference ("diese Befunde") is no mention.
- Do not add an ancestor term for the same occurrence. Separate general and
  specific occurrences each get the term their own phrase supports (R1).
- `assertion`: `present`, `absent`, or `uncertain` (R3). Use `uncertain` only
  when the text hedges the finding itself. A hedge on its cause or pathogen
  leaves the finding `present`. An explicitly resolved or excluded finding
  is a separate `absent` proposal next to the earlier `present` or
  `uncertain` one; a normal test alone excludes nothing.
- `experiencer`: `patient`, `family_member`, or `other` (R3).
- `temporality`: `current` or `historical` (R3). `historical` needs an
  unambiguous time before the reported episode; past tense or an anamnesis
  heading alone is `current`.
- `verbalized`: always `true`. Non-verbalized measurement findings are no
  longer proposed (R6); the field stays only for the output format.
- `note`: `null`, or one short English sentence when a choice is not
  obvious.

## How to give a mention

A mention is located by two strings copied verbatim from the text:

- `phrase`: the span by R2 and R4, the shortest contiguous phrase that
  expresses the term, without negation or hedging cues. Contiguity comes
  before minimality, and a site-specific term needs its site in the phrase
  (R2). When several terms share wording (R4), each of them gets the same
  whole construction as its phrase. Complementary terms may share one phrase
  when no single term covers all its named characteristics and neither is an
  ancestor of the other (R4).
- `context`: a short excerpt of the text, at most 120 characters, that
  contains the phrase and occurs exactly once in the whole text. A clause
  around the phrase is usually enough; lengthen it only to make it unique.

Copy both exactly, including case, accents, and punctuation. Quotation
marks, dashes, and runs of spaces may differ; nothing else may.

If the phrase occurs more than once inside its context, add
`"occurrence": n`. Matches are counted whole words first, then matches inside
longer words: for "ache" in "headache and ache", the whole word "ache" is
occurrence 1 and the "ache" inside "headache" is occurrence 2. Prefer a
context in which the phrase occurs only once.

Mentions of one proposal must not overlap.

No string anywhere in your output (phrase, context, note) may be longer than
300 characters. The texts are licensed for non-commercial use and your
output is published, so it must contain short excerpts only. A file with a
longer string is discarded as a whole. This limit is a tooling constraint,
not part of the guideline: never shorten a phrase to fit it. If a complete
phrase would be longer, leave that proposal out and list it in your reply.

## German reports

German reports are machine translations (R7). Mark their wording as it
stands; do not correct it. When the wording of a phrase is unnatural or
wrong German, or the translation seems to change the medical meaning, still
propose the finding if a term fits and say so in `note`, starting with
"Translation:". The reviewer decides whether the text needs a correction.

## Output

Write exactly one file, `datasets/e3c-de/proposals/de-opus-v4/batch-07.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "de-opus-v4",
  "batch_id": "batch-07",
  "reports": [
    {
      "document_id": "<document_id from the list below>",
      "document_sha256": "<document_sha256 from the list below>",
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
  ]
}
```

- One entry in `reports` per document below, in the listed order, with its
  `document_id` and `document_sha256` copied exactly. A report without
  findings has `"annotations": []`.
- `proposal_id` is `p001`, `p002`, ... within each report.
- Change no other file. You may write helper scripts, for example to check
  your phrases and contexts against the texts, but only into the directory
  that holds your text files; it is not tracked. Write nothing anywhere
  else, inside or outside the repository.
- When done, reply with one line per report (document ID and number of
  proposals). Then list every finding you left out because no HPO term
  fits or its phrase exceeds the length limit, every file you read, and
  every command you ran.

## This batch

Run `de-opus-v4`, batch `batch-07`.

1. document_id `e3c:v2.0.0:de:FR100998:translated`, document_sha256 `def2232bf76527e83049f6617d8bccc78754da92dd3a726e52ecdc575ac0f189`, language `de`, text file `.artifacts/proposals/de-opus-v4/batch-07/FR100998.txt`

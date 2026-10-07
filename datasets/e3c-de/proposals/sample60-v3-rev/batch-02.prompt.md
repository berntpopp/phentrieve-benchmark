# Revising HPO span proposals for E3C reports (revision v1)

You revise machine-generated HPO annotation proposals for clinical case
reports against the report texts and write the revised proposals. Your
output is machine generated, not review data, and not gold: a physician
reviews every proposal later in an annotation editor.

## Read first

1. Read the annotation guideline
   `docs/annotation-guidelines/hpo-span-annotation.md` completely. Rules
   R0-R6 decide what is annotated, which term is chosen, where a span starts
   and ends, and which status is recorded. R7 does not concern you.
2. Then, for each report listed under "This batch" below, read the text, the
   first-pass file, and, where one is listed, the cross-read file. Read
   every text with Bash, for example `cat "<text file>"`; the Read tool
   truncates long lines.

All paths in this prompt are relative to the repository root, which is your
working directory. Where a tool needs an absolute path (for example to write
the output file), prepend the repository root.

Use nothing else. Do not open files under `datasets/`, other proposal runs,
E3C annotations, UMLS mappings, or the Phase 0 feasibility files, and do not
search the web. Your judgement must come from the text and the guideline.

## Your inputs per report

`<case>.first-pass.json` holds what the first pass proposed:

- `annotations`: the proposals in the format of your output (see "Output"),
  each with its `proposal_id`.
- `rejections`: proposals or mentions the validator rejected, with a reason.
  A rejected proposal is not usable as it is: repair it or leave it out.

`<case>.crossread.json`, where listed, holds what an earlier cross-read
found:

- `issues`: points on first-pass proposals, each with `proposal_id`, `kind`
  (`not_a_finding`, `wrong_term`, `wrong_span`, `wrong_status`,
  `wrong_verbalized`, `missing_occurrence`, `extra_occurrence`), `severity`
  (`clear` or `arguable`), a `correction`, and a `note`.
- `missed`: findings without a proposal, each with term, status, `phrase`,
  `context`, `severity`, and a `note`.

The cross-read is a second machine opinion, not a ruling.

## HPO terms

Every term must be an active term of HPO release v2026-06-23 under
*Phenotypic abnormality*. Look terms up with

    uv run phentrieve-benchmark proposals hpo-lookup "<english term>" ["<another term>" ...]

The lookup searches English labels and synonyms of terms under *Phenotypic
abnormality* and matches words, not meaning: try synonyms, the technical and
the lay name, and the finding together with its site. `hpo-lookup HP:0001945`
shows the label of an ID. Copy `hpo_label` from the lookup output. Never
invent an ID.

## What to do

Go through each report sentence by sentence and compare it with the first
pass.

For every first-pass proposal:

- Is it a phenotypic finding the guideline asks for (R0)? A normal finding,
  a hypothetical statement, a procedure, or a pathogen is not.
- Is the term the most specific one the text supports (R1)? Look for a more
  specific term before you accept a general one.
- Is each span the shortest contiguous phrase that expresses the term on its
  own, without negation or hedging cues (R2), and the whole shared
  construction where terms share wording (R4)?
- Is the status right (R3)? A finding the text only suggests is `uncertain`;
  a hedge on its cause or pathogen leaves it `present`; a negated finding is
  `absent`.
- Is `verbalized` false only for a pathological measurement the text does
  not interpret (R6)?
- Is every place marked where the text names the finding again (R5)? A
  back-reference ("the tumour", "this pain") is not an occurrence.

Then look for missed findings: every finding the guideline asks for that has
no proposal, whatever its status (negated, uncertain, historical, family
members, other persons). Findings an examination rules out are `absent`. Add
a finding only if the lookup gives a fitting term.

Where a cross-read file is listed, decide every point in it:

- Check each point against the text and the guideline. Apply a `clear` point
  unless the text or the guideline contradicts it. Decide an `arguable`
  point yourself; when both readings are defensible, keep the first pass.
- Check the term of a correction or a missed finding with the lookup before
  you use it.
- The cross-read does not replace your own reading: correct what it
  overlooked as well.

Where no cross-read file is listed, your own reading is the only check.

Apply R2 the same way everywhere: a word at the start or end of a span that
does not determine the term (side, size, degree, or a value after a finding
the text states in words) is outside the span; a word inside the phrase
stays (contiguity). Keep such a word when it determines the term you chose.

Leave a proposal unchanged when it is right. A defensible choice of the
first pass that you would merely have made differently is not a reason to
change it.

## The revised proposals

- One proposal per HPO term and status. The status is the combination of
  `assertion`, `experiencer`, `temporality`, and `verbalized`. Every
  occurrence with the same status belongs to the same proposal (R5); an
  occurrence with a different status is a separate proposal.
- A proposal you keep or change keeps its `proposal_id`. A proposal you drop
  is left out. A proposal you add gets the next free number after the
  highest `proposal_id` of the first pass. When a changed term or status
  makes two proposals equal in term and status, put their mentions into the
  one with the lower number and leave the other out.
- `note`: `null`, or one short English sentence when a choice is not
  obvious. Keep a first-pass note that still applies.

A mention is located by two strings copied verbatim from the text:

- `phrase`: the span by R2 and R4.
- `context`: a short excerpt of the text, at most 120 characters, that
  contains the phrase and occurs exactly once in the whole text.

Copy both exactly, including case, accents, and punctuation. Quotation
marks, dashes, and runs of spaces may differ; nothing else may. If the
phrase occurs more than once inside its context, add `"occurrence": n`
(whole-word matches are counted first, then matches inside longer words);
prefer a context in which the phrase occurs only once. Mentions of one
proposal must not overlap.

No string anywhere in your output (phrase, context, note) may be longer than
300 characters. The texts are licensed for non-commercial use and your
output is published, so it must contain short excerpts only. A file with a
longer string is discarded as a whole.

## Output

Write exactly one file, `datasets/e3c-de/proposals/sample60-v3-rev/batch-02.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "sample60-v3-rev",
  "batch_id": "batch-02",
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
- Change no other file. You may write helper scripts, for example to copy
  the unchanged proposals from the first-pass files and to check your
  phrases and contexts against the texts, but only into the directory that
  holds your text files; it is not tracked. Write nothing anywhere else,
  inside or outside the repository.
- When done, reply with one line per report: document ID, first-pass
  proposals, proposals unchanged, changed, dropped, and added; where a
  cross-read file was listed, also its points applied and not applied. Then
  name every `clear` cross-read point you did not apply, with the reason in
  one sentence each, every file you read, and every command you ran.

## This batch

Run `sample60-v3-rev`, batch `batch-02`.

1. document_id `e3c:v2.0.0:en:EN100655:native`, document_sha256 `772a08645287605062b431e8f003393fb5dbe4875dc50646c1fb56cec5da1ec6`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN100655.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN100655.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN100655.crossread.json`
2. document_id `e3c:v2.0.0:en:EN101318:native`, document_sha256 `9beb750b345365a13cf32d2f29d14c31086e910036ea50cee39567f86a706286`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN101318.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN101318.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN101318.crossread.json`
3. document_id `e3c:v2.0.0:en:EN102305:native`, document_sha256 `65a17cec78ee34e7d1c160378fa826d7e4fe53712f9caef479a7621b2ce93a51`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN102305.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN102305.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN102305.crossread.json`
4. document_id `e3c:v2.0.0:en:EN103266:native`, document_sha256 `9cc56aa4a7ac18475034ce1f2845165107dc6927aa4b45186861904354b0f284`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN103266.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN103266.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN103266.crossread.json`
5. document_id `e3c:v2.0.0:en:EN104184:native`, document_sha256 `4b7eb14715159b7d25e356d04b05a31e3978b4e48af162f36a4eb4721b723686`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN104184.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN104184.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN104184.crossread.json`
6. document_id `e3c:v2.0.0:en:EN104263:native`, document_sha256 `0a7b200c399a9b10c78a8658d4542236a618e994f9cf55aede1eb38b1cc180a2`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN104263.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN104263.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN104263.crossread.json`
7. document_id `e3c:v2.0.0:en:EN105223:native`, document_sha256 `4e5fa38ada4c4d7a68679c8db3534d39bc3bccd0f14c80cec3a8b6b32629c838`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN105223.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN105223.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN105223.crossread.json`
8. document_id `e3c:v2.0.0:en:EN105832:native`, document_sha256 `6190efdf31fd74dda4ade83935c138b845cd4f4cf42447c840be1f0452ab30e3`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN105832.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN105832.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN105832.crossread.json`
9. document_id `e3c:v2.0.0:en:EN108055:native`, document_sha256 `1199784e5861a6c6ac292923f06c887ed23fa1403c45d2d41933d20869c8a3c8`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN108055.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN108055.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN108055.crossread.json`
10. document_id `e3c:v2.0.0:en:EN108254:native`, document_sha256 `60d02964037934fa941f2a7362ac80971a2b98ce08a72fadf5e72d0000a71414`, language `en`, text file `.artifacts/proposals/sample60-v3-rev/batch-02/EN108254.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-02/EN108254.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-02/EN108254.crossread.json`

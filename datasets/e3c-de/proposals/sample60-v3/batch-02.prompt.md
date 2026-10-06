# HPO span proposals for E3C reports (prompt v3)

You propose HPO annotations for clinical case reports. Your output is
machine generated, not review data, and not gold: a physician reviews every
proposal later in an annotation editor.

## Read first

1. Read the annotation guideline
   `docs/annotation-guidelines/hpo-span-annotation.md` completely. Rules
   R0-R6 decide what you annotate, which term you choose, where a span starts
   and ends, and which status you record. R7 does not concern you.
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
finding. Choose the most specific term the text supports (R1).

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
eye, skin, or neurological), laboratory values, imaging, and histology all
count. A negated list gives one absent proposal per finding ("no A, B, or
C" gives three). When a report is drafted, read it once more and add every
finding you passed over.

- One proposal per HPO term and status. The status is the combination of
  `assertion`, `experiencer`, `temporality`, and `verbalized`. Put every
  occurrence with the same status into the same proposal as further mentions
  (R5). An occurrence with a different status is a separate proposal.
- Mark every place where the text names the finding again, also when it is
  worded differently (R5).
- `assertion`: `present`, `absent`, or `uncertain` (R3). Use `uncertain` only
  when the text hedges the finding itself. A hedge on its cause or pathogen
  leaves the finding `present`.
- `experiencer`: `patient`, `family_member`, or `other` (R3).
- `temporality`: `current` or `historical` (R3).
- `verbalized`: `false` only for a pathological measurement the text does
  not interpret (R6); otherwise `true`.
- `note`: `null`, or one short English sentence when a choice is not
  obvious.

## How to give a mention

A mention is located by two strings copied verbatim from the text:

- `phrase`: the span by R2 and R4, the shortest contiguous phrase that
  expresses the term, without negation or hedging cues. When several terms
  share wording (R4), each of them gets the same whole construction as its
  phrase.
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
longer string is discarded as a whole.

## Output

Write exactly one file, `datasets/e3c-de/proposals/sample60-v3/batch-02.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "sample60-v3",
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
- `proposal_id` is `p001`, `p002`, ... within each report.
- Change no other file. You may write helper scripts, for example to check
  your phrases and contexts against the texts, but only into the directory
  that holds your text files; it is not tracked. Write nothing anywhere
  else, inside or outside the repository.
- When done, reply with one line per report (document ID and number of
  proposals). Then list every finding you left out because no HPO term
  fits, every file you read, and every command you ran.

## This batch

Run `sample60-v3`, batch `batch-02`.

1. document_id `e3c:v2.0.0:en:EN100655:native`, document_sha256 `772a08645287605062b431e8f003393fb5dbe4875dc50646c1fb56cec5da1ec6`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN100655.txt`
2. document_id `e3c:v2.0.0:en:EN101318:native`, document_sha256 `9beb750b345365a13cf32d2f29d14c31086e910036ea50cee39567f86a706286`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN101318.txt`
3. document_id `e3c:v2.0.0:en:EN102305:native`, document_sha256 `65a17cec78ee34e7d1c160378fa826d7e4fe53712f9caef479a7621b2ce93a51`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN102305.txt`
4. document_id `e3c:v2.0.0:en:EN103266:native`, document_sha256 `9cc56aa4a7ac18475034ce1f2845165107dc6927aa4b45186861904354b0f284`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN103266.txt`
5. document_id `e3c:v2.0.0:en:EN104184:native`, document_sha256 `4b7eb14715159b7d25e356d04b05a31e3978b4e48af162f36a4eb4721b723686`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN104184.txt`
6. document_id `e3c:v2.0.0:en:EN104263:native`, document_sha256 `0a7b200c399a9b10c78a8658d4542236a618e994f9cf55aede1eb38b1cc180a2`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN104263.txt`
7. document_id `e3c:v2.0.0:en:EN105223:native`, document_sha256 `4e5fa38ada4c4d7a68679c8db3534d39bc3bccd0f14c80cec3a8b6b32629c838`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN105223.txt`
8. document_id `e3c:v2.0.0:en:EN105832:native`, document_sha256 `6190efdf31fd74dda4ade83935c138b845cd4f4cf42447c840be1f0452ab30e3`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN105832.txt`
9. document_id `e3c:v2.0.0:en:EN108055:native`, document_sha256 `1199784e5861a6c6ac292923f06c887ed23fa1403c45d2d41933d20869c8a3c8`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN108055.txt`
10. document_id `e3c:v2.0.0:en:EN108254:native`, document_sha256 `60d02964037934fa941f2a7362ac80971a2b98ce08a72fadf5e72d0000a71414`, language `en`, text file `.artifacts/proposals/sample60-v3/batch-02/EN108254.txt`

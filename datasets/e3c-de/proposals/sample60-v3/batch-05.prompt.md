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

Write exactly one file, `datasets/e3c-de/proposals/sample60-v3/batch-05.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "sample60-v3",
  "batch_id": "batch-05",
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

Run `sample60-v3`, batch `batch-05`.

1. document_id `e3c:v2.0.0:fr:FR100227:native`, document_sha256 `40182a37675c61fd91b1cd0b078afc19a9a08e86768fdefc00af776308e42ce8`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100227.txt`
2. document_id `e3c:v2.0.0:fr:FR100296:native`, document_sha256 `dcf8044bb9f06ea5898a48019c41cf920d182796da489414c08a3be1d25b6a74`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100296.txt`
3. document_id `e3c:v2.0.0:fr:FR100344:native`, document_sha256 `1c53752c1d51b6bd3da44ffae2d309d6bba578e2bb963c419db6d1da2a6cf5bb`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100344.txt`
4. document_id `e3c:v2.0.0:fr:FR100597:native`, document_sha256 `e1218ae4cc338ad1042898d4d14a2f4c77d1ff8035391aeb21a4840923e11983`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100597.txt`
5. document_id `e3c:v2.0.0:fr:FR100603:native`, document_sha256 `b35c4d40ea5d6ea437017df71d12f7d1d94574a77ffb3b2aa68bca1854ff8f99`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100603.txt`
6. document_id `e3c:v2.0.0:fr:FR100611:native`, document_sha256 `458c831c1d39c39396827f2f62a4fc7d736a48ad9416b70c999c86f25cb01a2a`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100611.txt`
7. document_id `e3c:v2.0.0:fr:FR100614:native`, document_sha256 `7d2126866b1c3c01b00d5b9f82d9f3d24363cf9d4813dda5906bcb8840849a74`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100614.txt`
8. document_id `e3c:v2.0.0:fr:FR100620:native`, document_sha256 `2550d99cae3e7bcee7868229e5c73816e17ffab1485ec311b74c23297a2a40b0`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100620.txt`
9. document_id `e3c:v2.0.0:fr:FR100666:native`, document_sha256 `b2077d46892bbbeeb1d74de6577cf35755cb15243ad014e32e0d6120733ab662`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100666.txt`
10. document_id `e3c:v2.0.0:fr:FR100683:native`, document_sha256 `f2d5450c55d9b217c3463a871a1240f2f9df2c9c414dcbe8d0c49ad33d1074f2`, language `fr`, text file `.artifacts/proposals/sample60-v3/batch-05/FR100683.txt`

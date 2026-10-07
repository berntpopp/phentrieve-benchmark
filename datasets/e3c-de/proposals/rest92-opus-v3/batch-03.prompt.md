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

Write exactly one file, `datasets/e3c-de/proposals/rest92-opus-v3/batch-03.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "rest92-opus-v3",
  "batch_id": "batch-03",
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

Run `rest92-opus-v3`, batch `batch-03`.

1. document_id `e3c:v2.0.0:en:EN101114:native`, document_sha256 `ed798f8c6b75c4f78b303c1c0d430a3ae4135a488919b1822df78efb942035a1`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN101114.txt`
2. document_id `e3c:v2.0.0:en:EN101783:native`, document_sha256 `ee7b4085f07f2d15f2bd3c5fec064dfad2bb7915be874a5544b6cf0d46d023fd`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN101783.txt`
3. document_id `e3c:v2.0.0:en:EN103007:native`, document_sha256 `7cff231d5a253f3d43f537ecec1cdd1080ad7841497259e11229e81032ad51f3`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN103007.txt`
4. document_id `e3c:v2.0.0:en:EN104655:native`, document_sha256 `1eb9d4144280e72be2261bde698614755ddd63ce1b03a4addc5e476f43bd1be8`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN104655.txt`
5. document_id `e3c:v2.0.0:en:EN104891:native`, document_sha256 `9637c9925f729f27d0fb1315447206689e015e7fe171185787605a2c7e382368`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN104891.txt`
6. document_id `e3c:v2.0.0:en:EN105094:native`, document_sha256 `0c698f5909f76bce399373778f3f68f64e61f871c2c7bf576548b9762154ca4a`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN105094.txt`
7. document_id `e3c:v2.0.0:en:EN105114:native`, document_sha256 `977ce11ff1cac43072fa7d126012a698a45cf40003ddd42ec702f649b2f4a9bc`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN105114.txt`
8. document_id `e3c:v2.0.0:en:EN105551:native`, document_sha256 `81f6aaa294e4fb5a0a49854d729f9226538b2b1ab200f0a63f6ae4d9f9a521ac`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN105551.txt`
9. document_id `e3c:v2.0.0:en:EN106233:native`, document_sha256 `227b50f2289856c8a51f5fdcfbfbf185e14013ffaa980674139e83a691f4c55d`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN106233.txt`
10. document_id `e3c:v2.0.0:en:EN107021:native`, document_sha256 `b5981fe746e991857f944886fc7405f9be07478dee7d02ef9201fccff1604f61`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-03/EN107021.txt`

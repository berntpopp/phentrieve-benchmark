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

Write exactly one file, `datasets/e3c-de/proposals/rest92-opus-v3/batch-02.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "rest92-opus-v3",
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

Run `rest92-opus-v3`, batch `batch-02`.

1. document_id `e3c:v2.0.0:en:EN100399:native`, document_sha256 `265eaa0616c02aeee09f936f1d2baa0b6f2db0dc560c8133dc7a9e477de128f0`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100399.txt`
2. document_id `e3c:v2.0.0:en:EN100437:native`, document_sha256 `2a69642c2b65da14568f1ce2511f77649d672f313bf3113599ed0ac37e2f0dd9`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100437.txt`
3. document_id `e3c:v2.0.0:en:EN100497:native`, document_sha256 `64353460823072d7ebd537c845780bb0993ee7f6879826aa1f7f53a20d980087`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100497.txt`
4. document_id `e3c:v2.0.0:en:EN100506:native`, document_sha256 `72815a53e4de97283fce91d518b48b09c54a63cf3e83d16157aae4c140a4a2c1`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100506.txt`
5. document_id `e3c:v2.0.0:en:EN100600:native`, document_sha256 `c9498839723deccda1ca1ccfe28818015044cf80fac67ae19ec2b212d5876367`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100600.txt`
6. document_id `e3c:v2.0.0:en:EN100605:native`, document_sha256 `30822241830e6102036a3b1c583df193f8695e8d5119949fda3c5abfa5244ef2`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100605.txt`
7. document_id `e3c:v2.0.0:en:EN100606:native`, document_sha256 `0a32c5fe8da521f1ef8090520bee59cbfbca1deb6034705c82d5f47e982729c1`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100606.txt`
8. document_id `e3c:v2.0.0:en:EN100658:native`, document_sha256 `7456f82518e9fbc5b545c66b94265338c86c512f23616fa65b1ffd54b162cead`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100658.txt`
9. document_id `e3c:v2.0.0:en:EN100700:native`, document_sha256 `8f4f98c5eeeb43af3cf287c64c47244c85bf978eea6e0e78033e17f8b83e90c0`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100700.txt`
10. document_id `e3c:v2.0.0:en:EN100705:native`, document_sha256 `98ef222b75442b72981dbbb8be97b7663a7fedc1159a0538899d5001b209a31b`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-02/EN100705.txt`

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

Write exactly one file, `datasets/e3c-de/proposals/rest92-opus-v3/batch-05.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "rest92-opus-v3",
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

Run `rest92-opus-v3`, batch `batch-05`.

1. document_id `e3c:v2.0.0:es:ES100284:native`, document_sha256 `574bc57051fae98e0d3c6efc9871e2d07ea0b83c762a30e7c1a0d91d5d75ca43`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100284.txt`
2. document_id `e3c:v2.0.0:es:ES100310:native`, document_sha256 `ff6256fa05c048f58e24298c0829bbce71c04efaa672e975cd7f83f860cbc888`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100310.txt`
3. document_id `e3c:v2.0.0:es:ES100410:native`, document_sha256 `937b13afc92e3ea9d5eff6b31937be91c262546213abc369ffa92fcff0ce8f11`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100410.txt`
4. document_id `e3c:v2.0.0:es:ES100417:native`, document_sha256 `6b45f918cd5a613cce1b7243591bd266827008b5db83a7cc810d3b064ad09728`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100417.txt`
5. document_id `e3c:v2.0.0:es:ES100423:native`, document_sha256 `72e55a60201cfeef9c40d8ec0988c97d297c6177c74f75d309830c06b6dfd903`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100423.txt`
6. document_id `e3c:v2.0.0:es:ES100519:native`, document_sha256 `ddf1dc262f69fbd9c1d48870bb8eee8bf4ac75dc92e211194d6dd77aedd945a5`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100519.txt`
7. document_id `e3c:v2.0.0:es:ES100521:native`, document_sha256 `00d466a3fd6eced2f7bbfc59da85e918185665c54e1572b50b9b65a45ab1e55d`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100521.txt`
8. document_id `e3c:v2.0.0:es:ES100578:native`, document_sha256 `3cf1e06ade256f9b4f5cc44e7e60821dca89ca1a4e980f01428c8fd42b117e5e`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100578.txt`
9. document_id `e3c:v2.0.0:es:ES100605:native`, document_sha256 `bfc522aa4e3aa1eb326825ddc1a6ca61e4451601fd3c2b574e4c917dab1fa744`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100605.txt`
10. document_id `e3c:v2.0.0:es:ES100634:native`, document_sha256 `0ea5376e8e29f020e39d34b59e33239b930cf95cdc2e59ecda4be70edfb435a7`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100634.txt`

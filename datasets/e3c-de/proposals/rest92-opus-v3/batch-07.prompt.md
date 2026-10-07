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

Write exactly one file, `datasets/e3c-de/proposals/rest92-opus-v3/batch-07.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "rest92-opus-v3",
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
  fits, every file you read, and every command you ran.

## This batch

Run `rest92-opus-v3`, batch `batch-07`.

1. document_id `e3c:v2.0.0:es:ES100832:native`, document_sha256 `afc6facc805df8816fba5a122829d118b0d08eed9d04939f710f0c0c820f0a4b`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/ES100832.txt`
2. document_id `e3c:v2.0.0:es:ES100840:native`, document_sha256 `34b778a7f608871085f108bbaa34a6754677760e005c27d0c0bb7294cc71f829`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/ES100840.txt`
3. document_id `e3c:v2.0.0:fr:FR100003:native`, document_sha256 `b7809e009ad1d240ef4c253d7cabf553ecced9514095a620060e2cc86076ab67`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100003.txt`
4. document_id `e3c:v2.0.0:fr:FR100078:native`, document_sha256 `b718a60c0432a01a174d59d57787d672d8e8426da88ed41f8effbc0fddefda05`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100078.txt`
5. document_id `e3c:v2.0.0:fr:FR100092:native`, document_sha256 `1e392e8962a62b82fd2da4c0a780cc4c8a1c809dcca0ff81aab419ab1190d30a`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100092.txt`
6. document_id `e3c:v2.0.0:fr:FR100130:native`, document_sha256 `ecb61fb69b34c156c8c21a48ffbdc64567073254017d2f67ac3d3abccbedcea0`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100130.txt`
7. document_id `e3c:v2.0.0:fr:FR100168:native`, document_sha256 `4c2519221313901a902c70413bdda15d2debd04e016958cd26aeb1f87879400b`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100168.txt`
8. document_id `e3c:v2.0.0:fr:FR100275:native`, document_sha256 `bd871f909c965a43fcc4be35c24ea501f067106b7273f3094e186b5a7487989b`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100275.txt`
9. document_id `e3c:v2.0.0:fr:FR100276:native`, document_sha256 `5bdb5663e7848d7291d6a113757c49f3933f0e5609162fc7a517652d15a79b29`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100276.txt`
10. document_id `e3c:v2.0.0:fr:FR100282:native`, document_sha256 `b163ee3e3186fc87fa6e0d96439171603a2aa9cc8e75f4bfa8cb06ca6605b276`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100282.txt`

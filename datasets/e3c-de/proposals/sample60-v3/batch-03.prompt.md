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

Write exactly one file, `datasets/e3c-de/proposals/sample60-v3/batch-03.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "sample60-v3",
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

Run `sample60-v3`, batch `batch-03`.

1. document_id `e3c:v2.0.0:es:ES100030:native`, document_sha256 `c840b419b27e69dd174136384362096e917d0f649f7eefffb626d7d573d701e2`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100030.txt`
2. document_id `e3c:v2.0.0:es:ES100042:native`, document_sha256 `dbddd892c0a59cc68d54b50c336b9439ceef409714613a9e980224056cf8ff81`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100042.txt`
3. document_id `e3c:v2.0.0:es:ES100051:native`, document_sha256 `4fa3a0cdfb3d75c6fea9d6a522a511aba45d26b59cc24b228525400699ea92c2`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100051.txt`
4. document_id `e3c:v2.0.0:es:ES100178:native`, document_sha256 `f61f4650ec1c5fa95a8e775fe5102209bce974968fba436999a0aa5fcb7bfd31`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100178.txt`
5. document_id `e3c:v2.0.0:es:ES100278:native`, document_sha256 `363c42ce946acb41864fdb5441bb389e67b7deb5b05bd5e35331ce25f6c90e7a`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100278.txt`
6. document_id `e3c:v2.0.0:es:ES100363:native`, document_sha256 `e33bc3faf300fbbdf80e45c20d95262a9b499ebd8d2e82d95db7c43609b1bdc4`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100363.txt`
7. document_id `e3c:v2.0.0:es:ES100420:native`, document_sha256 `c460060e3c4ed17c39a80a82ea13eb4409883efade011a17d42cb47b61861a9e`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100420.txt`
8. document_id `e3c:v2.0.0:es:ES100445:native`, document_sha256 `25bf544fd9aec1030d0e621c0f9148a614c23bf453eb5ab5f17e89868ffc6f92`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100445.txt`
9. document_id `e3c:v2.0.0:es:ES100552:native`, document_sha256 `e264ca9d413faea00e63bad18c6a6fd9f02295631f68701a7ff41cfa854f6032`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100552.txt`
10. document_id `e3c:v2.0.0:es:ES100594:native`, document_sha256 `b926a6f515a50a9ad25ce91878c487ce3dc23f7aa554d3372c2d1424ce38fb55`, language `es`, text file `.artifacts/proposals/sample60-v3/batch-03/ES100594.txt`

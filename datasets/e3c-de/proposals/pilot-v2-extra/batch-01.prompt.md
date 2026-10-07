# HPO span proposals for E3C reports (prompt v2)

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
"tumor"). Use only terms for phenotypic findings. Terms that describe
course, onset, mortality, or inheritance are not findings.

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

Write exactly one file, `datasets/e3c-de/proposals/pilot-v2-extra/batch-01.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "pilot-v2-extra",
  "batch_id": "batch-01",
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
- Write no other file and change no file, inside or outside the repository.
  You may check your phrases and contexts against the texts with an inline
  script that writes nothing (for example `uv run python - <<'EOF'`).
- When done, reply with one line per report (document ID and number of
  proposals). Then list every finding you left out because no HPO term
  fits, every file you read, and every command you ran.

## This batch

Run `pilot-v2-extra`, batch `batch-01`.

1. document_id `e3c:v2.0.0:en:EN100068:native`, document_sha256 `fe8cdd0a669c2078b6f55d162e10dea278c1f54a025a55455db3b4cb919947e0`, language `en`, text file `.artifacts/proposals/pilot-v2-extra/batch-01/EN100068.txt`
2. document_id `e3c:v2.0.0:en:EN106156:native`, document_sha256 `83146cc94952b053e9e5ad554f4771ec494a7aed7bb20e805aea628d511f7da5`, language `en`, text file `.artifacts/proposals/pilot-v2-extra/batch-01/EN106156.txt`
3. document_id `e3c:v2.0.0:en:EN108139:native`, document_sha256 `a0d82b94cc894517b66e648636a37f4ffc9835960055466c3cd4a4fe77f037b5`, language `en`, text file `.artifacts/proposals/pilot-v2-extra/batch-01/EN108139.txt`
4. document_id `e3c:v2.0.0:es:ES100561:native`, document_sha256 `6fa5e50025fa0a0627b936bc568a7c32a4fc80fabf397cb792e11ba23995bc5f`, language `es`, text file `.artifacts/proposals/pilot-v2-extra/batch-01/ES100561.txt`
5. document_id `e3c:v2.0.0:es:ES100633:native`, document_sha256 `5dda5e13e77045e4fd47d9640a93f12ae960da7ca2d3743d86ff006a9b46db95`, language `es`, text file `.artifacts/proposals/pilot-v2-extra/batch-01/ES100633.txt`
6. document_id `e3c:v2.0.0:es:ES100937:native`, document_sha256 `d6cb1db2bc1087ef834cd768cf419c894dd2f86fd25e9a1de226fe873f8dd1ff`, language `es`, text file `.artifacts/proposals/pilot-v2-extra/batch-01/ES100937.txt`
7. document_id `e3c:v2.0.0:fr:FR100579:native`, document_sha256 `e99f2b05788a94a6e63a3610e312fb4cbcc79c0ff75e124d531bc3b44cebda48`, language `fr`, text file `.artifacts/proposals/pilot-v2-extra/batch-01/FR100579.txt`
8. document_id `e3c:v2.0.0:fr:FR100629:native`, document_sha256 `dd819d1f1d705bfa233617738a0743c9aefadfd229ff0235313c99137bf6dd26`, language `fr`, text file `.artifacts/proposals/pilot-v2-extra/batch-01/FR100629.txt`
9. document_id `e3c:v2.0.0:fr:FR100663:native`, document_sha256 `16f46eaf442090a59a81d0f02f15f1a448ac0b147aa581de90b14650dfa03738`, language `fr`, text file `.artifacts/proposals/pilot-v2-extra/batch-01/FR100663.txt`

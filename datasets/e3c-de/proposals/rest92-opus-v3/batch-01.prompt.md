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

Write exactly one file, `datasets/e3c-de/proposals/rest92-opus-v3/batch-01.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "rest92-opus-v3",
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
- Change no other file. You may write helper scripts, for example to check
  your phrases and contexts against the texts, but only into the directory
  that holds your text files; it is not tracked. Write nothing anywhere
  else, inside or outside the repository.
- When done, reply with one line per report (document ID and number of
  proposals). Then list every finding you left out because no HPO term
  fits, every file you read, and every command you ran.

## This batch

Run `rest92-opus-v3`, batch `batch-01`.

1. document_id `e3c:v2.0.0:en:EN100017:native`, document_sha256 `d56d319068dd6bd37f9010a06fc8cadcc54f09b7129ac82dd2b534e48dbcd4bb`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100017.txt`
2. document_id `e3c:v2.0.0:en:EN100029:native`, document_sha256 `6057fe87ad18ee1694fe2441803a0394da465e69637100c201d7422a39d6672a`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100029.txt`
3. document_id `e3c:v2.0.0:en:EN100046:native`, document_sha256 `bea5519fd5a8e80b3a636d4ed68c62e83cbc937fe274416855a5bdc887776afb`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100046.txt`
4. document_id `e3c:v2.0.0:en:EN100067:native`, document_sha256 `bb206ae50c8ed2cc5c879467a7ecc90d124f08776aa9a282b94a480360a5f236`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100067.txt`
5. document_id `e3c:v2.0.0:en:EN100075:native`, document_sha256 `c2dffd605e534d7f65c9ad3de434550cff15d7e506d20702856de39d951b22e8`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100075.txt`
6. document_id `e3c:v2.0.0:en:EN100090:native`, document_sha256 `5abd85942863efce44d86b7b3ece17677b1dae1889ac6fc22038eade90315ace`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100090.txt`
7. document_id `e3c:v2.0.0:en:EN100156:native`, document_sha256 `0b19fca1121f6b521fa023a09710eac0d1f63514f04b9729cb2688b369494959`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100156.txt`
8. document_id `e3c:v2.0.0:en:EN100339:native`, document_sha256 `c8c3897bfb45c6f3e9786992180c3c0c1e979753a1901ee28033e41d17fe4564`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100339.txt`
9. document_id `e3c:v2.0.0:en:EN100372:native`, document_sha256 `e02897fa491ec55556b601a3549b96a4a9ab0efe804c365dde60178905701653`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100372.txt`
10. document_id `e3c:v2.0.0:en:EN100376:native`, document_sha256 `acb5f8e284777e9a340ce03dbd53bc3a1bf288943f34ea7aa6536d006b05df25`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-01/EN100376.txt`

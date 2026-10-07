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

Write exactly one file, `datasets/e3c-de/proposals/sample60-v3-rev/batch-05.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "sample60-v3-rev",
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

Run `sample60-v3-rev`, batch `batch-05`.

1. document_id `e3c:v2.0.0:fr:FR100227:native`, document_sha256 `40182a37675c61fd91b1cd0b078afc19a9a08e86768fdefc00af776308e42ce8`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100227.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100227.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100227.crossread.json`
2. document_id `e3c:v2.0.0:fr:FR100296:native`, document_sha256 `dcf8044bb9f06ea5898a48019c41cf920d182796da489414c08a3be1d25b6a74`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100296.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100296.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100296.crossread.json`
3. document_id `e3c:v2.0.0:fr:FR100344:native`, document_sha256 `1c53752c1d51b6bd3da44ffae2d309d6bba578e2bb963c419db6d1da2a6cf5bb`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100344.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100344.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100344.crossread.json`
4. document_id `e3c:v2.0.0:fr:FR100597:native`, document_sha256 `e1218ae4cc338ad1042898d4d14a2f4c77d1ff8035391aeb21a4840923e11983`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100597.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100597.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100597.crossread.json`
5. document_id `e3c:v2.0.0:fr:FR100603:native`, document_sha256 `b35c4d40ea5d6ea437017df71d12f7d1d94574a77ffb3b2aa68bca1854ff8f99`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100603.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100603.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100603.crossread.json`
6. document_id `e3c:v2.0.0:fr:FR100611:native`, document_sha256 `458c831c1d39c39396827f2f62a4fc7d736a48ad9416b70c999c86f25cb01a2a`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100611.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100611.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100611.crossread.json`
7. document_id `e3c:v2.0.0:fr:FR100614:native`, document_sha256 `7d2126866b1c3c01b00d5b9f82d9f3d24363cf9d4813dda5906bcb8840849a74`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100614.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100614.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100614.crossread.json`
8. document_id `e3c:v2.0.0:fr:FR100620:native`, document_sha256 `2550d99cae3e7bcee7868229e5c73816e17ffab1485ec311b74c23297a2a40b0`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100620.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100620.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100620.crossread.json`
9. document_id `e3c:v2.0.0:fr:FR100666:native`, document_sha256 `b2077d46892bbbeeb1d74de6577cf35755cb15243ad014e32e0d6120733ab662`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100666.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100666.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100666.crossread.json`
10. document_id `e3c:v2.0.0:fr:FR100683:native`, document_sha256 `f2d5450c55d9b217c3463a871a1240f2f9df2c9c414dcbe8d0c49ad33d1074f2`, language `fr`, text file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100683.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100683.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-05/FR100683.crossread.json`

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

Write exactly one file, `datasets/e3c-de/proposals/sample60-v3-rev/batch-04.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-proposal-batch/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "sample60-v3-rev",
  "batch_id": "batch-04",
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

Run `sample60-v3-rev`, batch `batch-04`.

1. document_id `e3c:v2.0.0:es:ES100663:native`, document_sha256 `3416e473ae7cbc7efc6205d88f65c448e9d428ebdfae598cb748999f00ad0ac1`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100663.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100663.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100663.crossread.json`
2. document_id `e3c:v2.0.0:es:ES100686:native`, document_sha256 `2b14858085667c4649b7c44034efdf419b8bb9f065300a6c3566799847d14670`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100686.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100686.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100686.crossread.json`
3. document_id `e3c:v2.0.0:es:ES100736:native`, document_sha256 `3e05e83e7e818ceb40c5278c7b5532e07db75f134ddae964d8c374bbe8e7f772`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100736.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100736.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100736.crossread.json`
4. document_id `e3c:v2.0.0:es:ES100778:native`, document_sha256 `c517fa3d294f9f1924d053653ff732924d28325f55edb1807e81c0df990af750`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100778.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100778.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100778.crossread.json`
5. document_id `e3c:v2.0.0:es:ES100803:native`, document_sha256 `1bc8974b6c2751656c62ec33a476c2e61597fe6414231ba409b5c1281634e915`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100803.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100803.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100803.crossread.json`
6. document_id `e3c:v2.0.0:es:ES100848:native`, document_sha256 `6e893b32e84e806bd74978a51cd9c7f9be65cd36dbb2376f672d5999579989f9`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100848.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100848.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100848.crossread.json`
7. document_id `e3c:v2.0.0:es:ES100924:native`, document_sha256 `e5c7457bc7cb6db25708e26316a2ed92c3156b18ab7602ba50f259370a1cfff5`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100924.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100924.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100924.crossread.json`
8. document_id `e3c:v2.0.0:es:ES100946:native`, document_sha256 `9268394edf3ef69be8245b68305d4fc7885a205b83969b1ac16736727929a01c`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100946.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100946.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100946.crossread.json`
9. document_id `e3c:v2.0.0:es:ES100962:native`, document_sha256 `beb018cbf0aceb3c2763d056033c18223c743dca22510f76c42a4c05bdf1650e`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100962.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100962.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100962.crossread.json`
10. document_id `e3c:v2.0.0:es:ES100994:native`, document_sha256 `4762bdae548bea84158d10952bfe85be50bb690e6c0054c12d79b4a97e3a34ae`, language `es`, text file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100994.txt`, first-pass file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100994.first-pass.json`, cross-read file `.artifacts/proposals/sample60-v3-rev/batch-04/ES100994.crossread.json`

# Cross-reading HPO span proposals for E3C reports (cross-read v1)

You check machine-generated HPO annotation proposals for clinical case
reports against the report texts. Your result is machine generated, not
review data, and not gold: a physician reviews everything later in an
annotation editor.

## Read first

1. Read the annotation guideline
   `docs/annotation-guidelines/hpo-span-annotation.md` completely. Rules
   R0-R6 decide what is annotated, which term is chosen, where a span starts
   and ends, and which status is recorded. R7 does not concern you.
2. Then, for each report listed under "This batch" below, read the text and
   the first-pass file next to it. Read every text with Bash, for example
   `cat "<text file>"`; the Read tool truncates long lines.

All paths in this prompt are relative to the repository root, which is your
working directory. Where a tool needs an absolute path, prepend the
repository root.

Use nothing else. Do not open files under `datasets/`, other proposal runs,
E3C annotations, UMLS mappings, or the Phase 0 feasibility files, and do not
search the web. Your judgement must come from the text and the guideline.

## The first-pass file

`<case>.first-pass.json` holds what the first pass proposed for that report
and what the validator made of it:

- `proposals`: the validated proposals, each with `proposal_id`, `hpo_id`,
  `hpo_label`, `assertion`, `experiencer`, `temporality`, `verbalized`,
  `notes`, and `mentions`. A mention has `start`, `end` (character offsets
  into the text) and `phrase` (the verbatim span).
- `rejections`: proposals or mentions the validator rejected, with a reason.
  They are not part of the result; look at them only to see what the first
  pass tried.

## HPO terms

Every term must be an active term of HPO release v2026-06-23 under
*Phenotypic abnormality*. Look terms up with

    uv run phentrieve-benchmark proposals hpo-lookup "<english term>" ["<another term>" ...]

The lookup searches English labels and synonyms of terms under *Phenotypic
abnormality* and matches words, not meaning: try synonyms, the technical and
the lay name, and the finding together with its site. `hpo-lookup HP:0001945`
shows the label of an ID. Never invent an ID.

## What to check

Go through each report sentence by sentence and compare it with the
proposals.

For every proposal:

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
members, other persons). Findings an examination rules out are `absent`.
Report a missed finding only if the lookup gives a fitting term.

Be strict and fair. Report what the guideline decides. Mark a point as
`clear` when the guideline leaves no room, and as `arguable` when a careful
annotator could decide either way. A defensible choice of the first pass
that you would merely have made differently is not an issue.

## Output

Write exactly one file, `.artifacts/proposals/rest92-opus-v3/batch-08/crossread.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-crossread/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "rest92-opus-v3",
  "batch_id": "batch-08",
  "reports": [
    {
      "document_id": "<document_id from the list below>",
      "document_sha256": "<document_sha256 from the list below>",
      "issues": [
        {
          "proposal_id": "p003",
          "kind": "wrong_status",
          "severity": "clear",
          "correction": {"assertion": "uncertain"},
          "note": "The histology is only suggestive."
        }
      ],
      "missed": [
        {
          "hpo_id": "HP:0001945",
          "hpo_label": "Fever",
          "assertion": "absent",
          "experiencer": "patient",
          "temporality": "current",
          "verbalized": true,
          "phrase": "Fieber",
          "context": "kein Fieber bei Aufnahme",
          "severity": "clear",
          "note": "Negated finding without a proposal."
        }
      ]
    }
  ]
}
```

- One entry in `reports` per document below, in the listed order. A report
  with nothing to report has two empty lists.
- `kind` is one of `not_a_finding` (drop the proposal), `wrong_term`,
  `wrong_span`, `wrong_status`, `wrong_verbalized`, `missing_occurrence`,
  and `extra_occurrence` (a marked place that is no occurrence, for example
  a back-reference).
- `correction` holds only what should change: `hpo_id` with `hpo_label`,
  `assertion`, `experiencer`, `temporality`, `verbalized`, or `phrase` with
  `context` for a span to add, replace, or remove. Use `{}` for
  `not_a_finding`.
- `phrase` and `context` are copied verbatim from the text. `context`
  contains the phrase, occurs exactly once in the whole text, and has at
  most 120 characters; it may be the phrase itself when that is unique.
- `note` is one short English sentence. No string may be longer than 300
  characters.
- Change no other file. You may write helper scripts, but only into the
  directory that holds your text files; it is not tracked. Write nothing
  anywhere else, inside or outside the repository.
- When done, reply with one line per report: document ID, proposals checked,
  clear and arguable issues, clear and arguable missed findings. Then list
  every file you read and every command you ran.

## This batch

Run `rest92-opus-v3`, batch `batch-08`.

1. document_id `e3c:v2.0.0:fr:FR100283:native`, document_sha256 `97c854600a3cbf4ba128ae40b9a29ba4312faffa345db71a23f5c836a1e13c44`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100283.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100283.first-pass.json`
2. document_id `e3c:v2.0.0:fr:FR100361:native`, document_sha256 `5be3fb7e531e1676cd90fd1250e3c5359da017d74657de9bb7b3878e75c4ecb5`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100361.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100361.first-pass.json`
3. document_id `e3c:v2.0.0:fr:FR100400:native`, document_sha256 `25cd9e638f40b656d3247e58650db30a8083b6c4fcfdfb2935d0308c9657fd3e`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100400.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100400.first-pass.json`
4. document_id `e3c:v2.0.0:fr:FR100439:native`, document_sha256 `8b41c6f1e8202b3bcf765fded0d432548f20fbf471fde54bb2d8d10e782f38e0`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100439.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100439.first-pass.json`
5. document_id `e3c:v2.0.0:fr:FR100515:native`, document_sha256 `1727395a07572ed0e92b4ea1d20c3d3bfacc660aacf244f59be30961eff4b68b`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100515.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100515.first-pass.json`
6. document_id `e3c:v2.0.0:fr:FR100517:native`, document_sha256 `ebfba2533292daf2efa76166ea692d53fda76d2cf5bb76a39b93bf0398e053ce`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100517.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100517.first-pass.json`
7. document_id `e3c:v2.0.0:fr:FR100589:native`, document_sha256 `64f1d04bb0bcee5994642547f8b3113b654853c9fded533101a6d41866356a58`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100589.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100589.first-pass.json`
8. document_id `e3c:v2.0.0:fr:FR100623:native`, document_sha256 `c16f2f0950c5b58fb682ee5c2f7162cd6fb5862ab95f9b5ff82bbd140510532e`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100623.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100623.first-pass.json`
9. document_id `e3c:v2.0.0:fr:FR100689:native`, document_sha256 `0253734a528eb5ee7d31dd958b8fd7486093183ed29da305645a9b01c8f460e0`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100689.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100689.first-pass.json`
10. document_id `e3c:v2.0.0:fr:FR100697:native`, document_sha256 `be089c188dbf6d24e2d82720d6a128fc93ae23829dc0ad3f6608498534156a69`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100697.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-08/FR100697.first-pass.json`

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

Write exactly one file, `.artifacts/proposals/rest92-opus-v3/batch-04/crossread.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-crossread/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "rest92-opus-v3",
  "batch_id": "batch-04",
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

Run `rest92-opus-v3`, batch `batch-04`.

1. document_id `e3c:v2.0.0:en:EN107424:native`, document_sha256 `f09d5589884a40beb01e2e0a41240c5bea3990efa3c5450cab15c2be7350dcc5`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/EN107424.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/EN107424.first-pass.json`
2. document_id `e3c:v2.0.0:en:EN107559:native`, document_sha256 `031c4fbc35366ccd717be1dd8c9d4b69023ace88895e4ed12f771c676559642e`, language `en`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/EN107559.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/EN107559.first-pass.json`
3. document_id `e3c:v2.0.0:es:ES100050:native`, document_sha256 `3b2e6d10fc3b1579bc597a0b090d6c9132c7360e793029c58bf94af3db4a8784`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100050.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100050.first-pass.json`
4. document_id `e3c:v2.0.0:es:ES100091:native`, document_sha256 `d6aa6913556acdc4ef79a912c8d6bf24b2174eeb2a9fac4f26a4c4b5bbc91af5`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100091.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100091.first-pass.json`
5. document_id `e3c:v2.0.0:es:ES100098:native`, document_sha256 `18f7983e8facea511198238ae12d0f25f53d12f4453e2e97d4680a0d1777ab08`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100098.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100098.first-pass.json`
6. document_id `e3c:v2.0.0:es:ES100112:native`, document_sha256 `a95ae1923b45ceaa42a9a7837a1b70c191c61f5ce7dd9bd60f5ac47e80899aff`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100112.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100112.first-pass.json`
7. document_id `e3c:v2.0.0:es:ES100143:native`, document_sha256 `5d6173041c8aca636f363b2c7c478a33c2888ff8d391a61c2e8d0583eb780e56`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100143.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100143.first-pass.json`
8. document_id `e3c:v2.0.0:es:ES100163:native`, document_sha256 `b84e8c0e49c554556c4e795f14fc63893f8863c2fccc524c990543decc657c22`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100163.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100163.first-pass.json`
9. document_id `e3c:v2.0.0:es:ES100177:native`, document_sha256 `9a0d7c834624d264691efe091f62b5717b5e27ef32541b6d7b7df299007060db`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100177.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100177.first-pass.json`
10. document_id `e3c:v2.0.0:es:ES100273:native`, document_sha256 `aca3ff065065e3d5bd0ec05aaac794a8bc2e71ec02f25c723d2ed6150d3de120`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100273.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-04/ES100273.first-pass.json`

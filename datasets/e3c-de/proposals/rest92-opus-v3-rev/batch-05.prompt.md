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

Write exactly one file, `.artifacts/proposals/rest92-opus-v3/batch-05/crossread.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-crossread/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "rest92-opus-v3",
  "batch_id": "batch-05",
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

Run `rest92-opus-v3`, batch `batch-05`.

1. document_id `e3c:v2.0.0:es:ES100284:native`, document_sha256 `574bc57051fae98e0d3c6efc9871e2d07ea0b83c762a30e7c1a0d91d5d75ca43`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100284.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100284.first-pass.json`
2. document_id `e3c:v2.0.0:es:ES100310:native`, document_sha256 `ff6256fa05c048f58e24298c0829bbce71c04efaa672e975cd7f83f860cbc888`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100310.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100310.first-pass.json`
3. document_id `e3c:v2.0.0:es:ES100410:native`, document_sha256 `937b13afc92e3ea9d5eff6b31937be91c262546213abc369ffa92fcff0ce8f11`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100410.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100410.first-pass.json`
4. document_id `e3c:v2.0.0:es:ES100417:native`, document_sha256 `6b45f918cd5a613cce1b7243591bd266827008b5db83a7cc810d3b064ad09728`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100417.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100417.first-pass.json`
5. document_id `e3c:v2.0.0:es:ES100423:native`, document_sha256 `72e55a60201cfeef9c40d8ec0988c97d297c6177c74f75d309830c06b6dfd903`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100423.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100423.first-pass.json`
6. document_id `e3c:v2.0.0:es:ES100519:native`, document_sha256 `ddf1dc262f69fbd9c1d48870bb8eee8bf4ac75dc92e211194d6dd77aedd945a5`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100519.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100519.first-pass.json`
7. document_id `e3c:v2.0.0:es:ES100521:native`, document_sha256 `00d466a3fd6eced2f7bbfc59da85e918185665c54e1572b50b9b65a45ab1e55d`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100521.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100521.first-pass.json`
8. document_id `e3c:v2.0.0:es:ES100578:native`, document_sha256 `3cf1e06ade256f9b4f5cc44e7e60821dca89ca1a4e980f01428c8fd42b117e5e`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100578.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100578.first-pass.json`
9. document_id `e3c:v2.0.0:es:ES100605:native`, document_sha256 `bfc522aa4e3aa1eb326825ddc1a6ca61e4451601fd3c2b574e4c917dab1fa744`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100605.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100605.first-pass.json`
10. document_id `e3c:v2.0.0:es:ES100634:native`, document_sha256 `0ea5376e8e29f020e39d34b59e33239b930cf95cdc2e59ecda4be70edfb435a7`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100634.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-05/ES100634.first-pass.json`

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

Write exactly one file, `.artifacts/proposals/rest92-opus-v3/batch-07/crossread.json`, containing this JSON and nothing
else:

```json
{
  "schema_version": "e3c-hpo-crossread/v1",
  "provenance": "machine generated, not review data, not gold",
  "run_id": "rest92-opus-v3",
  "batch_id": "batch-07",
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

Run `rest92-opus-v3`, batch `batch-07`.

1. document_id `e3c:v2.0.0:es:ES100832:native`, document_sha256 `afc6facc805df8816fba5a122829d118b0d08eed9d04939f710f0c0c820f0a4b`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/ES100832.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/ES100832.first-pass.json`
2. document_id `e3c:v2.0.0:es:ES100840:native`, document_sha256 `34b778a7f608871085f108bbaa34a6754677760e005c27d0c0bb7294cc71f829`, language `es`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/ES100840.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/ES100840.first-pass.json`
3. document_id `e3c:v2.0.0:fr:FR100003:native`, document_sha256 `b7809e009ad1d240ef4c253d7cabf553ecced9514095a620060e2cc86076ab67`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100003.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100003.first-pass.json`
4. document_id `e3c:v2.0.0:fr:FR100078:native`, document_sha256 `b718a60c0432a01a174d59d57787d672d8e8426da88ed41f8effbc0fddefda05`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100078.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100078.first-pass.json`
5. document_id `e3c:v2.0.0:fr:FR100092:native`, document_sha256 `1e392e8962a62b82fd2da4c0a780cc4c8a1c809dcca0ff81aab419ab1190d30a`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100092.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100092.first-pass.json`
6. document_id `e3c:v2.0.0:fr:FR100130:native`, document_sha256 `ecb61fb69b34c156c8c21a48ffbdc64567073254017d2f67ac3d3abccbedcea0`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100130.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100130.first-pass.json`
7. document_id `e3c:v2.0.0:fr:FR100168:native`, document_sha256 `4c2519221313901a902c70413bdda15d2debd04e016958cd26aeb1f87879400b`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100168.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100168.first-pass.json`
8. document_id `e3c:v2.0.0:fr:FR100275:native`, document_sha256 `bd871f909c965a43fcc4be35c24ea501f067106b7273f3094e186b5a7487989b`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100275.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100275.first-pass.json`
9. document_id `e3c:v2.0.0:fr:FR100276:native`, document_sha256 `5bdb5663e7848d7291d6a113757c49f3933f0e5609162fc7a517652d15a79b29`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100276.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100276.first-pass.json`
10. document_id `e3c:v2.0.0:fr:FR100282:native`, document_sha256 `b163ee3e3186fc87fa6e0d96439171603a2aa9cc8e75f4bfa8cb06ca6605b276`, language `fr`, text file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100282.txt`, first-pass file `.artifacts/proposals/rest92-opus-v3/batch-07/FR100282.first-pass.json`

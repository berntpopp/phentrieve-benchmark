# HPO span proposals

> **Machine generated, not review data, not gold.** Every file below this
> directory is LLM output or its deterministic validation. A physician
> reviews each proposal in the annotation editor before anything enters gold.

Design: [`docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md`](../../../docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md) §6.
Rules applied by the subagents: [`docs/annotation-guidelines/hpo-span-annotation.md`](../../../docs/annotation-guidelines/hpo-span-annotation.md) (R0-R6).
Prompt template: [`configs/prompts/hpo-span-proposal-v1.md`](../../../configs/prompts/hpo-span-proposal-v1.md).

## Run layout

Each run lives in `<run_id>/`:

| File | Content |
|---|---|
| `prompt.md` | the committed prompt template (SHA-256 in `run.json`) |
| `run.json` | model ID, run date, corpus manifest hash, HPO release, guideline path, commit, and blob hash, batches with document IDs and hashes, German reports left out as pending |
| `batch-NN.prompt.md` | the exact prompt given to the subagent of that batch (paths, IDs, hashes; no report text) |
| `batch-NN.json` | the unchanged subagent output |
| `validation.json` | resolved offsets, merges, rejections with reasons, label warnings, summary; canonical JSON, so its file hash is its canonical hash (recorded in the table below) |

Files are stored byte-exact (`-text` in `.gitattributes`). Batch outputs
hold only short phrases, context excerpts, and notes: any string longer than
300 characters makes validation fail for that batch, the output is discarded
and the batch dispatched again, so such a file is never committed. This fits
the non-commercial scientific-use assumption recorded in
[`../license-evidence.yaml`](../license-evidence.yaml) and
[`../LICENSES.md`](../LICENSES.md). Full texts for the subagents are written
only to `.artifacts/proposals/<run_id>/` (Git-ignored).

## Procedure

Run every step in the main checkout, not in a Git worktree: the corpus, the
object store, and the HPO source lock live in its `.artifacts/`.

1. Build the corpus (refresh verified stages first if the code changed):

   ```bash
   uv run phentrieve-benchmark acquire e3c
   uv run phentrieve-benchmark normalize e3c
   uv run phentrieve-benchmark build-corpus e3c [--review-import SHA ...]
   ```

   Note the printed `corpus_sha256`.

2. Prepare a run (guideline and prompt template must be committed):

   ```bash
   uv run phentrieve-benchmark proposals prepare-run <run_id> \
     --corpus <corpus_sha256> --model-id <model id> \
     [--pilot | --language de --language en ...] [--batch-size 10]
   ```

3. Dispatch one Claude Code subagent per batch (Agent tool,
   `subagent_type: general-purpose`, `model` matching `--model-id`). The
   prompt is the content of `datasets/e3c-de/proposals/<run_id>/batch-NN.prompt.md`,
   passed verbatim. Run up to five batches in parallel. Each subagent ends
   its reply with the files it read and the commands it ran: reject the
   batch (delete its output, dispatch again) if it opened anything under
   `datasets/` other than its own output, for example E3C annotations,
   mappings, or `annotation-feasibility/`.

4. Validate:

   ```bash
   uv run phentrieve-benchmark proposals validate <run_id>
   ```

   `batch_error=...` (exit code 1) lists every batch output that cannot be
   validated at all: invalid JSON, a string over 300 characters, wrong
   envelope, missing or unknown report, or hash mismatch. Delete those
   `batch-NN.json` files and dispatch the same prompts again; failed attempts
   are not kept, but count them for the table below. Proposal- and
   mention-level problems never stop validation; they are listed in
   `validation.json` with a reason.

5. Add the run to the table below and commit the run directory.

Reproducibility: subagent runs have no pinned temperature or seed and cannot
be regenerated identically. Validation, editor packages, and import are
deterministic functions of the archived batch outputs.

## German group

German reports enter the corpus only with an accepted translation review.
Until then `prepare-run --language de` stops with "N German reports pending
translation review". Once reviews are imported, rebuild the corpus with
`--review-import` and prepare a separate run, for example `de-v1`, with
`--language de`. Such a run covers every German report reviewed by then. If
only part of the group is reviewed, a later run on the rebuilt corpus covers
all German reports again, including those of the earlier run.

## Runs

| Run | Model | Documents | Re-dispatched batches | `validation_sha256` | Status |
|---|---|---:|---:|---|---|
| `pilot-v1` | `claude-sonnet-5-5` | 9 | 0 | `b4d7bb7e621cd46c90198c89a80e6e69ca6a50549086caad1ebce41b9f130c82` | pilot; see below |

## Pilot pilot-v1

Run date 2026-10-06. Corpus `f1c1f12d32d7594ce6f55a0d915bbe74ac891b27d86127c9076cb31d70e47c42`,
prompt v1, 9 reports (3 EN, 3 FR, 3 ES; one per language and length stratum)
in one batch.

### Dispatch

- One dispatch, no re-dispatch. Validation passed on the first attempt.
- Files the subagent reported as read: the guideline and its nine text files.
  No other file in the repository changed.
- Deviations from the prompt: the subagent wrote a helper script outside the
  repository (`C:\tmp\gen.py`), ran it to check every phrase and context
  against the texts and to write the output, and deleted it afterwards. It
  also ran `proposals validate --help`. The prompt says "Write no other file".
  The zero rejection rate below was reached with that self-check.

### Validation

| Count | Value |
|---|---:|
| Proposals received | 94 |
| Proposals rejected | 0 (0 %) |
| Validated proposals | 94 |
| Mentions evaluated | 101 |
| Mentions rejected | 0 (0 %) |
| Label warnings | 0 |

Rejections by reason: none.

Proposals per report: EN100265 26, EN100415 5, EN107423 1, ES100320 30,
ES100447 13, ES100791 1, FR100161 6, FR100658 11, FR100971 1.

Status of the 94 proposals: 74 present, 16 absent, 2 uncertain (all patient,
current); 1 present/other/current; 1 present/patient/historical. 8 proposals
are not verbalized (R6). 5 of 101 spans are longer than 50 characters.

Terms outside *Phenotypic abnormality* (HP:0000118): 1 of 94, *Stillbirth*
(HP:0003826) in EN100265.

Excerpt volume: the contexts of a report add up to 11-35 % of its text
length (highest: ES100320, 1,349 of 3,851 characters); the longest single
context has 93 characters.

Findings the subagent reported as dropped because the lookup returned no
term: palmar erythema and tenderness (EN100265), a lower-back lump
(EN107423), intervertebral disc herniation (ES100791), vulvar condylomas,
ventricular septal rupture (FR100971), germ cell tumor, metastasis.

### Spot check

Three reports, one per language, compared with the text against R0-R6 by the
main session (not a physician review).

| Report | Proposals | Obvious misses | Wrong terms | Wrong spans | Wrong status | R6 misuse |
|---|---:|---:|---:|---:|---:|---:|
| EN100415 | 5 | 0 | 0 | 0 | 0 | 0 |
| ES100447 | 13 | 4 | 0 | 0 | 0 | 0 |
| FR100161 | 6 | 2 | 0 | 0 | 0 | 0 |

- EN100415: all five proposals fit the text. *Neuroendocrine neoplasm* was
  chosen for "neuroendocrine carcinoma of the pancreas" although the more
  specific *Pancreatic endocrine tumor* (HP:0030405) exists (R1). One further
  occurrence of the pancreatic tumour ("a large tumour ... in the body and
  tail of pancreas") is not marked (R5).
- ES100447: missed are the reduced prothrombin activity (*Prolonged
  prothrombin time*, HP:0008151), the reduced tear break-up time (*Brief tear
  break-up time*, HP:6000069), the punctate corneal and conjunctival
  epithelial staining, and the whitish mottling of the mid-peripheral fundus.
  "obesidad mórbida" is proposed as *Obesity*; *Class III obesity*
  (HP:0025501) exists, but the lookup finds nothing for "morbid obesity". The
  one R6 annotation (retinol 0,07 mg/l) is used correctly.
- FR100161: missed are the negated adrenal hyperfunction ("pas de signes
  cliniques en faveur d'un syndrome d'hyperfonctionnement cortico ou
  médullosurrénalien") and, arguably, fibrosis stage F4. The second
  occurrence of "cytolyse" is not marked (R5). *Ganglioneuroma* is recorded
  as present although the text says "un aspect en faveur d'un
  ganglioneurome"; `uncertain` is arguable.

Outside the three reports: in ES100320, *Pneumonia* is recorded as uncertain
although "presuntivamente" qualifies the pathogen, not the pneumonia.

### Verdict

Format and location are reliable: every proposal and mention validated, and
no label deviated from the pinned release. The 24 spot-checked proposals
contain no wrong term, span, or status; two are less specific than HPO
allows. Completeness is the weak point: 6 findings with an HPO term are
missing next to those 24 proposals, mostly specialised examination and
laboratory findings, and further occurrences of an annotated finding are not
always marked. Sonnet 5.5 with prompt v1 is usable as a proposal source for
physician review if reviewers are told to expect missing findings; whether
that is good enough for the full run is the user's decision.

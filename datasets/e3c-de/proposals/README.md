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

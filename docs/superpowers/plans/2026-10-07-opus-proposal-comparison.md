# Opus as Proposer: Comparison Run (handoff)

**Goal:** Measure whether `claude-opus-5-5` as the proposing model already
finds what the Opus cross-read had to add to the Sonnet proposals. The result
decides between "Sonnet proposes, Opus cross-reads" and "Opus proposes, with
a lighter cross-read".

**Branch:** `agent/e3c-phase2-proposals`, main checkout
`C:\Users\jan-p\Development\phentrieve-benchmark-local` (not a worktree: the
corpus, the object store, and the HPO source lock live in its `.artifacts/`).
Nothing is pushed.

**Read first:** `datasets/e3c-de/proposals/README.md`, sections "Procedure",
"Which results count", and "Sample run sample60-v3 with agentic
cross-reading". They hold the reference numbers.

## Background

- `sample60-v3`: 60 reports, proposals by Sonnet 5.5 with prompt v3, all
  validated (530 proposals), cross-read by Opus 5.5. The cross-read outputs
  are in `datasets/e3c-de/proposal-crossreads/sample60-v3/`.
- The cross-read found 48 clear missed findings, 15 clear term corrections
  (all "a more specific term exists"), and 10 clear missing occurrences.
  About half of the missed findings were findings the Sonnet subagent had
  seen and dropped because its lookup queries found no term.
- Decided by the user on 2026-10-07: proposals count as results only after
  they were cross-read against the text.

## Steps

Run every command from the repository root with Git Bash.

- [ ] **Step 1: Check the state.** `git status --short` is empty,
  `uv run pytest -q` passes, and
  `.artifacts/proposals/_tools/compare_runs.py` exists. The tools directory
  is git-ignored and local. If it is missing, rewrite the comparison from
  the description in Step 5.

- [ ] **Step 2: Prepare the run** for the 30 reports of batches 01, 03, and
  05 of `sample60-v3` (10 EN, 10 ES, 10 FR; they hold 34 of the 48 clear
  missed findings):

  ```bash
  CORPUS=f1c1f12d32d7594ce6f55a0d915bbe74ac891b27d86127c9076cb31d70e47c42
  CASES="EN100114 EN100129 EN100247 EN100310 EN100345 EN100432 EN100453 EN100490 EN100508 EN100543 ES100030 ES100042 ES100051 ES100178 ES100278 ES100363 ES100420 ES100445 ES100552 ES100594 FR100227 FR100296 FR100344 FR100597 FR100603 FR100611 FR100614 FR100620 FR100666 FR100683"
  uv run phentrieve-benchmark proposals prepare-run sample30-opus \
    --corpus $CORPUS --model-id claude-opus-5-5 \
    $(for c in $CASES; do printf -- "--case %s " $c; done)
  ```

  Expected: `run_id=sample30-opus documents=30 batches=3 pending_review=0`.
  If the corpus object is missing, rebuild it first with `acquire e3c`,
  `normalize e3c`, and `build-corpus e3c` and use the printed hash.

- [ ] **Step 3: Dispatch three subagents in parallel** (Agent tool,
  `subagent_type: general-purpose`, `model: opus`,
  description `HPO proposals sample30-opus batch-NN`) with this prompt, one
  per batch:

  > Your complete task is described in the file
  > `datasets/e3c-de/proposals/sample30-opus/batch-NN.prompt.md` (path
  > relative to the repository root
  > `C:\Users\jan-p\Development\phentrieve-benchmark-local`, which is your
  > working directory). Read that file completely with Bash (`cat`) and carry
  > it out exactly as written. It is the only file under `datasets/` that you
  > may read.

  Note the dispatch time. From each completion notification, record
  `subagent_tokens`, `tool_uses`, and `duration_ms`.

- [ ] **Step 4: Check and validate.**
  `git status --short --untracked-files=all` shows only the new run
  directory with `prompt.md`, `run.json`, three `batch-NN.prompt.md`, and
  three `batch-NN.json`. Then
  `uv run phentrieve-benchmark proposals validate sample30-opus`. On
  `batch_error=...`, delete that batch file, dispatch it again, and count
  the re-dispatch.

- [ ] **Step 5: Compare with the reference.**

  ```bash
  PYTHONUTF8=1 uv run python .artifacts/proposals/_tools/compare_runs.py sample60-v3 sample30-opus
  ```

  It reports, for the 30 common reports: proposals in both runs and in only
  one of them (same HPO ID and status); how many of the cross-read's missed
  findings the candidate has (same HPO ID and assertion), and how many it
  covers with another term on the same text; how many term corrections it
  already uses; how many missing occurrences it marks. The Sonnet run scores
  zero on all three by construction (checked with
  `compare_runs.py sample60-v3 sample60-v3`).

  Read the numbers with care: proposals that only Opus has are either
  further correct findings or false positives. The comparison cannot tell
  which; only a cross-read can. Look at ten of them by hand against the text
  and say what they are.

- [ ] **Step 6: Record and commit.** Add the run to the "Runs" table of the
  runbook and a section "Comparison run sample30-opus" with: tokens and time
  per batch next to the Sonnet figures of the same batches (107,187 /
  104,133 / 101,090 tokens; 6.0 / 6.3 / 5.8 minutes), validation counts, the
  comparison numbers, and the hand check. Write facts only, in English. Then:

  ```bash
  uv run pytest -q && uv run ruff check . && uv run python scripts/check_repository_safety.py
  git add datasets/e3c-de/proposals
  git commit -m "data: add proposal comparison run sample30-opus"
  ```

  No AI co-authorship trailers. Do not push.

- [ ] **Step 7: Report to the user and stop.** Give the share of clear
  missed findings, term corrections, and occurrences that Opus had on its
  own, the token and time cost next to Sonnet, and a recommendation between:
  Sonnet proposes and Opus cross-reads (then build the mechanical
  application of the cross-read corrections); Opus proposes with a lighter
  cross-read; Opus proposes and Opus cross-reads. Do not start further runs
  without the user's decision.

## Tools (git-ignored, local)

`.artifacts/proposals/_tools/`:

- `compare_runs.py <reference_run> <candidate_run>`: Step 5.
- `crossread_prepare.py <run_id>`: writes `<case>.first-pass.json` and
  `crossread.prompt.md` into each batch's text directory, from
  `configs/prompts/hpo-span-crossread-v1.md`.
- `crossread_report.py <run_id> [--detail]`: aggregates the cross-read
  outputs under `.artifacts/proposals/<run_id>/<batch>/crossread.json` and
  checks them against text and ontology.

## Open points not part of this run

- How the cross-read corrections are applied to the proposals (none applied
  so far).
- A guideline line on span edges: side, size, and intensity words at the
  edge of a span (53 of the 80 clear cross-read issues).
- The 18 pilot reports that were only validated, not cross-read.
- *Preeclampsia* is outside *Phenotypic abnormality* in the pinned release;
  the pinned release has tuberculosis terms although R0 names "Tuberkulose"
  as a diagnosis without a matching term.
- An independent review of the late code changes (`--case`, lookup and
  validator restriction, CLI error handling).

# E3C Layer 1 preparation

This target prepares the English, French, and Spanish Layer 1 reports from
E3C v2.0.0. It does not translate, map concepts to HPO, invoke a provider,
perform clinical review, or create a release.

The immutable source is `hltfbk/E3C-Corpus` commit
`f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc`. Its ZIP is 233,811,002 bytes
with SHA-256
`04e06d0a153a8ea845b647459ab51eb2fed5007bdf450d441c1469f8719a2206`.
The recipe selects only Layer 1 XML: 84 English, 81 French, and 81 Spanish
documents. These are public upstream data. The complete source XML snapshot
and canonical generated artifacts remain under the Git-ignored `.artifacts/`
directory. An explicit snapshot containing the canonical source texts and the
unreviewed German translations (`tllm-full` variant) of all 246 reports is
tracked under `translations/` for non-commercial scientific review.

For the full corpus, the text-free inventory and the annotation group manifest
(`selections/e3c-annotation-groups-v1.json`) are also tracked. Upstream
licensing and the explicit translation-snapshot redistribution decision are
recorded in `license-evidence.yaml` and `LICENSES.md`.

Run `uv run phentrieve-benchmark prepare e3c`; use
`uv run phentrieve-benchmark smoke live-download` only for an explicit live
verification. XMI offsets are interpreted as UTF-16 code-unit offsets and
mapped to NFC-normalized canonical text. Terminal formatting newlines are
removed according to the adapter contract.

All 246 reports have been translated into German with the Google Translation
LLM (`general/translation-llm`, variant `tllm-full`, pinned by
`translation-llm-full.yaml`). The earlier 30-case NMT/TLLM feasibility
snapshot was removed from the tracked files on 2026-10-06 and remains in Git
history. Operation, costing, artifact separation, and review boundaries are
documented in `translations/README.md`. Translation runs remain outside
regular offline CI and require explicit confirmation after the cost preview.

UMLS-to-HPO mapping is an independent, local stage and does not require a
translation or Google credentials. Run
`uv run phentrieve-benchmark map-hpo e3c`; exact results and classification
counts are documented under `mappings/`.

All 246 reports are split into four annotation groups (German, English,
French, Spanish) by `uv run phentrieve-benchmark select e3c-groups`; the
tracked, text-free result is `selections/e3c-annotation-groups-v1.json`.
`uv run phentrieve-benchmark build-corpus e3c [--review-import SHA ...]`
builds the annotation corpus: original-language reports as native
documents, German reports only from accepted translation reviews. German
reports without one are listed as pending. Review imports are applied in the
given order; for each report the last decision wins. The translation review
for the German group is exported with
`uv run phentrieve-benchmark review-workbook export-e3c <destination> --variant tllm-full --groups datasets/e3c-de/selections/e3c-annotation-groups-v1.json`.

## Analysis reading path

The E3C-DE analyses build on each other. Read them in this order:

1. [`mappings/README.md`](mappings/README.md) - mechanical UMLS-to-HPO
   mapping of all 246 reports: classification counts, OxO2 and
   Monarch/MedGen probes, and the granularity limits of the source
   annotations.
2. [`mappings/audit/README.md`](mappings/audit/README.md) - per-annotation
   semantic audit of the 458 cohort annotations by two independent passes:
   consensus set, audit classes, and typical problems.
3. [`annotation-feasibility/README.md`](annotation-feasibility/README.md) -
   Phase 0 feasibility probe: do the consensus terms survive the German
   translation (Part A) and triage of the most frequent unresolved CUIs
   (Part B). Kept as comparison data; superseded as a working plan.
4. [`translations/README.md`](translations/README.md) - translation
   operation, costs, artifact separation, and the automatic-check status
   model.
5. [`../../docs/project-checklist.md`](../../docs/project-checklist.md) -
   current status and priorities across the whole project.
6. [`../../docs/annotation-guidelines/hpo-span-annotation.md`](../../docs/annotation-guidelines/hpo-span-annotation.md) -
   span annotation rules for all four annotation groups.
7. [`proposals/README.md`](proposals/README.md) - LLM proposal runs
   (machine generated, not gold), their validation, and the runbook.

# Phase 0 Feasibility Report: E3C-DE Annotation Feasibility

> **Machine-generated diagnosis — not review data, not a gold standard.**
> Created on 2026-08-24 by Claude (Opus 5, main session) with seven
> parallel subagents. All HPO proposals were machine-validated against the
> pinned `hp.obo` `v2026-06-23`
> (`a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b`).
> Nothing was written into canonical artifacts.

## Question

Can a reliable document-level HPO gold standard emerge from the unreviewed
German TLLM translations of the 30-case cohort — and how large is the
concept gap of the E3C source annotations? This report informs the decision
whether to invest medical review time.

## Inputs

- German translations: variant `tllm` (manifest `2dd428da…`), view
  `.artifacts/views/e3c-de-tllm/`; full-corpus source texts from
  `datasets/e3c-de/translations/e3c-de-full-246-google-tllm-v1/`
  (manifest `759f0026…`).
- Part A test set: the 210 consensus annotations of the two-agent audit of
  2026-07-29 (`datasets/e3c-de/mappings/audit/`), 176 of which are positive
  index-patient findings.
- Part B test set: 200 missing CUIs with >= 2 occurrences not covered by
  the cohort audit (595 of the 1,925 missing mentions).

| File | SHA-256 |
| --- | --- |
| `input/teil-a-faelle.json` | `b2d00d0c1b9cbe8caf126da59d1f3cc074a130b87faba28fa883cc23c1ed5d2c` |
| `input/triage-cuis.json` | `3a5908d887c5dac5ec7e3195b63839c409ef6480d754fdec41fc07de784b698c` |
| `teil-a-en.json` | `edaee2e4093e5a9dca19f9f4c9972e38f3bea0fef56035b95c1f0d9cc9000123` |
| `teil-a-es.json` | `a514a66d7253f779e86e69024bd6cb1c1ed9c20f47691e9c7f135216de92b77c` |
| `teil-a-fr.json` | `95126fa67685e12804970ec41b3e4ec9b6232f48b87ef8e57b13b74ceeb94a96` |
| `teil-b-validiert.json` | `995a4f6e87a7e22ea1287a2d35be1f1c6d82237ca8d342aa219ce3c5a5c0ad06` |

## Part A — Do the consensus terms survive translation?

**Yes, almost completely: 208 of 210 hold (99.0 %).**

| Language | Terms | holds | does not hold | uncertain |
| --- | ---: | ---: | ---: | ---: |
| EN | 69 | 67 | 1 | 1 |
| ES | 75 | 75 | 0 | 0 |
| FR | 66 | 66 | 0 | 0 |

- Assertion status (negation, uncertainty, historical, non-index subject)
  was preserved in **all 210 cases**.
- Both problem cases sit in EN100593: "blurred vision" was generalized to
  "Sehstoerungen" (loss of granularity); "loss of conscious" was weakened
  to "Bewusstseinstruebung".
- Quote check: 209 of 210 evidence quotes were verified verbatim against
  the German texts (one was abbreviated by the agent).
- Side finding: for ES100840/annotation 9762 ("mioma uterino") the audit
  category `negated_or_absent` looks questionable; both source and
  translation state it as a positive history item. Flag for the annotation
  review.

## Part A — Concept gap in the gold core (gap analysis)

The agents reported **100 obvious index-patient phenotypes not covered** by
the consensus terms (avg. 3.3 per case; EN 45, FR 33, ES 22). 81 of the 100
suggestions resolve mechanically against the pinned HPO. Frequent types:
laboratory findings (CRP, leukocytosis), neurological signs (Babinski,
hyperreflexia), and missing lead findings (e.g. jaundice, preeclampsia).

A gold standard built only from the 176 positive consensus terms would
therefore be **structurally incomplete (roughly one third missing)** —
critical for a retrieval benchmark, because correct retrievals would be
scored as errors. The gap is, however, small enough to close per case
during medical review.

## Part B — Triage of the 200 most frequent unresolved CUIs

| Category | CUIs | Mentions |
| --- | ---: | ---: |
| not a phenotype (procedure, diagnosis, anatomy, …) | 83 | 240 |
| phenotype without xref (rescuable) | 64 | 170 |
| too generic for a 1:1 mapping | 48 | 169 |
| unclear | 5 | 16 |

- Of the 64 rescue proposals, **55 pass machine validation against the
  pinned HPO** (26 with a correct ID, 29 via an unambiguous label or
  synonym); 9 labels were not found; **0 fabricated or obsolete IDs**.
- Extrapolated: roughly 40 % of the examined missing mentions are
  legitimately outside HPO gold ("not a phenotype"), roughly 29 % are
  rescuable with modest review effort, and roughly 28 % remain without a
  safe 1:1 mapping.

## Recommendation

1. **Translation is not the bottleneck for the document-level goal.** The
   medical translation review can stay lean and risk-based (starting
   points: EN100593 and the 61 `units_added` cases of the full corpus).
2. **The bottleneck is concept coverage, not language.** For the 30-case
   cohort a document-level gold standard is achievable as: 176 positive
   consensus terms + gaps closed under medical review (~100 candidates).
   The 55 validated rescue proposals concern CUIs outside the cohort audit
   and become relevant when scaling to the full 246-report corpus.
3. **Recommendation: start Phase 1** — medical review on the 30-case
   cohort using these building blocks as the template. Report the residual
   gap (too-generic and rare CUIs) openly instead of papering over it.

## Notes on preservation

- Agent rationales inside the JSON files are written in German; this
  report is the English summary.
- `input/hpo-lookup.json` (label/ID lookup derived from the pinned
  `hp.obo`) and the four raw `teil-b-batch-*.json` files (merged into
  `teil-b-validiert.json` without loss) are not preserved; both are
  reproducible from preserved inputs.

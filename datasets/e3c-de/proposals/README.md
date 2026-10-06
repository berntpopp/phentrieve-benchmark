# HPO span proposals

> **Machine generated, not review data, not gold.** Every file below this
> directory is LLM output or its deterministic validation. A physician
> reviews each proposal in the annotation editor before anything enters gold.

Design: [`docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md`](../../../docs/superpowers/specs/2026-10-06-e3c-multilingual-span-annotation-design.md) §6.
Rules applied by the subagents: [`docs/annotation-guidelines/hpo-span-annotation.md`](../../../docs/annotation-guidelines/hpo-span-annotation.md) (R0-R6).
Prompt template: [`configs/prompts/hpo-span-proposal-v3.md`](../../../configs/prompts/hpo-span-proposal-v3.md).
Earlier versions: [v1](../../../configs/prompts/hpo-span-proposal-v1.md)
(`pilot-v1`), [v2](../../../configs/prompts/hpo-span-proposal-v2.md)
(`pilot-v2`, `pilot-v2-extra`). Each run keeps its own copy as `prompt.md`.

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
     [--pilot | --language de --language en ... | --case EN100001 ...] \
     [--batch-size 10]
   ```

   `--pilot` picks one report per original language and length stratum.
   `--case` names source case IDs and can be repeated.

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
| `pilot-v1` | `claude-sonnet-5-5` | 9 | 0 | `b4d7bb7e621cd46c90198c89a80e6e69ca6a50549086caad1ebce41b9f130c82` | pilot, prompt v1; see below |
| `pilot-v2` | `claude-sonnet-5-5` | 9 | 0 | `2236103656da47cd7ff8467d5a5bf937732c9ae4e6287ae5671e9f22baf2e837` | pilot, prompt v2, same reports as `pilot-v1`; see below |
| `pilot-v2-extra` | `claude-sonnet-5-5` | 9 | 0 | `ff32831802115b47294f8098858bd2398e6141625592f9b7255bc32f3d2464a3` | pilot, prompt v2, nine further reports; see below |
| `pilot-v3` | `claude-sonnet-5-5` | 9 | 0 | `ae24e1d706c1c12cf3ad1ae32a8eda8350cd10c57915169bb58fe43d635f4dd0` | pilot, prompt v3 and restricted lookup, nine further reports; see below |

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

Decision of 2026-10-06: revise the prompt and repeat the pilot.

## Pilots pilot-v2 and pilot-v2-extra

Run date 2026-10-06, same corpus, prompt v2. Prompt v2 adds to v1: a
completeness pass over all kinds of findings, marking reworded further
occurrences, alternative lookup wordings, phenotypic terms only, `uncertain`
only for a hedge on the finding itself, and an inline self-check instead of
extra files.

- `pilot-v2`: the nine reports of `pilot-v1`.
- `pilot-v2-extra`: nine further reports, the second report per original
  language and length stratum in the pilot's seeded order (EN100068,
  EN106156, EN108139, ES100561, ES100633, ES100937, FR100579, FR100629,
  FR100663), selected with `--case`.

### Dispatch

- One dispatch per run, no re-dispatch. Both validated on the first attempt.
- Files reported as read: the guideline and the run's own nine text files.
  No other file in the repository changed.
- Deviation from the prompt in both runs: the inline self-check suggested by
  prompt v2 failed with a shell parse error, and each subagent then wrote a
  generator script to the user's temporary directory outside the repository.
  One deleted it; the other was removed by the main session.

### Validation

| Count | `pilot-v1` | `pilot-v2` | `pilot-v2-extra` |
|---|---:|---:|---:|
| Proposals received | 94 | 104 | 60 |
| Proposals rejected | 0 | 0 | 0 |
| Mentions evaluated | 101 | 113 | 69 |
| Mentions rejected | 0 | 0 | 0 |
| Label warnings | 0 | 0 | 0 |
| Not verbalized (R6) | 8 | 10 | 4 |
| Terms outside HP:0000118 | 1 | 1 | 3 |
| Spans longer than 50 characters | 5 | 5 | 1 |
| Context characters / text length, per report | 11-35 % | 10-38 % | 3-32 % |

Proposals per report, `pilot-v2`: EN100265 29, EN100415 5, EN107423 1,
ES100320 33, ES100447 16, ES100791 1, FR100161 6, FR100658 11, FR100971 2.
`pilot-v2-extra`: EN100068 11, EN106156 2, EN108139 12, ES100561 3,
ES100633 4, ES100937 11, FR100579 3, FR100629 11, FR100663 3.

Terms outside *Phenotypic abnormality*: *Stillbirth* again in `pilot-v2`
(EN100265); in `pilot-v2-extra` *Ectopic pregnancy* twice (EN100068, under
*Past medical history*) and *Chest pain triggered by palpation* (FR100629,
under *Clinical modifier*). The lookup output does not show the branch of a
term.

### pilot-v1 against pilot-v2 on the same reports

84 proposals (HPO ID and status) are identical in both runs; 10 occur only
in `pilot-v1`, 20 only in `pilot-v2`. The differences mix prompt effects
with run-to-run variation.

| Report | v1 proposals | v2 proposals | v1 obvious misses | still missing in v2 |
|---|---:|---:|---:|---:|
| EN100415 | 5 | 5 | 0 | 0 |
| ES100447 | 13 | 16 | 4 | 1 |
| FR100161 | 6 | 6 | 2 | 2 |

- EN100415: unchanged apart from the span "neuroendocrine carcinoma of the
  pancreas". The term is still *Neuroendocrine neoplasm*, and the second
  description of the pancreatic tumour is still not marked.
- ES100447: v2 adds the punctate epithelial staining (*Punctate keratitis*),
  the fundus mottling (*Retinal flecks*), and the reduced prothrombin
  activity, the latter as *Abnormality of prothrombin* although *Prolonged
  prothrombin time* (HP:0008151) carries the synonym "Reduced prothrombin
  activity". "obesidad mórbida" is now *Class III obesity*. The reduced tear
  break-up time is still missing; the subagent reported no lookup match.
- FR100161: the negated adrenal hyperfunction and fibrosis stage F4 are
  still not proposed, and the second "cytolyse" is still not marked.
  *Ganglioneuroma* is now `uncertain`. Two spans now include a word or value
  that does not determine the term ("légère cytolyse hépatique",
  "hyperglycémie à 8,54 mmol/l"; R2).

Elsewhere: in ES100320, *Pneumonia* is now `present`, the vulvar condylomas
are proposed (*Genital warts*), and the mediastinal mass has the more
specific *Anterior mediastinal mass*; but the thrombocytosis proposed in v1
(682.000 platelets/µL) is absent in v2, and "tos seca" went from
*Nonproductive cough* to the less specific *Cough*. In EN100265, a bare
"Pain" is attached to *Epigastric pain* as a further mention. In FR100971, a
post-infarction "rupture septale apicale" is proposed as *Apical muscular
ventricular septal defect*, with a note.

### Spot check of pilot-v2-extra

Three reports, one per language, compared with the text against R0-R6 by the
main session (not a physician review).

| Report | Proposals | Obvious misses | Wrong terms | Wrong spans | Wrong status | R6 misuse |
|---|---:|---:|---:|---:|---:|---:|
| EN108139 | 12 | 0 | 0 | 0 | 0 | 0 |
| ES100937 | 11 | 0 | 0 | 0 | 0 | 0 |
| FR100629 | 11 | 0 | 1 | 0 | 0 | 0 |

- EN108139: further occurrences are marked ("T-cell prolymphocytic
  leukemia" and "T-PLL"), and the historical and the current breast
  carcinoma are separate proposals. The sternum destruction is not proposed
  (reported as without term).
- ES100937: repeated findings carry two mentions each (fever, irritability,
  rash, pancytopenia), and "sugestivos de edema agudo de pulmón" is
  `uncertain`. Not proposed and arguable: CSF protein 133,9 mg/dl, pH 7,32,
  and 5 % atypical lymphocytes. CRP 8,9 mg/l is proposed as not verbalized
  although it is borderline.
- FR100629: *Chest pain triggered by palpation* is a clinical modifier, not
  a phenotypic abnormality (counted as wrong term). *Sarcoma* is recorded as
  present for "en faveur d'un sarcome épithélioide".

### Verdict

Format and location stay reliable with prompt v2: all 164 proposals and 182
mentions of the two runs validated on the first attempt. Completeness
improved: of the six findings missed in the `pilot-v1` spot check, three are
now proposed, and the spot check of the nine further reports found no
obvious miss in three reports. Further occurrences are marked more often,
but not always. Three weaknesses remain:

- terms outside *Phenotypic abnormality* (5 of 258 proposals over all three
  runs), which an instruction in the prompt did not prevent;
- less specific terms where the lookup wording did not lead to the specific
  one;
- run-to-run variation: a finding proposed in one run can be absent in the
  next.

The self-check without extra files did not work as written in the prompt.
Whether prompt v2 is good enough for the full run is the user's decision.

Decision of 2026-10-06, taken after these pilots:

- `proposals hpo-lookup` lists only terms under *Phenotypic abnormality* in
  text search; a lookup by ID marks a term outside it as "not a phenotypic
  abnormality". The validator still accepts every active term, so a
  proposal with such a term reaches the review and is not rejected.
- Prompt v3 describes this lookup behaviour and replaces the self-check rule:
  helper scripts are allowed, but only in the git-ignored directory that
  holds the batch's text files.

## Pilot pilot-v3

Run date 2026-10-06, same corpus, prompt v3 with the restricted lookup. Nine
further reports, the third report per original language and length stratum
in the pilot's seeded order (EN100383, EN100593, EN104179, ES100001,
ES100526, ES100978, FR100120, FR100519, FR101000), selected with `--case`.

### Dispatch

- One dispatch, no re-dispatch. Validation passed on the first attempt.
- Files reported as read: the guideline and the nine text files. No other
  file in the repository changed.
- The helper script stayed where prompt v3 allows it: `gen.py` in the
  git-ignored text directory of the batch. Nothing was written to the
  temporary directory.

### Validation

| Count | Value |
|---|---:|
| Proposals received | 111 |
| Proposals rejected | 0 |
| Mentions evaluated | 128 |
| Mentions rejected | 0 |
| Label warnings | 0 |
| Not verbalized (R6) | 5 |
| Terms outside HP:0000118 | 0 |
| Spans longer than 50 characters | 6 |

Proposals per report: EN100383 13, EN100593 32, EN104179 3, ES100001 3,
ES100526 2, ES100978 31, FR100120 8, FR100519 17, FR101000 2.

Status of the 111 proposals: 90 present, 14 absent, 3 uncertain (all
patient, current); 3 present/patient/historical; 1
present/family_member/current.

### Excerpt volume across the pilots

Share of a report's characters that lie inside at least one context of the
tracked batch file (overlapping contexts counted once):

| Run | Lowest | Highest |
|---|---:|---:|
| `pilot-v1` | 11 % | 27 % (ES100320) |
| `pilot-v2` | 10 % | 30 % (ES100320) |
| `pilot-v2-extra` | 3 % | 29 % (EN108139) |
| `pilot-v3` | 8 % | 40 % (EN100593) |

The limit of 300 characters per string holds everywhere (longest context:
100 characters). There is no limit on the sum. A report with many findings
has up to 40 % of its text in the tracked contexts.

### Spot check

Three reports, one per language, compared with the text against R0-R6 by the
main session (not a physician review).

| Report | Proposals | Obvious misses | Wrong terms | Wrong spans | Wrong status | R6 misuse |
|---|---:|---:|---:|---:|---:|---:|
| EN100593 | 32 | 0 | 0 | 1 | 0 | 0 |
| ES100526 | 2 | 1 | 0 | 0 | 0 | 0 |
| FR100120 | 8 | 0 | 0 | 0 | 0 | 0 |

- EN100593: the negated lists give one absent proposal per finding
  (headache, blurred vision, spontaneous bleeding; diabetes, hypertension),
  shared wording is attached to both terms ("total protein and albumin were
  low"), and a stated finding and its later measurement are separate
  proposals (leukocytosis and "WBC 37500 cells/dL"; anemia and "HB-8.4g/dL").
  The span "grossly distended" for *Abdominal distention* does not express
  the term on its own (R2). *Splenomegaly* is proposed as absent for "spleen
  was not palpable", a normal finding by R0, with a note.
- ES100526: the lymphedema that the lymphography rules out ("para descartar
  un posible linfedema") is not proposed as absent. Not proposed and
  arguable: the pain that prevents intercourse (*Dyspareunia* exists) and
  the soft, mobile tumours (reported as without term).
- FR100120: "papules prurigineuses" is attached to *Papule* and *Pruritus*
  (R4). "lésions furonculoïdes" is proposed as *Furuncle* with a note; the
  lesions are myiasis, so the term is arguable. A third mention of the
  diabetes is not marked.

### Verdict

Prompt v3 with the restricted lookup removes the two problems it was made
for: no proposal lies outside *Phenotypic abnormality* (5 of 258 before),
and the helper script stays in the git-ignored text directory. Format and
location remain reliable (111 of 111 proposals, 128 of 128 mentions). The
spot check found one obvious miss, one span that does not stand on its own,
and two arguable proposals among 42. Open before the full run: the share
of report text in the tracked contexts (up to 40 %). Whether to start the
full run is the user's decision.

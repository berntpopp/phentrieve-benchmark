# E3C German translations

This directory documents the German translation stage for E3C. The provider
is Google Cloud Translation Advanced v3. Source languages are passed
explicitly as English, French, or Spanish; the target is German.

Three translation variants exist side by side. A variant is identified
entirely by its recipe, and each recipe produces its own manifest, artifacts,
and readable view. None replaces another.

| Variant | Recipe | Model | Location | Price |
|---|---|---|---|---|
| `nmt` | `../translation.yaml` | `general/nmt` | `global` | 20 USD per million input characters |
| `tllm` | `../translation-llm.yaml` | `general/translation-llm` | `us-central1` | 10 USD per million input **and** 10 USD per million output characters |
| `tllm-full` | `../translation-llm-full.yaml` | `general/translation-llm` | `us-central1` | same pinned TLLM price |

The 30-case `tllm` snapshot is the basis for the current manual review;
`tllm-full` extends the same model to the complete corpus.

## Cost preview

`tllm-full` binds directly to the verified 246-report normalization inventory.
It reuses the compatible 30-case `tllm` results for the same Google project,
so the current preview contains only the remaining 216 provider calls: 441,414
input codepoints and a pinned upper bound of USD 10.152522. Preparation and the
preview do not contact Google.

Verified acquisition and normalization pointers are bound to the pipeline
code hash. After the final code and documentation commits, publish both stages
again with the same roots that the translation command will use:

```text
uv run phentrieve-benchmark acquire e3c --dataset-root DATASET_ROOT --artifact-root ARTIFACT_ROOT
uv run phentrieve-benchmark normalize e3c --dataset-root DATASET_ROOT --artifact-root ARTIFACT_ROOT
```

These two commands do not invoke the paid translation provider. Then inspect
the full-corpus preview:

```text
uv run phentrieve-benchmark translate e3c --project-id PROJECT_ID --variant tllm-full --dataset-root DATASET_ROOT --artifact-root ARTIFACT_ROOT
```

Append `--retranslate-all` to deliberately translate all 246 reports again.
The existing 30-case manifest remains unchanged for a later one-off comparison;
the current full rerun preview is 500,931 input codepoints with a pinned upper
bound of USD 11.521413.

The translation command still asks for confirmation before constructing the
Google client. Declining exits without a provider call.
The 30 reused records keep their source and translation artifacts, statuses,
and checks; the full manifest gives them the full selection identity and
records the prior translation ID. This includes the five records marked
`automatic_check_failed`: they are completed provider outputs, not accepted
translations, and their warnings remain visible for medical review.

After a full manifest has been published, preparation resolves the newest
manifest matching both the full recipe and requested Google project even when
the pipeline code hash has changed. A manifest for another project is never a
reuse candidate.

The selected source texts contain 59,517 Unicode codepoints. At the pinned
list prices the conservative upper bounds are USD 1.19034 for `nmt` and
USD 1.368891 for `tllm`. A Google monthly credit may reduce the invoice,
but the pipeline does not rely on it.

The Translation LLM bills output characters as well, so an input-only
estimate would not be an upper bound. The recipe therefore pins
`output_expansion_factor: "1.30"`. That number is measured, not guessed: the
30 completed NMT translations produced 64,614 output codepoints from 59,517
input codepoints, a ratio of 1.0856, with a worst single case of 1.2151. The
pinned 1.30 sits above that observed maximum.

The completed TLLM run produced 67,679 output codepoints, a ratio of 1.1371,
and actually cost USD 1.27196 against the predicted bound of USD 1.368891.
The total estimate therefore held. One single case reached 1.3021 and thereby
exceeded the pinned factor, so that record's per-case `estimated_max_cost` was
not an upper bound. The recipe is deliberately left unchanged: its hash is
part of the published identity of this run, and correcting the factor
afterwards would rewrite history to look more accurate than it was.

Run the existing preparation first:

```text
uv run phentrieve-benchmark prepare e3c
```

Then inspect the translation preview:

```text
uv run phentrieve-benchmark translate e3c --project-id PROJECT_ID --variant tllm
```

The command prints the variant, model, case count, input characters, and the
upper bound before asking for confirmation. Answering no exits before
constructing the Google client. Answering yes requires an enabled Cloud
Translation API, billing, and Google Application Default Credentials. API keys
are not accepted as command arguments. The request location comes from the
recipe, so a regional model is reached without any extra option.

`--variant` defaults to `nmt`.

## Artifact boundary

Canonical source texts and German translations are stored as separate,
immutable objects below the Git-ignored `.artifacts/` directory. Translation
records and manifests contain only identifiers, hashes, provider metadata,
checks, counts, and costs—not report text. A retry creates a new translation
identity; an existing compatible successful result is reused.

The exact 30-case source texts and both current unreviewed translation variants
are additionally tracked in the case-oriented `../review/` snapshot for
non-commercial scientific review. That review snapshot is not the canonical
artifact store and does not change translation identity or status.

The complete authorized 246-case `tllm-full` result is tracked byte-for-byte
under [e3c-de-full-246-google-tllm-v1/](e3c-de-full-246-google-tllm-v1/) for
sharing and backup. It contains the canonical manifest plus the existing flat
readable view; the manifest SHA-256 is
`759f00260dab85a3fbeb24204683f790b4b14a18759c2bb80910ff1725b4451a`.

Reuse is keyed by a semantic hash that contains the recipe hash, so the two
variants publish independently and neither invalidates the other. The
published NMT recipe hash is frozen by a contract test; changing
`translation.yaml` would hide the completed NMT batch and silently trigger a
paid re-translation.

Regular tests use injected provider fakes and do not authenticate, contact
Google, or incur charges.

Records that pass all automatic checks reach `ready_for_review`; records that
fail remain `automatic_check_failed`. Neither status is `accepted`, and both
still require manual review. A review decision on one variant says nothing
about the other.

## Readable local view

After a successful translation run, the pipeline automatically materializes a
non-canonical, human-readable view, one directory per variant:

```text
.artifacts/views/e3c-de-nmt/
.artifacts/views/e3c-de-tllm/
.artifacts/views/e3c-de-tllm-full/
```

Each contains flat `CASE.source.LANG.txt` and `CASE.translation.de.txt` files
plus an `index.csv` with hashes, provider metadata, status, and failed check
codes. Filenames are identical across variants, so the same case sits under
the same name in both directories and any diff tool or editor compares them
directly. No separate comparison artifact is produced.

Rebuild a deleted view without contacting Google:

```text
uv run phentrieve-benchmark materialize translations e3c --variant tllm
```

The rebuild resolves the manifest belonging to that variant's recipe, verifies
existing artifacts, and never modifies canonical objects or provenance state.

## Medical review workbook

The 30-case TLLM snapshot is the default input for bilingual medical review.
Export the internal Excel workbook after the translation artifacts are present:

```text
uv run phentrieve-benchmark review-workbook export-e3c review.xlsx
```

Add the existing NMT text as a read-only comparison column only when needed:

```text
uv run phentrieve-benchmark review-workbook export-e3c review.xlsx --include-nmt
```

One multilingual medical reviewer completes the metadata and every row in the
two-sheet workbook, then saves it as `.xlsx`. Import the completed workbook:

```text
uv run phentrieve-benchmark review-workbook import-e3c review.xlsx
```

This workbook is an internal editing interface, not a release artifact. Import
validates it as a whole and creates immutable proposed texts, review records,
diffs, and an import manifest. Later stages consume those canonical artifacts,
not the `.xlsx` file; the original source, TLLM, and optional NMT artifacts are
never overwritten.

## Automatic checks

Each translation carries `nonempty_output`, `source_changed`, `length_ratio`,
`units_added`, and `target_language_de`. A single failure holds the record at
`automatic_check_failed`; otherwise it reaches `ready_for_review`. Both
variants run the identical checks, which is what makes their results
comparable.

`units_added` reports a unit that the translation attaches to a numeric value
the source leaves bare. It compares units per value rather than counting them
across the document, so a unit the translation legitimately repeats is not an
addition. It is the check that catches invented laboratory units—the failure
mode that produced the most damaging defects in the first batch, where an
unqualified `47` became `47 U/l` and turned a severe hepatitis into a normal
result.

`length_ratio` also records source and target paragraph counts in its `detail`
field. Those counts never gate; they are kept because a changed count means
source offsets no longer transfer to the translation, which matters once
annotations are anchored per paragraph.

### The Translation LLM does not remove the need for review

A language model completes context rather than leaving it open, so an
unqualified number acquiring a plausible unit is a failure mode it is prone
to—the same defect that damaged the first batch. Expect a different error
profile rather than fewer errors: fewer word-by-word absurdities, more
omissions and silent smoothing.

The automatic checks and the bilingual review therefore remain necessary for
both variants, and the pipeline computes no comparison score, ranking, or
automatic winner. Comparing the two views supplies material; the judgement is
the reviewer's.

### Removed checks

`numbers_preserved` and `units_preserved` were removed. Both compared
multisets of regular-expression matches across languages, which measured
typography rather than meaning: German thousands separators, spelled-out
numerals, marker notation (`CD 45` → `CD45`), and units glued to their value in
the source all registered as defects. Over the first 30 translations they
flagged 28 documents and detected none of the 24 clinically meaning-changing
errors a bilingual review found. Normalising the comparison was attempted and
abandoned—each additional rule broke another, because the four languages use
incompatible number, ordinal, and unit conventions.

Numeric fidelity is therefore no longer checked automatically. It is part of
the manual review.

## Re-evaluating stored translations

When check definitions change, re-run them over the artifacts already in the
store instead of translating again:

```text
uv run phentrieve-benchmark recheck translations e3c --variant tllm
```

This contacts no provider and spends nothing. It publishes a new manifest,
leaves the previous one intact, refreshes that variant's readable view, and
reports how many records changed. Running it twice in a row reports no change.
A record already `reviewed` or `accepted` keeps that status: an automatic
re-run records findings but does not revoke a human decision.

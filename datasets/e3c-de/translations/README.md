# E3C German translations

This directory documents the German translation stage for the 30 reports in
`e3c-de-feasibility-30-v1`. The provider is Google Cloud Translation
Advanced v3. Source languages are passed explicitly as English, French, or
Spanish; the target is German.

Two translation variants exist side by side. A variant is identified entirely
by its recipe, and each recipe produces its own manifest, artifacts, and
readable view. Neither replaces the other.

| Variant | Recipe | Model | Location | Price |
|---|---|---|---|---|
| `nmt` | `../translation.yaml` | `general/nmt` | `global` | 20 USD per million input characters |
| `tllm` | `../translation-llm.yaml` | `general/translation-llm` | `us-central1` | 10 USD per million input **and** 10 USD per million output characters |

Which variant becomes the basis for the manual review is decided after both
are available, not in advance.

## Cost preview

The selected source texts contain 59,517 Unicode codepoints. At the pinned
list prices the conservative upper bounds are USD 1.19034 for `nmt` and
USD 1.368891 for `tllm`. A Google monthly credit may reduce the invoice,
but the pipeline does not rely on it.

The Translation LLM bills output characters as well, so an input-only
estimate would not be an upper bound. The recipe therefore pins
`output_expansion_factor: "1.30"`. That number is measured, not guessed: the
30 completed NMT translations produced 64,614 output codepoints from 59,517
input codepoints, a ratio of 1.0856, with a worst single case of 1.2151. The
pinned 1.30 sits above the observed maximum.

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

Reuse is keyed by a semantic hash that contains the recipe hash, so the two
variants publish independently and neither invalidates the other. The
published NMT recipe hash is frozen by a contract test; changing
`translation.yaml` would hide the completed NMT batch and silently trigger a
paid re-translation.

Regular tests use injected provider fakes and do not authenticate, contact
Google, or incur charges. A generated text-free manifest may be tracked here
after a complete authorized run. Machine translation is only
`ready_for_review`; it is not `accepted` until the planned manual review has
been documented. A review decision on one variant says nothing about the
other.

## Readable local view

After a successful translation run, the pipeline automatically materializes a
non-canonical, human-readable view, one directory per variant:

```text
.artifacts/views/e3c-de-nmt/
.artifacts/views/e3c-de-tllm/
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

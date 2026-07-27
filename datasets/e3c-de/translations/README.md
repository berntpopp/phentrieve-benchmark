# E3C German translations

This directory documents the German translation stage for the 30 reports in
`e3c-de-feasibility-30-v1`. The provider is Google Cloud Translation
Advanced v3 with the standard NMT model `general/nmt`. Source languages are
passed explicitly as English, French, or Spanish; the target is German.

## Cost preview

The selected source texts contain 59,517 Unicode codepoints. At the pinned
list price of USD 20 per million NMT input characters, the conservative
upper bound is USD 1.19034. A Google monthly credit may reduce the invoice,
but the pipeline does not rely on it.

Run the existing preparation first:

```text
uv run phentrieve-benchmark prepare e3c
```

Then inspect the translation preview:

```text
uv run phentrieve-benchmark translate e3c --project-id PROJECT_ID
```

The command prints case count, input characters, and the upper bound before
asking for confirmation. Answering no exits before constructing the Google
client. Answering yes requires an enabled Cloud Translation API, billing, and
Google Application Default Credentials. API keys are not accepted as command
arguments.

## Artifact boundary

Canonical source texts and German translations are stored as separate,
immutable objects below the Git-ignored `.artifacts/` directory. Translation
records and manifests contain only identifiers, hashes, provider metadata,
checks, counts, and costs—not report text. A retry creates a new translation
identity; an existing compatible successful result is reused.

Regular tests use injected provider fakes and do not authenticate, contact
Google, or incur charges. A generated text-free manifest may be tracked here
after a complete authorized run. Machine translation is only
`ready_for_review`; it is not `accepted` until the planned manual review has
been documented.

## Readable local view

After a successful translation run, the pipeline automatically materializes a
non-canonical, human-readable view in `.artifacts/views/e3c-de/`. It contains
flat `CASE.source.LANG.txt` and `CASE.translation.de.txt` files plus an
`index.csv` with hashes, provider metadata, status, and failed check codes.

Rebuild a deleted view without contacting Google:

```text
uv run phentrieve-benchmark materialize translations e3c
```

The rebuild verifies existing artifacts and never modifies canonical objects
or provenance state.

## Automatic checks

Each translation carries `nonempty_output`, `source_changed`, `length_ratio`,
`units_added`, and `target_language_de`. A single failure holds the record at
`automatic_check_failed`; otherwise it reaches `ready_for_review`.

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
uv run phentrieve-benchmark recheck translations e3c
```

This contacts no provider and spends nothing. It publishes a new manifest,
leaves the previous one intact, refreshes the readable view, and reports how
many records changed. Running it twice in a row reports no change. A record
already `reviewed` or `accepted` keeps that status: an automatic re-run records
findings but does not revoke a human decision.

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

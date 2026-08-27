# E3C Review Resources

**Date:** 2026-07-29

## Goal

Publish the selected E3C source reports and both existing German machine
translation variants directly in this repository so collaborators can inspect
and compare them without reproducing the local translation pipeline.

These resources are review inputs, not an accepted benchmark release.

## Scope

The package contains all 30 cases from
`e3c-de-feasibility-30-v1`. Every case contains:

- the canonical E3C source text in its original language;
- the German Google NMT translation;
- the German Google Translation LLM translation.

Both variants are included regardless of automatic-check status. No text is
corrected, reformatted, or selected as the preferred translation during
publication.

The package does not introduce a review form, review database, new CLI
command, provider integration, or generalized translation pipeline.

## Repository Layout

The tracked files live below:

```text
datasets/e3c-de/review/e3c-de-feasibility-30-v1/
├── README.md
├── EN100075/
│   ├── source.en.txt
│   ├── nmt.de.txt
│   └── tllm.de.txt
```

There is one directory per source case. The source filename is
`source.<language>.txt`, where the language is `en`, `fr`, or `es`.
Translation filenames follow `<variant>.de.txt`.

The variant naming rule deliberately permits additional translation variants
later without changing the case-oriented layout. This work publishes only
`nmt` and `tllm`; it does not generalize the pipeline that produced them.

The files are normal Git blobs. Git LFS and a separate release archive are not
used because this 30-case text package is small and should be directly
browsable and reviewable.

## Source of Truth and Materialization

Publication copies exact canonical bytes from the existing artifact-backed
translation views:

- `.artifacts/views/e3c-de-nmt/`
- `.artifacts/views/e3c-de-tllm/`

For each case, the NMT and TLLM views must contain source files with identical
bytes. A mismatch aborts publication instead of choosing one copy.

The translation bytes are copied without modification from their respective
views. The tracked package is a review snapshot; `.artifacts/` remains the
canonical pipeline store and stays Git-ignored.

No reusable export command is added in this phase. Materialization is a
one-time, verified repository operation.

## Documentation and Status

The package README states:

- the selection identity and number of cases;
- that `nmt` and `tllm` are unreviewed machine translations;
- that automatic checks do not establish clinical correctness;
- that all variants require bilingual or fachsprachliche review;
- that the material must not be used for clinical decisions;
- the E3C source repository, pinned commit, and recorded CC BY-NC
  attribution with unspecified license version;
- that the package is intended for non-commercial scientific review.

No editable review table is introduced. Review decisions and corrected texts
remain separate future work so the original machine outputs stay immutable.

Existing repository documentation and machine-readable evidence must no
longer claim that all E3C text is local-only. The root README, E3C README,
E3C licensing notes, and translation documentation distinguish the new,
explicitly tracked 30-case review snapshot from the full upstream corpus and
the canonical local artifact store.

`license-evidence.yaml` records the explicit
`noncommercial_scientific_review_snapshot` redistribution decision and the
working assumption behind it. The license-evidence model accepts that decision
in addition to `source_not_redistributed`, and `dataset.yaml` pins the updated
semantic evidence hash.

## Validation

A focused contract test verifies:

- exactly the 30 selected case identifiers are present;
- the source-language distribution remains 10 English, 10 French, and
  10 Spanish cases;
- every case has exactly one correctly named source file and the two expected
  German variant files;
- every text file is non-empty, valid UTF-8, NFC-normalized, and uses LF
  rather than CR or CRLF line endings;
- one deterministic digest over the sorted relative paths and exact file
  bytes pins the complete review snapshot;
- no unexpected files or variant names appear in the review package.

The existing repository safety scan still runs after the text files are
staged. It protects the credential and forbidden-local-path boundaries but is
not treated as a clinical-text or licensing classifier.

## Future Extension

A later translation variant can add one `<variant>.de.txt` file per case and
update the package README and contract expectations. Supporting its creation
may separately require a new recipe, provider adapter, pricing model,
provenance fields, and tests.

Accepted or corrected translations will not overwrite the files in this
unreviewed snapshot. They will be published through a separate curated
benchmark or release structure.

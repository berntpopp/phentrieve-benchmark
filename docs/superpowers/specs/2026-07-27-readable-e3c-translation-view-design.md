# Readable E3C Translation View

**Status:** Approved after automatic-export revision

## Goal

Provide a compact, human-readable projection of the existing content-addressed
E3C source and German translation artifacts without changing canonical
objects, manifests, or stage state.

## Interface

Every successful E3C translation run automatically refreshes the readable
view after publishing the canonical manifest and stage state. Automatic and
manual materialization use the same implementation.

Also add this recovery and rebuild command:

```text
phentrieve-benchmark materialize translations e3c
```

The command resolves the current compatible E3C translation manifest through
pipeline state and writes the same deterministic view as the automatic path:

```text
.artifacts/views/e3c-de/
├── index.csv
├── EN100075.source.en.txt
├── EN100075.translation.de.txt
└── ...
```

Every selected case has one UTF-8 source file and one UTF-8 German translation
file. Files use canonical text bytes from the object store without modifying
their contents.

## Index

`index.csv` is ordered by source case ID and contains:

- source case ID and source language;
- source and translation relative paths;
- source and translation SHA-256 digests;
- translation ID, status, and failed automatic-check codes;
- provider, API version, model, Google project ID, and location;
- creation time and input/output codepoint counts.

CSV output uses a stable header, UTF-8 encoding, and deterministic line
endings.

## Integrity and safety

Before publishing the view, materialization validates the translation manifest
and reads every source and translation through `ArtifactStore`, which verifies
content hashes. Output is assembled in a temporary sibling directory and
published as a complete view so readers do not observe a partial result.

The generator owns only `.artifacts/views/e3c-de`. Re-running the command
replaces a previously generated view. It refuses to replace the directory when
the expected generator marker is absent. Canonical data under
`.artifacts/objects` and `.artifacts/state` is read-only throughout.

Translation success is defined by publication of the canonical translation
manifest and stage state. A subsequent view-generation failure does not roll
back or mutate that canonical result. The translation command reports the view
failure and exits unsuccessfully so the operator can repair the view manually
without repeating paid translation requests.

## Failure behavior

The command fails without publishing a new view when translation state,
manifest objects, referenced text objects, or the generator marker are missing
or invalid. Error messages identify metadata and hashes, never clinical text.

## Tests and documentation

Unit tests cover deterministic filenames, byte-preserving contents, CSV
metadata and ordering, failed-check serialization, missing/corrupt artifacts,
safe regeneration, refusal to replace an unowned directory, automatic
materialization after translation, and canonical-result preservation when
view generation fails. CLI tests cover command exposure and failure reporting.
Translation documentation explains the automatic readable view, recovery
command, and non-canonical status.

After implementation, the command is run once against the existing 30-case
manifest to create the local view.

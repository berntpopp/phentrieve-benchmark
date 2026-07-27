# Readable E3C Translation View

**Status:** Approved for implementation

## Goal

Provide a compact, human-readable projection of the existing content-addressed
E3C source and German translation artifacts without changing canonical
objects, manifests, or stage state.

## Interface

Add this command:

```text
phentrieve-benchmark materialize translations e3c
```

It resolves the current compatible E3C translation manifest through pipeline
state and writes a deterministic view below:

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

## Failure behavior

The command fails without publishing a new view when translation state,
manifest objects, referenced text objects, or the generator marker are missing
or invalid. Error messages identify metadata and hashes, never clinical text.

## Tests and documentation

Unit tests cover deterministic filenames, byte-preserving contents, CSV
metadata and ordering, failed-check serialization, missing/corrupt artifacts,
safe regeneration, and refusal to replace an unowned directory. CLI tests
cover command exposure. Translation documentation explains the readable view
and its non-canonical status.

After implementation, the command is run once against the existing 30-case
manifest to create the local view.

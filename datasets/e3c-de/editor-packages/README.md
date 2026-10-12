# E3C editor package build records

One text-free record per Ontocurator work package built by
`scripts/build_editor_packages.py e3c`. The packages themselves contain the
report texts and stay in the git-ignored `.artifacts/editor-packages/`.

```text
uv run --with-editable ../ontocurator \
    python scripts/build_editor_packages.py e3c --hp ../phentrieve/data/hp.json
```

A record states what a package was built from:

- `manifest_sha256`: the canonical hash of the package manifest. An editor
  export reports the same value as `origin_manifest_hash`, so every export
  leads back to exactly one record.
- `proposal_index`: path and SHA-256 of `current-proposals.json`.
- `runs`, `corpus_manifest_sha256`, `guideline_commits`: the proposal runs,
  corpus manifests, and guideline versions behind the included proposals.
- `task_profile`, `ontology`: profile hash and pinned HPO release.

The build is deterministic. Rebuilding at the commit that added a record
reproduces its `manifest_sha256`; the ZIP bytes differ because of archive
timestamps. The builder refuses to overwrite a record with a different hash:
changed content needs a new `--package-version`, because the editor does not
replace an imported package under the same ID.

The ZIP is built in a temporary directory on the destination filesystem,
read back and checked against the existing record before it replaces the
published ZIP. A failed write, package validation or version check leaves
the existing ZIP and build record unchanged.

The guideline version a reviewer works under is not part of a package. It
belongs to the review round and is supplied when the export is imported.

The recorded packages predate the guideline revision of 2026-10-09. Their
profiles still include the `verbalization` axis, and their proposals may
include non-verbalized measurement findings. Such findings do not enter gold
unchanged under the revised guideline: only findings explicitly interpreted
in the text are annotated. Adapting the profile/import handling and reviewing
affected proposals are pending. Existing package IDs and build records remain
historical evidence; changed package content requires a new package version.

The active proposal, cross-read and revision prompt templates also still
describe the earlier measurement rule. Update the templates and package
profile together before new proposal runs under the revised guideline;
technical proposal validation does not establish guideline compliance.

Test packages built with `--limit` get no record.

Synthetic integration tests for package publication use the editor overlay:

```text
uv run --with-editable ../ontocurator pytest tests/integration/test_editor_packages.py
```

The normal offline suite skips these tests when Ontocurator is unavailable.

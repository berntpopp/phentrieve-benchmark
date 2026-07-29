# E3C Layer 1 preparation

This target prepares the English, French, and Spanish Layer 1 reports from
E3C v2.0.0. It does not translate, map concepts to HPO, invoke a provider,
perform clinical review, or create a release.

The immutable source is `hltfbk/E3C-Corpus` commit
`f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc`. Its ZIP is 233,811,002 bytes
with SHA-256
`04e06d0a153a8ea845b647459ab51eb2fed5007bdf450d441c1469f8719a2206`.
The recipe selects only Layer 1 XML: 84 English, 81 French, and 81 Spanish
documents. These are public upstream data. The complete source XML snapshot
and canonical generated artifacts remain under the Git-ignored `.artifacts/`
directory. An explicit 30-case snapshot containing selected canonical source
texts and both unreviewed German translation variants is tracked under
`review/` for non-commercial scientific review.

Only the text-free inventory and selection manifest are tracked for the full
corpus. Upstream licensing and the explicit review-snapshot redistribution
decision are recorded in `license-evidence.yaml` and `LICENSES.md`.

Run `uv run phentrieve-benchmark prepare e3c`; use
`uv run phentrieve-benchmark smoke live-download` only for an explicit live
verification. XMI offsets are interpreted as UTF-16 code-unit offsets and
mapped to NFC-normalized canonical text. Terminal formatting newlines are
removed according to the adapter contract.

The next independent stage translates the selected 30 reports with Google
NMT. Its pinned configuration is in `translation.yaml`, and operation,
costing, artifact separation, and review boundaries are documented in
`translations/README.md`. Translation is never part of the regular offline
CI and requires an explicit confirmation after the cost preview.

UMLS-to-HPO mapping is an independent, local stage and does not require a
translation or Google credentials. Run
`uv run phentrieve-benchmark map-hpo e3c`; exact results and classification
counts are documented under `mappings/`.

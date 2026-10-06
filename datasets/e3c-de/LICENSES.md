# E3C licensing evidence

The [pinned upstream README](https://github.com/hltfbk/E3C-Corpus/blob/f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc/README.md)
states “CC BY-NC” but does not identify a version. The local
[license evidence](license-evidence.yaml) therefore records
`LicenseRef-E3C-CC-BY-NC-version-unspecified` and does not infer CC BY-NC 4.0.
This corpus-level statement is the basis for the project's documented working
assumption about non-commercial scientific review, not legal clearance.

The complete acquired corpus remains in Git-ignored local artifacts. The
tracked 246-report source and unreviewed German translation snapshot under
`translations/` is redistributed for attributed, non-commercial scientific review
under the project's documented working assumption. The unspecified upstream
license version remains recorded rather than silently resolved.

Each original report also supplies its own `docAuthor`, `docDOI`, `docUrl`,
and `docLicense`. Those values are retained verbatim for all 246 reports in
[`ATTRIBUTION.md`](ATTRIBUTION.md), generated from the pinned source.
The generic supplied values `CC BY`, `CC-BY`, and `CC BY-NC` remain
version-unspecified; no license version is inferred from them. Seven reports
supply `CC BY-NC`; their non-commercial condition applies independently of how
the corpus-level license is resolved.

The supplied `docLicense` values were checked against the publisher or archive
copy of every report on 2026-10-06; the result and its evidence are in
[`PUBLISHER-LICENSES.md`](PUBLISHER-LICENSES.md). Five reports (`EN102305`,
`EN104179`, `EN104184`, `EN104263`, `EN106233`, Journal of Orthopaedic Case
Reports) are published under CC BY-NC-SA 3.0, not the `CC BY-NC` that E3C
supplies. Their ShareAlike condition requires adaptations to be shared under
the same or a compatible license, so it applies to the German translations of
these five reports. The license under which the project shares those
translations is not yet decided.

Every German `*.translation.de.txt` file under
`translations/e3c-de-full-246-google-tllm-v1/` is an unreviewed
machine-translated adaptation of its attributed original report. The files
themselves carry no notice; the adaptation status is stated here and the
per-report attribution is in [`ATTRIBUTION.md`](ATTRIBUTION.md). Only the
Translation LLM variant (`tllm-full`) is tracked.

The translation snapshot is not an accepted benchmark release and must not be
used for clinical decisions.

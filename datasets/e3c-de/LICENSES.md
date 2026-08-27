# E3C licensing evidence

The [pinned upstream README](https://github.com/hltfbk/E3C-Corpus/blob/f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc/README.md)
states “CC BY-NC” but does not identify a version. The local
[license evidence](license-evidence.yaml) therefore records
`LicenseRef-E3C-CC-BY-NC-version-unspecified` and does not infer CC BY-NC 4.0.
This corpus-level statement is the basis for the project's documented working
assumption about non-commercial scientific review, not legal clearance.

The complete acquired corpus remains in Git-ignored local artifacts. The
selected 30-case source and unreviewed German translation snapshot under
`review/` is redistributed for attributed, non-commercial scientific review
under the project's documented working assumption. The unspecified upstream
license version remains recorded rather than silently resolved.

Each selected original report also supplies its own `docAuthor`, `docDOI`,
`docUrl`, and `docLicense`. Those values are retained verbatim in the review
package's [per-case attribution appendix](review/e3c-de-feasibility-30-v1/README.md#original-report-attribution-and-adaptation-notice).
The generic supplied values `CC BY` and `CC-BY` remain version-unspecified; no
license version is inferred from them.

Every German `*.de.txt` file in the review package is an unreviewed
machine-translated adaptation of its attributed original report. This applies
to both the NMT and Translation LLM variants.

The review snapshot is not an accepted benchmark release and must not be used
for clinical decisions.

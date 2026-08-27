# CSC normalization

CSC uses the workbook as its authoritative source. `CSC Input` supplies
columns `Case` and `clinical_note` for 116 documents. `CSC Manual
Annotations` supplies `Patient ID`, `hpo_description`, and `hpo_term`: 1,789
rows expand to 1,795 HPO annotations. The earlier CSV duplicate discrepancy is
recorded in `source-resolution.md`.

Identifiers and workbook joins are exact. HPO strings may yield multiple
identifiers, while source descriptions remain only in the local sidecar.
Because the workbook contains no offsets, derived annotations have empty
evidence spans. Revision against HPO `v2026-06-23` is recorded separately and
does not silently rewrite the canonical source normalization.

Run `uv run phentrieve-benchmark prepare csc`.


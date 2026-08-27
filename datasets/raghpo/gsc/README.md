# GSC normalization

GSC reads `GSC Input` columns `patient_id`, `ID`, and `clinical_note` for 114
documents. Sheet `GSC Manual Annotations ` (including its trailing space)
provides `Patient ID`, `ID`, `hpo_description`, `hpo_term`, and `Category`;
its 1,012 rows produce 1,012 HPO annotations.

Joins and identifiers are exact. Source descriptions stay in a local sidecar,
and derived annotations have empty evidence spans because no offsets are
provided. HPO `v2026-06-23` revision results are audited without rewriting the
canonical source normalization.

Run `uv run phentrieve-benchmark prepare gsc`.


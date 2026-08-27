# RAG-HPO source preparation

CSC and GSC share one verified source snapshot but have independent
normalization state. The source is `PoseyPod/RAG-HPO` commit
`080fc3a04c91ee45c8986076765f4d4b4f14ddd9`; its ZIP is 12,524,020 bytes
with SHA-256
`a2ece2b7b44e522a299dff02733dd1cad69d5ba11f7dc4da9c346c201662b52b`.
Only the pinned workbook, CSV, README, and license evidence are acquired.

Run `uv run phentrieve-benchmark prepare csc` and
`uv run phentrieve-benchmark prepare gsc`. The upstream data are public.
Workbooks and normalized records remain in `.artifacts/` to keep Git lean and
preserve the documented source boundary, not because they are confidential.
HPO identifiers are audited against `v2026-06-23`; the audit and revision
policy document active, replaced, ambiguous, and unknown identifiers.

This phase does not translate, invoke a provider, conduct manual review, or
publish a release.

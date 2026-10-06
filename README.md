# Phentrieve Benchmark

Reproducible, provenance-preserving data pipelines for Phentrieve benchmark datasets.

Real source text, translations, provider responses, curation packets, and
restricted release bundles normally remain in Git-ignored local artifact
paths. The explicit exception is the tracked, unreviewed 246-report E3C German
translation snapshot under `datasets/e3c-de/translations/`, with per-report
attribution in `datasets/e3c-de/ATTRIBUTION.md`.

Dataset preparation is split into independently runnable stages:
`acquire`, `normalize`, `select`, and `prepare`. For example:

```text
uv run phentrieve-benchmark prepare e3c
uv run phentrieve-benchmark prepare csc
uv run phentrieve-benchmark prepare gsc
```

Normal CI is offline and uses synthetic fixtures. The explicit
`smoke live-download` command is reserved for deliberate real-source checks.

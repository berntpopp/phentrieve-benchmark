# E3C UMLS-to-HPO mapping

These text-free outputs map every E3C Layer 1 `CLINENTITY` annotation against
exact `UMLS:` cross-references in the official HPO release `v2026-06-23`
(`hp.obo` SHA-256
`a5092cbdf605f568403cf7380d9173014015692433b2cc631bc5c1b053876b1b`).
The command is:

```text
uv run phentrieve-benchmark map-hpo e3c
```

The complete population contains 246 documents and 3,696 eligible source
annotations. Results are:

- 1,321 `unique_active`;
- 58 `ambiguous`;
- 1,925 `missing`;
- 0 `obsolete`; and
- 392 `invalid`.

`invalid` comprises source values without a valid `C` plus seven digits,
including 311 `CUILESS`, 78 absent identifiers, two `C036572` values, and one
`C0042963x` value.

The selected 30-case view contains 458 annotations: 162 `unique_active`, 3
`ambiguous`, 244 `missing`, 0 `obsolete`, and 49 `invalid`.

The pinned ontology contains one malformed cross-reference,
`HP:0034420 -> UMLS:0189573`. It is excluded rather than silently rewritten
to a different CUI and is retained as the deterministic ontology warning
`HP:0034420:malformed_umls_xref:0189573`.

`unique_active` records remain candidates rather than accepted clinical
annotations. All other classifications require review. No labels are used to
infer missing mappings, obsolete terms are not replaced automatically, and
this phase creates no German evidence spans.


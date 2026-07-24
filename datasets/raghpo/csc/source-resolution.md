# CSC source-text resolution

The pinned RAG-HPO snapshot contains CSC clinical notes in both
`Test_Cases.csv` and the workbook sheet `CSC Input`.

For 115 of 116 cases, the canonical texts agree exactly. For case `68`,
`Test_Cases.csv` repeats the complete text and SHA-256 of case `67`:

```text
52f3c7030d1e78d91af2f8c2c123829d21a5be6a0526c93c60cfc820b5848ee8
```

The workbook contains a distinct case-68 text:

```text
6a15d5b360da752be91ef9de875e1a1307ba2724297b64419885b0c3879a15fe
```

The workbook is authoritative for all CSC clinical texts. The CSC adapter
therefore reads `CSC Input` and joins it directly to
`CSC Manual Annotations`; it does not consume `Test_Cases.csv`.

The CSV remains part of the immutable upstream source snapshot because it is
an upstream benchmark input and the discrepancy is relevant provenance. It is
not a normalization input for this benchmark.

# HPO annotation editor: backend and storage assessment

Date: 2026-09-13.

Status: evidence and recommendation, not an accepted architecture decision.
This assessment documents the discussion about retaining the existing editor,
rebuilding its interface, or creating a new application. No implementation or
schema migration is part of this document.

## Scope and evidence

Inspected the local `JohannKaspar/hpo-span-annotator` checkout at commit
`27c5dad` (the commit titled "Work as a group without hosting: local instances,
one shared dataset repo"). Links below pin that source revision. Read the model,
store, HTTP save path, export, event log, synchronization, agreement reporting,
and UI rendering code. Ran one synthetic model/offset-validation probe; no full
test suite, concurrency stress test, or browser usability evaluation was run.

The user's assessment is that the current interface is visually busy, especially
its many radio buttons. Code inspection confirms axes are rendered on each
mention card; this records the usability concern without claiming a formal study.

Related design discussions:

- [Schema, axes, and gold policy (#2)](https://github.com/berntpopp/phentrieve-benchmark/issues/2)
- [Editor scope (#3)](https://github.com/berntpopp/phentrieve-benchmark/issues/3)
- [Current handoff](hpo-annotation-editor-findings.md)
- [Local snapshot of #3](hpo-annotation-editor-issue-draft.md)

## Current storage model

```text
corpus.jsonl                          input documents
records/<annotator_id>/<doc_id>.json  current mutable record
events/<annotator_id>.jsonl           appended interaction events
```

Each `DocumentRecord` stores document and annotator IDs, language, HPO release,
corpus version, timestamps, a `complete` flag, metadata, and mentions. A mention
contains an ID, span segments, HPO term links, shared axes, and a simple origin
label. Term links retain retrieval route, rank, and display position. Axis data
can include basis and cue/marker spans.

The unit is a mention with several terms. There is no independent HPO annotation
entity linking several distinct evidence mentions. JSON and per-record files
are not inherently unsuitable; the limiting factors are the model and its
validation, versioning, and concurrency guarantees.

Source: [model.py](https://github.com/JohannKaspar/hpo-span-annotator/blob/27c5dad/hpo_span_annotator/model.py).

## Strengths worth preserving

- Explicit span segments support discontinuity, overlap, and nesting.
- Offsets reference the source text; stored records avoid a second copy of quotes.
- Separate annotator records support independent annotation.
- Search provenance distinguishes retrieval rank from displayed position.
- Search/ontology modules provide lexical, exact, ID, dense, and hierarchy routes.
- Record replacement uses a temporary file; event appends are protected by
  per-annotator process-local locks and flushed with `fsync`.
- Optional Hugging Face mirroring restricts writes to the annotator's own paths.

These are useful components and ideas, not evidence that the whole backend meets
the benchmark's contracts. Mirroring assumes one writer for an annotator's paths;
it is not review reconciliation or conflict-safe editing of the same record.

Sources: [store.py](https://github.com/JohannKaspar/hpo-span-annotator/blob/27c5dad/hpo_span_annotator/store.py),
[search.py](https://github.com/JohannKaspar/hpo-span-annotator/blob/27c5dad/hpo_span_annotator/search.py),
[persist.py](https://github.com/JohannKaspar/hpo-span-annotator/blob/27c5dad/hpo_span_annotator/persist.py).

## Structural limitations

| Finding | Consequence for the benchmark editor |
| --- | --- |
| Axes belong to a mention shared by its terms. | Terms sharing that mention cannot have independent assertions or experiencers. |
| `validate_offsets` rejects terms without evidence spans. | Span-free document annotations cannot be saved through the normal path. |
| Multiple segments belong to one mention; no annotation groups separate mentions. | Repeated evidence and one discontinuous mention lack the required explicit relationship to one annotation. |
| A save replaces the current record. | No canonical immutable submission or review bound to an exact content version. |
| Records have no schema version. | Future record interpretation and compatibility are not explicitly governed. |
| Document and ontology references lack content digests. | IDs/version strings alone do not detect changed text or ontology content. |
| `complete` is mutable record state. | It does not establish an immutable reviewed completeness assertion. |
| Export emits one row per mention. | A completed document with zero mentions produces no row, losing its completion evidence in that export. |

The export does have `schema: hpo-span-annotator/1`; this is distinct from the
unversioned working records. It does not emit complete proposal derivation and
review artifacts. Agreement reporting compares term sets and covered character
sets; it does not reconcile conflicting annotations or assess axis agreement.

Sources: [export.py](https://github.com/JohannKaspar/hpo-span-annotator/blob/27c5dad/hpo_span_annotator/export.py),
[merge.py](https://github.com/JohannKaspar/hpo-span-annotator/blob/27c5dad/hpo_span_annotator/merge.py).

## Validation findings and reproducible probe

The model declares allowed axis values but does not enforce them in the record
parsing or save validation. `axes` is an arbitrary dictionary. Evidence bounds
and non-whitespace content are checked; cue spans are not checked there. HPO IDs
are checked for their shape, not resolved against the loaded ontology on save.

Run from the inspected annotator checkout with `uv run python`:

```python
from hpo_span_annotator.model import DocumentRecord, validate_offsets

raw = {
    "document_id": "demo",
    "complete": True,
    "mentions": [{
        "mention_id": "m1",
        "spans": [{"char_start": 0, "char_end": 4}],
        "terms": [{"hpo_id": "HP:9999999"}],
        "axes": {"certainty": {
            "value": "NOT_AN_ALLOWED_VALUE",
            "marker_span": {"char_start": 500, "char_end": 900},
        }},
    }],
}
record = validate_offsets(DocumentRecord.from_dict(raw), "Test document")
assert record.complete is True
assert record.mentions[0].axes == raw["mentions"][0]["axes"]
assert record.mentions[0].terms[0].hpo_id == "HP:9999999"
assert "schema_version" not in record.as_dict()
```

Observed: the invalid axis value and out-of-bounds marker survive validation,
including `complete=True`. The HPO-shaped ID is accepted without an ontology
lookup; this probe does not claim that the ID was checked against any release.
The actual HTTP save path calls this model parsing and store validation without
adding axis or term-existence checks. This was a direct model probe, not an HTTP
integration test.

Source: [service.py](https://github.com/JohannKaspar/hpo-span-annotator/blob/27c5dad/hpo_span_annotator/service.py).

## Persistence and provenance findings

- There is no expected-version check to reject stale saves. A later arriving
  browser state can overwrite a more recent edit.
- The temporary record filename contains the process ID, with no per-record
  save lock. Concurrent requests for the same record in one process use the
  same temporary path. Collision/failure is a code-derived risk, not a reproduced
  concurrency failure in this assessment.
- Record saves and event appends are separate requests/writes, without a shared
  transaction. The log is useful interaction telemetry, not a demonstrated
  complete reconstruction of immutable annotation versions.
- File replacement helps avoid partially replaced records, but does not itself
  establish conflict protection or power-loss durability. Record writes do not
  use the event append path's `fsync`.
- Completed records can be replaced through the save API; the UI's closed-state
  interaction is not an immutable server-side submission mechanism.

Correction to the earlier draft: ontology identity is not necessarily `latest`.
The loader reads the supplied ontology's version, extracts a release date where
possible, and the server stamps it onto saved records. The remaining gaps are
strict accepted-release validation and content-digest binding. Corpus version
is also server-stamped, but a per-document text digest is absent.

Source: [hpo.py](https://github.com/JohannKaspar/hpo-span-annotator/blob/27c5dad/hpo_span_annotator/hpo.py).

## Recommendation and unresolved choices

Recommend a new UI and a persistence/submission/review layer based on the
benchmark contracts, evolving those contracts explicitly where necessary.
Evaluate selective reuse of `spans.js` and search/ontology modules. Do not adopt
the existing record format as the benchmark's canonical annotation format.

The interface concern alone would not justify replacing a backend. Here, the
independent structural and validation gaps make retaining the whole application
less compelling. This does not prove extraction is cheaper: in-place refactoring
could also reuse benchmark validators. A small prototype should compare the
integration work before accepting the architecture and code location.

`spans.js` reuse needs an offset compatibility check. The existing loader rejects
non-BMP text because browser UTF-16 indices and Python code-point indices differ.
General Unicode support needs an explicit, tested conversion or an agreed text
restriction. Unchanged extraction is not established.

The existing benchmark v1 is also not a complete answer: its flat evidence list
does not distinguish repeated from discontinuous mentions, and evidence edits
change content-derived annotation IDs. Native benchmark integration therefore
still needs the structural decisions in #2.

## What can start before final axes are accepted

A bounded prototype can cover text display, evidence editing, HPO lookup,
annotation selection, and controls rendered from a built-in versioned axis
definition. Final clinical axis values need not block that work. Keep the same
definition authoritative for UI choices and server validation; a general profile
authoring framework is unnecessary.

Before durable annotation work, decide annotation/evidence structure, shared
evidence edit behavior, text offsets, stable IDs versus content versions, and
workspace schema versioning. Before canonical submission and productive review,
agree supported schema semantics and version-bound review behavior. Gold release
also requires an accepted selection policy and document completeness contract.

Autosave may use a private versioned workspace. Canonical submission must reject
unsupported versions or unrepresentable content rather than silently flatten
mention structure into v1. Clinical defaults must not silently fill unavailable
legacy information. Schema migration remains separate pipeline work.

Suggested prototype cases are already listed in #3: attach spans to a span-free
annotation; share and detach evidence with independent axes; distinguish repeated
and discontinuous mentions; edit evidence after review without inheriting
approval; complete a zero-finding document; and check non-BMP offsets.

No final architecture, axis values, contract version, or implementation scope is
approved by recording this recommendation.

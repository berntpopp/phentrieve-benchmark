# E3C Translation LLM Variant

**Status:** Approved

## Goal

Translate the same 30 selected E3C cases a second time with Google's
Translation LLM (`general/translation-llm`) so the result can be compared
against the existing `general/nmt` batch, in which a bilingual review found 24
clinically meaning-changing errors.

The NMT translation is not replaced. Both manifests, both sets of artifacts,
and both readable views exist side by side. Which one becomes the basis for
the manual review is decided after the comparison, not by this change.

Glossaries and contextual translation are explicitly out of scope. Introducing
them together with the model change would make it impossible to tell whether a
quality difference came from the model or from forced terminology. They are a
later step with their own identity.

## Non-goal: automatic quality judgement

Translation LLM does not prevent hallucination. The specific defect that
damaged the first batch—an unqualified `47` becoming `47 U/l`—is a failure mode
an LLM is prone to, because it completes context rather than leaving it open.
The existing automatic checks stay unchanged and stay necessary. No comparison
score, ranking, or automatic winner is produced; the comparison provides
material, the judgement comes from the bilingual review.

## Variant selection

A translation variant is identified by its recipe. Two recipes exist:

| Variant | Recipe | Model | Location |
|---|---|---|---|
| `nmt` | `datasets/e3c-de/translation.yaml` | `general/nmt` | `global` |
| `tllm` | `datasets/e3c-de/translation-llm.yaml` | `general/translation-llm` | `us-central1` |

`translation.yaml` is not modified. Its `recipe_sha256` is part of the semantic
key under which the existing NMT result is published; any change would silence
reuse and trigger a paid re-translation.

The new recipe uses `translation_id: e3c-de-feasibility-30-google-tllm-v1` and
the same `selection_id`.

Regional requests need no client change: the default global endpoint accepts a
regional `location` in the parent path, so the adapter only has to pass the
location it already receives from the recipe.

These commands take `--variant {nmt|tllm}`, defaulting to `nmt` so existing
documented invocations keep their meaning and stay free:

```text
phentrieve-benchmark translate e3c --project-id PROJECT_ID --variant tllm
phentrieve-benchmark recheck translations e3c --variant tllm
phentrieve-benchmark materialize translations e3c --variant tllm
```

## Stage state resolution

`StageState` needs no change. Its semantic key already contains
`recipe_sha256`, so the two variants publish to distinct pointer files inside
`state/translate/e3c/` without colliding.

What must change is how a published pointer is found again. `recheck` and
`materialize` currently take the newest file in that directory by modification
time. That directory already holds two pointers today, and with two variants
the choice becomes wrong rather than merely fragile. Both commands instead load
the selected variant's recipe, compute its `recipe_sha256`, and resolve the
pointer through `StageState.reuse` with the full semantic key. Failure to
resolve is an error naming the variant, not a fallback to another pointer.

## Schema changes

Both `model` fields—in `E3cTranslationRecipe` and in `TranslationRecord`—widen
to `Literal["general/nmt", "general/translation-llm"]`. Widening a literal adds
no field, so existing manifests re-serialize byte-identically and keep their
hashes.

`GoogleNmtPricing` gains two optional fields:

- `price_per_million_output_characters`
- `output_expansion_factor`

Translation LLM is billed at 10 USD per million input characters **plus** 10
USD per million output characters, so an input-only estimate is not an upper
bound. `output_expansion_factor` is not guessed: the existing NMT records carry
`input_codepoints` and `output_codepoints` per case, so the observed
en/fr/es→de ratio is computed from them and pinned rounded up. With a
conservative 1.30 the upper bound is roughly 1.37 USD for 59,517 input
characters, against 1.19 USD for NMT.

When the recipe pins both fields, `estimate_google_nmt` computes

```text
input_codepoints * input_price / 1e6
  + input_codepoints * output_expansion_factor * output_price / 1e6
```

and reports it as both estimate and upper bound. When they are absent the
existing input-only calculation applies unchanged. Pinning only one of the two
fields is a recipe validation error.

### Recipe canonicalization

`load_translation_recipe` hashes `model_dump(mode="json")`. An optional field
appears as `null` for the existing NMT recipe, which would change its
`recipe_sha256`, change the semantic key, hide the published NMT manifest from
`prepare_e3c_translation`, and cause a silent paid re-translation.

Recipe canonicalization therefore switches to `exclude_none=True`. The current
NMT recipe has no `None` field, so its hash is unchanged; the TLLM recipe may
carry the additional pricing fields. A regression test pins the existing NMT
`recipe_sha256` literally.

This applies to the recipe only. `TranslationRecord.previous_translation_id` is
serialized as `null` in the stored records, so the same change on the manifest
side would alter existing manifest hashes.

### What deliberately does not change

`TranslationRecord` gains no field. It keeps the true input list price in
`price_per_million_input_characters` and the full pre-run bound in
`estimated_max_cost`. The derivation stays reconstructible because the manifest
carries `recipe_sha256` and the recipe carries both prices. Avoiding a new
record field avoids re-serializing the stored NMT manifest and therefore avoids
republishing it under a new hash on the next `recheck`.

Manifest canonicalization, the five automatic checks, the cost preview, and the
explicit confirmation before the Google client is constructed all stay as they
are. Identical checks across both variants are what makes the two runs
comparable.

## Provider adapter

`GoogleNmtAdapter` no longer hard-codes `general/nmt`. It takes the model ID as
a constructor argument and builds
`projects/PROJECT/locations/LOCATION/models/MODEL`. The factory passes the
model ID and location from the selected recipe. Response validation, the
single-translation requirement, empty-response rejection, and canonical text
normalization are unchanged.

## Readable views

Views become siblings, one per variant:

```text
.artifacts/views/e3c-de-nmt/
.artifacts/views/e3c-de-tllm/
```

Filenames inside a view are unchanged, so the same case has the same filename
in both directories and any diff tool compares them directly. No separate
comparison artifact or command is produced.

The existing `.artifacts/views/e3c-de/` is deleted once. It is non-canonical
and regenerated by `materialize translations e3c`.

## Review status

TLLM records start at `translated`, then `automatic_check_failed` or
`ready_for_review`, exactly like NMT records. No review status is inherited
from the NMT batch; a human decision on one variant says nothing about the
other.

## Tests and documentation

Offline only, injected provider fakes, no authentication and no charges, as
before. New coverage:

- the existing NMT recipe loads unchanged and keeps its pinned `recipe_sha256`
  after the canonicalization change;
- the TLLM recipe loads with output price and expansion factor;
- cost estimation with and without an output price;
- the adapter builds the TLLM model path and a regional parent;
- pointer resolution picks the right variant when two pointers exist, and fails
  clearly when the requested variant was never published;
- `--variant` on all three commands, including the `nmt` default;
- views are written to variant-specific directories.

`datasets/e3c-de/translations/README.md` documents both variants, the differing
price model, the changed view paths, and that Translation LLM does not remove
the need for the automatic checks or the bilingual review.

The project checklist records the second translation path and that the choice
between variants is pending the comparison.

## Execution

After implementation, the TLLM run is executed once against the same 30 cases,
after the cost preview and explicit confirmation, and both views are
materialized for the bilingual review.

# E3C Translation LLM Variant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second E3C German translation path using Google's Translation LLM (`general/translation-llm`) beside the existing `general/nmt` path, so both can be compared on the same 30 cases without disturbing the existing result.

**Architecture:** A translation variant is identified entirely by its recipe file. `translation.yaml` (NMT) stays byte-identical; `translation-llm.yaml` (TLLM) is new. A `--variant {nmt|tllm}` flag selects the recipe, and published stage pointers are resolved by matching the manifest's `recipe_sha256` instead of by file modification time. Readable views become one directory per variant.

**Tech Stack:** Python 3.12, pydantic v2 (strict, frozen, `extra="forbid"`), typer, pytest, uv, google-cloud-translate v3.

---

## Background the implementer needs

Read `docs/superpowers/specs/2026-07-27-e3c-translation-llm-variant-design.md` first.

Three facts drive almost every decision below:

1. **Money is at stake.** A real translation run costs about 1.19 USD (NMT, already spent) or about 1.37 USD (TLLM). Reuse of the already-translated NMT batch is keyed by a semantic hash that contains `recipe_sha256`. If `datasets/e3c-de/translation.yaml` or the way it is hashed changes, the pipeline silently stops recognising the existing result and re-translates for money. Task 2 pins that hash with a test before anything else touches the recipe code.

2. **Manifest hashes must not drift.** `TranslationManifest.canonical_bytes()` dumps every field including `null`s. Adding any field to `TranslationRecord` changes the bytes of the already-stored manifest and republishes it under a new hash. This plan therefore adds no record field. Widening a `Literal` adds no field and is safe.

3. **Clinical text never appears in manifests, logs, or error messages.** Only identifiers, hashes, counts, and provider metadata. Keep it that way.

Run the whole suite with:

```bash
uv run pytest -q
```

---

## File structure

| File | Responsibility | Action |
|---|---|---|
| `src/phentrieve_benchmark/translation/variants.py` | Map a variant name to its recipe path and view directory; resolve a published stage pointer by recipe hash | Create |
| `src/phentrieve_benchmark/translation/pricing.py` | Recipe schema, recipe loading/hashing, cost estimation | Modify |
| `src/phentrieve_benchmark/models/translation.py` | Record/manifest schema | Modify (one literal) |
| `src/phentrieve_benchmark/translation/e3c.py` | Per-case translation runner | Modify (use recipe model) |
| `src/phentrieve_benchmark/translation/google_nmt.py` | Google client adapter | Modify (model ID parameter) |
| `src/phentrieve_benchmark/translation/view.py` | Readable view materialization | Modify (resolve by recipe hash, variant destination) |
| `src/phentrieve_benchmark/pipeline/translate.py` | Stage orchestration | Modify (thread variant through) |
| `src/phentrieve_benchmark/cli.py` | Commands | Modify (`--variant`, drop `--location`) |
| `datasets/e3c-de/translation-llm.yaml` | TLLM recipe | Create |
| `datasets/e3c-de/translations/README.md` | Operator documentation | Modify |
| `docs/project-checklist.md` | Project status | Modify |

**Deliberately not renamed:** `GoogleNmtPricing`, `GoogleNmtAdapter`, `estimate_google_nmt`, `google_nmt.py`. The names are historical and now slightly wide, but renaming them touches a dozen test files for zero functional gain. Leave them.

---

### Task 1: Allow the Translation LLM model in both schemas

Two `Literal["general/nmt"]` annotations must accept the new model, and the runner must stop hard-coding the model into the record.

**Files:**
- Modify: `src/phentrieve_benchmark/models/translation.py:48`
- Modify: `src/phentrieve_benchmark/translation/pricing.py:41`
- Modify: `src/phentrieve_benchmark/translation/e3c.py:148`
- Test: `tests/unit/translation/test_e3c_runner.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/translation/test_e3c_runner.py`:

```python
def test_record_carries_the_recipe_model(tmp_path: Path) -> None:
    document = _document()
    store = ArtifactStore(tmp_path / "objects")
    recipe = _recipe().model_copy(
        update={"model": "general/translation-llm", "location": "us-central1"}
    )

    result = translate_documents(
        inputs=(
            TranslationInput(
                document=document,
                expected_source_sha256=document.document_sha256,
            ),
        ),
        provider=_Provider(),
        store=store,
        recipe=recipe,
        selection_sha256="c" * 64,
        project_id="benchmark-project",
        created_at=datetime(2026, 7, 27, tzinfo=UTC),
        language_detector=lambda _text: "de",
    )

    record = result.manifest.records[0]
    assert record.model == "general/translation-llm"
    assert record.location == "us-central1"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/translation/test_e3c_runner.py::test_record_carries_the_recipe_model -v
```

Expected: FAIL. `model_copy` with an invalid literal is not validated, so the failure surfaces when `TranslationRecord` is constructed with the hard-coded `"general/nmt"`; the assertion on `record.model` fails.

- [ ] **Step 3: Widen both literals**

In `src/phentrieve_benchmark/models/translation.py`, change the `model` field of `TranslationRecord`:

```python
    model: Literal["general/nmt", "general/translation-llm"]
```

In `src/phentrieve_benchmark/translation/pricing.py`, change the `model` field of `E3cTranslationRecipe`:

```python
    model: Literal["general/nmt", "general/translation-llm"]
```

- [ ] **Step 4: Use the recipe model in the runner**

In `src/phentrieve_benchmark/translation/e3c.py`, inside the `TranslationRecord(...)` construction, replace:

```python
                model="general/nmt",
```

with:

```python
                model=recipe.model,
```

- [ ] **Step 5: Run the translation tests**

```bash
uv run pytest tests/unit/translation tests/unit/models/test_translation.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/phentrieve_benchmark/models/translation.py src/phentrieve_benchmark/translation/pricing.py src/phentrieve_benchmark/translation/e3c.py tests/unit/translation/test_e3c_runner.py
git commit -m "feat: allow the Translation LLM model in translation schemas"
```

---

### Task 2: Pin the existing NMT recipe hash

This is a characterization test. It passes immediately and exists to fail loudly in Task 3 if the recipe hash drifts. Do not skip it — it is the guard against a silent paid re-translation.

**Files:**
- Test: `tests/contracts/test_dataset_recipes.py`

- [ ] **Step 1: Write the test**

Append to `tests/contracts/test_dataset_recipes.py`:

```python
def test_e3c_google_nmt_recipe_hash_is_frozen() -> None:
    loaded = load_translation_recipe(ROOT / "datasets/e3c-de/translation.yaml")

    assert loaded.sha256 == (
        "abb8542fd1d2362bc714c3c9f1a59cf941fd1f74f4cd3812ddf587abe490c8b0"
    )
```

- [ ] **Step 2: Run it and confirm it already passes**

```bash
uv run pytest tests/contracts/test_dataset_recipes.py::test_e3c_google_nmt_recipe_hash_is_frozen -v
```

Expected: PASS. If it fails, stop and investigate — the stored NMT result is no longer reachable and nothing further in this plan is safe.

- [ ] **Step 3: Commit**

```bash
git add tests/contracts/test_dataset_recipes.py
git commit -m "test: freeze the published E3C NMT recipe hash"
```

---

### Task 3: Add optional output pricing without moving the NMT hash

Translation LLM bills input **and** output characters, so the pricing block needs two more values. Both must be optional, and adding them must not change the NMT recipe hash — which it would, because `model_dump(mode="json")` emits them as `null`.

**Files:**
- Modify: `src/phentrieve_benchmark/translation/pricing.py`
- Test: `tests/unit/translation/test_pricing.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/translation/test_pricing.py`:

```python
def test_pricing_accepts_output_price_and_expansion_factor() -> None:
    pricing = GoogleNmtPricing(
        currency="USD",
        price_per_million_input_characters=Decimal("10"),
        price_per_million_output_characters=Decimal("10"),
        output_expansion_factor=Decimal("1.30"),
        pricing_snapshot_id="google-cloud-translation-llm-2026-07-27",
    )

    assert pricing.price_per_million_output_characters == Decimal("10")
    assert pricing.output_expansion_factor == Decimal("1.30")


def test_pricing_rejects_output_price_without_expansion_factor() -> None:
    with pytest.raises(ValueError, match="expansion factor"):
        GoogleNmtPricing(
            currency="USD",
            price_per_million_input_characters=Decimal("10"),
            price_per_million_output_characters=Decimal("10"),
            pricing_snapshot_id="google-cloud-translation-llm-2026-07-27",
        )


def test_pricing_rejects_expansion_factor_without_output_price() -> None:
    with pytest.raises(ValueError, match="expansion factor"):
        GoogleNmtPricing(
            currency="USD",
            price_per_million_input_characters=Decimal("10"),
            output_expansion_factor=Decimal("1.30"),
            pricing_snapshot_id="google-cloud-translation-llm-2026-07-27",
        )
```

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/unit/translation/test_pricing.py -v
```

Expected: FAIL with pydantic `extra_forbidden` errors for the unknown fields.

- [ ] **Step 3: Extend the pricing model**

In `src/phentrieve_benchmark/translation/pricing.py`, replace the whole `GoogleNmtPricing` class with:

```python
class GoogleNmtPricing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_per_million_input_characters: Decimal = Field(ge=0)
    price_per_million_output_characters: Decimal | None = None
    output_expansion_factor: Decimal | None = None
    pricing_snapshot_id: str = Field(min_length=1)

    @field_validator(
        "price_per_million_input_characters",
        "price_per_million_output_characters",
        "output_expansion_factor",
        mode="before",
    )
    @classmethod
    def price_is_decimal(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        if not isinstance(value, Decimal):
            raise ValueError("price must be represented as Decimal")
        if not value.is_finite() or value < 0:
            raise ValueError("price must be finite and non-negative")
        return value

    @model_validator(mode="after")
    def output_pricing_is_complete(self) -> Self:
        price = self.price_per_million_output_characters
        factor = self.output_expansion_factor
        if (price is None) != (factor is None):
            raise ValueError(
                "output pricing requires an output price and an "
                "expansion factor together"
            )
        if factor is not None and factor <= 0:
            raise ValueError("expansion factor must be positive")
        return self
```

Update the imports at the top of the file:

```python
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
```

- [ ] **Step 4: Parse the new values from YAML**

Still in `src/phentrieve_benchmark/translation/pricing.py`, inside `load_translation_recipe`, replace this block:

```python
    raw_price = pricing.get("price_per_million_input_characters")
    if not isinstance(raw_price, str):
        raise ValueError("translation recipe price must be a decimal string")
    try:
        pricing["price_per_million_input_characters"] = Decimal(raw_price)
    except ArithmeticError as error:
        raise ValueError("translation recipe price is invalid") from error
```

with:

```python
    for name in (
        "price_per_million_input_characters",
        "price_per_million_output_characters",
        "output_expansion_factor",
    ):
        raw_value = pricing.get(name)
        if raw_value is None:
            if name == "price_per_million_input_characters":
                raise ValueError(
                    "translation recipe price must be a decimal string"
                )
            continue
        if not isinstance(raw_value, str):
            raise ValueError("translation recipe price must be a decimal string")
        try:
            pricing[name] = Decimal(raw_value)
        except ArithmeticError as error:
            raise ValueError("translation recipe price is invalid") from error
```

- [ ] **Step 5: Run the frozen-hash test and watch it break**

```bash
uv run pytest tests/contracts/test_dataset_recipes.py::test_e3c_google_nmt_recipe_hash_is_frozen -v
```

Expected: FAIL. The NMT recipe now dumps `"price_per_million_output_characters": null` and `"output_expansion_factor": null`, which changes its hash. This is exactly the silent re-translation trap; the next step closes it.

- [ ] **Step 6: Exclude absent fields from recipe canonicalization**

In `src/phentrieve_benchmark/translation/pricing.py`, at the end of `load_translation_recipe`, change:

```python
    semantic = canonical_json_bytes(value.model_dump(mode="json"))
```

to:

```python
    semantic = canonical_json_bytes(
        value.model_dump(mode="json", exclude_none=True)
    )
```

Apply this to the **recipe only**. Do not touch `TranslationManifest.canonical_bytes`; existing records serialize `previous_translation_id` as `null`, so the same change there would move every stored manifest hash.

- [ ] **Step 7: Run both test files to verify they pass**

```bash
uv run pytest tests/contracts/test_dataset_recipes.py tests/unit/translation/test_pricing.py -v
```

Expected: PASS, including the frozen hash `abb8542f…`.

- [ ] **Step 8: Commit**

```bash
git add src/phentrieve_benchmark/translation/pricing.py tests/unit/translation/test_pricing.py
git commit -m "feat: add optional output pricing to the translation recipe"
```

---

### Task 4: Include the output share in the cost estimate

**Files:**
- Modify: `src/phentrieve_benchmark/translation/pricing.py`
- Test: `tests/unit/translation/test_pricing.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/translation/test_pricing.py`:

```python
def test_estimate_adds_the_output_share_when_pinned() -> None:
    pricing = GoogleNmtPricing(
        currency="USD",
        price_per_million_input_characters=Decimal("10"),
        price_per_million_output_characters=Decimal("10"),
        output_expansion_factor=Decimal("1.30"),
        pricing_snapshot_id="google-cloud-translation-llm-2026-07-27",
    )

    estimate = estimate_google_nmt(59_517, pricing)

    assert estimate.estimated_cost == Decimal("1.368891")
    assert estimate.upper_bound == Decimal("1.368891")
```

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run pytest tests/unit/translation/test_pricing.py::test_estimate_adds_the_output_share_when_pinned -v
```

Expected: FAIL, actual `0.59517` — the input share only.

- [ ] **Step 3: Add the output share**

In `src/phentrieve_benchmark/translation/pricing.py`, replace the body of `estimate_google_nmt` between the guard and the `return` with:

```python
    cost = (
        Decimal(input_codepoints)
        * pricing.price_per_million_input_characters
        / _MILLION
    )
    output_price = pricing.price_per_million_output_characters
    factor = pricing.output_expansion_factor
    if output_price is not None and factor is not None:
        cost += Decimal(input_codepoints) * factor * output_price / _MILLION
```

- [ ] **Step 4: Run the pricing tests**

```bash
uv run pytest tests/unit/translation/test_pricing.py -v
```

Expected: PASS, including the unchanged NMT case at `1.19034`.

- [ ] **Step 5: Commit**

```bash
git add src/phentrieve_benchmark/translation/pricing.py tests/unit/translation/test_pricing.py
git commit -m "feat: estimate input and output characters for LLM translation"
```

---

### Task 5: Add the Translation LLM recipe

Prices are the pinned Google list prices of 10 USD per million input characters and 10 USD per million output characters. The expansion factor is not guessed: the 30 existing NMT records total 59,517 input and 64,614 output codepoints, a ratio of 1.0856, with a worst single case of 1.2151 (EN107021). The pinned 1.30 sits above the observed maximum, so the estimate is an upper bound.

**Files:**
- Create: `datasets/e3c-de/translation-llm.yaml`
- Test: `tests/contracts/test_dataset_recipes.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/contracts/test_dataset_recipes.py`:

```python
def test_e3c_translation_llm_recipe_is_pinned() -> None:
    recipe = load_translation_recipe(
        ROOT / "datasets/e3c-de/translation-llm.yaml"
    ).value

    assert recipe.translation_id == "e3c-de-feasibility-30-google-tllm-v1"
    assert recipe.selection_id == "e3c-de-feasibility-30-v1"
    assert recipe.provider == "google-cloud-translation"
    assert recipe.api_version == "v3"
    assert recipe.model == "general/translation-llm"
    assert recipe.location == "us-central1"
    assert recipe.target_language == "de"
    assert recipe.pricing.price_per_million_input_characters == Decimal("10")
    assert recipe.pricing.price_per_million_output_characters == Decimal("10")
    assert recipe.pricing.output_expansion_factor == Decimal("1.30")
```

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run pytest tests/contracts/test_dataset_recipes.py::test_e3c_translation_llm_recipe_is_pinned -v
```

Expected: FAIL with "invalid translation recipe: translation-llm.yaml".

- [ ] **Step 3: Create the recipe**

Create `datasets/e3c-de/translation-llm.yaml`:

```yaml
schema_version: e3c-translation-recipe/v1
translation_id: e3c-de-feasibility-30-google-tllm-v1
selection_id: e3c-de-feasibility-30-v1
provider: google-cloud-translation
api_version: v3
model: general/translation-llm
location: us-central1
target_language: de
pricing:
  currency: USD
  price_per_million_input_characters: "10"
  price_per_million_output_characters: "10"
  output_expansion_factor: "1.30"
  pricing_snapshot_id: google-cloud-translation-llm-2026-07-27
```

- [ ] **Step 4: Run the contract tests**

```bash
uv run pytest tests/contracts -q
```

Expected: PASS. If a repository-safety or tracked-output contract test objects to the new file, read its assertion and extend its expected file list rather than deleting the recipe.

- [ ] **Step 5: Commit**

```bash
git add datasets/e3c-de/translation-llm.yaml tests/contracts/test_dataset_recipes.py
git commit -m "feat: pin the E3C Translation LLM recipe"
```

---

### Task 6: Make the adapter model configurable

**Files:**
- Modify: `src/phentrieve_benchmark/translation/google_nmt.py:30-81`
- Test: `tests/unit/translation/test_google_nmt.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/translation/test_google_nmt.py`:

```python
def test_adapter_builds_a_regional_translation_llm_request() -> None:
    class _Client:
        def __init__(self) -> None:
            self.request: dict[str, object] | None = None

        def translate_text(self, *, request: dict[str, object]) -> object:
            self.request = request
            return SimpleNamespace(
                translations=[
                    SimpleNamespace(translated_text="Der Patient hatte Fieber.")
                ]
            )

    client = _Client()
    adapter = GoogleNmtAdapter(
        client=client,
        project_id="benchmark-project",
        location="us-central1",
        model="general/translation-llm",
    )

    adapter.translate(
        "The patient had fever.", source_language="en", target_language="de"
    )

    assert client.request is not None
    parent = "projects/benchmark-project/locations/us-central1"
    assert client.request["parent"] == parent
    assert client.request["model"] == f"{parent}/models/general/translation-llm"
```

Add `from types import SimpleNamespace` to that file's imports if it is not already there.

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run pytest tests/unit/translation/test_google_nmt.py::test_adapter_builds_a_regional_translation_llm_request -v
```

Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'model'`.

- [ ] **Step 3: Add the model parameter**

In `src/phentrieve_benchmark/translation/google_nmt.py`, change `GoogleNmtAdapter.__init__` to:

```python
    def __init__(
        self,
        *,
        client: TranslationClient,
        project_id: str,
        location: str = "global",
        model: str = "general/nmt",
    ) -> None:
        self._client = client
        self.project_id = project_id
        self.location = location
        self.model = model
```

In the same class, change the request's model line from:

```python
                "model": f"{parent}/models/general/nmt",
```

to:

```python
                "model": f"{parent}/models/{self.model}",
```

And change the factory to:

```python
def create_google_nmt_adapter(
    *,
    project_id: str,
    location: str = "global",
    model: str = "general/nmt",
) -> GoogleNmtAdapter:
    from google.cloud import translate_v3

    return GoogleNmtAdapter(
        client=translate_v3.TranslationServiceClient(),
        project_id=project_id,
        location=location,
        model=model,
    )
```

No client endpoint change is needed. The default global endpoint accepts a regional `location` in the parent path.

- [ ] **Step 4: Run the adapter tests**

```bash
uv run pytest tests/unit/translation/test_google_nmt.py -v
```

Expected: PASS, including the existing NMT tests that rely on the defaults.

- [ ] **Step 5: Commit**

```bash
git add src/phentrieve_benchmark/translation/google_nmt.py tests/unit/translation/test_google_nmt.py
git commit -m "feat: make the Google translation model configurable"
```

---

### Task 7: Add the variant module

Three things need to be derived from a variant name: its recipe path, its view directory, and its published stage pointer. Pointer resolution matches on the manifest's `recipe_sha256` because the semantic key requires a Google project ID that `recheck` and `materialize` do not have.

**Files:**
- Create: `src/phentrieve_benchmark/translation/variants.py`
- Test: `tests/unit/translation/test_variants.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/translation/test_variants.py`:

```python
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.models.translation import (
    TranslationCheck,
    TranslationManifest,
    TranslationRecord,
    TranslationStatus,
)
from phentrieve_benchmark.pipeline.state import StageState
from phentrieve_benchmark.translation.variants import (
    resolve_translation_pointer,
    translation_recipe_path,
    translation_view_destination,
)


def _manifest(store: ArtifactStore, *, recipe_sha256: str) -> str:
    source = store.put_bytes(b"The patient had fever.\n")
    translated = store.put_bytes(b"Der Patient hatte Fieber.\n")
    manifest = TranslationManifest(
        selection_id="selection-1",
        selection_sha256="a" * 64,
        recipe_sha256=recipe_sha256,
        records=(
            TranslationRecord(
                translation_id=f"translation-{recipe_sha256[:4]}",
                selection_id="selection-1",
                source_case_id="EN000001",
                source_language="en",
                target_language="de",
                source_sha256=source,
                translation_sha256=translated,
                provider="google-cloud-translation",
                api_version="v3",
                model="general/nmt",
                project_id="phentrieve",
                location="global",
                created_at=datetime(2026, 7, 27, tzinfo=UTC),
                input_codepoints=23,
                output_codepoints=25,
                price_per_million_input_characters=Decimal("20"),
                estimated_max_cost=Decimal("0.00046"),
                status=TranslationStatus.READY_FOR_REVIEW,
                checks=(TranslationCheck(code="nonempty_output", passed=True),),
            ),
        ),
    )
    return store.put_bytes(manifest.canonical_bytes())


def test_recipe_path_and_view_destination_per_variant(tmp_path: Path) -> None:
    assert translation_recipe_path(tmp_path, "nmt") == (
        tmp_path / "e3c-de" / "translation.yaml"
    )
    assert translation_recipe_path(tmp_path, "tllm") == (
        tmp_path / "e3c-de" / "translation-llm.yaml"
    )
    assert translation_view_destination(tmp_path, "nmt") == (
        tmp_path / "views" / "e3c-de-nmt"
    )
    assert translation_view_destination(tmp_path, "tllm") == (
        tmp_path / "views" / "e3c-de-tllm"
    )


def test_unknown_variant_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown translation variant"):
        translation_recipe_path(tmp_path, "gemini")
    with pytest.raises(ValueError, match="unknown translation variant"):
        translation_view_destination(tmp_path, "gemini")


def test_resolver_picks_the_pointer_matching_the_recipe(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    state = StageState(tmp_path / "state", store)
    first = _manifest(store, recipe_sha256="1" * 64)
    second = _manifest(store, recipe_sha256="2" * 64)
    for subject, key in ((first, "3" * 64), (second, "4" * 64)):
        state.publish(
            stage="translate",
            target="e3c",
            subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
            subject_sha256=subject,
            semantic_hashes={"recipe_sha256": key},
        )

    pointer = resolve_translation_pointer(
        artifact_root=tmp_path, store=store, recipe_sha256="1" * 64
    )

    assert pointer.subject_sha256 == first


def test_resolver_reports_a_missing_variant(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    state = StageState(tmp_path / "state", store)
    state.publish(
        stage="translate",
        target="e3c",
        subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
        subject_sha256=_manifest(store, recipe_sha256="1" * 64),
        semantic_hashes={"recipe_sha256": "3" * 64},
    )

    with pytest.raises(ValueError, match="no published E3C translation"):
        resolve_translation_pointer(
            artifact_root=tmp_path, store=store, recipe_sha256="9" * 64
        )
```

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/unit/translation/test_variants.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'phentrieve_benchmark.translation.variants'`.

- [ ] **Step 3: Write the module**

Create `src/phentrieve_benchmark/translation/variants.py`:

```python
from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.models.translation import TranslationManifest
from phentrieve_benchmark.pipeline.state import StagePointer

TRANSLATION_VARIANTS: dict[str, str] = {
    "nmt": "translation.yaml",
    "tllm": "translation-llm.yaml",
}


def _recipe_filename(variant: str) -> str:
    try:
        return TRANSLATION_VARIANTS[variant]
    except KeyError:
        raise ValueError(
            f"unknown translation variant: {variant}"
        ) from None


def translation_recipe_path(dataset_root: Path, variant: str) -> Path:
    return dataset_root / "e3c-de" / _recipe_filename(variant)


def translation_view_destination(artifact_root: Path, variant: str) -> Path:
    _recipe_filename(variant)
    return artifact_root / "views" / f"e3c-de-{variant}"


def resolve_translation_pointer(
    *, artifact_root: Path, store: ArtifactStore, recipe_sha256: str
) -> StagePointer:
    """Find the published translation manifest produced by one recipe.

    Both variants publish into the same stage directory, so the newest file
    is not necessarily the requested one. Matching on the manifest's recipe
    hash identifies the variant without needing the Google project ID that
    the full semantic key contains.
    """
    state_root = artifact_root / "state" / "translate" / "e3c"
    candidates = sorted(
        state_root.glob("*.json"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for path in candidates:
        pointer = StagePointer.model_validate_json(path.read_bytes())
        if (
            pointer.subject_role
            is not ProvenanceSubjectRole.TRANSLATION_MANIFEST
        ):
            continue
        manifest = TranslationManifest.model_validate_json(
            store.read_bytes(pointer.subject_sha256), strict=True
        )
        if manifest.recipe_sha256 == recipe_sha256:
            return pointer
    raise ValueError(
        f"no published E3C translation for recipe {recipe_sha256}"
    )
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/unit/translation/test_variants.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/phentrieve_benchmark/translation/variants.py tests/unit/translation/test_variants.py
git commit -m "feat: resolve translation variants by recipe hash"
```

---

### Task 8: Thread the variant through views and the pipeline

This replaces the "newest file in the directory" heuristic everywhere it appears and sends each variant's view to its own directory.

**Files:**
- Modify: `src/phentrieve_benchmark/translation/view.py:23-44`
- Modify: `src/phentrieve_benchmark/pipeline/translate.py`
- Test: `tests/unit/translation/test_view.py`
- Test: `tests/unit/pipeline/test_translate.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/translation/test_view.py`, replace the import of `materialize_latest_translation_view` with `materialize_published_translation_view`, and append:

```python
def test_published_view_selects_the_variant_and_directory(tmp_path) -> None:
    from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
    from phentrieve_benchmark.pipeline.state import StageState

    store = ArtifactStore(tmp_path / "objects")
    manifest = _manifest(store)
    subject = store.put_bytes(manifest.canonical_bytes())
    StageState(tmp_path / "state", store).publish(
        stage="translate",
        target="e3c",
        subject_role=ProvenanceSubjectRole.TRANSLATION_MANIFEST,
        subject_sha256=subject,
        semantic_hashes={"recipe_sha256": "c" * 64},
    )

    result = materialize_published_translation_view(
        artifact_root=tmp_path,
        store=store,
        recipe_sha256="b" * 64,
        variant="tllm",
    )

    assert result.destination == (tmp_path / "views" / "e3c-de-tllm").resolve()
    assert (result.destination / "EN000001.translation.de.txt").is_file()
```

The helper `_manifest` in that file already sets `recipe_sha256="b" * 64`, which is why the call asks for `"b" * 64`.

Any existing test in this file that calls `materialize_latest_translation_view` must be updated to the new function and arguments; there is no compatibility shim.

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run pytest tests/unit/translation/test_view.py -v
```

Expected: FAIL with `ImportError: cannot import name 'materialize_published_translation_view'`.

- [ ] **Step 3: Rewrite the view entry point**

In `src/phentrieve_benchmark/translation/view.py`, delete `materialize_latest_translation_view` entirely and put this in its place:

```python
def materialize_published_translation_view(
    *,
    artifact_root: Path,
    store: ArtifactStore,
    recipe_sha256: str,
    variant: str,
) -> TranslationViewResult:
    pointer = resolve_translation_pointer(
        artifact_root=artifact_root,
        store=store,
        recipe_sha256=recipe_sha256,
    )
    manifest = TranslationManifest.model_validate_json(
        store.read_bytes(pointer.subject_sha256)
    )
    return materialize_translation_view(
        manifest=manifest,
        store=store,
        destination=translation_view_destination(artifact_root, variant),
    )
```

Replace the now-unused imports of `ProvenanceSubjectRole` and `StagePointer` at the top of the file with:

```python
from phentrieve_benchmark.translation.variants import (
    resolve_translation_pointer,
    translation_view_destination,
)
```

Keep the `ArtifactStore`, `TranslationManifest`, and `Path` imports.

- [ ] **Step 4: Thread the variant through the pipeline**

In `src/phentrieve_benchmark/pipeline/translate.py`:

Add to the imports:

```python
from phentrieve_benchmark.translation.variants import (
    resolve_translation_pointer,
    translation_recipe_path,
    translation_view_destination,
)
```

Change the signature of `prepare_e3c_translation`:

```python
def prepare_e3c_translation(
    context: PipelineContext, project_id: str, variant: str = "nmt"
) -> PreparedE3cTranslation:
```

and inside it replace:

```python
    loaded_recipe = load_translation_recipe(
        context.dataset_root / "e3c-de" / "translation.yaml"
    )
```

with:

```python
    loaded_recipe = load_translation_recipe(
        translation_recipe_path(context.dataset_root, variant)
    )
```

Add a `variant` keyword to `translate_e3c`:

```python
def translate_e3c(
    *,
    prepared: PreparedE3cTranslation,
    context: PipelineContext,
    project_id: str,
    authorized: bool,
    provider_factory: Callable[[], object],
    variant: str = "nmt",
) -> TranslationStageResult:
```

and change its view call to:

```python
    materialize_translation_view(
        manifest=translated.manifest,
        store=context.store,
        destination=translation_view_destination(
            context.artifact_root, variant
        ),
    )
```

Delete the `_latest_translation_pointer` function entirely.

Change `recheck_e3c_translations` to:

```python
def recheck_e3c_translations(
    context: PipelineContext, variant: str = "nmt"
) -> TranslationRecheckStageResult:
    """Re-run the automatic checks over already translated artifacts.

    Contacts no provider and spends nothing. When the verdicts are unchanged
    the existing manifest is returned untouched rather than republished.
    """
    recipe = load_translation_recipe(
        translation_recipe_path(context.dataset_root, variant)
    )
    pointer = resolve_translation_pointer(
        artifact_root=context.artifact_root,
        store=context.store,
        recipe_sha256=recipe.sha256,
    )
```

The rest of that function's body is unchanged except its two `materialize_translation_view` destination arguments, which both become:

```python
        destination=translation_view_destination(
            context.artifact_root, variant
        ),
```

(There is one such call at the end of `recheck_e3c_translations`; the early-return branch has none.)

- [ ] **Step 5: Add a pipeline test for variant separation**

Add `import pytest` to the imports of `tests/unit/pipeline/test_translate.py` and
`recheck_e3c_translations` to its existing
`from phentrieve_benchmark.pipeline.translate import (...)` block, then append:

```python
def test_recheck_reports_a_missing_variant(tmp_path: Path) -> None:
    context = _context(tmp_path)

    with pytest.raises(ValueError, match="no published E3C translation"):
        recheck_e3c_translations(context, "tllm")
```

`_context(tmp_path)` is the existing helper at line 64 of that file. Do not add a second one.

The existing `test_successful_translation_materializes_readable_view` asserts the
old `views/e3c-de` path. Change its expected destination to
`views/e3c-de-nmt`, since `translate_e3c` now defaults to the `nmt` variant.

- [ ] **Step 6: Run the affected tests**

```bash
uv run pytest tests/unit/translation tests/unit/pipeline -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/phentrieve_benchmark/translation/view.py src/phentrieve_benchmark/pipeline/translate.py tests/unit/translation/test_view.py tests/unit/pipeline/test_translate.py
git commit -m "feat: select translation manifests and views per variant"
```

---

### Task 9: Expose `--variant` on the CLI

The translate command also loses its `--location` option. It duplicated the recipe's location and could contradict the value written into the record.

**Files:**
- Modify: `src/phentrieve_benchmark/cli.py:18-28,124-185`
- Test: `tests/unit/test_cli_pipeline.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_cli_pipeline.py`:

```python
def test_translate_command_accepts_a_variant() -> None:
    from typer.testing import CliRunner

    from phentrieve_benchmark.cli import app

    result = CliRunner().invoke(app, ["translate", "e3c", "--help"])

    assert result.exit_code == 0
    assert "--variant" in result.stdout
    assert "--location" not in result.stdout


def test_recheck_and_materialize_accept_a_variant() -> None:
    from typer.testing import CliRunner

    from phentrieve_benchmark.cli import app

    runner = CliRunner()
    for command in (
        ["recheck", "translations", "e3c", "--help"],
        ["materialize", "translations", "e3c", "--help"],
    ):
        result = runner.invoke(app, command)
        assert result.exit_code == 0
        assert "--variant" in result.stdout
```

If the file already imports `CliRunner` and `app` at module level, use those instead of the local imports.

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/unit/test_cli_pipeline.py -k variant -v
```

Expected: FAIL — `--variant` is absent and `--location` is present.

- [ ] **Step 3: Update the CLI**

In `src/phentrieve_benchmark/cli.py`, change the view import:

```python
from phentrieve_benchmark.translation.view import (
    materialize_published_translation_view,
)
```

Add:

```python
from phentrieve_benchmark.translation.pricing import load_translation_recipe
from phentrieve_benchmark.translation.variants import translation_recipe_path
```

Add a shared option type next to `Cohort`:

```python
Variant = Annotated[str, typer.Option()]
```

Replace `translate_e3c_command` with:

```python
@translate_app.command("e3c")
def translate_e3c_command(
    project_id: Annotated[str, typer.Option()],
    variant: Variant = "nmt",
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    context = _pipeline_context(dataset_root, artifact_root)
    prepared = prepare_e3c_translation(context, project_id, variant)
    estimate = estimate_prepared_translation(prepared)
    typer.echo(
        f"variant={variant} model={prepared.recipe.model} "
        f"cases={estimate.case_count} "
        f"input_characters={estimate.input_codepoints} "
        f"upper_bound={estimate.cost.currency} "
        f"{estimate.cost.upper_bound:f}"
    )
    if not typer.confirm(
        f"Google translation ({prepared.recipe.model}) starten?"
    ):
        raise typer.Exit(code=1)
    result = translate_e3c(
        prepared=prepared,
        context=context,
        project_id=project_id,
        authorized=True,
        variant=variant,
        provider_factory=lambda: create_google_nmt_adapter(
            project_id=project_id,
            location=prepared.recipe.location,
            model=prepared.recipe.model,
        ),
    )
    typer.echo(
        f"subject_sha256={result.subject_sha256} "
        f"translated={result.translated_count} "
        f"failed={result.failed_count} reused={result.reused_count}"
    )
```

Replace `materialize_e3c_translations_command` with:

```python
@materialize_translations_app.command("e3c")
def materialize_e3c_translations_command(
    variant: Variant = "nmt",
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    context = _pipeline_context(dataset_root, artifact_root)
    recipe = load_translation_recipe(
        translation_recipe_path(context.dataset_root, variant)
    )
    result = materialize_published_translation_view(
        artifact_root=context.artifact_root,
        store=context.store,
        recipe_sha256=recipe.sha256,
        variant=variant,
    )
    typer.echo(
        f"destination={result.destination} cases={result.case_count}"
    )
```

Replace `recheck_e3c_translations_command` with:

```python
@recheck_translations_app.command("e3c")
def recheck_e3c_translations_command(
    variant: Variant = "nmt",
    dataset_root: DatasetRoot = Path("datasets"),
    artifact_root: ArtifactRoot = Path(".artifacts"),
) -> None:
    """Re-run the automatic checks over already translated artifacts."""
    context = _pipeline_context(dataset_root, artifact_root)
    result = recheck_e3c_translations(context, variant)
    typer.echo(
        f"subject_sha256={result.subject_sha256} "
        f"cases={result.case_count} changed={result.changed_count} "
        f"failed={result.failed_count}"
    )
```

- [ ] **Step 4: Run the CLI tests**

```bash
uv run pytest tests/unit/test_cli_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 5: Run the whole suite**

```bash
uv run pytest -q
```

Expected: PASS with the same skip count as before this plan started. Fix anything the wider suite catches — in particular any remaining reference to `materialize_latest_translation_view`.

- [ ] **Step 6: Commit**

```bash
git add src/phentrieve_benchmark/cli.py tests/unit/test_cli_pipeline.py
git commit -m "feat: select the translation variant from the command line"
```

---

### Task 10: Update documentation and remove the stale view

**Files:**
- Modify: `datasets/e3c-de/translations/README.md`
- Modify: `docs/project-checklist.md`
- Delete: `.artifacts/views/e3c-de/` (untracked, regenerable)

- [ ] **Step 1: Rewrite the provider section of the translations README**

In `datasets/e3c-de/translations/README.md`, replace the opening paragraph and the cost preview section with content covering both variants:

- two variants, `nmt` (`general/nmt`, `global`, 20 USD per million input characters) and `tllm` (`general/translation-llm`, `us-central1`, 10 USD per million input **and** 10 USD per million output characters);
- the pinned output expansion factor of 1.30 and where it comes from: 59,517 input against 64,614 output codepoints across the 30 NMT records, a ratio of 1.0856 with a worst case of 1.2151, so 1.30 is an upper bound;
- upper bounds of 1.19034 USD for `nmt` and roughly 1.368891 USD for `tllm`;
- the commands, each with `--variant`:

```text
uv run phentrieve-benchmark translate e3c --project-id PROJECT_ID --variant tllm
uv run phentrieve-benchmark recheck translations e3c --variant tllm
uv run phentrieve-benchmark materialize translations e3c --variant tllm
```

- [ ] **Step 2: Update the readable view section**

Replace the `.artifacts/views/e3c-de/` path with the two variant directories `.artifacts/views/e3c-de-nmt/` and `.artifacts/views/e3c-de-tllm/`, and state that filenames are identical across variants so any diff tool compares them directly. State that no separate comparison artifact is produced.

- [ ] **Step 3: Add the honest caveat**

Add a short section stating that Translation LLM does not remove hallucination: an unqualified number acquiring a unit is a failure mode a language model is prone to, so `units_added`, the other automatic checks, and the bilingual review remain necessary, and no automatic winner between the variants is computed.

- [ ] **Step 4: Update the project checklist**

In `docs/project-checklist.md`, under "Deutsche Übersetzung", add:

```markdown
- [x] Zweiten Übersetzungsweg mit `general/translation-llm` als eigene
      Rezeptidentität neben `general/nmt` bereitstellen.
- ⚠ Welche Variante die Grundlage des manuellen Reviews wird, ist bis zum
  Vergleich beider Fassungen offen.
```

Under "Aktuelle Priorität", replace item 1 with:

```markdown
1. Den vorbereiteten Translation-LLM-Lauf nach Kostenanzeige und
   ausdrücklicher Freigabe ausführen und beide Fassungen vergleichen.
```

- [ ] **Step 5: Delete the stale view directory**

```bash
rm -rf .artifacts/views/e3c-de
```

This directory is non-canonical, git-ignored, and rebuilt by `materialize translations e3c --variant nmt` in Task 11.

- [ ] **Step 6: Run the documentation contract tests**

```bash
uv run pytest tests/contracts -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add datasets/e3c-de/translations/README.md docs/project-checklist.md
git commit -m "docs: document both E3C translation variants"
```

---

### Task 11: Rebuild the NMT view and run the paid Translation LLM translation

This task spends money and needs the operator. Do not run it unattended.

- [ ] **Step 1: Rebuild the NMT view under its new path**

```bash
uv run phentrieve-benchmark materialize translations e3c --variant nmt
```

Expected: `destination=…/.artifacts/views/e3c-de-nmt cases=30`. This contacts no provider and spends nothing.

- [ ] **Step 2: Confirm the NMT batch is still recognised**

```bash
uv run phentrieve-benchmark translate e3c --project-id PROJECT_ID --variant nmt
```

Answer **no** at the prompt. The point is the line before it: `cases=30` with `upper_bound=USD 1.190340`. If this command were to re-translate, the reuse chain is broken — stop and fix that before spending anything.

- [ ] **Step 3: Preview the Translation LLM cost**

```bash
uv run phentrieve-benchmark translate e3c --project-id PROJECT_ID --variant tllm
```

Expected preview: `variant=tllm model=general/translation-llm cases=30 input_characters=59517 upper_bound=USD 1.368891`. Answering no exits before the Google client is constructed.

- [ ] **Step 4: Authorize the run**

Requires an enabled Cloud Translation API, billing, and Application Default Credentials. Answer yes. Expected output reports `translated=30` with `reused=0`, plus however many cases failed an automatic check.

- [ ] **Step 5: Verify both views exist side by side**

```bash
ls .artifacts/views/e3c-de-nmt .artifacts/views/e3c-de-tllm
```

Expected: identical filenames in both directories, 30 cases each.

- [ ] **Step 6: Check the pinned expansion factor against reality**

```bash
uv run python -c "
import csv
rows = list(csv.DictReader(open('.artifacts/views/e3c-de-tllm/index.csv', encoding='utf-8')))
i = sum(int(r['input_codepoints']) for r in rows)
o = sum(int(r['output_codepoints']) for r in rows)
print('cases', len(rows), 'ratio %.4f' % (o / i), 'worst %.4f' % max(int(r['output_codepoints']) / int(r['input_codepoints']) for r in rows))
"
```

If the worst observed ratio exceeds the pinned 1.30, the estimate was not an upper bound. Record that in the README rather than silently editing the recipe — the recipe hash is part of the published identity of this run.

- [ ] **Step 7: Report the comparison inputs**

Report to the user: how many TLLM cases reached `ready_for_review` versus `automatic_check_failed`, which check codes failed, and how that compares with the NMT run. Do not judge translation quality — that is the bilingual review's job.

---

## Verification

Before declaring the plan complete:

```bash
uv run pytest -q
```

Expected: all tests pass, skip count unchanged from the start of the plan. Report the actual numbers, not "tests pass".

Confirm all four of these:

- `git diff HEAD~N -- datasets/e3c-de/translation.yaml` is empty for the whole plan;
- `test_e3c_google_nmt_recipe_hash_is_frozen` passes with `abb8542f…`;
- `translate e3c --variant nmt` still reports 30 reusable cases and spends nothing;
- no new field appeared on `TranslationRecord`.

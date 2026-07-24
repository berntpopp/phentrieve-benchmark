# E3C Google NMT Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare a resumable, explicitly authorized Google NMT translation stage for the 30 selected E3C L1 reports without making a paid request during implementation or CI.

**Architecture:** Keep translation contracts, pricing, provider access, deterministic checks, and orchestration in separate modules. Source and German text are stored as independent content-addressed artifacts; a text-free manifest links them to the existing normalization and selection manifests. The Google client is injected behind a protocol so every automated test remains offline.

**Tech Stack:** Python 3.11+, Pydantic 2, Typer, Google Cloud Translation v3 client, Lingua language detection, pytest, Ruff, mypy, existing canonical JSON and artifact-store utilities.

---

## File map

- `src/phentrieve_benchmark/models/translation.py`: immutable translation attempt, record, check, and manifest contracts.
- `src/phentrieve_benchmark/translation/pricing.py`: exact character-based Google NMT cost calculation.
- `src/phentrieve_benchmark/translation/google_nmt.py`: injected provider protocol and production Advanced-v3 adapter.
- `src/phentrieve_benchmark/translation/checks.py`: deterministic response and translation checks.
- `src/phentrieve_benchmark/translation/e3c.py`: joins selected cases to normalized documents and runs/resumes translations.
- `src/phentrieve_benchmark/pipeline/translate.py`: resolves existing stage outputs, authorizes cost, records provenance, and publishes state.
- `src/phentrieve_benchmark/cli.py`: `translate e3c` command.
- `datasets/e3c-de/translation.yaml`: pinned provider, model, target, region, and pricing snapshot.
- `datasets/e3c-de/translations/README.md`: operational documentation and artifact boundary.
- `datasets/e3c-de/translations/e3c-de-feasibility-30-google-nmt-v1.json`: generated text-free manifest, added only after an authorized real run.
- Corresponding unit, integration, CLI, and contract tests under `tests/`.

### Task 1: Translation contracts

**Files:**

- Create: `src/phentrieve_benchmark/models/translation.py`
- Modify: `src/phentrieve_benchmark/models/__init__.py`
- Create: `tests/unit/models/test_translation.py`

- [ ] **Step 1: Write failing model tests**

```python
from decimal import Decimal

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.translation import (
    TranslationCheck,
    TranslationManifest,
    TranslationRecord,
    TranslationStatus,
)


def test_ready_record_keeps_text_out_of_metadata() -> None:
    record = TranslationRecord(
        translation_id="e3c-google-nmt-EN101318-r1",
        selection_id="e3c-de-feasibility-30-v1",
        source_case_id="EN101318",
        source_language="en",
        target_language="de",
        source_sha256="a" * 64,
        translation_sha256="b" * 64,
        provider="google-cloud-translation",
        api_version="v3",
        model="general/nmt",
        project_id="benchmark-project",
        location="global",
        created_at="2026-07-24T12:00:00Z",
        input_codepoints=601,
        output_codepoints=640,
        price_per_million_input_characters=Decimal("20"),
        estimated_max_cost=Decimal("0.01202"),
        previous_translation_id=None,
        status=TranslationStatus.READY_FOR_REVIEW,
        checks=(TranslationCheck(code="target_language_de", passed=True),),
    )

    payload = record.model_dump(mode="json")
    assert "text" not in payload
    assert payload["estimated_max_cost"] == "0.01202"


def test_ready_record_rejects_failed_check() -> None:
    values = {
        **record_values(),
        "status": TranslationStatus.READY_FOR_REVIEW,
        "checks": (TranslationCheck(code="target_language_de", passed=False),),
    }
    with pytest.raises(ValidationError, match="ready_for_review"):
        TranslationRecord(**values)


def test_manifest_requires_one_record_per_case() -> None:
    record = TranslationRecord(**record_values())
    with pytest.raises(ValidationError, match="duplicate"):
        TranslationManifest(
            selection_id="e3c-de-feasibility-30-v1",
            selection_sha256="c" * 64,
            records=(record, record),
        )
```

Add this local fixture in the same test file:

```python
def record_values() -> dict[str, object]:
    return {
        "translation_id": "e3c-google-nmt-EN101318-r1",
        "selection_id": "e3c-de-feasibility-30-v1",
        "source_case_id": "EN101318",
        "source_language": "en",
        "target_language": "de",
        "source_sha256": "a" * 64,
        "translation_sha256": "b" * 64,
        "provider": "google-cloud-translation",
        "api_version": "v3",
        "model": "general/nmt",
        "project_id": "benchmark-project",
        "location": "global",
        "created_at": "2026-07-24T12:00:00Z",
        "input_codepoints": 601,
        "output_codepoints": 640,
        "price_per_million_input_characters": Decimal("20"),
        "estimated_max_cost": Decimal("0.01202"),
        "previous_translation_id": None,
        "status": TranslationStatus.TRANSLATED,
        "checks": (),
    }
```

- [ ] **Step 2: Verify the tests fail**

Run:

```powershell
uv run pytest tests/unit/models/test_translation.py -v
```

Expected: collection fails because `models.translation` does not exist.

- [ ] **Step 3: Implement strict immutable contracts**

Define:

```python
class TranslationStatus(StrEnum):
    TRANSLATED = "translated"
    AUTOMATIC_CHECK_FAILED = "automatic_check_failed"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"


class TranslationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    code: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    passed: bool
    detail: str | None = None


class TranslationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    translation_id: str = Field(min_length=1)
    selection_id: str = Field(min_length=1)
    source_case_id: str = Field(min_length=1)
    source_language: Literal["en", "fr", "es"]
    target_language: Literal["de"]
    source_sha256: Sha256Hex
    translation_sha256: Sha256Hex
    provider: Literal["google-cloud-translation"]
    api_version: Literal["v3"]
    model: Literal["general/nmt"]
    project_id: str = Field(min_length=1)
    location: str = Field(min_length=1)
    created_at: datetime
    input_codepoints: int = Field(gt=0)
    output_codepoints: int = Field(gt=0)
    price_per_million_input_characters: Decimal
    estimated_max_cost: Decimal
    previous_translation_id: str | None = None
    status: TranslationStatus
    checks: tuple[TranslationCheck, ...]
```

Add validators that serialize money as plain decimal strings, require failed
checks for `automatic_check_failed`, forbid failed checks for
`ready_for_review`, and require unique check codes. Define
`TranslationManifest` with schema version, selection identity, provider
configuration identity, records, total counts, and canonical byte/hash
methods. Require unique case IDs and translation IDs.

- [ ] **Step 4: Run model tests and static checks**

```powershell
uv run pytest tests/unit/models/test_translation.py -v
uv run ruff check src/phentrieve_benchmark/models tests/unit/models
uv run mypy
```

Expected: all commands pass.

- [ ] **Step 5: Commit**

```powershell
git add src/phentrieve_benchmark/models tests/unit/models/test_translation.py
git commit -m "feat: define E3C translation contracts"
```

### Task 2: Pinned pricing and exact estimate

**Files:**

- Create: `datasets/e3c-de/translation.yaml`
- Create: `src/phentrieve_benchmark/translation/__init__.py`
- Create: `src/phentrieve_benchmark/translation/pricing.py`
- Create: `tests/unit/translation/test_pricing.py`
- Modify: `tests/contracts/test_dataset_recipes.py`

- [ ] **Step 1: Add failing pricing tests**

```python
from decimal import Decimal

from phentrieve_benchmark.translation.pricing import (
    GoogleNmtPricing,
    estimate_google_nmt,
)


def test_estimate_uses_input_codepoints_only() -> None:
    pricing = GoogleNmtPricing(
        currency="USD",
        price_per_million_input_characters=Decimal("20"),
        pricing_snapshot_id="google-cloud-translation-2026-07-24",
    )
    estimate = estimate_google_nmt(59_517, pricing)

    assert estimate.estimated_cost == Decimal("1.19034")
    assert estimate.upper_bound == Decimal("1.19034")


def test_zero_or_negative_input_is_rejected() -> None:
    pricing = GoogleNmtPricing(
        currency="USD",
        price_per_million_input_characters=Decimal("20"),
        pricing_snapshot_id="google-cloud-translation-2026-07-24",
    )
    with pytest.raises(ValueError, match="positive"):
        estimate_google_nmt(0, pricing)
```

- [ ] **Step 2: Verify failure**

```powershell
uv run pytest tests/unit/translation/test_pricing.py -v
```

Expected: import fails because the pricing module is absent.

- [ ] **Step 3: Add the pinned configuration**

```yaml
schema_version: e3c-translation-recipe/v1
translation_id: e3c-de-feasibility-30-google-nmt-v1
selection_id: e3c-de-feasibility-30-v1
provider: google-cloud-translation
api_version: v3
model: general/nmt
location: global
target_language: de
pricing:
  currency: USD
  price_per_million_input_characters: "20"
  pricing_snapshot_id: google-cloud-translation-2026-07-24
```

Extend the dataset recipe contract test to parse this file strictly and assert
the exact provider/model/price values.

- [ ] **Step 4: Implement exact Decimal arithmetic**

```python
_MILLION = Decimal(1_000_000)


def estimate_google_nmt(
    input_codepoints: int, pricing: GoogleNmtPricing
) -> CostEstimate:
    if input_codepoints <= 0:
        raise ValueError("input_codepoints must be positive")
    cost = (
        Decimal(input_codepoints)
        * pricing.price_per_million_input_characters
        / _MILLION
    )
    return CostEstimate(
        currency=pricing.currency,
        estimated_cost=cost,
        upper_bound=cost,
        pricing_snapshot_id=pricing.pricing_snapshot_id,
    )
```

Load YAML monetary values as strings and explicitly construct `Decimal`;
reject floats and extra keys.

- [ ] **Step 5: Run tests**

```powershell
uv run pytest tests/unit/translation/test_pricing.py tests/contracts/test_dataset_recipes.py -v
uv run ruff check src/phentrieve_benchmark/translation tests/unit/translation
uv run mypy
```

Expected: all commands pass.

- [ ] **Step 6: Commit**

```powershell
git add datasets/e3c-de/translation.yaml src/phentrieve_benchmark/translation tests/unit/translation/test_pricing.py tests/contracts/test_dataset_recipes.py
git commit -m "feat: pin Google NMT translation pricing"
```

### Task 3: Provider boundary and automatic checks

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `src/phentrieve_benchmark/translation/google_nmt.py`
- Create: `src/phentrieve_benchmark/translation/checks.py`
- Create: `tests/unit/translation/test_google_nmt.py`
- Create: `tests/unit/translation/test_checks.py`

- [ ] **Step 1: Add failing provider-boundary tests**

```python
def test_adapter_sends_explicit_languages_and_model() -> None:
    client = FakeTranslationServiceClient("Der Patient hatte Fieber.")
    adapter = GoogleNmtAdapter(
        client=client,
        project_id="benchmark-project",
        location="global",
    )

    result = adapter.translate(
        "The patient had fever.",
        source_language="en",
        target_language="de",
    )

    assert result.text == "Der Patient hatte Fieber."
    assert client.request == {
        "contents": ["The patient had fever."],
        "parent": "projects/benchmark-project/locations/global",
        "source_language_code": "en",
        "target_language_code": "de",
        "mime_type": "text/plain",
        "model": (
            "projects/benchmark-project/locations/global/models/general/nmt"
        ),
    }


@pytest.mark.parametrize("response", ["", "   "])
def test_adapter_rejects_empty_provider_text(response: str) -> None:
    adapter = adapter_with_response(response)
    with pytest.raises(ProviderResponseError, match="empty"):
        adapter.translate("fever", source_language="en", target_language="de")
```

The fake must implement only `translate_text(request=...)` and retain the
request dictionary.

- [ ] **Step 2: Add failing deterministic-check tests**

```python
def test_checks_flag_missing_number_and_unit() -> None:
    checks = check_translation(
        source_text="Temperature was 39 °C.",
        translated_text="Der Patient hatte Fieber.",
        detected_language="de",
    )
    by_code = {item.code: item for item in checks}

    assert not by_code["numbers_preserved"].passed
    assert not by_code["units_preserved"].passed
    assert by_code["target_language_de"].passed


def test_checks_flag_unchanged_source() -> None:
    checks = check_translation(
        source_text="The patient had fever.",
        translated_text="The patient had fever.",
        detected_language="en",
    )
    assert not {item.code: item for item in checks}["source_changed"].passed
```

- [ ] **Step 3: Verify both test files fail**

```powershell
uv run pytest tests/unit/translation/test_google_nmt.py tests/unit/translation/test_checks.py -v
```

Expected: imports fail because both modules are absent.

- [ ] **Step 4: Add production dependencies**

```powershell
uv add "google-cloud-translate>=3,<4" "lingua-language-detector>=2,<3"
```

Expected: `pyproject.toml` and `uv.lock` contain both runtime dependencies.

- [ ] **Step 5: Implement the injected provider**

Define a `TranslationProvider` protocol:

```python
class TranslationProvider(Protocol):
    def translate(
        self,
        text: str,
        *,
        source_language: Literal["en", "fr", "es"],
        target_language: Literal["de"],
    ) -> ProviderTranslation: ...
```

`GoogleNmtAdapter` accepts a v3 `TranslationServiceClient`, project ID, and
location. It builds the exact request asserted above, requires exactly one
translation response, canonicalizes returned text with
`canonical_text_bytes`, and rejects empty or whitespace-only output. The
default client is created only by an explicit factory function, so importing
the module never authenticates or contacts Google.

- [ ] **Step 6: Implement deterministic checks**

Use regular expressions to extract normalized number tokens, `%`, and the
finite unit vocabulary `mg`, `g`, `kg`, `ml`, `l`, `mm`, `cm`, `m`, `°c`,
`mmhg`, `bpm`, and `hz`. Compare source and target multisets. Add checks for
non-empty output, changed source, a target/source length ratio between 0.35
and 3.0, and German detection. Build one shared Lingua detector restricted to
German, English, French, and Spanish; pass the detected ISO code into the
pure `check_translation` function.

- [ ] **Step 7: Run tests and static checks**

```powershell
uv run pytest tests/unit/translation/test_google_nmt.py tests/unit/translation/test_checks.py -v
uv run ruff check src/phentrieve_benchmark/translation tests/unit/translation
uv run mypy
```

Expected: all commands pass without network access.

- [ ] **Step 8: Commit**

```powershell
git add pyproject.toml uv.lock src/phentrieve_benchmark/translation tests/unit/translation
git commit -m "feat: add offline-testable Google NMT adapter"
```

### Task 4: E3C translation runner and resumption

**Files:**

- Create: `src/phentrieve_benchmark/translation/e3c.py`
- Create: `tests/unit/translation/test_e3c_runner.py`
- Add fixture helpers: `tests/fixtures/e3c.py`

- [ ] **Step 1: Write a failing selected-document join test**

```python
def test_runner_translates_only_selected_cases() -> None:
    documents = (
        document("EN101318", "en", "The patient had fever."),
        document("EN999999", "en", "This case is not selected."),
    )
    provider = RecordingProvider({"EN101318": "Der Patient hatte Fieber."})

    result = translate_selected_e3c(
        selection=selection(("EN101318", "en")),
        documents=documents,
        provider=provider,
        store=ArtifactStore(tmp_path / "objects"),
        recipe=translation_recipe(),
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
    )

    assert provider.calls == [("The patient had fever.", "en", "de")]
    assert [record.source_case_id for record in result.records] == ["EN101318"]
```

- [ ] **Step 2: Write failing integrity and resumption tests**

```python
def test_runner_rejects_selection_document_hash_mismatch() -> None:
    with pytest.raises(ValueError, match="document hash"):
        translate_selected_e3c(
            selection=selection_with_hash("a" * 64),
            documents=(document("EN101318", "en", "Different text"),),
            provider=FailIfCalledProvider(),
            store=store,
            recipe=translation_recipe(),
            created_at=created_at,
        )


def test_runner_reuses_compatible_successful_revision() -> None:
    result = translate_selected_e3c(
        selection=selection(("EN101318", "en")),
        documents=(document("EN101318", "en", "The patient had fever."),),
        provider=FailIfCalledProvider(),
        store=store,
        recipe=translation_recipe(),
        created_at=created_at,
        previous_manifest=manifest_with_ready_record(),
    )
    assert result.reused_case_ids == ("EN101318",)
```

- [ ] **Step 3: Verify tests fail**

```powershell
uv run pytest tests/unit/translation/test_e3c_runner.py -v
```

Expected: import fails because the runner is absent.

- [ ] **Step 4: Implement the runner**

Build indices by `(source_case_id, language)`, require exact selection hash
matches, and sort work by `(language, source_case_id)`. For each new result:

```python
source_sha256 = store.put_bytes(canonical_text_bytes(document.text))
provider_result = provider.translate(
    document.text,
    source_language=document.language,
    target_language="de",
)
translation_sha256 = store.put_bytes(
    canonical_text_bytes(provider_result.text)
)
checks = run_automatic_checks(document.text, provider_result.text)
status = (
    TranslationStatus.READY_FOR_REVIEW
    if all(check.passed for check in checks)
    else TranslationStatus.AUTOMATIC_CHECK_FAILED
)
```

Reuse only records whose selection ID, source hash, source/target language,
provider, API version, model, project ID, and location match. Return a result
containing records plus sorted translated, failed, and reused case IDs.
Never catch provider exceptions as successful records.

- [ ] **Step 5: Run runner tests**

```powershell
uv run pytest tests/unit/translation/test_e3c_runner.py -v
uv run ruff check src/phentrieve_benchmark/translation/e3c.py tests/unit/translation/test_e3c_runner.py
uv run mypy
```

Expected: all commands pass.

- [ ] **Step 6: Commit**

```powershell
git add src/phentrieve_benchmark/translation/e3c.py tests/fixtures/e3c.py tests/unit/translation/test_e3c_runner.py
git commit -m "feat: translate and resume selected E3C cases"
```

### Task 5: Pipeline authorization, state, and provenance

**Files:**

- Modify: `src/phentrieve_benchmark/models/manifest.py`
- Modify: `src/phentrieve_benchmark/models/pipeline.py`
- Create: `src/phentrieve_benchmark/pipeline/translate.py`
- Create: `tests/unit/pipeline/test_translate.py`
- Create: `tests/integration/test_translate_pipeline.py`

- [ ] **Step 1: Write a failing authorization test**

```python
def test_pipeline_computes_cost_before_constructing_provider() -> None:
    confirmations: list[PaidRunRequest] = []
    providers: list[object] = []

    result = translate_e3c(
        context=context_with_selected_documents(tmp_path),
        project_id="benchmark-project",
        authorize=lambda request: confirmations.append(request) or False,
        provider_factory=lambda: providers.append(object()) or object(),
    )

    assert result.authorized is False
    assert confirmations[0].case_count == 30
    assert confirmations[0].estimate.upper_bound == Decimal("1.19034")
    assert providers == []
```

- [ ] **Step 2: Write a failing offline integration test**

```python
def test_translation_pipeline_publishes_text_free_manifest(tmp_path: Path) -> None:
    result = translate_e3c(
        context=prepared_e3c_context(tmp_path),
        project_id="benchmark-project",
        authorize=lambda _request: True,
        provider_factory=lambda: FixtureProvider(),
    )
    manifest_bytes = result.context.store.read_bytes(result.subject_sha256)

    assert b"The patient" not in manifest_bytes
    assert b"Der Patient" not in manifest_bytes
    assert result.translated_count == 30
```

- [ ] **Step 3: Verify tests fail**

```powershell
uv run pytest tests/unit/pipeline/test_translate.py tests/integration/test_translate_pipeline.py -v
```

Expected: import fails because `pipeline.translate` is absent.

- [ ] **Step 4: Extend pipeline enums**

Add `TRANSLATE` to the run-stage type and
`TRANSLATION_MANIFEST = "translation_manifest"` to
`ProvenanceSubjectRole`. Update their existing contract tests with the new
allowed values.

- [ ] **Step 5: Implement pipeline orchestration**

The service must:

1. resolve and integrity-check the acquisition, normalization, and selection
   stage pointers;
2. load the selected 30 normalized `Document` objects;
3. sum `len(document.text)` and build a `PaidRunRequest`;
4. return an unauthorized result without constructing a provider if approval
   is denied;
5. call the E3C runner after authorization;
6. publish the canonical text-free manifest and a `RunManifest`;
7. publish a provenance link with role `translation_manifest`; and
8. store a reusable stage pointer keyed by selection hash, recipe hash,
   project ID, location, model, and code hash.

Do not include credentials, access tokens, original text, or German text in
state pointers, manifests, provenance, or exceptions.

- [ ] **Step 6: Run pipeline tests**

```powershell
uv run pytest tests/unit/pipeline/test_translate.py tests/integration/test_translate_pipeline.py tests/contracts/test_pipeline_manifests.py -v
uv run ruff check src/phentrieve_benchmark/pipeline src/phentrieve_benchmark/models tests/unit/pipeline tests/integration
uv run mypy
```

Expected: all commands pass.

- [ ] **Step 7: Commit**

```powershell
git add src/phentrieve_benchmark/models src/phentrieve_benchmark/pipeline tests/unit/pipeline tests/integration tests/contracts/test_pipeline_manifests.py
git commit -m "feat: orchestrate authorized E3C translation"
```

### Task 6: CLI and operator documentation

**Files:**

- Modify: `src/phentrieve_benchmark/cli.py`
- Modify: `tests/unit/test_cli_pipeline.py`
- Create: `datasets/e3c-de/translations/README.md`
- Modify: `datasets/e3c-de/README.md`
- Modify: `docs/project-checklist.md`
- Modify: `tests/contracts/test_dataset_documentation.py`

- [ ] **Step 1: Write failing CLI tests**

```python
def test_translate_command_requires_explicit_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "_pipeline_context", lambda *_: object())
    monkeypatch.setattr(
        cli,
        "estimate_e3c_translation",
        lambda *_args, **_kwargs: estimate_result("1.19034"),
    )
    called: list[object] = []
    monkeypatch.setattr(
        cli,
        "translate_e3c",
        lambda *_args, **_kwargs: called.append(object()),
    )

    invocation = CliRunner().invoke(
        cli.app,
        ["translate", "e3c", "--project-id", "benchmark-project"],
        input="n\n",
    )

    assert invocation.exit_code == 1
    assert "USD 1.19034" in invocation.stdout
    assert called == []
```

Add a positive test entering `y`, asserting one delegated service call, plus a
help test asserting that `translate` is exposed. Mock the provider factory so
the test cannot authenticate or access the network.

- [ ] **Step 2: Verify CLI tests fail**

```powershell
uv run pytest tests/unit/test_cli_pipeline.py -v
```

Expected: the `translate` command is missing.

- [ ] **Step 3: Add the command**

Expose:

```text
phentrieve-benchmark translate e3c \
  --project-id PROJECT_ID \
  --location global \
  --dataset-root datasets \
  --artifact-root .artifacts
```

The command prints the 30-case character count and exact USD upper bound,
uses `typer.confirm`, and exits nonzero when declined. It constructs the
Google client only after confirmation. It emits subject hash plus translated,
failed, and reused counts; it never prints source or translated text.

- [ ] **Step 4: Document operation and update the checklist**

The translation README must state:

- prerequisites: Google project, enabled Cloud Translation API, billing, and
  Application Default Credentials;
- no API key is accepted as a CLI option;
- exact dry estimate and explicit confirmation behavior;
- `.artifacts/` contains the separate source and translation objects;
- the tracked manifest is text-free;
- regular CI uses only an injected fake provider;
- manual review is still required before `accepted`.

Mark only “translation phase specified and cost estimated” as complete in the
project checklist. Keep actual translation, review, HPO mapping, and single
terms open.

- [ ] **Step 5: Run CLI and documentation tests**

```powershell
uv run pytest tests/unit/test_cli_pipeline.py tests/contracts/test_dataset_documentation.py -v
uv run ruff check src/phentrieve_benchmark/cli.py tests/unit/test_cli_pipeline.py
uv run mypy
```

Expected: all commands pass.

- [ ] **Step 6: Commit**

```powershell
git add src/phentrieve_benchmark/cli.py tests/unit/test_cli_pipeline.py datasets/e3c-de docs/project-checklist.md tests/contracts/test_dataset_documentation.py
git commit -m "docs: expose E3C translation workflow"
```

### Task 7: Full offline verification and real-run handoff

**Files:**

- Modify only files needed to fix failures directly caused by Tasks 1–6.

- [ ] **Step 1: Prove the suite is offline**

Run with Google credentials deliberately unavailable:

```powershell
Remove-Item Env:GOOGLE_APPLICATION_CREDENTIALS -ErrorAction SilentlyContinue
uv run pytest
```

Expected: all tests pass; no test attempts authentication or network access.

- [ ] **Step 2: Run repository quality checks**

```powershell
uv run ruff check .
uv run mypy
git diff --check
git status --short
```

Expected: Ruff, mypy, and diff check pass. Status contains only intentional
implementation changes, or is clean after the task commits.

- [ ] **Step 3: Inspect the cost preview without authorizing Google**

```powershell
uv run phentrieve-benchmark translate e3c --project-id benchmark-project
```

Enter `n` at the confirmation prompt.

Expected: the command reports 30 cases, 59.517 input characters, and a
1.19034 USD upper bound; it exits without constructing the Google client and
without creating translation artifacts.

- [ ] **Step 4: Handle verification corrections**

If verification exposes a defect, return to the task that introduced it,
repeat that task's failing-test/fix/pass cycle, and include the correction in
that task's commit. Do not create an empty verification commit.

- [ ] **Step 5: Stop before the real paid run**

Report the verified preview and required Google setup to the user. Do not run
the affirmative command until the user explicitly authorizes the displayed
cost and the local environment has valid Application Default Credentials.

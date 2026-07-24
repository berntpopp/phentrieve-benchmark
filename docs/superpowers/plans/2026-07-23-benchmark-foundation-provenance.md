# Benchmark Foundation and Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the tested Python foundation for canonical data identities, immutable artifacts, provenance manifests, safe paid-operation authorization, structured events, and the CLI used by every later benchmark pipeline stage.

**Architecture:** A small `src/phentrieve_benchmark` package separates immutable domain models, canonical serialization, content-addressed storage, provenance, policies, and CLI concerns. Every persisted identity is derived from canonical bytes; execution manifests remain distinct from deterministic release manifests. Provider integrations and real datasets are deliberately deferred to later plans so this phase remains synthetic, offline, and independently testable.

**Tech Stack:** Python 3.11+, uv, Pydantic 2, Typer, RFC 8785 canonical JSON, pytest, Hypothesis, Ruff, mypy

---

## Delivery sequence

The approved design contains several independently testable subsystems. Implement
them in this order:

1. **This plan:** package foundation, contracts, identities, artifacts,
   provenance, safety policies, events, and CLI shell.
2. `2026-07-23-acquisition-normalization-selection.md`: pinned E3C and RAG-HPO
   acquisition, normalization, and deterministic E3C selection.
3. `2026-07-23-ontology-mapping-revision.md`: pinned HPO loading, UMLS-to-HPO
   mapping, and CSC/GSC identifier revision.
4. `2026-07-23-translation-review.md`: cost estimation, interactive paid calls,
   EN/FR/ES-to-German translation, automated review, and risk-based bilingual
   sampling.
5. `2026-07-23-annotation-curation-derivation.md`: German span adaptation,
   blinded review, adjudication, curation packets, and term derivation.
6. `2026-07-23-validation-release-adapter.md`: release eligibility, licensing
   gates, deterministic bundles, Phentrieve export, and synthetic end-to-end
   validation.

Each later plan consumes only public interfaces established here.

## Design coverage map

| Approved design area | Implementation plan |
|---|---|
| Repository boundaries and ignored artifacts | This plan, Tasks 1, 5, and 10 |
| Core document, annotation, and review identities | This plan, Tasks 2–4 |
| Canonical provenance, code identity, and run records | This plan, Tasks 2, 3, 6, 7, and 9 |
| Paid-call confirmation foundation | This plan, Task 8; provider wiring in translation-review plan |
| Acquisition and deterministic E3C selection | Acquisition-normalization-selection plan |
| UMLS-to-HPO mapping and CSC/GSC HPO revision | Ontology-mapping-revision plan |
| German translation and provisional 20% bilingual review | Translation-review plan |
| Blinded annotation, adjudication, curation, and term records | Annotation-curation-derivation plan |
| Release eligibility, licensing, deterministic packaging, and adapter | Validation-release-adapter plan |
| Synthetic complete pipeline | Validation-release-adapter plan after all preceding contracts exist |

## Planned file structure

```text
.
├── .github/workflows/ci.yml
├── .gitignore
├── README.md
├── pyproject.toml
├── scripts/check_repository_safety.py
├── src/phentrieve_benchmark/
│   ├── __init__.py
│   ├── cli.py
│   ├── artifacts/
│   │   ├── __init__.py
│   │   └── store.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── annotation.py
│   │   ├── document.py
│   │   ├── manifest.py
│   │   └── review.py
│   ├── policies/
│   │   ├── __init__.py
│   │   └── paid_operations.py
│   └── provenance/
│       ├── __init__.py
│       ├── canonical.py
│       ├── code_identity.py
│       ├── digests.py
│       └── events.py
└── tests/
    ├── contracts/
    │   ├── test_manifests.py
    │   └── test_repository_safety.py
    └── unit/
        ├── artifacts/test_store.py
        ├── models/test_contracts.py
        ├── policies/test_paid_operations.py
        └── provenance/
            ├── test_canonical.py
            ├── test_code_identity.py
            ├── test_digests.py
            └── test_events.py
```

### Task 1: Bootstrap the package and quality gates

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/phentrieve_benchmark/__init__.py`
- Create: `src/phentrieve_benchmark/cli.py`
- Create: `tests/unit/test_package.py`

- [ ] **Step 1: Write the failing package smoke test**

```python
from typer.testing import CliRunner

from phentrieve_benchmark import __version__
from phentrieve_benchmark.cli import app


def test_package_exposes_version_and_cli() -> None:
    result = CliRunner().invoke(app, ["version"])

    assert __version__ == "0.1.0"
    assert result.exit_code == 0
    assert result.stdout.strip() == "phentrieve-benchmark 0.1.0"
```

- [ ] **Step 2: Run the smoke test and verify the missing package failure**

Run: `uv run pytest tests/unit/test_package.py -v`

Expected: FAIL during collection with `ModuleNotFoundError:
phentrieve_benchmark`.

- [ ] **Step 3: Create the project metadata**

Create `pyproject.toml` with:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "phentrieve-benchmark"
version = "0.1.0"
description = "Reproducible benchmark data pipelines for Phentrieve"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2,<3",
  "rfc8785>=0.1,<1",
  "typer>=0.16,<1",
]

[project.scripts]
phentrieve-benchmark = "phentrieve_benchmark.cli:app"

[dependency-groups]
dev = [
  "hypothesis>=6,<7",
  "mypy>=1.15,<3",
  "pytest>=8,<10",
  "pytest-cov>=6,<8",
  "ruff>=0.11,<1",
]

[tool.hatch.build.targets.wheel]
packages = ["src/phentrieve_benchmark"]

[tool.pytest.ini_options]
addopts = "-ra --strict-config --strict-markers"
testpaths = ["tests"]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.11"
strict = true
packages = ["phentrieve_benchmark"]
```

Create `.gitignore` with:

```gitignore
.artifacts/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.venv/
__pycache__/
*.py[cod]
.coverage
htmlcov/
records/local/
releases/local/
configs/providers/local/
*.env
.env.*
!.env.example
```

Create `README.md` with:

```markdown
# Phentrieve Benchmark

Reproducible, provenance-preserving data pipelines for Phentrieve benchmark
datasets.

Real source text, translations, provider responses, curation packets, and
restricted release bundles remain in Git-ignored local artifact paths.
```

- [ ] **Step 4: Implement the minimal package and CLI**

Create `src/phentrieve_benchmark/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/phentrieve_benchmark/cli.py`:

```python
import typer

from phentrieve_benchmark import __version__

app = typer.Typer(no_args_is_help=True)


@app.command()
def version() -> None:
    """Print the installed package version."""
    typer.echo(f"phentrieve-benchmark {__version__}")
```

- [ ] **Step 5: Lock dependencies and run all initial checks**

Run:

```bash
uv lock
uv run pytest tests/unit/test_package.py -v
uv run ruff check .
uv run mypy
```

Expected: the test passes, Ruff reports `All checks passed!`, and mypy reports
`Success: no issues found`.

- [ ] **Step 6: Commit the package scaffold**

```bash
git add pyproject.toml uv.lock .gitignore README.md src tests/unit/test_package.py
git commit -m "chore: scaffold benchmark package"
```

### Task 2: Canonical text, JSON, and JSONL serialization

**Files:**
- Create: `src/phentrieve_benchmark/provenance/__init__.py`
- Create: `src/phentrieve_benchmark/provenance/canonical.py`
- Create: `tests/unit/provenance/test_canonical.py`

- [ ] **Step 1: Write failing canonicalization tests**

```python
import unicodedata

from phentrieve_benchmark.provenance.canonical import (
    canonical_json_bytes,
    canonical_jsonl_bytes,
    canonical_text_bytes,
)


def test_canonical_text_normalizes_unicode_and_line_endings() -> None:
    decomposed = unicodedata.normalize("NFD", "Größe\r\n")

    assert canonical_text_bytes(decomposed) == "Größe\n".encode()


def test_canonical_json_is_independent_of_mapping_order() -> None:
    left = canonical_json_bytes({"b": 2, "a": "Größe"})
    right = canonical_json_bytes({"a": "Gro\u0308ße", "b": 2})

    assert left == right


def test_jsonl_uses_stable_record_order_and_final_newline() -> None:
    value = canonical_jsonl_bytes(
        [{"document_id": "b", "value": 2}, {"document_id": "a", "value": 1}],
        identity_key="document_id",
    )

    assert value.splitlines() == [
        b'{"document_id":"a","value":1}',
        b'{"document_id":"b","value":2}',
    ]
    assert value.endswith(b"\n")
```

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run: `uv run pytest tests/unit/provenance/test_canonical.py -v`

Expected: FAIL during collection because
`phentrieve_benchmark.provenance.canonical` does not exist.

- [ ] **Step 3: Implement canonical serialization**

Create `src/phentrieve_benchmark/provenance/__init__.py` as an empty file.

Create `src/phentrieve_benchmark/provenance/canonical.py`:

```python
from collections.abc import Mapping, Sequence
from typing import Any
import unicodedata

import rfc8785


def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        return {
            unicodedata.normalize("NFC", str(key)): normalize_value(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        return [normalize_value(item) for item in value]
    return value


def canonical_text_bytes(text: str) -> bytes:
    normalized = unicodedata.normalize("NFC", text)
    return normalized.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_json_bytes(value: Any) -> bytes:
    return rfc8785.dumps(normalize_value(value))


def canonical_jsonl_bytes(
    records: Sequence[Mapping[str, Any]],
    *,
    identity_key: str,
) -> bytes:
    normalized = [normalize_value(record) for record in records]
    ordered = sorted(normalized, key=lambda record: str(record[identity_key]))
    return b"".join(canonical_json_bytes(record) + b"\n" for record in ordered)
```

- [ ] **Step 4: Run focused and property checks**

Run:

```bash
uv run pytest tests/unit/provenance/test_canonical.py -v
uv run ruff check src/phentrieve_benchmark/provenance tests/unit/provenance
uv run mypy
```

Expected: three tests pass and both static checks succeed.

- [ ] **Step 5: Commit canonical serialization**

```bash
git add src/phentrieve_benchmark/provenance tests/unit/provenance
git commit -m "feat: add canonical serialization"
```

### Task 3: Content and aggregate digests

**Files:**
- Create: `src/phentrieve_benchmark/provenance/digests.py`
- Create: `tests/unit/provenance/test_digests.py`

- [ ] **Step 1: Write failing digest tests**

```python
from phentrieve_benchmark.provenance.digests import (
    ComponentDigest,
    aggregate_sha256,
    sha256_bytes,
)


def test_sha256_bytes_uses_lowercase_hex() -> None:
    assert sha256_bytes(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )


def test_aggregate_hash_is_order_independent_but_role_sensitive() -> None:
    source = ComponentDigest(role="source", stable_id="case-1", sha256="a" * 64)
    gold = ComponentDigest(role="gold", stable_id="case-1", sha256="b" * 64)

    assert aggregate_sha256("document-set/v1", [source, gold]) == (
        aggregate_sha256("document-set/v1", [gold, source])
    )
    assert aggregate_sha256(
        "document-set/v1",
        [source.model_copy(update={"role": "input"}), gold],
    ) != aggregate_sha256("document-set/v1", [source, gold])
```

- [ ] **Step 2: Run the tests and verify the missing API failure**

Run: `uv run pytest tests/unit/provenance/test_digests.py -v`

Expected: FAIL during collection because `digests` does not exist.

- [ ] **Step 3: Implement digest contracts**

Create `src/phentrieve_benchmark/provenance/digests.py`:

```python
from hashlib import sha256
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes


Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ComponentDigest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: str = Field(min_length=1)
    stable_id: str = Field(min_length=1)
    sha256: Sha256Hex


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def aggregate_sha256(
    schema_version: str,
    components: list[ComponentDigest],
) -> str:
    ordered = sorted(
        components,
        key=lambda item: (item.role, item.stable_id, item.sha256),
    )
    payload = {
        "schema_version": schema_version,
        "components": [item.model_dump(mode="json") for item in ordered],
    }
    return sha256_bytes(canonical_json_bytes(payload))
```

- [ ] **Step 4: Run the digest tests and static checks**

Run:

```bash
uv run pytest tests/unit/provenance/test_digests.py -v
uv run ruff check src/phentrieve_benchmark/provenance tests/unit/provenance
uv run mypy
```

Expected: two digest tests pass and static checks succeed.

- [ ] **Step 5: Commit digest support**

```bash
git add src/phentrieve_benchmark/provenance/digests.py tests/unit/provenance/test_digests.py
git commit -m "feat: add semantic digest contracts"
```

### Task 4: Immutable document, annotation, and review models

**Files:**
- Create: `src/phentrieve_benchmark/models/__init__.py`
- Create: `src/phentrieve_benchmark/models/document.py`
- Create: `src/phentrieve_benchmark/models/annotation.py`
- Create: `src/phentrieve_benchmark/models/review.py`
- Create: `tests/unit/models/test_contracts.py`

- [ ] **Step 1: Write failing contract tests**

```python
import pytest

from phentrieve_benchmark.models.annotation import (
    Annotation,
    AnnotationSet,
    EvidenceSpan,
    validate_annotation_set,
)
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.review import (
    ManualReviewRequirement,
    ManualReviewStatus,
    ReviewKind,
    ReviewRecord,
)


def test_unicode_half_open_span_matches_document() -> None:
    document = Document.from_text(
        source_case_id="e3c-en-1",
        case_group_id="e3c-en-1",
        document_id="e3c-en-1-de",
        language="de",
        translation_status=TranslationStatus.TRANSLATED,
        text="Der Patient hat große Hände.",
    )
    start = document.text.index("große")
    annotation_set = AnnotationSet(
        annotation_set_id="ann-1",
        document_sha256=document.document_sha256,
        hpo_release="v2026-06-23",
        annotations=(
            Annotation(
                annotation_id="a-1",
                hpo_id="HP:0001176",
                evidence_spans=(
                    EvidenceSpan(start_char=start, end_char=start + 5, text_snippet="große"),
                ),
            ),
        ),
    )

    validate_annotation_set(document, annotation_set)


def test_span_mismatch_fails_closed() -> None:
    document = Document.from_text(
        source_case_id="case-1",
        case_group_id="case-1",
        document_id="case-1-de",
        language="de",
        translation_status=TranslationStatus.TRANSLATED,
        text="Keine Ataxie.",
    )
    annotation_set = AnnotationSet(
        annotation_set_id="ann-1",
        document_sha256=document.document_sha256,
        hpo_release="v2026-06-23",
        annotations=(
            Annotation(
                annotation_id="a-1",
                hpo_id="HP:0001251",
                evidence_spans=(EvidenceSpan(start_char=6, end_char=12, text_snippet="Ataxia"),),
            ),
        ),
    )

    with pytest.raises(ValueError, match="span text mismatch"):
        validate_annotation_set(document, annotation_set)


def test_non_selected_manual_review_is_not_an_acceptance() -> None:
    review = ReviewRecord(
        review_id="review-1",
        review_kind=ReviewKind.BILINGUAL,
        subject_sha256="a" * 64,
        review_policy_id="feasibility-risk-v1",
        manual_requirement=ManualReviewRequirement.NOT_SELECTED,
        manual_status=ManualReviewStatus.NOT_APPLICABLE,
        reviewer_role="not_selected",
    )

    assert not review.is_manual_acceptance


def test_non_selected_review_cannot_claim_manual_acceptance() -> None:
    with pytest.raises(ValueError, match="not_selected requires not_applicable"):
        ReviewRecord(
            review_id="review-1",
            review_kind=ReviewKind.BILINGUAL,
            subject_sha256="a" * 64,
            review_policy_id="feasibility-risk-v1",
            manual_requirement=ManualReviewRequirement.NOT_SELECTED,
            manual_status=ManualReviewStatus.ACCEPTED,
            reviewer_role="not_selected",
        )
```

- [ ] **Step 2: Run tests and verify missing model modules**

Run: `uv run pytest tests/unit/models/test_contracts.py -v`

Expected: FAIL during collection because the `models` package does not exist.

- [ ] **Step 3: Implement immutable documents**

Create `src/phentrieve_benchmark/models/__init__.py` as an empty file.

Create `src/phentrieve_benchmark/models/document.py`:

```python
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from phentrieve_benchmark.provenance.canonical import canonical_text_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class TranslationStatus(StrEnum):
    NATIVE = "native"
    TRANSLATED = "translated"


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_case_id: str = Field(min_length=1)
    case_group_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    language: str = Field(pattern=r"^[a-z]{2}$")
    translation_status: TranslationStatus
    text: str = Field(min_length=1)
    document_sha256: Sha256Hex

    @classmethod
    def from_text(
        cls,
        *,
        source_case_id: str,
        case_group_id: str,
        document_id: str,
        language: str,
        translation_status: TranslationStatus,
        text: str,
    ) -> "Document":
        canonical_bytes = canonical_text_bytes(text)
        return cls(
            source_case_id=source_case_id,
            case_group_id=case_group_id,
            document_id=document_id,
            language=language,
            translation_status=translation_status,
            text=canonical_bytes.decode("utf-8"),
            document_sha256=sha256_bytes(canonical_bytes),
        )
```

- [ ] **Step 4: Implement annotation contracts and cross-artifact validation**

Create `src/phentrieve_benchmark/models/annotation.py`:

```python
from pydantic import BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.provenance.digests import Sha256Hex


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    text_snippet: str = Field(min_length=1)

    @model_validator(mode="after")
    def end_follows_start(self) -> "EvidenceSpan":
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        return self


class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    annotation_id: str = Field(min_length=1)
    hpo_id: str = Field(pattern=r"^HP:\d{7}$")
    assertion: str = "present"
    experiencer: str = "patient"
    temporality: str = "current"
    evidence_spans: tuple[EvidenceSpan, ...]


class AnnotationSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    annotation_set_id: str = Field(min_length=1)
    document_sha256: Sha256Hex
    hpo_release: str = Field(pattern=r"^v\d{4}-\d{2}-\d{2}$")
    annotations: tuple[Annotation, ...]


def validate_annotation_set(
    document: Document,
    annotation_set: AnnotationSet,
) -> None:
    if annotation_set.document_sha256 != document.document_sha256:
        raise ValueError("annotation set references a different document hash")
    for annotation in annotation_set.annotations:
        for span in annotation.evidence_spans:
            actual = document.text[span.start_char : span.end_char]
            if actual != span.text_snippet:
                raise ValueError(
                    f"span text mismatch for {annotation.annotation_id}: "
                    f"{actual!r} != {span.text_snippet!r}"
                )
```

- [ ] **Step 5: Implement separate review states**

Create `src/phentrieve_benchmark/models/review.py`:

```python
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.provenance.digests import Sha256Hex


class ReviewKind(StrEnum):
    AUTOMATED = "automated"
    BILINGUAL = "bilingual"
    ANNOTATION = "annotation"
    ADJUDICATION = "adjudication"


class ManualReviewRequirement(StrEnum):
    REQUIRED = "required"
    NOT_SELECTED = "not_selected"


class ManualReviewStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"
    NOT_APPLICABLE = "not_applicable"


class ReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str = Field(min_length=1)
    review_kind: ReviewKind
    subject_sha256: Sha256Hex
    review_policy_id: str = Field(min_length=1)
    manual_requirement: ManualReviewRequirement
    manual_status: ManualReviewStatus
    reviewer_role: str = Field(min_length=1)

    @model_validator(mode="after")
    def manual_state_is_consistent(self) -> "ReviewRecord":
        if (
            self.manual_requirement is ManualReviewRequirement.NOT_SELECTED
            and self.manual_status is not ManualReviewStatus.NOT_APPLICABLE
        ):
            raise ValueError("not_selected requires not_applicable status")
        if (
            self.manual_requirement is ManualReviewRequirement.REQUIRED
            and self.manual_status is ManualReviewStatus.NOT_APPLICABLE
        ):
            raise ValueError("required review cannot be not_applicable")
        return self

    @property
    def is_manual_acceptance(self) -> bool:
        return (
            self.manual_requirement is ManualReviewRequirement.REQUIRED
            and self.manual_status is ManualReviewStatus.ACCEPTED
        )
```

- [ ] **Step 6: Run contract tests and static checks**

Run:

```bash
uv run pytest tests/unit/models/test_contracts.py -v
uv run ruff check src/phentrieve_benchmark/models tests/unit/models
uv run mypy
```

Expected: three contract tests pass and static checks succeed.

- [ ] **Step 7: Commit the core contracts**

```bash
git add src/phentrieve_benchmark/models tests/unit/models
git commit -m "feat: add immutable benchmark contracts"
```

### Task 5: Content-addressed artifact storage

**Files:**
- Create: `src/phentrieve_benchmark/artifacts/__init__.py`
- Create: `src/phentrieve_benchmark/artifacts/store.py`
- Create: `tests/unit/artifacts/test_store.py`

- [ ] **Step 1: Write failing artifact-store tests**

```python
from pathlib import Path

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactCorruptionError, ArtifactStore
from phentrieve_benchmark.provenance.digests import sha256_bytes


def test_put_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    digest = store.put_bytes(b"clinical fixture")

    assert digest == sha256_bytes(b"clinical fixture")
    assert store.read_bytes(digest) == b"clinical fixture"
    assert store.put_bytes(b"clinical fixture") == digest


def test_existing_corrupt_artifact_fails_closed(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    digest = sha256_bytes(b"expected")
    path = store.path_for(digest)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"corrupt")

    with pytest.raises(ArtifactCorruptionError):
        store.put_bytes(b"expected")
```

- [ ] **Step 2: Run tests and verify the missing store failure**

Run: `uv run pytest tests/unit/artifacts/test_store.py -v`

Expected: FAIL during collection because the `artifacts` package does not exist.

- [ ] **Step 3: Implement atomic content-addressed writes**

Create `src/phentrieve_benchmark/artifacts/__init__.py` as an empty file.

Create `src/phentrieve_benchmark/artifacts/store.py`:

```python
from pathlib import Path
import os
import tempfile

from phentrieve_benchmark.provenance.digests import sha256_bytes


class ArtifactCorruptionError(RuntimeError):
    pass


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, digest: str) -> Path:
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("artifact digest must be 64 lowercase hexadecimal characters")
        return self.root / "sha256" / digest[:2] / digest

    def put_bytes(self, value: bytes) -> str:
        digest = sha256_bytes(value)
        destination = self.path_for(digest)
        if destination.exists():
            if sha256_bytes(destination.read_bytes()) != digest:
                raise ArtifactCorruptionError(f"artifact {digest} is corrupt")
            return digest

        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{digest}.",
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return digest

    def read_bytes(self, digest: str) -> bytes:
        value = self.path_for(digest).read_bytes()
        if sha256_bytes(value) != digest:
            raise ArtifactCorruptionError(f"artifact {digest} is corrupt")
        return value
```

- [ ] **Step 4: Run storage tests and static checks**

Run:

```bash
uv run pytest tests/unit/artifacts/test_store.py -v
uv run ruff check src/phentrieve_benchmark/artifacts tests/unit/artifacts
uv run mypy
```

Expected: two tests pass and static checks succeed.

- [ ] **Step 5: Commit the artifact store**

```bash
git add src/phentrieve_benchmark/artifacts tests/unit/artifacts
git commit -m "feat: add content-addressed artifact store"
```

### Task 6: Exact code identity v2 for clean and dirty worktrees

**Files:**
- Create: `src/phentrieve_benchmark/provenance/code_identity.py`
- Create: `tests/unit/provenance/test_code_identity.py`

- [ ] **Step 1: Write failing worktree-identity tests**

```python
from pathlib import Path
import subprocess

from phentrieve_benchmark.provenance.code_identity import code_sha256


def git(repo: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True)


def test_dirty_and_untracked_sources_change_code_identity(tmp_path: Path) -> None:
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.org")
    git(tmp_path, "config", "user.name", "Test")
    source = tmp_path / "src" / "module.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "initial")
    clean = code_sha256(tmp_path)

    source.write_text("VALUE = 2\n", encoding="utf-8")
    dirty = code_sha256(tmp_path)
    (tmp_path / "new_config.yaml").write_text("enabled: true\n", encoding="utf-8")
    untracked = code_sha256(tmp_path)

    assert len({clean, dirty, untracked}) == 3


def test_ignored_artifacts_do_not_change_code_identity(tmp_path: Path) -> None:
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.org")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / ".gitignore").write_text(".artifacts/\n", encoding="utf-8")
    (tmp_path / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "initial")
    before = code_sha256(tmp_path)

    artifact = tmp_path / ".artifacts" / "sha256" / "ab" / ("a" * 64)
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"restricted data")

    assert code_sha256(tmp_path) == before
```

Also cover: a HEAD-only change; tracked deletion; deterministic ordering;
subdirectory resolution to the Git top-level; project-only ignore rules; raw
invalid UTF-8 Git path bytes and literal backslashes on POSIX; regular-file
executable mode; broken symlinks; unsupported special files; and gitlinks.
Platform-specific filesystem tests may skip when their primitives are
unavailable.

- [ ] **Step 2: Run tests and verify the missing identity function**

Run: `uv run pytest tests/unit/provenance/test_code_identity.py -v`

Expected: FAIL during collection because `code_identity` does not exist.

- [ ] **Step 3: Implement repository-state hashing**

Create `src/phentrieve_benchmark/provenance/code_identity.py` with
`_git(repo, *arguments)` using `subprocess.run(..., check=True,
capture_output=True).stdout`. Resolve `repo`, ascend to the nearest `.git`
file or directory, and validate that worktree before every identity operation;
do not parse newline-terminated Git root-path output. Read raw NUL-delimited paths
from `git ls-files -z --cached --others --exclude-per-directory=.gitignore`;
do not use `--exclude-standard`, `.git/info/exclude`, or global excludes.

Encode each raw Git path into an injective ASCII `path`: leave only ASCII
letters, digits, `-`, `.`, `_`, and `/` literal, and percent-encode `%`,
backslash, and every other byte. Sort by this final encoded path. Do not UTF-8
decode Git path bytes.
Parse `git ls-files --stage -z` and fail closed for gitlinks or duplicate index
entries. Use `lstat`: regular files bind their executable bit and a
descriptor-read SHA-256; symlinks bind raw link-target bytes; absent tracked
files are `deleted`/`missing` with the empty-byte SHA-256, while an untracked
path that vanishes fails closed. Reject all other file kinds. For regular
files, open without following symlinks and non-blocking on POSIX when possible;
derive the executable bit and digest from the same descriptor snapshot; compare
path and descriptor identity, kind, mode, size, mtime, and stable ctime where
available before and after reading; retry boundedly, then raise on detected
concurrent mutation.

Before Git enumeration, scan raw filesystem entries without following symlink
directories and skip `.git` metadata. Reject FIFOs, sockets, devices, and all
other unsupported kinds unless `git check-ignore -z -v --no-index` identifies
a non-negated winning pattern from an in-worktree `.gitignore`; never accept a
global exclude or `.git/info/exclude` as authorization to ignore a special
entry.

Hash canonical JSON with this exact payload shape:

```python
{
    "schema_version": "code-identity/v2",
    "head": head,
    "exclusion_policy": "repository-gitignore/v1",
    "path_encoding": "percent-encoded-git-path-bytes/v1",
    "entries": [
        {
            "path": encoded_path,
            "state": "present" | "deleted",
            "kind": "file" | "symlink" | "missing",
            "executable": bool,
            "sha256": lowercase_sha256,
        },
    ],
}
```

- [ ] **Step 4: Run worktree tests and static checks**

Run:

```bash
uv run pytest tests/unit/provenance/test_code_identity.py -v
uv run ruff check src/phentrieve_benchmark/provenance tests/unit/provenance
uv run mypy
```

Expected: all worktree-identity tests pass, with filesystem-specific cases
skipped only where the platform cannot provide the needed primitive.

- [ ] **Step 5: Commit code identity**

```bash
git add src/phentrieve_benchmark/provenance/code_identity.py tests/unit/provenance/test_code_identity.py
git commit -m "feat: fingerprint exact repository state"
```

### Task 7: Separate run, release, and linkage manifests

**Files:**
- Create: `src/phentrieve_benchmark/models/manifest.py`
- Create: `tests/contracts/test_manifests.py`

- [ ] **Step 1: Write failing manifest-separation tests**

```python
from datetime import UTC, datetime

from phentrieve_benchmark.models.manifest import (
    ProviderRunIdentity,
    ReleaseManifest,
    ReleaseRunLink,
    RunManifest,
    RunStatus,
    UsageMetrics,
)


def test_release_bytes_ignore_execution_identity() -> None:
    release = ReleaseManifest(
        dataset_id="synthetic",
        dataset_version="1.0.0",
        hpo_release="v2026-06-23",
        source_sha256="a" * 64,
        input_sha256="b" * 64,
        gold_sha256="c" * 64,
        document_ids_sha256="d" * 64,
        selection_id="synthetic-v1",
        licensing_identity="synthetic-license-v1",
        review_policy_id="synthetic-review-v1",
        bilingual_review_coverage=0.2,
        physician_review_coverage=0.1,
    )
    first = ReleaseRunLink(
        release_sha256=release.sha256(),
        run_manifest_sha256=("e" * 64,),
    )
    second = ReleaseRunLink(
        release_sha256=release.sha256(),
        run_manifest_sha256=("f" * 64,),
    )

    assert release.canonical_bytes() == release.canonical_bytes()
    assert first != second
    assert first.release_sha256 == second.release_sha256


def test_run_manifest_retains_volatile_execution_fields() -> None:
    run = RunManifest(
        run_id="run-1",
        stage="normalize",
        status=RunStatus.COMPLETE,
        started_at=datetime(2026, 7, 23, tzinfo=UTC),
        finished_at=datetime(2026, 7, 23, 0, 1, tzinfo=UTC),
        pipeline_commit="a" * 40,
        dirty_state=True,
        code_sha256="a" * 64,
        config_sha256="d" * 64,
        provider=ProviderRunIdentity(
            provider="openai",
            engine="responses",
            requested_model="gpt-5.6-terra",
            returned_model="gpt-5.6-terra-2026-07-21",
            endpoint_class="standard",
            processing_mode="synchronous",
        ),
        pricing_snapshot_id="openai-2026-07-23",
        usage=UsageMetrics(input_tokens=100, output_tokens=20, estimated_cost=0.01),
        input_sha256=("b" * 64,),
        output_sha256=("c" * 64,),
    )

    assert run.run_id == "run-1"
    assert run.started_at != run.finished_at
    assert run.provider is not None
    assert run.provider.returned_model == "gpt-5.6-terra-2026-07-21"
```

- [ ] **Step 2: Run tests and verify missing manifest contracts**

Run: `uv run pytest tests/contracts/test_manifests.py -v`

Expected: FAIL during collection because `models.manifest` does not exist.

- [ ] **Step 3: Implement manifest models and deterministic release bytes**

Create `src/phentrieve_benchmark/models/manifest.py`:

```python
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import (
    ComponentDigest,
    Sha256Hex,
    sha256_bytes,
)


class RunStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class ProviderRunIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1)
    engine: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    returned_model: str = Field(min_length=1)
    endpoint_class: str = Field(min_length=1)
    processing_mode: str = Field(min_length=1)


class UsageMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_characters: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0, ge=0)


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    status: RunStatus
    started_at: AwareDatetime
    finished_at: AwareDatetime | None
    pipeline_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    dirty_state: bool
    code_sha256: Sha256Hex
    config_sha256: Sha256Hex
    source: tuple[ComponentDigest, ...] = ()
    input_sha256: tuple[Sha256Hex, ...]
    output_sha256: tuple[Sha256Hex, ...]
    prompt_sha256: Sha256Hex | None = None
    provider: ProviderRunIdentity | None = None
    hpo_release: str | None = None
    selection_id: str | None = None
    pricing_snapshot_id: str | None = None
    usage: UsageMetrics = Field(default_factory=UsageMetrics)
    retry_count: int = Field(default=0, ge=0)
    error_codes: tuple[str, ...] = ()
    environment: tuple[ComponentDigest, ...] = ()

    @model_validator(mode="after")
    def completion_has_valid_time_range(self) -> "RunManifest":
        if self.status is RunStatus.COMPLETE and self.finished_at is None:
            raise ValueError("complete run requires finished_at")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        return self


class ReleaseManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "release-manifest/v1"
    dataset_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    hpo_release: str = Field(pattern=r"^v\d{4}-\d{2}-\d{2}$")
    source_sha256: Sha256Hex
    input_sha256: Sha256Hex
    gold_sha256: Sha256Hex
    document_ids_sha256: Sha256Hex
    selection_id: str = Field(min_length=1)
    licensing_identity: str = Field(min_length=1)
    review_policy_id: str = Field(min_length=1)
    bilingual_review_coverage: float = Field(ge=0, le=1)
    physician_review_coverage: float = Field(ge=0, le=1)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())


class ReleaseRunLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    release_sha256: Sha256Hex
    run_manifest_sha256: tuple[Sha256Hex, ...]
```

- [ ] **Step 4: Run manifest contracts and static checks**

Run:

```bash
uv run pytest tests/contracts/test_manifests.py -v
uv run ruff check src/phentrieve_benchmark/models tests/contracts
uv run mypy
```

Expected: two contract tests pass and static checks succeed.

- [ ] **Step 5: Commit manifest separation**

```bash
git add src/phentrieve_benchmark/models/manifest.py tests/contracts/test_manifests.py
git commit -m "feat: separate run and release manifests"
```

### Task 8: Fail-closed paid-operation authorization

**Files:**
- Create: `src/phentrieve_benchmark/policies/__init__.py`
- Create: `src/phentrieve_benchmark/policies/paid_operations.py`
- Create: `tests/unit/policies/test_paid_operations.py`

**Security contract amendment:** Python callers construct monetary fields with
finite, non-negative `Decimal` instances; JSON represents them as plain
decimal strings matching `-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?`; the validation
JSON Schema advertises only that string form. Values are normalized for display
without currency-specific rounding, so the displayed upper bound is never
understated. A signed zero is canonicalized to zero. Every prompt-displayed
identifier (`stage`, `provider`, `model`, and `pricing_snapshot_id`) is a
nonempty ASCII identifier composed only of letters, digits, and `._/@:+-`; this
rejects whitespace, controls, bidi characters, ANSI escapes, and prompt
delimiters. Currency is exactly three uppercase ASCII letters. Authorization
invokes `confirm` only when `interactive is True` and accepts only a literal
boolean `True` result. Adapters must convert their explicitly documented UI
input to that boolean before calling this function.

- [ ] **Step 1: Write failing authorization tests**

```python
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.policies.paid_operations import (
    CostEstimate,
    PaidRunRequest,
    authorize_paid_run,
)


def request(**updates: object) -> PaidRunRequest:
    values: dict[str, object] = {
        "stage": "translate",
        "provider": "google",
        "model": "general/nmt",
        "case_count": 30,
        "estimate": CostEstimate(
            currency="USD",
            estimated_cost=Decimal("2.83"),
            upper_bound=Decimal("3.00"),
            pricing_snapshot_id="google-2026-07-23",
        ),
    }
    values.update(updates)
    return PaidRunRequest(**values)


def test_non_interactive_paid_run_fails_without_prompting() -> None:
    prompts: list[str] = []

    assert not authorize_paid_run(
        request(),
        interactive=False,
        confirm=lambda message: prompts.append(message) or True,
    )
    assert prompts == []


@pytest.mark.parametrize("interactive", [False, 1, "false", object(), None])
def test_only_literal_boolean_true_can_prompt_for_paid_run(interactive: object) -> None:
    prompts: list[str] = []

    assert not authorize_paid_run(
        request(),
        interactive=interactive,
        confirm=lambda message: prompts.append(message) or True,
    )
    assert prompts == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("stage", "translate\nStart paid run?"),
        ("provider", "google\rStart paid run?"),
        ("model", "general/nmt\x1b[2J"),
        ("pricing_snapshot_id", "snapshot|Start paid run?"),
    ],
)
def test_prompt_identifiers_reject_control_and_deceptive_text(
    field: str, value: str
) -> None:
    estimate_values = request().estimate.model_dump()
    request_values = request().model_dump()
    if field == "pricing_snapshot_id":
        estimate_values[field] = value
        request_values["estimate"] = estimate_values
    else:
        request_values[field] = value

    with pytest.raises(ValidationError, match=field):
        PaidRunRequest(**request_values)


def test_estimate_json_uses_exact_decimal_strings() -> None:
    estimate = CostEstimate.model_validate_json(
        json.dumps(
            {
                "currency": "USD",
                "estimated_cost": "2.675",
                "upper_bound": "3.00",
                "pricing_snapshot_id": "google-2026-07-23",
            }
        )
    )

    assert estimate.estimated_cost == Decimal("2.675")
    assert estimate.upper_bound == Decimal("3")


def test_estimate_validation_schema_advertises_plain_decimal_strings() -> None:
    schema = CostEstimate.model_json_schema(mode="validation")

    for field in ("estimated_cost", "upper_bound"):
        money_schema = schema["properties"][field]
        assert money_schema["type"] == "string"
        assert money_schema["pattern"] == r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
        assert "anyOf" not in money_schema


def test_estimate_rejects_upper_bound_below_estimate() -> None:
    with pytest.raises(ValueError, match="upper_bound"):
        CostEstimate(
            currency="USD",
            estimated_cost=Decimal("2.83"),
            upper_bound=Decimal("2.00"),
            pricing_snapshot_id="google-2026-07-23",
        )
```

- [ ] **Step 2: Run tests and verify the missing policy module**

Run: `uv run pytest tests/unit/policies/test_paid_operations.py -v`

Expected: FAIL during collection because the `policies` package does not exist.

- [ ] **Step 3: Implement authorization without provider side effects**

Create `src/phentrieve_benchmark/policies/__init__.py` as the package marker.

Create `src/phentrieve_benchmark/policies/paid_operations.py`:

```python
import re
from collections.abc import Callable
from decimal import Decimal
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

_SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9._/@:+-]+", re.ASCII)
_DECIMAL_JSON = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", re.ASCII)


def _validate_safe_identifier(value: str) -> str:
    if _SAFE_IDENTIFIER.fullmatch(value) is None:
        raise ValueError("must use safe ASCII identifier characters")
    return value


def _canonical_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("monetary amount must be finite")
    if value < 0:
        raise ValueError("monetary amount must be non-negative")
    if value.is_zero():
        return Decimal(0)
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return Decimal(rendered)


class CostEstimate(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, allow_inf_nan=False
    )

    currency: str
    estimated_cost: Decimal = Field(
        ge=0, json_schema_extra={"pattern": _DECIMAL_JSON.pattern}
    )
    upper_bound: Decimal = Field(
        ge=0, json_schema_extra={"pattern": _DECIMAL_JSON.pattern}
    )
    pricing_snapshot_id: str = Field(min_length=1)

    @field_validator("currency")
    @classmethod
    def currency_is_three_uppercase_ascii_letters(cls, currency: str) -> str:
        if re.fullmatch(r"[A-Z]{3}", currency, flags=re.ASCII) is None:
            raise ValueError("currency must be three uppercase ASCII letters")
        return currency

    @field_validator(
        "estimated_cost", "upper_bound", mode="before", json_schema_input_type=str
    )
    @classmethod
    def require_exact_decimal_money(
        cls, value: object, info: ValidationInfo
    ) -> Decimal:
        if info.mode == "python":
            if not isinstance(value, Decimal):
                raise ValueError("monetary amount must be a Decimal")
            return _canonical_decimal(value)
        if not isinstance(value, str) or _DECIMAL_JSON.fullmatch(value) is None:
            raise ValueError("JSON monetary amount must be a plain decimal string")
        return _canonical_decimal(Decimal(value))

    @field_validator("pricing_snapshot_id")
    @classmethod
    def pricing_snapshot_id_is_prompt_safe(cls, value: str) -> str:
        return _validate_safe_identifier(value)

    @model_validator(mode="after")
    def upper_bound_covers_estimate(self) -> Self:
        if self.upper_bound < self.estimated_cost:
            raise ValueError("upper_bound must be at least estimated_cost")
        return self


class PaidRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    stage: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    case_count: int = Field(gt=0)
    estimate: CostEstimate

    @field_validator("stage", "provider", "model")
    @classmethod
    def prompt_identifiers_are_safe(cls, value: str) -> str:
        return _validate_safe_identifier(value)


def authorize_paid_run(
    request: PaidRunRequest,
    *,
    interactive: object,
    confirm: Callable[[str], object],
) -> bool:
    if interactive is not True:
        return False
    message = (
        f"{request.stage} | provider {request.provider} | model {request.model} | "
        f"cases {request.case_count}\n"
        f"Estimated cost: {request.estimate.currency} "
        f"{request.estimate.estimated_cost:f} "
        f"(upper bound {request.estimate.upper_bound:f}; "
        f"pricing {request.estimate.pricing_snapshot_id})\n"
        "Start paid run?"
    )
    return confirm(message) is True
```

- [ ] **Step 4: Run authorization tests and static checks**

Run:

```bash
uv run pytest tests/unit/policies/test_paid_operations.py -v
uv run ruff check src/phentrieve_benchmark/policies tests/unit/policies
uv run mypy
```

Expected: 37 policy tests pass, including the validation-schema assertion, and
the static checks succeed.

- [ ] **Step 5: Commit paid-operation safety**

```bash
git add src/phentrieve_benchmark/policies tests/unit/policies
git commit -m "feat: require interactive paid-run authorization"
```

### Task 9: Structured events without clinical text or raw exceptions

**Files:**
- Create: `src/phentrieve_benchmark/provenance/events.py`
- Create: `tests/unit/provenance/test_events.py`

- [ ] **Step 1: Write failing event-safety tests**

```python
from pathlib import Path

import pytest

from phentrieve_benchmark.provenance.events import EventWriter, UnsafeEventError


def test_writer_emits_canonical_text_free_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    writer = EventWriter(path)

    writer.write(
        event="case_complete",
        fields={"case_id": "synthetic-1", "duration_ms": 12, "status": "ok"},
    )

    assert path.read_bytes() == (
        b'{"case_id":"synthetic-1","duration_ms":12,'
        b'"event":"case_complete","status":"ok"}\n'
    )


@pytest.mark.parametrize("field", ["text", "full_text", "prompt", "credential", "exception"])
def test_writer_rejects_sensitive_field_names(tmp_path: Path, field: str) -> None:
    writer = EventWriter(tmp_path / "events.jsonl")

    with pytest.raises(UnsafeEventError, match=field):
        writer.write(event="unsafe", fields={field: "must not be logged"})
```

- [ ] **Step 2: Run tests and verify the missing writer**

Run: `uv run pytest tests/unit/provenance/test_events.py -v`

Expected: FAIL during collection because `provenance.events` does not exist.

- [ ] **Step 3: Implement safe structured events**

Create `src/phentrieve_benchmark/provenance/events.py`:

```python
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes


class UnsafeEventError(ValueError):
    pass


class EventWriter:
    _forbidden = frozenset(
        {"text", "full_text", "prompt", "credential", "credentials", "exception"}
    )

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, *, event: str, fields: Mapping[str, Any]) -> None:
        forbidden = self._forbidden.intersection(key.casefold() for key in fields)
        if forbidden:
            joined = ", ".join(sorted(forbidden))
            raise UnsafeEventError(f"unsafe event fields: {joined}")
        payload = {"event": event, **fields}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(canonical_json_bytes(payload) + b"\n")
```

- [ ] **Step 4: Run event tests and static checks**

Run:

```bash
uv run pytest tests/unit/provenance/test_events.py -v
uv run ruff check src/phentrieve_benchmark/provenance tests/unit/provenance
uv run mypy
```

Expected: six event tests pass and static checks succeed.

- [ ] **Step 5: Commit structured events**

```bash
git add src/phentrieve_benchmark/provenance/events.py tests/unit/provenance/test_events.py
git commit -m "feat: add safe structured run events"
```

### Task 10: Repository safety scanner and continuous integration

**Files:**
- Create: `scripts/check_repository_safety.py`
- Create: `tests/contracts/test_repository_safety.py`
- Create: `.github/workflows/ci.yml`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing repository-safety tests**

```python
from pathlib import Path

import pytest

from scripts.check_repository_safety import SafetyViolation, check_paths


def test_restricted_artifact_path_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / ".artifacts" / "sha256" / "ab" / ("a" * 64)
    path.parent.mkdir(parents=True)
    path.write_text("synthetic", encoding="utf-8")

    with pytest.raises(SafetyViolation, match=r"\.artifacts"):
        check_paths(tmp_path, [path])


def test_source_file_without_secrets_is_allowed(tmp_path: Path) -> None:
    path = tmp_path / "src" / "module.py"
    path.parent.mkdir()
    path.write_text('MODEL = "general/nmt"\n', encoding="utf-8")

    check_paths(tmp_path, [path])
```

- [ ] **Step 2: Run tests and verify the missing scanner**

Run: `uv run pytest tests/contracts/test_repository_safety.py -v`

Expected: FAIL during collection because `scripts.check_repository_safety`
does not exist.

- [ ] **Step 3: Implement the tracked-file safety scanner**

Create `scripts/check_repository_safety.py`:

```python
from collections.abc import Sequence
from pathlib import Path
import re
import subprocess
import sys


class SafetyViolation(RuntimeError):
    pass


FORBIDDEN_PARTS = {
    ".artifacts",
    "records/local",
    "releases/local",
    "configs/providers/local",
}
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?i)(?:api[_-]?key|client[_-]?secret)\s*[:=]\s*['\"][^'\"]{12,}"),
)


def check_paths(root: Path, paths: Sequence[Path]) -> None:
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if any(relative == part or relative.startswith(f"{part}/") for part in FORBIDDEN_PARTS):
            raise SafetyViolation(f"forbidden tracked path: {relative}")
        if path.is_file():
            content = path.read_bytes()
            for pattern in SECRET_PATTERNS:
                if pattern.search(content):
                    raise SafetyViolation(f"possible secret in tracked file: {relative}")


def tracked_paths(root: Path) -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    return [root / item.decode("utf-8") for item in output.split(b"\0") if item]


def main() -> int:
    root = Path.cwd()
    try:
        check_paths(root, tracked_paths(root))
    except SafetyViolation as error:
        print(str(error), file=sys.stderr)
        return 1
    print("repository safety check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add script typing and CI**

Create `scripts/__init__.py` with:

```python
"""Repository maintenance scripts."""
```

Change the mypy configuration in `pyproject.toml` to:

```toml
[tool.mypy]
python_version = "3.11"
strict = true
packages = ["phentrieve_benchmark", "scripts"]
```

Create `.github/workflows/ci.yml`:

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --locked --all-groups
      - run: uv run ruff check .
      - run: uv run mypy
      - run: uv run pytest --cov=phentrieve_benchmark --cov-report=term-missing
      - run: uv run python scripts/check_repository_safety.py
```

- [ ] **Step 5: Run all foundation verification**

Run:

```bash
uv lock --check
uv run ruff check .
uv run mypy
uv run pytest --cov=phentrieve_benchmark --cov-report=term-missing
uv run python scripts/check_repository_safety.py
```

Expected: the lockfile is current, static checks succeed, all tests pass, and
the scanner prints `repository safety check passed`.

- [ ] **Step 6: Commit safety and CI**

```bash
git add scripts tests/contracts/test_repository_safety.py .github/workflows/ci.yml pyproject.toml uv.lock
git commit -m "ci: enforce offline benchmark safety checks"
```

### Task 11: Verify the complete foundation contract

**Files:**
- Modify only if verification exposes a defect in a file created above.

- [ ] **Step 1: Run the complete offline suite from a clean environment**

Run:

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run mypy
uv run pytest --cov=phentrieve_benchmark --cov-report=term-missing
uv run python scripts/check_repository_safety.py
git diff --check
git status --short
```

Expected:

- dependency synchronization succeeds without provider credentials;
- Ruff and mypy report no errors;
- every test passes without network or paid-provider access;
- repository safety passes;
- `git diff --check` emits nothing;
- `git status --short` emits nothing.

- [ ] **Step 2: Exercise the installed CLI**

Run:

```bash
uv run phentrieve-benchmark version
uv run phentrieve-benchmark --help
```

Expected: the first command prints `phentrieve-benchmark 0.1.0`; the second
lists the `version` command and exits successfully.

- [ ] **Step 3: Record the phase boundary**

Do not add a commit when verification is clean. If verification required a
correction, commit only that correction with:

```bash
git add -u
git commit -m "fix: satisfy foundation contract"
```

The next implementation phase starts with the acquisition, normalization, and
selection plan and may import only the public interfaces verified here.

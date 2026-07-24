from enum import StrEnum
from typing import Literal, Self
from unicodedata import normalize

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from phentrieve_benchmark.models.identifiers import HpoRelease
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
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: str = Field(min_length=1)
    engine: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    returned_model: str = Field(min_length=1)
    endpoint_class: str = Field(min_length=1)
    processing_mode: str = Field(min_length=1)


class UsageMetrics(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, allow_inf_nan=False
    )

    input_characters: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0.0, ge=0)


class RunManifest(BaseModel):
    """Volatile execution record with canonicalized set-like identities."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["run-manifest/v1"] = "run-manifest/v1"
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
    # Inputs and outputs are logical sets; their stored order is canonical.
    input_sha256: tuple[Sha256Hex, ...]
    output_sha256: tuple[Sha256Hex, ...]
    prompt_sha256: Sha256Hex | None = None
    provider: ProviderRunIdentity | None = None
    hpo_release: HpoRelease | None = None
    selection_id: str | None = None
    pricing_snapshot_id: str | None = None
    usage: UsageMetrics = Field(default_factory=UsageMetrics)
    retry_count: int = Field(default=0, ge=0)
    error_codes: tuple[str, ...] = ()
    environment: tuple[ComponentDigest, ...] = ()

    @field_validator("source", "environment")
    @classmethod
    def canonicalize_component_sets(
        cls, components: tuple[ComponentDigest, ...]
    ) -> tuple[ComponentDigest, ...]:
        canonical_components = tuple(
            component.model_copy(
                update={
                    "role": normalize("NFC", component.role),
                    "stable_id": normalize("NFC", component.stable_id),
                }
            )
            for component in components
        )
        identities = {
            (component.role, component.stable_id)
            for component in canonical_components
        }
        if len(identities) != len(canonical_components):
            raise ValueError("duplicate component identity")
        return tuple(
            sorted(
                canonical_components,
                key=lambda component: (
                    component.role,
                    component.stable_id,
                    component.sha256,
                ),
            )
        )

    @field_validator("input_sha256", "output_sha256")
    @classmethod
    def canonicalize_digest_sets(cls, digests: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(digests)) != len(digests):
            raise ValueError("duplicate digest")
        return tuple(sorted(digests))

    @field_validator("error_codes")
    @classmethod
    def canonicalize_error_codes(cls, error_codes: tuple[str, ...]) -> tuple[str, ...]:
        canonical_codes = tuple(normalize("NFC", code) for code in error_codes)
        if len(set(canonical_codes)) != len(canonical_codes):
            raise ValueError("duplicate error code")
        return tuple(sorted(canonical_codes))

    @model_validator(mode="after")
    def completion_has_valid_time_range(self) -> Self:
        if self.status is RunStatus.COMPLETE and self.finished_at is None:
            raise ValueError("complete run requires finished_at")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        return self


class ReleaseManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["release-manifest/v1"] = "release-manifest/v1"
    dataset_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    hpo_release: HpoRelease
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
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["release-run-link/v1"] = "release-run-link/v1"
    release_sha256: Sha256Hex
    run_manifest_sha256: tuple[Sha256Hex, ...]

    @field_validator("run_manifest_sha256")
    @classmethod
    def canonicalize_run_manifest_hashes(
        cls, run_manifest_hashes: tuple[str, ...]
    ) -> tuple[str, ...]:
        if len(set(run_manifest_hashes)) != len(run_manifest_hashes):
            raise ValueError("duplicate run manifest digest")
        return tuple(sorted(run_manifest_hashes))

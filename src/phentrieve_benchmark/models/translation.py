from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


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
    price_per_million_input_characters: Decimal = Field(ge=0)
    estimated_max_cost: Decimal = Field(ge=0)
    previous_translation_id: str | None = None
    status: TranslationStatus
    checks: tuple[TranslationCheck, ...]

    @field_validator(
        "price_per_million_input_characters",
        "estimated_max_cost",
        mode="before",
    )
    @classmethod
    def money_is_decimal(cls, value: object) -> Decimal:
        if not isinstance(value, Decimal):
            raise ValueError("money must be represented as Decimal")
        if not value.is_finite():
            raise ValueError("money must be finite")
        return value

    @field_serializer(
        "price_per_million_input_characters", "estimated_max_cost"
    )
    def serialize_money(self, value: Decimal) -> str:
        rendered = format(value, "f")
        return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered

    @model_validator(mode="after")
    def status_matches_checks(self) -> Self:
        codes = [check.code for check in self.checks]
        if len(codes) != len(set(codes)):
            raise ValueError("duplicate translation check code")
        has_failure = any(not check.passed for check in self.checks)
        if (
            self.status is TranslationStatus.AUTOMATIC_CHECK_FAILED
            and not has_failure
        ):
            raise ValueError("automatic_check_failed requires a failed check")
        if self.status is TranslationStatus.READY_FOR_REVIEW and has_failure:
            raise ValueError("ready_for_review forbids failed checks")
        return self


class TranslationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-translation-manifest/v1"] = (
        "e3c-translation-manifest/v1"
    )
    selection_id: str = Field(min_length=1)
    selection_sha256: Sha256Hex
    recipe_sha256: Sha256Hex
    records: tuple[TranslationRecord, ...]

    @model_validator(mode="after")
    def records_are_unique(self) -> Self:
        case_ids = [record.source_case_id for record in self.records]
        translation_ids = [record.translation_id for record in self.records]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("duplicate source case in translation manifest")
        if len(translation_ids) != len(set(translation_ids)):
            raise ValueError("duplicate translation ID in translation manifest")
        return self

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())


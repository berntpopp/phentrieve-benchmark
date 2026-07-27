from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, field_validator

from phentrieve_benchmark.acquisition.recipes import LoadedRecipe
from phentrieve_benchmark.policies.paid_operations import CostEstimate
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes

_MILLION = Decimal(1_000_000)


class GoogleNmtPricing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_per_million_input_characters: Decimal = Field(ge=0)
    pricing_snapshot_id: str = Field(min_length=1)

    @field_validator("price_per_million_input_characters", mode="before")
    @classmethod
    def price_is_decimal(cls, value: object) -> Decimal:
        if not isinstance(value, Decimal):
            raise ValueError("price must be represented as Decimal")
        if not value.is_finite():
            raise ValueError("price must be finite")
        return value


class E3cTranslationRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-translation-recipe/v1"]
    translation_id: str = Field(min_length=1)
    selection_id: str = Field(min_length=1)
    provider: Literal["google-cloud-translation"]
    api_version: Literal["v3"]
    model: Literal["general/nmt", "general/translation-llm"]
    location: str = Field(min_length=1)
    target_language: Literal["de"]
    pricing: GoogleNmtPricing


def load_translation_recipe(
    path: Path,
) -> LoadedRecipe[E3cTranslationRecipe]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"invalid translation recipe: {path.name}") from error
    if not isinstance(payload, dict):
        raise ValueError("translation recipe must contain one mapping")
    pricing = payload.get("pricing")
    if not isinstance(pricing, dict):
        raise ValueError("translation recipe pricing must be a mapping")
    raw_price = pricing.get("price_per_million_input_characters")
    if not isinstance(raw_price, str):
        raise ValueError("translation recipe price must be a decimal string")
    try:
        pricing["price_per_million_input_characters"] = Decimal(raw_price)
    except ArithmeticError as error:
        raise ValueError("translation recipe price is invalid") from error
    value = E3cTranslationRecipe.model_validate(payload, strict=True)
    semantic = canonical_json_bytes(value.model_dump(mode="json"))
    return LoadedRecipe(value=value, sha256=sha256_bytes(semantic))


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

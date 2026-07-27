from decimal import Decimal
from pathlib import Path
from typing import Literal, Self

import yaml  # type: ignore[import-untyped]
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from phentrieve_benchmark.acquisition.recipes import LoadedRecipe
from phentrieve_benchmark.policies.paid_operations import CostEstimate
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes

_MILLION = Decimal(1_000_000)


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
    value = E3cTranslationRecipe.model_validate(payload, strict=True)
    semantic = canonical_json_bytes(
        value.model_dump(mode="json", exclude_none=True)
    )
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
    output_price = pricing.price_per_million_output_characters
    factor = pricing.output_expansion_factor
    if output_price is not None and factor is not None:
        cost += Decimal(input_codepoints) * factor * output_price / _MILLION
    return CostEstimate(
        currency=pricing.currency,
        estimated_cost=cost,
        upper_bound=cost,
        pricing_snapshot_id=pricing.pricing_snapshot_id,
    )

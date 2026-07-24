"""Fail-closed authorization for operations that may incur provider charges."""

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
    """Accept only prompt-safe ASCII identifiers without delimiters or controls."""
    if _SAFE_IDENTIFIER.fullmatch(value) is None:
        raise ValueError("must use safe ASCII identifier characters")
    return value


def _canonical_decimal(value: Decimal) -> Decimal:
    """Return a finite, non-negative decimal without redundant precision."""
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
    """Immutable exact money estimate from a recorded pricing snapshot.

    Python construction requires :class:`~decimal.Decimal` money values. JSON
    represents money as plain decimal strings, which are canonicalized without
    guessing a currency-specific precision.
    """

    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, allow_inf_nan=False
    )

    currency: str
    estimated_cost: Decimal = Field(ge=0)
    upper_bound: Decimal = Field(ge=0)
    pricing_snapshot_id: str = Field(min_length=1)

    @field_validator("currency")
    @classmethod
    def currency_is_three_uppercase_ascii_letters(cls, currency: str) -> str:
        if re.fullmatch(r"[A-Z]{3}", currency, flags=re.ASCII) is None:
            raise ValueError("currency must be three uppercase ASCII letters")
        return currency

    @field_validator("estimated_cost", "upper_bound", mode="before")
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
    """The complete, immutable input required to authorize a paid pipeline run."""

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
    """Authorize only an interactive run confirmed by the literal boolean ``True``."""
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

"""Fail-closed authorization for operations that may incur provider charges."""

from collections.abc import Callable
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CostEstimate(BaseModel):
    """Immutable, finite cost estimate from a recorded pricing snapshot."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, allow_inf_nan=False
    )

    currency: str = Field(pattern=r"^[A-Z]{3}$")
    estimated_cost: float = Field(ge=0)
    upper_bound: float = Field(ge=0)
    pricing_snapshot_id: str = Field(min_length=1)

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


def authorize_paid_run(
    request: PaidRunRequest,
    *,
    interactive: bool,
    confirm: Callable[[str], object],
) -> bool:
    """Authorize only an interactive run confirmed by the literal boolean ``True``."""
    if not interactive:
        return False

    message = (
        f"{request.stage} | provider {request.provider} | model {request.model} | "
        f"cases {request.case_count}\n"
        f"Estimated cost: {request.estimate.currency} "
        f"{request.estimate.estimated_cost:.2f} "
        f"(upper bound {request.estimate.upper_bound:.2f}; "
        f"pricing {request.estimate.pricing_snapshot_id})\n"
        "Start paid run?"
    )
    return confirm(message) is True

import json

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.policies.paid_operations import (
    CostEstimate,
    PaidRunRequest,
    authorize_paid_run,
)


def request() -> PaidRunRequest:
    return PaidRunRequest(
        stage="translate",
        provider="google",
        model="general/nmt",
        case_count=30,
        estimate=CostEstimate(
            currency="USD",
            estimated_cost=2.83,
            upper_bound=3.00,
            pricing_snapshot_id="google-2026-07-23",
        ),
    )


def test_non_interactive_paid_run_fails_without_prompting() -> None:
    prompts: list[str] = []

    assert not authorize_paid_run(
        request(),
        interactive=False,
        confirm=lambda message: prompts.append(message) or True,
    )
    assert prompts == []


def test_interactive_paid_run_requires_explicit_boolean_true() -> None:
    messages: list[str] = []

    assert authorize_paid_run(
        request(),
        interactive=True,
        confirm=lambda message: messages.append(message) or True,
    )
    assert messages == [
        "translate | provider google | model general/nmt | cases 30\n"
        "Estimated cost: USD 2.83 (upper bound 3.00; "
        "pricing google-2026-07-23)\n"
        "Start paid run?"
    ]


@pytest.mark.parametrize("response", [False, "yes", "YES", " yes ", 1, None])
def test_interactive_paid_run_rejects_non_boolean_confirmation(
    response: object,
) -> None:
    assert not authorize_paid_run(
        request(),
        interactive=True,
        confirm=lambda _message: response,
    )


@pytest.mark.parametrize("value", [-0.01, float("nan"), float("inf"), float("-inf")])
def test_estimate_rejects_invalid_float_values(value: float) -> None:
    with pytest.raises(ValidationError):
        CostEstimate(
            currency="USD",
            estimated_cost=value,
            upper_bound=3.00,
            pricing_snapshot_id="google-2026-07-23",
        )
    with pytest.raises(ValidationError):
        CostEstimate.model_validate_json(
            json.dumps(
                {
                    "currency": "USD",
                    "estimated_cost": value,
                    "upper_bound": 3.00,
                    "pricing_snapshot_id": "google-2026-07-23",
                }
            )
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"currency": "USD", "estimated_cost": "2.83"},
        {"currency": "USD", "estimated_cost": True},
        {"currency": 123, "estimated_cost": 2.83},
        {"currency": "USD", "estimated_cost": 2.83, "upper_bound": "3.00"},
        {"currency": "USD", "estimated_cost": 2.83, "upper_bound": True},
    ],
)
def test_estimate_rejects_coercive_values_direct_and_json(
    payload: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "currency": "USD",
        "estimated_cost": 2.83,
        "upper_bound": 3.00,
        "pricing_snapshot_id": "google-2026-07-23",
    }
    values.update(payload)

    with pytest.raises(ValidationError):
        CostEstimate(**values)
    with pytest.raises(ValidationError):
        CostEstimate.model_validate_json(json.dumps(values))


def test_estimate_rejects_upper_bound_below_estimate() -> None:
    with pytest.raises(ValueError, match="upper_bound"):
        CostEstimate(
            currency="USD",
            estimated_cost=2.83,
            upper_bound=2.00,
            pricing_snapshot_id="google-2026-07-23",
        )


def test_cost_estimate_is_frozen_and_forbids_extra_fields() -> None:
    estimate = request().estimate

    with pytest.raises(ValidationError):
        CostEstimate(**{**estimate.model_dump(), "unapproved": "field"})
    with pytest.raises(ValidationError):
        estimate.estimated_cost = 4.00

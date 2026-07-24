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


class _TruthyValue:
    def __bool__(self) -> bool:
        return True


@pytest.mark.parametrize("interactive", [False, 1, "false", _TruthyValue(), None])
def test_only_literal_boolean_true_can_prompt_for_paid_run(interactive: object) -> None:
    prompts: list[str] = []

    assert not authorize_paid_run(
        request(),
        interactive=interactive,
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
        "Estimated cost: USD 2.83 (upper bound 3; pricing google-2026-07-23)\n"
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("stage", "translate\nStart paid run?"),
        ("provider", "google\rStart paid run?"),
        ("model", "general/nmt\x1b[2J"),
        ("pricing_snapshot_id", "snapshot|Start paid run?"),
        ("stage", "translate\u202eapproved"),
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


@pytest.mark.parametrize(
    "value",
    [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_estimate_rejects_negative_and_nonfinite_decimal_values(value: Decimal) -> None:
    with pytest.raises(ValidationError):
        CostEstimate(
            currency="USD",
            estimated_cost=value,
            upper_bound=Decimal("3.00"),
            pricing_snapshot_id="google-2026-07-23",
        )


@pytest.mark.parametrize("value", ["2.83", True, 2, 2.83])
def test_estimate_requires_decimal_values_at_the_python_boundary(value: object) -> None:
    with pytest.raises(ValidationError, match="Decimal"):
        CostEstimate(
            currency="USD",
            estimated_cost=value,
            upper_bound=Decimal("3.00"),
            pricing_snapshot_id="google-2026-07-23",
        )


@pytest.mark.parametrize("value", [True, 2, 2.83])
def test_estimate_json_rejects_non_string_money_values(value: object) -> None:
    with pytest.raises(ValidationError):
        CostEstimate.model_validate_json(
            json.dumps(
                {
                    "currency": "USD",
                    "estimated_cost": value,
                    "upper_bound": "3.00",
                    "pricing_snapshot_id": "google-2026-07-23",
                }
            )
        )


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
    assert estimate.model_dump(mode="json") == {
        "currency": "USD",
        "estimated_cost": "2.675",
        "upper_bound": "3",
        "pricing_snapshot_id": "google-2026-07-23",
    }


def test_estimate_canonicalizes_signed_zero() -> None:
    estimate = CostEstimate(
        currency="USD",
        estimated_cost=Decimal("-0"),
        upper_bound=Decimal("0"),
        pricing_snapshot_id="google-2026-07-23",
    )

    assert estimate.estimated_cost == Decimal("0")
    assert estimate.estimated_cost.as_tuple().sign == 0


def test_estimate_rejects_upper_bound_below_estimate() -> None:
    with pytest.raises(ValueError, match="upper_bound"):
        CostEstimate(
            currency="USD",
            estimated_cost=Decimal("2.83"),
            upper_bound=Decimal("2.00"),
            pricing_snapshot_id="google-2026-07-23",
        )


@pytest.mark.parametrize(
    ("estimated_cost", "upper_bound"),
    [
        (Decimal("2.675"), Decimal("2.675")),
        (Decimal("1.005"), Decimal("1.005")),
        (Decimal("0.004"), Decimal("0.004")),
    ],
)
def test_prompt_displays_exact_decimal_costs_without_rounding(
    estimated_cost: Decimal, upper_bound: Decimal
) -> None:
    messages: list[str] = []
    paid_request = request(
        estimate=CostEstimate(
            currency="USD",
            estimated_cost=estimated_cost,
            upper_bound=upper_bound,
            pricing_snapshot_id="google-2026-07-23",
        )
    )

    assert authorize_paid_run(
        paid_request,
        interactive=True,
        confirm=lambda message: messages.append(message) or True,
    )
    expected_cost = (
        f"Estimated cost: USD {estimated_cost} (upper bound {upper_bound};"
    )
    assert expected_cost in messages[0]


def test_cost_estimate_is_frozen_and_forbids_extra_fields() -> None:
    estimate = request().estimate

    with pytest.raises(ValidationError):
        CostEstimate(**{**estimate.model_dump(), "unapproved": "field"})
    with pytest.raises(ValidationError):
        estimate.estimated_cost = Decimal("4.00")

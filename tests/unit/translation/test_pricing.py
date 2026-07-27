from decimal import Decimal

import pytest

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


def test_pricing_accepts_output_price_and_expansion_factor() -> None:
    pricing = GoogleNmtPricing(
        currency="USD",
        price_per_million_input_characters=Decimal("10"),
        price_per_million_output_characters=Decimal("10"),
        output_expansion_factor=Decimal("1.30"),
        pricing_snapshot_id="google-cloud-translation-llm-2026-07-27",
    )

    assert pricing.price_per_million_output_characters == Decimal("10")
    assert pricing.output_expansion_factor == Decimal("1.30")


def test_pricing_rejects_output_price_without_expansion_factor() -> None:
    with pytest.raises(ValueError, match="expansion factor"):
        GoogleNmtPricing(
            currency="USD",
            price_per_million_input_characters=Decimal("10"),
            price_per_million_output_characters=Decimal("10"),
            pricing_snapshot_id="google-cloud-translation-llm-2026-07-27",
        )


def test_pricing_rejects_expansion_factor_without_output_price() -> None:
    with pytest.raises(ValueError, match="expansion factor"):
        GoogleNmtPricing(
            currency="USD",
            price_per_million_input_characters=Decimal("10"),
            output_expansion_factor=Decimal("1.30"),
            pricing_snapshot_id="google-cloud-translation-llm-2026-07-27",
        )


def test_estimate_rejects_nonpositive_input() -> None:
    pricing = GoogleNmtPricing(
        currency="USD",
        price_per_million_input_characters=Decimal("20"),
        pricing_snapshot_id="google-cloud-translation-2026-07-24",
    )

    with pytest.raises(ValueError, match="positive"):
        estimate_google_nmt(0, pricing)


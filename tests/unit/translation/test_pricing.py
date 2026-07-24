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


def test_estimate_rejects_nonpositive_input() -> None:
    pricing = GoogleNmtPricing(
        currency="USD",
        price_per_million_input_characters=Decimal("20"),
        pricing_snapshot_id="google-cloud-translation-2026-07-24",
    )

    with pytest.raises(ValueError, match="positive"):
        estimate_google_nmt(0, pricing)


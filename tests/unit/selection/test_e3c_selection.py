from fractions import Fraction

from phentrieve_benchmark.selection.e3c import select_e3c_feasibility
from phentrieve_benchmark.selection.metrics import (
    E3cInventoryRecord,
    LengthStratum,
    Rational,
)


def _record(language: str, stratum: LengthStratum, index: int):
    tokens = {
        LengthStratum.SHORT: 100,
        LengthStratum.MEDIUM: 300,
        LengthStratum.LONG: 500,
    }[stratum] + index
    return E3cInventoryRecord(
        source_case_id=f"{language}-{stratum.value}-{index:02d}",
        language=language,
        document_sha256=f"{index + 1:064x}",
        codepoint_count=tokens * 4,
        whitespace_token_count=tokens,
        sentence_count=1,
        annotation_counts=(("EVENT", index + 1),),
        total_annotation_density=Rational.from_fraction(
            Fraction((index + 1) * 100, tokens)
        ),
        marker_counts=(),
        marker_densities=(),
        length_stratum=stratum,
        warnings=(),
    )


def test_selects_exact_language_and_stratum_allocation_deterministically() -> None:
    records = [
        _record(language, stratum, index)
        for language in ("en", "fr", "es")
        for stratum in LengthStratum
        for index in range(7)
    ]
    first = select_e3c_feasibility(records)
    second = select_e3c_feasibility(reversed(records))
    assert first.canonical_bytes() == second.canonical_bytes()
    assert len(first.records) == 30
    for language in ("en", "fr", "es"):
        selected = [item for item in first.records if item.language == language]
        assert len(selected) == 10
        assert [item.stratum for item in selected].count(LengthStratum.SHORT) == 3
        assert [item.stratum for item in selected].count(LengthStratum.MEDIUM) == 4
        assert [item.stratum for item in selected].count(LengthStratum.LONG) == 3

from phentrieve_benchmark.translation.checks import check_translation


def _by_code(
    source: str, translation: str, language: str | None = "de"
) -> dict[str, object]:
    return {
        item.code: item
        for item in check_translation(
            source_text=source,
            translated_text=translation,
            detected_language=language,
        )
    }


def test_units_added_flags_a_unit_invented_for_a_bare_value() -> None:
    # FR100925: "ASAT à 47 la normale" (47 times the upper limit, no unit)
    # became "AST 47 U/l (normal)", which reads as a normal result.
    checks = _by_code(
        "hyper-transaminasémie avec ASAT à 47 la normale",
        "erhöhte Transaminasen mit AST 47 U/l",
    )

    assert not checks["units_added"].passed
    assert checks["units_added"].detail == "u/l"


def test_units_added_ignores_a_unit_glued_to_its_value_in_the_source() -> None:
    # The previous implementation could not see "200mg" in the source, so the
    # correct German spacing counted as an addition and flagged the document.
    checks = _by_code(
        "Sodium Valproate 200mg once a day, temperature 37°C, saturation 67%.",
        "Natriumvalproat 200 mg einmal täglich, Temperatur 37 °C, "
        "Sättigung 67 %.",
    )

    assert checks["units_added"].passed
    assert checks["units_added"].detail is None


def test_units_added_ignores_a_unit_repeated_across_values() -> None:
    checks = _by_code(
        "lesions of 20 mm and 33 mm", "Läsionen von 20 mm bzw. 33 mm"
    )

    assert checks["units_added"].passed


def test_units_added_ignores_letters_that_are_not_measurements() -> None:
    # "Ig G", "IgM" and "a.m." used to be counted as gram and metre.
    checks = _by_code(
        "Ig G 2,1 index, inmunoglobulina M, at 4 a.m.",
        "IgG-Index 2,1, Immunglobulin M, um 4 Uhr",
    )

    assert checks["units_added"].passed


def test_number_formatting_differences_do_not_fail_any_check() -> None:
    # Spelled-out numerals, German thousands separators and marker notation
    # were the dominant false positives of the removed numbers_preserved check.
    checks = _by_code(
        "3 months later the WBC was 37500 cells/dL, CD 45 positive.",
        "Drei Monate später lagen die Leukozyten bei 37.500 Zellen/dl, "
        "CD45-positiv.",
    )

    assert all(item.passed for item in checks.values())


def test_length_ratio_records_paragraph_counts_without_gating() -> None:
    checks = _by_code("One.\nTwo.\nThree.", "Eins. Zwei. Drei.")

    assert checks["length_ratio"].passed
    assert checks["length_ratio"].detail is not None
    assert "paragraphs=3/1" in checks["length_ratio"].detail


def test_empty_and_unchanged_output_still_fail() -> None:
    empty = _by_code("The patient had fever.", "   ")
    unchanged = _by_code(
        "The patient had fever.", "The patient had fever.", language="en"
    )

    assert not empty["nonempty_output"].passed
    assert not unchanged["source_changed"].passed
    assert not unchanged["target_language_de"].passed


def test_removed_checks_are_gone() -> None:
    checks = _by_code("39 °C", "39 °C gemessen")

    assert "numbers_preserved" not in checks
    assert "units_preserved" not in checks

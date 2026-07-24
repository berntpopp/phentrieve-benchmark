from phentrieve_benchmark.translation.checks import check_translation


def test_checks_flag_missing_number_and_unit() -> None:
    checks = check_translation(
        source_text="Temperature was 39 °C.",
        translated_text="Der Patient hatte Fieber.",
        detected_language="de",
    )
    by_code = {item.code: item for item in checks}

    assert not by_code["numbers_preserved"].passed
    assert not by_code["units_preserved"].passed
    assert by_code["target_language_de"].passed


def test_checks_flag_unchanged_source() -> None:
    checks = check_translation(
        source_text="The patient had fever.",
        translated_text="The patient had fever.",
        detected_language="en",
    )

    assert not {item.code: item for item in checks}["source_changed"].passed


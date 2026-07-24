import pytest

from phentrieve_benchmark.normalization.text import (
    TextBoundaryError,
    canonicalize_source_text,
)


def test_canonicalizes_nfc_and_line_endings() -> None:
    mapped = canonicalize_source_text(
        "Cafe\u0301\r\nzweite\rZeile",
        remove_terminal_format_newline=False,
    )
    assert mapped.canonical_text == "Café\nzweite\nZeile"


def test_optionally_removes_exactly_one_terminal_format_newline() -> None:
    assert canonicalize_source_text(
        "Text\r\n", remove_terminal_format_newline=True
    ).canonical_text == "Text"
    assert canonicalize_source_text(
        "Text\n\n", remove_terminal_format_newline=True
    ).canonical_text == "Text\n"
    assert canonicalize_source_text(
        "Text\n", remove_terminal_format_newline=False
    ).canonical_text == "Text\n"


@pytest.mark.parametrize("source", ["", "\n", "\r\n"])
def test_rejects_empty_canonical_clinical_text(source: str) -> None:
    with pytest.raises(ValueError, match="empty"):
        canonicalize_source_text(
            source, remove_terminal_format_newline=True
        )


def test_maps_uima_utf16_offsets_around_non_bmp_character() -> None:
    mapped = canonicalize_source_text(
        "A😀B", remove_terminal_format_newline=False
    )
    span = mapped.utf16_span(3, 4)
    assert (span.start_char, span.end_char, span.text_snippet) == (2, 3, "B")
    with pytest.raises(TextBoundaryError, match="UTF-16"):
        mapped.utf16_span(1, 2)


def test_rejects_boundaries_inside_normalization_and_crlf_clusters() -> None:
    composed = canonicalize_source_text(
        "Cafe\u0301 noir", remove_terminal_format_newline=False
    )
    with pytest.raises(TextBoundaryError, match="canonical"):
        composed.utf16_span(0, 4)

    newline = canonicalize_source_text(
        "A\r\nB", remove_terminal_format_newline=False
    )
    with pytest.raises(TextBoundaryError, match="canonical"):
        newline.utf16_span(0, 2)


def test_converts_span_through_utf16_and_canonicalization_maps() -> None:
    mapped = canonicalize_source_text(
        "😀 Cafe\u0301\r\nfin", remove_terminal_format_newline=False
    )
    span = mapped.utf16_span(3, 8)
    assert (span.start_char, span.end_char) == (2, 6)
    assert span.text_snippet == "Café"
    assert mapped.canonical_text[span.start_char : span.end_char] == "Café"

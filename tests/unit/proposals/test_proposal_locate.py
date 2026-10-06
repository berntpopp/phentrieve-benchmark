import pytest

from phentrieve_benchmark.models.hpo_proposal import RejectionReason
from phentrieve_benchmark.proposals.locate import (
    LocatedSpan,
    MentionLocationError,
    locate_mention,
    normalize_typography,
)


def _locate(
    text: str, phrase: str, context: str, occurrence: int | None = None
) -> LocatedSpan:
    return locate_mention(
        normalize_typography(text),
        phrase=phrase,
        context=context,
        occurrence=occurrence,
    )


def _reason(
    text: str, phrase: str, context: str, occurrence: int | None = None
) -> RejectionReason:
    with pytest.raises(MentionLocationError) as caught:
        _locate(text, phrase, context, occurrence)
    return caught.value.reason


def test_normalization_maps_typography_and_collapses_whitespace() -> None:
    normalized = normalize_typography("a\u00a0 \u201eb\u201c\u2013c")
    assert normalized.value == 'a "b"-c'
    assert normalized.starts == (0, 1, 3, 4, 5, 6, 7)
    assert normalized.ends == (1, 3, 4, 5, 6, 7, 8)


def test_exact_phrase_resolves_to_original_offsets() -> None:
    text = "Die Schwellung ging mit hohem Fieber einher."
    span = _locate(text, "Fieber", "mit hohem Fieber einher")
    assert (span.start, span.end) == (text.index("Fieber"), text.index("Fieber") + 6)


def test_typography_differences_are_tolerated_and_spans_stay_verbatim() -> None:
    text = "Temperatur 39,5\u00a0\u00b0C \u2013 \u201ehohes Fieber\u201c."
    span = _locate(text, "39,5 \u00b0C", 'Temperatur 39,5 \u00b0C - "hohes')
    assert text[span.start : span.end] == "39,5\u00a0\u00b0C"
    span = _locate(text, "hohes Fieber", '"hohes Fieber"')
    assert text[span.start : span.end] == "hohes Fieber"


def test_whole_word_match_takes_precedence() -> None:
    text = "She reported headache and ache in the back."
    span = _locate(text, "ache", "headache and ache in")
    assert span.start == text.index("and ache") + 4


def test_in_word_matches_count_after_whole_words() -> None:
    text = "She reported headache and ache in the back."
    span = _locate(text, "ache", "headache and ache in", occurrence=2)
    assert span.start == text.index("headache") + 4


def test_occurrence_selects_among_repeated_matches() -> None:
    text = "Fever on day one, fever on day three, fever on day five."
    context = "fever on day three, fever on day five"
    span = _locate(text, "fever", context, occurrence=2)
    assert span.start == text.index("fever on day five")
    assert (
        _reason(text, "fever", context)
        is RejectionReason.PHRASE_NOT_UNIQUE_IN_CONTEXT
    )
    assert (
        _reason(text, "fever", context, occurrence=3)
        is RejectionReason.OCCURRENCE_OUT_OF_RANGE
    )


@pytest.mark.parametrize(
    ("text", "phrase", "context", "reason"),
    [
        ("Hohes Fieber.", "Fieber", "kein Fieber", RejectionReason.CONTEXT_NOT_FOUND),
        ("Fieber. Fieber.", "Fieber", "Fieber", RejectionReason.CONTEXT_NOT_UNIQUE),
        (
            "mit hohem Fieber einher",
            "Husten",
            "hohem Fieber",
            RejectionReason.PHRASE_NOT_IN_CONTEXT,
        ),
        (
            "Hohes Fieber.",
            " Fieber",
            "Hohes Fieber",
            RejectionReason.PHRASE_NOT_TRIMMED,
        ),
    ],
)
def test_unlocatable_mentions_name_their_reason(
    text: str, phrase: str, context: str, reason: RejectionReason
) -> None:
    assert _reason(text, phrase, context) is reason


def test_non_alphanumeric_phrase_edge_needs_no_word_boundary() -> None:
    text = "Temp 38\u00b0C und 39 \u00b0C."
    reason = _reason(text, "\u00b0C", "38\u00b0C und 39 \u00b0C")
    assert reason is RejectionReason.PHRASE_NOT_UNIQUE_IN_CONTEXT


def test_phrase_across_collapsed_whitespace_run_stays_verbatim() -> None:
    text = "Er hat hohes\r\n  Fieber."
    span = _locate(text, "hohes Fieber", "hat hohes Fieber")
    assert text[span.start : span.end] == "hohes\r\n  Fieber"


def test_decomposed_phrase_and_context_match_nfc_text() -> None:
    text = "Er klagt \u00dcbelkeit."
    decomposed = "U\u0308belkeit"
    span = _locate(text, decomposed, "klagt " + decomposed)
    assert text[span.start : span.end] == "\u00dcbelkeit"

"""Locate proposed mentions in a document text.

Language models do not count characters reliably, so a mention is given as
two verbatim strings: the phrase and a short context that contains it.
Matching tolerates typography a model may alter (quotation marks, dashes,
non-breaking and repeated whitespace); offsets always refer to the original
text, so a stored span is the verbatim original.
"""

import unicodedata
from dataclasses import dataclass

from phentrieve_benchmark.models.hpo_proposal import RejectionReason

_TYPOGRAPHY = {
    "\u00ab": '"',
    "\u00bb": '"',
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u2039": "'",
    "\u203a": "'",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
}


@dataclass(frozen=True)
class NormalizedText:
    """Normalized text; normalized character i covers original [starts[i], ends[i])."""

    value: str
    starts: tuple[int, ...]
    ends: tuple[int, ...]


@dataclass(frozen=True)
class LocatedSpan:
    start: int
    end: int


class MentionLocationError(ValueError):
    def __init__(self, reason: RejectionReason, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def normalize_typography(text: str) -> NormalizedText:
    characters: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    index = 0
    while index < len(text):
        character = text[index]
        if character.isspace():
            end = index + 1
            while end < len(text) and text[end].isspace():
                end += 1
            characters.append(" ")
            starts.append(index)
            ends.append(end)
            index = end
            continue
        characters.append(_TYPOGRAPHY.get(character, character))
        starts.append(index)
        ends.append(index + 1)
        index += 1
    return NormalizedText("".join(characters), tuple(starts), tuple(ends))


def _normalized(value: str) -> str:
    return normalize_typography(unicodedata.normalize("NFC", value)).value


def _positions(haystack: str, needle: str, start: int, end: int) -> list[int]:
    positions: list[int] = []
    position = haystack.find(needle, start, end)
    while position != -1:
        positions.append(position)
        position = haystack.find(needle, position + 1, end)
    return positions


def _whole_word(haystack: str, start: int, end: int) -> bool:
    before = haystack[start - 1] if start > 0 else ""
    after = haystack[end] if end < len(haystack) else ""
    return not before.isalnum() and not after.isalnum()


def locate_mention(
    text: NormalizedText, *, phrase: str, context: str, occurrence: int | None
) -> LocatedSpan:
    """Return original offsets of the phrase inside its unique context.

    Candidates are ordered whole-word matches first, then matches inside
    longer words. Without `occurrence` the phrase must have exactly one
    candidate of the first kind present; `occurrence` (1-based) indexes the
    ordered candidates.
    """
    if phrase != phrase.strip():
        raise MentionLocationError(
            RejectionReason.PHRASE_NOT_TRIMMED,
            "phrase has leading or trailing whitespace",
        )
    needle_context = _normalized(context)
    contexts = _positions(text.value, needle_context, 0, len(text.value))
    if not contexts:
        raise MentionLocationError(
            RejectionReason.CONTEXT_NOT_FOUND, "context does not occur in the text"
        )
    if len(contexts) > 1:
        raise MentionLocationError(
            RejectionReason.CONTEXT_NOT_UNIQUE,
            f"context occurs {len(contexts)} times in the text",
        )
    context_start = contexts[0]
    context_end = context_start + len(needle_context)
    needle_phrase = _normalized(phrase)
    matches = _positions(text.value, needle_phrase, context_start, context_end)
    if not matches:
        raise MentionLocationError(
            RejectionReason.PHRASE_NOT_IN_CONTEXT,
            "phrase does not occur in its context",
        )
    whole_words = [
        position
        for position in matches
        if _whole_word(text.value, position, position + len(needle_phrase))
    ]
    in_words = [position for position in matches if position not in whole_words]
    candidates = whole_words + in_words
    if occurrence is None:
        preferred = whole_words or in_words
        if len(preferred) > 1:
            raise MentionLocationError(
                RejectionReason.PHRASE_NOT_UNIQUE_IN_CONTEXT,
                f"phrase occurs {len(preferred)} times in its context; "
                "set occurrence",
            )
        chosen = preferred[0]
    else:
        if occurrence > len(candidates):
            raise MentionLocationError(
                RejectionReason.OCCURRENCE_OUT_OF_RANGE,
                f"occurrence {occurrence} exceeds {len(candidates)} matches",
            )
        chosen = candidates[occurrence - 1]
    last = chosen + len(needle_phrase) - 1
    return LocatedSpan(start=text.starts[chosen], end=text.ends[last])

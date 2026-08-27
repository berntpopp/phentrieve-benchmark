from dataclasses import dataclass, field
from unicodedata import normalize

from phentrieve_benchmark.models.annotation import EvidenceSpan


class TextBoundaryError(ValueError):
    """A source offset is not a stable canonical-text boundary."""


def _canonicalize_fragment(value: str) -> str:
    return normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


@dataclass(frozen=True)
class CanonicalTextMap:
    source_text: str
    canonical_text: str
    _utf16_boundaries: dict[int, int] = field(repr=False, compare=False)
    _canonical_boundaries: dict[int, int] = field(repr=False, compare=False)
    _canonical_before_trim: str = field(repr=False, compare=False)

    def _canonical_boundary(self, source_index: int) -> int:
        cached = self._canonical_boundaries.get(source_index)
        if cached is not None:
            return cached
        left = _canonicalize_fragment(self.source_text[:source_index])
        right = _canonicalize_fragment(self.source_text[source_index:])
        canonical_offset = len(left)
        if (
            left + right != self._canonical_before_trim
            or canonical_offset > len(self.canonical_text)
        ):
            raise TextBoundaryError(
                "offset is not a stable canonical-text boundary"
            )
        self._canonical_boundaries[source_index] = canonical_offset
        return canonical_offset

    def utf16_span(self, begin: int, end: int) -> EvidenceSpan:
        if type(begin) is not int or type(end) is not int:
            raise TypeError("UTF-16 offsets must be integers")
        if begin < 0 or end <= begin:
            raise TextBoundaryError("UTF-16 span must be nonempty and ordered")
        try:
            source_begin = self._utf16_boundaries[begin]
            source_end = self._utf16_boundaries[end]
        except KeyError as error:
            raise TextBoundaryError(
                "offset is not a UTF-16 code-point boundary"
            ) from error
        canonical_begin = self._canonical_boundary(source_begin)
        canonical_end = self._canonical_boundary(source_end)
        if canonical_end <= canonical_begin:
            raise TextBoundaryError("span is empty after canonicalization")

        snippet = self.canonical_text[canonical_begin:canonical_end]
        source_snippet = _canonicalize_fragment(
            self.source_text[source_begin:source_end]
        )
        if snippet != source_snippet:
            raise TextBoundaryError(
                "canonical span differs from canonicalized source span"
            )
        return EvidenceSpan(
            start_char=canonical_begin,
            end_char=canonical_end,
            text_snippet=snippet,
        )


def canonicalize_source_text(
    source_text: str,
    *,
    remove_terminal_format_newline: bool,
) -> CanonicalTextMap:
    if not isinstance(source_text, str):
        raise TypeError("source_text must be a string")
    canonical_before_trim = _canonicalize_fragment(source_text)
    canonical_text = canonical_before_trim
    if remove_terminal_format_newline and canonical_text.endswith("\n"):
        canonical_text = canonical_text[:-1]
    if not canonical_text:
        raise ValueError("canonical clinical text must not be empty")

    utf16_boundaries: dict[int, int] = {0: 0}
    utf16_offset = 0
    for index, character in enumerate(source_text, start=1):
        utf16_offset += len(character.encode("utf-16-le")) // 2
        utf16_boundaries[utf16_offset] = index

    return CanonicalTextMap(
        source_text=source_text,
        canonical_text=canonical_text,
        _utf16_boundaries=utf16_boundaries,
        _canonical_boundaries={0: 0},
        _canonical_before_trim=canonical_before_trim,
    )

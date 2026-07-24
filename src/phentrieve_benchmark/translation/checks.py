import re
from collections import Counter

from phentrieve_benchmark.models.translation import TranslationCheck

_NUMBER = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?")
_UNIT = re.compile(
    r"(?<!\w)(?:mg|kg|ml|mmhg|bpm|hz|mm|cm|°\s*c|g|l|m|%)(?!\w)",
    flags=re.IGNORECASE,
)


def _tokens(pattern: re.Pattern[str], text: str) -> Counter[str]:
    return Counter(
        match.replace(" ", "").replace(",", ".").casefold()
        for match in pattern.findall(text)
    )


def check_translation(
    *,
    source_text: str,
    translated_text: str,
    detected_language: str | None,
) -> tuple[TranslationCheck, ...]:
    ratio = len(translated_text) / len(source_text) if source_text else 0.0
    return (
        TranslationCheck(
            code="nonempty_output", passed=bool(translated_text.strip())
        ),
        TranslationCheck(
            code="source_changed", passed=translated_text != source_text
        ),
        TranslationCheck(
            code="length_ratio",
            passed=0.35 <= ratio <= 3.0,
            detail=f"{ratio:.3f}",
        ),
        TranslationCheck(
            code="numbers_preserved",
            passed=_tokens(_NUMBER, source_text)
            == _tokens(_NUMBER, translated_text),
        ),
        TranslationCheck(
            code="units_preserved",
            passed=_tokens(_UNIT, source_text) == _tokens(_UNIT, translated_text),
        ),
        TranslationCheck(
            code="target_language_de", passed=detected_language == "de"
        ),
    )


def detect_supported_language(text: str) -> str | None:
    from lingua import Language, LanguageDetectorBuilder

    detector = LanguageDetectorBuilder.from_languages(
        Language.GERMAN,
        Language.ENGLISH,
        Language.FRENCH,
        Language.SPANISH,
    ).build()
    language = detector.detect_language_of(text)
    return None if language is None else language.iso_code_639_1.name.lower()


def run_automatic_checks(
    source_text: str, translated_text: str
) -> tuple[TranslationCheck, ...]:
    return check_translation(
        source_text=source_text,
        translated_text=translated_text,
        detected_language=detect_supported_language(translated_text),
    )


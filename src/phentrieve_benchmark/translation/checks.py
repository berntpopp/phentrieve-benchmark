import re
import unicodedata

from phentrieve_benchmark.models.translation import TranslationCheck

# Unit atoms, longest first so that mmol/mmhg win over mm, and dl/ml over l.
_UNIT_ATOMS = (
    "mmhg",
    "mmol",
    "mosm",
    "bpm",
    "u/l",
    "µg",
    "ug",
    "µl",
    "ul",
    "mg",
    "kg",
    "ng",
    "ml",
    "dl",
    "mm",
    "cm",
    "hz",
    "ui",
    "iu",
    "ie",
    r"°\s*c",
    "%",
    "g",
    "l",
    "m",
)

# Units are only recognised as the tail of a value-unit pair. Matching them as
# free-standing tokens made "Ig G", "IgM" and "a.m." register as gram and metre,
# and it made a unit glued to its value in the source ("200mg", "67%") invisible
# while the spaced German form counted, so correct typography read as a defect.
_MEASUREMENT = re.compile(
    r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*("
    + "|".join(_UNIT_ATOMS)
    + r")?(?![\w])",
    flags=re.IGNORECASE,
)
_THOUSANDS = re.compile(r"^\d{1,3}(?:\.\d{3})+$")


def _value_key(value: str) -> str:
    normalized = value.replace(",", ".")
    if _THOUSANDS.match(normalized):
        return normalized.replace(".", "")
    return normalized


def _measurements(text: str) -> dict[str, set[str]]:
    """Map each numeric value in `text` to the units attached to it.

    Keyed by value rather than counted globally. A translation may legitimately
    repeat a unit the source states once ("20 y 33 mm" -> "20 mm bzw. 33 mm"),
    so a plain count reads that as an addition; keying by value does not.
    """
    measurements: dict[str, set[str]] = {}
    for match in _MEASUREMENT.finditer(unicodedata.normalize("NFC", text)):
        units = measurements.setdefault(_value_key(match.group(1)), set())
        if match.group(2) is not None:
            units.add(match.group(2).replace(" ", "").casefold())
    return measurements


def _added_units(source_text: str, translated_text: str) -> list[str]:
    """Units the translation attaches to a value that the source leaves bare.

    Only values present on both sides are compared, so a value the translation
    introduces on its own is out of scope here.
    """
    source = _measurements(source_text)
    added: set[str] = set()
    for value, units in _measurements(translated_text).items():
        if value in source:
            added |= units - source[value]
    return sorted(added)


def _paragraph_count(text: str) -> int:
    return sum(1 for line in text.split("\n") if line.strip())


def check_translation(
    *,
    source_text: str,
    translated_text: str,
    detected_language: str | None,
) -> tuple[TranslationCheck, ...]:
    ratio = len(translated_text) / len(source_text) if source_text else 0.0
    added_units = _added_units(source_text, translated_text)
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
            # The paragraph counts do not gate. They are recorded because a
            # changed count means source offsets no longer transfer, which
            # matters when annotations are anchored per paragraph.
            detail=(
                f"ratio={ratio:.3f} "
                f"paragraphs={_paragraph_count(source_text)}"
                f"/{_paragraph_count(translated_text)}"
            ),
        ),
        TranslationCheck(
            code="units_added",
            passed=not added_units,
            detail=", ".join(added_units) or None,
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

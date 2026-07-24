from fractions import Fraction

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.source_annotation import (
    SourceAnnotation,
    SourceAnnotationSet,
)
from phentrieve_benchmark.selection.metrics import (
    LengthStratum,
    Rational,
    build_e3c_inventory_record,
)


def _record(tokens: int):
    text = " ".join(f"t{i}" for i in range(tokens))
    document = Document.from_text(
        source_case_id="case",
        case_group_id="group",
        document_id="e3c:v2.0.0:en:case:native",
        language="en",
        translation_status=TranslationStatus.NATIVE,
        text=text,
    )
    source_set = SourceAnnotationSet(
        annotation_set_id="e3c:v2.0.0:en:case:source:v1",
        document_sha256=document.document_sha256,
        source_schema_id="webanno-uima-xmi/v2",
        annotations=(
            SourceAnnotation(source_annotation_id="1", source_type="EVENT"),
            SourceAnnotation(source_annotation_id="2", source_type="BODYPART"),
        ),
    )
    return build_e3c_inventory_record(
        document, source_set, sentence_count=3
    )


@pytest.mark.parametrize(
    ("tokens", "stratum"),
    [
        (199, LengthStratum.SHORT),
        (200, LengthStratum.MEDIUM),
        (400, LengthStratum.MEDIUM),
        (401, LengthStratum.LONG),
    ],
)
def test_inventory_uses_exact_length_boundaries(
    tokens: int, stratum: LengthStratum
) -> None:
    record = _record(tokens)
    assert record.whitespace_token_count == tokens
    assert record.codepoint_count == len(record.source_case_id) - len("case") + len(
        " ".join(f"t{i}" for i in range(tokens))
    )
    assert record.sentence_count == 3
    assert record.length_stratum is stratum
    assert dict(record.annotation_counts) == {"BODYPART": 1, "EVENT": 1}
    assert record.total_annotation_density.fraction() == Fraction(200, tokens)


def test_rational_reduces_and_rejects_binary_float() -> None:
    assert Rational.from_fraction(Fraction(6, 8)) == Rational(
        numerator=3, denominator=4
    )
    with pytest.raises(ValidationError):
        Rational(numerator=0.5, denominator=1)  # type: ignore[arg-type]

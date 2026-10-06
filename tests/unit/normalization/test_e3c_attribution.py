import pytest

from phentrieve_benchmark.normalization.e3c_attribution import (
    E3cReportAttribution,
    extract_attribution,
    render_attribution_markdown,
)

_XMI = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<xmi:XMI xmlns:xmi="http://www.omg.org/XMI" '
    'xmlns:custom="http:///webanno/custom.ecore">'
    '<custom:METADATA xmi:id="1" docName="{name}" docAuthor="{author}" '
    'docDOI="10.1/x" docUrl="https://example.org/x" docLicense="CC BY 4.0"/>'
    "</xmi:XMI>"
)


def _payload(name: str = "EN1", author: str = "A. Author; B. Author") -> bytes:
    return _XMI.format(name=name, author=author).encode()


def test_extracts_metadata_verbatim() -> None:
    record = extract_attribution(_payload(), language="en")
    assert record == E3cReportAttribution(
        source_case_id="EN1",
        language="en",
        author="A. Author; B. Author",
        doi="10.1/x",
        url="https://example.org/x",
        license="CC BY 4.0",
    )


def test_rejects_document_without_metadata() -> None:
    payload = b'<xmi:XMI xmlns:xmi="http://www.omg.org/XMI"/>'
    with pytest.raises(ValueError, match="exactly one METADATA"):
        extract_attribution(payload, language="en")


def test_renders_sorted_table_and_escapes_pipes() -> None:
    first = extract_attribution(_payload("FR2", "X | Y"), language="fr")
    second = extract_attribution(_payload("EN1"), language="en")
    markdown = render_attribution_markdown(
        [first, second], source_commit="f" * 40
    )
    rows = [line for line in markdown.splitlines() if line.startswith("| `")]
    assert rows[0].startswith("| `EN1` | en |")
    assert "X \\| Y" in rows[1]
    assert "f" * 40 in markdown


def test_rejects_duplicate_cases() -> None:
    record = extract_attribution(_payload(), language="en")
    with pytest.raises(ValueError, match="duplicate"):
        render_attribution_markdown([record, record], source_commit="f" * 40)

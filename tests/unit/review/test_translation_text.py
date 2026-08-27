from phentrieve_benchmark.provenance.canonical import canonical_text_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.review.translation_text import unified_text_diff


def test_unified_diff_normalizes_newlines_and_unicode() -> None:
    result = unified_text_diff("Cafe\u0301\r\n", "Café\nBefund\n")

    assert result.payload == ("--- tllm\n+++ reviewed\n@@ -1 +1,2 @@\n Café\n+Befund\n")


def test_unified_diff_preserves_intentional_whitespace() -> None:
    result = unified_text_diff("Befund\n", " Befund \n")

    assert result.payload == (
        "--- tllm\n+++ reviewed\n@@ -1 +1 @@\n-Befund\n+ Befund \n"
    )


def test_unified_diff_marks_single_lines_without_terminal_newlines() -> None:
    result = unified_text_diff("Alt", "Neu")

    assert result.payload == (
        "--- tllm\n"
        "+++ reviewed\n"
        "@@ -1 +1 @@\n"
        "-Alt\n"
        "\\ No newline at end of file\n"
        "+Neu\n"
        "\\ No newline at end of file\n"
    )
    assert result.proposed_text_sha256 == sha256_bytes(canonical_text_bytes("Neu"))


def test_unified_diff_marks_changed_final_lines_without_terminal_newlines() -> None:
    result = unified_text_diff("Erste Zeile\nAlt", "Erste Zeile\nNeu")

    assert result.payload == (
        "--- tllm\n"
        "+++ reviewed\n"
        "@@ -1,2 +1,2 @@\n"
        " Erste Zeile\n"
        "-Alt\n"
        "\\ No newline at end of file\n"
        "+Neu\n"
        "\\ No newline at end of file\n"
    )

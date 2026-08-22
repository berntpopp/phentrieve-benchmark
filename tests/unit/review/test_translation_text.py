from phentrieve_benchmark.review.translation_text import unified_text_diff


def test_unified_diff_normalizes_newlines_and_unicode() -> None:
    result = unified_text_diff("Cafe\u0301\r\n", "Café\nBefund\n")

    assert result.payload == ("--- tllm\n+++ reviewed\n@@ -1 +1,2 @@\n Café\n+Befund\n")


def test_unified_diff_preserves_intentional_whitespace() -> None:
    result = unified_text_diff("Befund\n", " Befund \n")

    assert result.payload == (
        "--- tllm\n+++ reviewed\n@@ -1 +1 @@\n-Befund\n+ Befund \n"
    )

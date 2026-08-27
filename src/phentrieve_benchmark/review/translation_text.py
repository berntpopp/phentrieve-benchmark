from difflib import unified_diff

from phentrieve_benchmark.models.translation_review import TranslationReviewDiff
from phentrieve_benchmark.provenance.canonical import canonical_text_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes

_NO_NEWLINE_NOTE = "\\ No newline at end of file\n"


def _diff_lines(text: str, marker: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    if lines and not text.endswith("\n"):
        lines[-1] = f"{lines[-1]}{marker}\n"
    return lines


def unified_text_diff(tllm: str, reviewed: str) -> TranslationReviewDiff:
    canonical_tllm = canonical_text_bytes(tllm).decode("utf-8")
    canonical_reviewed = canonical_text_bytes(reviewed).decode("utf-8")
    marker = "\0__PHENTRIEVE_MISSING_NEWLINE__\0"
    while marker in canonical_tllm or marker in canonical_reviewed:
        marker += "_"
    diff_lines = unified_diff(
        _diff_lines(canonical_tllm, marker),
        _diff_lines(canonical_reviewed, marker),
        fromfile="tllm",
        tofile="reviewed",
        n=3,
        lineterm="\n",
    )
    payload = "".join(
        line.replace(marker, "") + (_NO_NEWLINE_NOTE if marker in line else "")
        for line in diff_lines
    )
    return TranslationReviewDiff(
        tllm_text_sha256=sha256_bytes(canonical_tllm.encode("utf-8")),
        proposed_text_sha256=sha256_bytes(canonical_reviewed.encode("utf-8")),
        payload=payload,
    )

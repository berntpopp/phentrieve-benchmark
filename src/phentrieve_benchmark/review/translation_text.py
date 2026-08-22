from difflib import unified_diff

from phentrieve_benchmark.models.translation_review import TranslationReviewDiff
from phentrieve_benchmark.provenance.canonical import canonical_text_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes


def unified_text_diff(tllm: str, reviewed: str) -> TranslationReviewDiff:
    canonical_tllm = canonical_text_bytes(tllm).decode("utf-8")
    canonical_reviewed = canonical_text_bytes(reviewed).decode("utf-8")
    payload = "".join(
        unified_diff(
            canonical_tllm.splitlines(keepends=True),
            canonical_reviewed.splitlines(keepends=True),
            fromfile="tllm",
            tofile="reviewed",
            n=3,
            lineterm="\n",
        )
    )
    return TranslationReviewDiff(
        tllm_text_sha256=sha256_bytes(canonical_tllm.encode("utf-8")),
        proposed_text_sha256=sha256_bytes(canonical_reviewed.encode("utf-8")),
        payload=payload,
    )

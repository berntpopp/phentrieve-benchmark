"""Plan a proposal run: which corpus documents, in which batches."""

from collections.abc import Collection, Sequence
from hashlib import sha256

from phentrieve_benchmark.models.annotation_corpus import (
    AnnotationCorpusEntry,
    AnnotationCorpusManifest,
)
from phentrieve_benchmark.models.hpo_proposal import BatchDocument, ProposalBatch
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationLanguage,
)
from phentrieve_benchmark.selection.metrics import LengthStratum

PILOT_SEED = "phentrieve-e3c-proposal-pilot-v1"
PILOT_LANGUAGES: tuple[AnnotationLanguage, ...] = ("en", "fr", "es")
PROMPT_PLACEHOLDERS = ("{run_id}", "{batch_id}", "{output_path}", "{documents}")


def _seeded(case_id: str) -> bytes:
    return sha256(f"{PILOT_SEED}\0{case_id}".encode()).digest()


def pilot_case_ids(
    corpus: AnnotationCorpusManifest, groups: AnnotationGroupManifest
) -> tuple[str, ...]:
    """One report per original language and length stratum, by seeded hash."""
    if corpus.groups_sha256 != sha256_bytes(groups.canonical_bytes()):
        raise ValueError("corpus was built from a different group manifest")
    strata = {record.source_case_id: record.length_stratum for record in groups.records}
    chosen: list[str] = []
    for language in PILOT_LANGUAGES:
        for stratum in LengthStratum:
            candidates = [
                entry.source_case_id
                for entry in corpus.entries
                if entry.annotation_language == language
                and strata[entry.source_case_id] is stratum
            ]
            if candidates:
                chosen.append(min(candidates, key=_seeded))
    return tuple(sorted(chosen))


def select_run_entries(
    corpus: AnnotationCorpusManifest,
    *,
    languages: Collection[AnnotationLanguage] | None,
    case_ids: Collection[str] | None,
) -> tuple[AnnotationCorpusEntry, ...]:
    entries = [
        entry
        for entry in corpus.entries
        if (languages is None or entry.annotation_language in languages)
        and (case_ids is None or entry.source_case_id in case_ids)
    ]
    if case_ids is not None:
        missing = set(case_ids) - {entry.source_case_id for entry in entries}
        if missing:
            raise ValueError(f"cases not in the corpus: {sorted(missing)}")
    if not entries:
        message = "no corpus document matches the selection"
        if (languages is None or "de" in languages) and corpus.pending_review:
            message += (
                f"; {len(corpus.pending_review)} German reports pending "
                "translation review"
            )
        raise ValueError(message)
    return tuple(
        sorted(
            entries,
            key=lambda entry: (entry.annotation_language, entry.source_case_id),
        )
    )


def plan_batches(
    entries: Sequence[AnnotationCorpusEntry], *, batch_size: int
) -> tuple[ProposalBatch, ...]:
    if batch_size < 1:
        raise ValueError("batch size must be positive")
    return tuple(
        ProposalBatch(
            batch_id=f"batch-{number:02d}",
            documents=tuple(
                BatchDocument(
                    document_id=entry.document_id,
                    document_sha256=entry.document_sha256,
                    source_case_id=entry.source_case_id,
                    annotation_language=entry.annotation_language,
                )
                for entry in entries[start : start + batch_size]
            ),
        )
        for number, start in enumerate(range(0, len(entries), batch_size), start=1)
    )


def render_batch_prompt(
    template: str,
    *,
    run_id: str,
    batch_id: str,
    output_path: str,
    documents: str,
) -> str:
    """Fill the batch placeholders; the template may contain literal JSON."""
    missing = [p for p in PROMPT_PLACEHOLDERS if p not in template]
    if missing:
        raise ValueError(f"prompt template lacks placeholders: {missing}")
    return (
        template.replace("{run_id}", run_id)
        .replace("{batch_id}", batch_id)
        .replace("{output_path}", output_path)
        .replace("{documents}", documents)
    )

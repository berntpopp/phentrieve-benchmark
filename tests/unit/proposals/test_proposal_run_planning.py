from collections import Counter
from fractions import Fraction
from typing import Literal

import pytest

from phentrieve_benchmark.models.annotation_corpus import (
    AnnotationCorpusEntry,
    AnnotationCorpusManifest,
)
from phentrieve_benchmark.proposals.run import (
    pilot_case_ids,
    plan_batches,
    render_batch_prompt,
    select_run_entries,
)
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationGroupRecord,
    AnnotationLanguage,
)
from phentrieve_benchmark.selection.metrics import LengthStratum, Rational

_SOURCES: tuple[Literal["en", "fr", "es"], ...] = ("en", "fr", "es")


def _record(
    case_id: str,
    source: Literal["en", "fr", "es"],
    language: AnnotationLanguage,
    stratum: LengthStratum,
) -> AnnotationGroupRecord:
    return AnnotationGroupRecord(
        source_case_id=case_id,
        source_language=source,
        annotation_language=language,
        document_sha256=sha256_bytes(case_id.encode()),
        length_stratum=stratum,
        total_annotation_density=Rational.from_fraction(Fraction(1)),
    )


def _groups() -> AnnotationGroupManifest:
    records = [
        _record(f"{source.upper()}{stratum.value}{index}", source, source, stratum)
        for source in _SOURCES
        for stratum in LengthStratum
        for index in range(2)
    ]
    records += [
        _record(f"ENDE{index}", "en", "de", LengthStratum.SHORT) for index in range(2)
    ]
    return AnnotationGroupManifest(
        inventory_sha256="a" * 64, records=tuple(records), aggregate_sha256="b" * 64
    )


def _entry(record: AnnotationGroupRecord) -> AnnotationCorpusEntry:
    german = record.annotation_language == "de"
    return AnnotationCorpusEntry(
        source_case_id=record.source_case_id,
        annotation_language=record.annotation_language,
        document_id=f"doc:{record.annotation_language}:{record.source_case_id}",
        document_sha256=sha256_bytes(record.source_case_id.encode()),
        review_import_sha256="c" * 64 if german else None,
        translation_review_record_sha256="d" * 64 if german else None,
    )


def _corpus(
    groups: AnnotationGroupManifest, *, german_reviewed: bool = True
) -> AnnotationCorpusManifest:
    entries = [
        _entry(record)
        for record in groups.records
        if german_reviewed or record.annotation_language != "de"
    ]
    pending = () if german_reviewed else groups.case_ids("de")
    return AnnotationCorpusManifest(
        groups_sha256=sha256_bytes(groups.canonical_bytes()),
        native_documents_sha256="e" * 64,
        documents_sha256="f" * 64,
        entries=tuple(entries),
        pending_review=pending,
    )


def test_pilot_takes_one_report_per_original_language_and_stratum() -> None:
    groups = _groups()
    case_ids = pilot_case_ids(_corpus(groups), groups)
    strata = {r.source_case_id: r for r in groups.records}
    cells = Counter(
        (strata[case_id].annotation_language, strata[case_id].length_stratum)
        for case_id in case_ids
    )
    assert len(case_ids) == 9
    assert set(cells.values()) == {1}
    assert all(language != "de" for language, _ in cells)
    assert case_ids == pilot_case_ids(_corpus(groups), groups)


def test_pilot_rejects_a_corpus_from_another_group_manifest() -> None:
    groups = _groups()
    corpus = _corpus(groups).model_copy(update={"groups_sha256": "0" * 64})
    with pytest.raises(ValueError, match="different group manifest"):
        pilot_case_ids(corpus, groups)


def test_selection_filters_languages_and_sorts_by_language_and_case() -> None:
    entries = select_run_entries(
        _corpus(_groups()), languages=("fr", "de"), case_ids=None
    )
    assert [entry.source_case_id for entry in entries][:3] == [
        "ENDE0",
        "ENDE1",
        "FRlong0",
    ]
    assert {entry.annotation_language for entry in entries} == {"de", "fr"}


def test_selection_explains_pending_german_reports() -> None:
    corpus = _corpus(_groups(), german_reviewed=False)
    with pytest.raises(ValueError, match="2 German reports pending"):
        select_run_entries(corpus, languages=("de",), case_ids=None)


def test_selection_rejects_cases_outside_the_corpus() -> None:
    with pytest.raises(ValueError, match="not in the corpus"):
        select_run_entries(_corpus(_groups()), languages=None, case_ids=("XX1",))


def test_batches_have_the_requested_size_and_numbered_ids() -> None:
    entries = select_run_entries(_corpus(_groups()), languages=("en",), case_ids=None)
    batches = plan_batches(entries, batch_size=4)
    assert [batch.batch_id for batch in batches] == ["batch-01", "batch-02"]
    assert [len(batch.documents) for batch in batches] == [4, 2]


def test_prompt_rendering_fills_every_placeholder() -> None:
    template = "Run {run_id} {batch_id} -> {output_path}\n{documents}\n{run_id}"
    rendered = render_batch_prompt(
        template,
        run_id="pilot-v1",
        batch_id="batch-01",
        output_path="out.json",
        documents="1. doc",
    )
    assert rendered == "Run pilot-v1 batch-01 -> out.json\n1. doc\npilot-v1"


def test_prompt_template_must_contain_every_placeholder() -> None:
    with pytest.raises(ValueError, match="documents"):
        render_batch_prompt(
            "{run_id} {batch_id} {output_path}",
            run_id="r",
            batch_id="b",
            output_path="o",
            documents="d",
        )

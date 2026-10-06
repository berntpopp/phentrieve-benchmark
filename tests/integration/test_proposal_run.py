import json
from collections.abc import Collection
from datetime import date
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation_corpus import (
    AnnotationCorpusEntry,
    AnnotationCorpusManifest,
)
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.hpo_proposal import (
    PROPOSAL_PROVENANCE,
    ProposalRun,
    ProposalValidationReport,
)
from phentrieve_benchmark.ontology.hpo import load_hpo_index
from phentrieve_benchmark.pipeline.proposals import (
    GuidelineVersion,
    prepare_proposal_run,
    validate_run_directory,
)
from phentrieve_benchmark.provenance.canonical import canonical_jsonl_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import (
    AnnotationGroupManifest,
    AnnotationGroupRecord,
    AnnotationLanguage,
)
from phentrieve_benchmark.selection.metrics import LengthStratum, Rational
from tests.fixtures.hpo import proposal_hpo_obo

_TEMPLATE = b"Run {run_id}, batch {batch_id}.\nWrite {output_path}.\n\n{documents}\n"
_ENGLISH = Document.from_text(
    source_case_id="EN1",
    case_group_id="e3c:v2.0.0:EN1",
    document_id="e3c:v2.0.0:en:EN1:native",
    language="en",
    translation_status=TranslationStatus.NATIVE,
    text="Fever and cough.",
)
_GERMAN = Document.from_text(
    source_case_id="EN2",
    case_group_id="e3c:v2.0.0:EN2",
    document_id="e3c:v2.0.0:de:EN2:translated",
    language="de",
    translation_status=TranslationStatus.TRANSLATED,
    text="Kein Fieber, aber \u201eHusten\u201c seit\u00a0zwei Tagen.",
)


def _groups() -> AnnotationGroupManifest:
    def record(
        case_id: str, language: AnnotationLanguage
    ) -> AnnotationGroupRecord:
        return AnnotationGroupRecord(
            source_case_id=case_id,
            source_language="en",
            annotation_language=language,
            document_sha256=sha256_bytes(case_id.encode()),
            length_stratum=LengthStratum.SHORT,
            total_annotation_density=Rational.from_fraction(Fraction(1)),
        )

    return AnnotationGroupManifest(
        inventory_sha256="a" * 64,
        records=(record("EN1", "en"), record("EN2", "de")),
        aggregate_sha256="b" * 64,
    )


def _corpus(store: ArtifactStore, *, german_reviewed: bool = True) -> str:
    documents = (_ENGLISH, _GERMAN) if german_reviewed else (_ENGLISH,)
    documents_sha256 = store.put_bytes(
        canonical_jsonl_bytes(
            [document.model_dump(mode="json") for document in documents],
            identity_key="document_id",
        )
    )
    entries = [
        AnnotationCorpusEntry(
            source_case_id="EN1",
            annotation_language="en",
            document_id=_ENGLISH.document_id,
            document_sha256=_ENGLISH.document_sha256,
        )
    ]
    if german_reviewed:
        entries.append(
            AnnotationCorpusEntry(
                source_case_id="EN2",
                annotation_language="de",
                document_id=_GERMAN.document_id,
                document_sha256=_GERMAN.document_sha256,
                review_import_sha256="e" * 64,
                translation_review_record_sha256="f" * 64,
            )
        )
    manifest = AnnotationCorpusManifest(
        groups_sha256=sha256_bytes(_groups().canonical_bytes()),
        native_documents_sha256="d" * 64,
        documents_sha256=documents_sha256,
        entries=tuple(entries),
        pending_review=() if german_reviewed else ("EN2",),
    )
    return store.put_bytes(manifest.canonical_bytes())


def _prepare(
    tmp_path: Path,
    store: ArtifactStore,
    corpus_sha256: str,
    *,
    languages: Collection[AnnotationLanguage] | None = None,
) -> ProposalRun:
    return prepare_proposal_run(
        store=store,
        repository_root=tmp_path,
        corpus_manifest_sha256=corpus_sha256,
        groups=_groups(),
        run_id="synthetic-v1",
        model_id="claude-sonnet-5-5",
        run_date=date(2026, 10, 7),
        prompt_template=_TEMPLATE,
        guideline=GuidelineVersion(
            path="docs/annotation-guidelines/hpo-span-annotation.md",
            commit="1" * 40,
            sha256="2" * 64,
        ),
        hpo_release="v2026-06-23",
        ontology_sha256=sha256(proposal_hpo_obo()).hexdigest(),
        languages=languages,
        pilot=False,
        batch_size=1,
        run_directory=tmp_path / "datasets/e3c-de/proposals/synthetic-v1",
        input_directory=tmp_path / ".artifacts/proposals/synthetic-v1",
    )


def _annotation(
    proposal_id: str, hpo_id: str, label: str, assertion: str, phrase: str, context: str
) -> dict[str, Any]:
    return {
        "proposal_id": proposal_id,
        "hpo_id": hpo_id,
        "hpo_label": label,
        "assertion": assertion,
        "experiencer": "patient",
        "temporality": "current",
        "verbalized": True,
        "mentions": [{"phrase": phrase, "context": context}],
        "note": None,
    }


def _batch_output(
    batch_id: str, document: Document, annotations: list[dict[str, Any]]
) -> bytes:
    payload = {
        "schema_version": "e3c-hpo-proposal-batch/v1",
        "provenance": PROPOSAL_PROVENANCE,
        "run_id": "synthetic-v1",
        "batch_id": batch_id,
        "reports": [
            {
                "document_id": document.document_id,
                "document_sha256": document.document_sha256,
                "annotations": annotations,
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode()


def test_german_report_goes_end_to_end_from_corpus_to_validation(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "objects")
    run = _prepare(tmp_path, store, _corpus(store))
    run_directory = tmp_path / "datasets/e3c-de/proposals/synthetic-v1"
    assert [batch.documents[0].document_id for batch in run.batches] == [
        _GERMAN.document_id,
        _ENGLISH.document_id,
    ]
    batch_input = tmp_path / ".artifacts/proposals/synthetic-v1/batch-01"
    assert (batch_input / "EN2.txt").read_bytes() == _GERMAN.text.encode()
    prompt = (run_directory / "batch-01.prompt.md").read_text(encoding="utf-8")
    assert "Write datasets/e3c-de/proposals/synthetic-v1/batch-01.json." in prompt
    assert ".artifacts/proposals/synthetic-v1/batch-01/EN2.txt" in prompt
    assert _GERMAN.document_sha256 in prompt
    assert _GERMAN.text not in prompt
    assert (run_directory / "prompt.md").read_bytes() == _TEMPLATE
    assert (run_directory / "run.json").read_bytes() == run.canonical_bytes()
    assert run.pending_review == ()

    outputs = {
        "batch-01": _batch_output(
            "batch-01",
            _GERMAN,
            [
                _annotation(
                    "p001",
                    "HP:0001945",
                    "Fever",
                    "absent",
                    "Fieber",
                    "Kein Fieber, aber",
                ),
                _annotation(
                    "p002", "HP:0012735", "Cough", "present", "Husten",
                    '"Husten" seit zwei Tagen',
                ),
            ],
        ),
        "batch-02": _batch_output(
            "batch-02",
            _ENGLISH,
            [
                _annotation(
                    "p001", "HP:0001945", "Fever", "present", "Fever", "Fever and"
                )
            ],
        ),
    }
    for batch_id, raw in outputs.items():
        (run_directory / f"{batch_id}.json").write_bytes(raw)

    body = proposal_hpo_obo()
    index = load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )
    report, digest = validate_run_directory(
        run_directory=run_directory, store=store, hpo_index=index
    )

    validation_bytes = (run_directory / "validation.json").read_bytes()
    assert digest == sha256_bytes(validation_bytes)
    assert (
        ProposalValidationReport.model_validate_json(validation_bytes, strict=True)
        == report
    )
    assert report.run_sha256 == sha256_bytes(run.canonical_bytes())
    assert report.rejections == ()
    german = next(d for d in report.documents if d.document_id == _GERMAN.document_id)
    cough = next(p for p in german.proposals if p.hpo_id == "HP:0012735")
    (mention,) = cough.mentions
    assert _GERMAN.text[mention.start : mention.end] == "Husten" == mention.phrase
    for batch_id, raw in outputs.items():
        assert (run_directory / f"{batch_id}.json").read_bytes() == raw


def test_existing_run_is_not_overwritten(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    corpus_sha256 = _corpus(store)
    _prepare(tmp_path, store, corpus_sha256)
    with pytest.raises(FileExistsError, match="synthetic-v1"):
        _prepare(tmp_path, store, corpus_sha256)


def test_german_run_stops_while_reviews_are_pending(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    corpus_sha256 = _corpus(store, german_reviewed=False)
    with pytest.raises(ValueError, match="1 German reports pending"):
        _prepare(tmp_path, store, corpus_sha256, languages=("de",))
    assert not (tmp_path / "datasets/e3c-de/proposals/synthetic-v1").exists()


def test_run_records_german_reports_left_out_as_pending(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    corpus_sha256 = _corpus(store, german_reviewed=False)
    run = _prepare(tmp_path, store, corpus_sha256, languages=("en", "de"))
    assert [batch.documents[0].source_case_id for batch in run.batches] == ["EN1"]
    assert run.pending_review == ("EN2",)


def test_validation_rejects_a_changed_prompt(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "objects")
    _prepare(tmp_path, store, _corpus(store))
    run_directory = tmp_path / "datasets/e3c-de/proposals/synthetic-v1"
    (run_directory / "prompt.md").write_bytes(b"edited")
    body = proposal_hpo_obo()
    index = load_hpo_index(
        body, release="v2026-06-23", ontology_sha256=sha256(body).hexdigest()
    )
    with pytest.raises(ValueError, match=r"prompt\.md"):
        validate_run_directory(
            run_directory=run_directory, store=store, hpo_index=index
        )

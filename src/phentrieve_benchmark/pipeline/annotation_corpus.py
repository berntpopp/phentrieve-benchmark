"""Build the annotation corpus: every E3C report in its annotation language.

Original-language reports reuse the verified native documents. German
reports use only text from an accepted translation review; reports without
one are listed as pending and left out. Review imports are applied in the
order given and the last decision for a case wins, so a later acceptance
replaces an earlier one and a later rejection or question makes it pending.
"""

from collections.abc import Sequence

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.annotation_corpus import (
    AnnotationCorpusEntry,
    AnnotationCorpusManifest,
)
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.models.translation_review import (
    TranslationReviewDecision,
    TranslationReviewImportManifest,
    TranslationReviewRecord,
)
from phentrieve_benchmark.provenance.canonical import canonical_jsonl_bytes
from phentrieve_benchmark.provenance.digests import sha256_bytes
from phentrieve_benchmark.selection.groups import AnnotationGroupManifest

_ACCEPTED = {
    TranslationReviewDecision.ACCEPTED_UNCHANGED,
    TranslationReviewDecision.ACCEPTED_CORRECTED,
}


def _read_documents(store: ArtifactStore, digest: str) -> dict[str, Document]:
    documents: dict[str, Document] = {}
    for line in store.read_bytes(digest).splitlines():
        if not line:
            continue
        document = Document.model_validate_json(line, strict=True)
        if document.source_case_id in documents:
            raise ValueError(
                f"more than one native document for {document.source_case_id}"
            )
        documents[document.source_case_id] = document
    return documents


def _accepted_reviews(
    store: ArtifactStore, review_import_sha256s: Sequence[str]
) -> dict[str, tuple[str, str, TranslationReviewRecord]]:
    accepted: dict[str, tuple[str, str, TranslationReviewRecord]] = {}
    for import_sha256 in review_import_sha256s:
        manifest = TranslationReviewImportManifest.model_validate_json(
            store.read_bytes(import_sha256), strict=True
        )
        seen: set[str] = set()
        for entry in manifest.entries:
            if entry.source_case_id in seen:
                raise ValueError(
                    f"case {entry.source_case_id} appears twice in one review import"
                )
            seen.add(entry.source_case_id)
            record = TranslationReviewRecord.model_validate_json(
                store.read_bytes(entry.record_sha256), strict=True
            )
            if (
                entry.source_case_id != record.source_case_id
                or entry.proposed_text_sha256 != record.proposed_text_sha256
            ):
                raise ValueError(
                    f"review import entry for {entry.source_case_id} does not "
                    "match its review record"
                )
            if record.decision in _ACCEPTED:
                accepted[entry.source_case_id] = (
                    import_sha256,
                    entry.record_sha256,
                    record,
                )
            else:
                accepted.pop(entry.source_case_id, None)
    return accepted


def _german_document(
    store: ArtifactStore, source: Document, record: TranslationReviewRecord
) -> Document:
    if record.source_text_sha256 != source.document_sha256:
        raise ValueError(
            f"review for {source.source_case_id} does not match the native source text"
        )
    version_prefix = source.case_group_id.rsplit(":", 1)[0]
    document = Document.from_text(
        source_case_id=source.source_case_id,
        case_group_id=source.case_group_id,
        document_id=f"{version_prefix}:de:{source.source_case_id}:translated",
        language="de",
        translation_status=TranslationStatus.TRANSLATED,
        text=store.read_bytes(record.proposed_text_sha256).decode("utf-8"),
    )
    if document.document_sha256 != record.proposed_text_sha256:
        raise ValueError(
            f"corpus text for {source.source_case_id} is not the reviewed text"
        )
    return document


def build_annotation_corpus(
    *,
    store: ArtifactStore,
    groups: AnnotationGroupManifest,
    native_documents_sha256: str,
    review_import_sha256s: Sequence[str],
) -> str:
    """Store the corpus documents and manifest; return the manifest hash."""
    native = _read_documents(store, native_documents_sha256)
    reviews = _accepted_reviews(store, review_import_sha256s)
    documents: list[Document] = []
    entries: list[AnnotationCorpusEntry] = []
    pending: list[str] = []
    for group_record in groups.records:
        case_id = group_record.source_case_id
        source = native.get(case_id)
        if source is None:
            raise ValueError(f"native document for {case_id} is missing")
        if source.document_sha256 != group_record.document_sha256:
            raise ValueError(
                f"native document for {case_id} does not match the group manifest"
            )
        if group_record.annotation_language != "de":
            documents.append(source)
            entries.append(
                AnnotationCorpusEntry(
                    source_case_id=case_id,
                    annotation_language=group_record.annotation_language,
                    document_id=source.document_id,
                    document_sha256=source.document_sha256,
                )
            )
            continue
        review = reviews.get(case_id)
        if review is None:
            pending.append(case_id)
            continue
        import_sha256, record_sha256, record = review
        document = _german_document(store, source, record)
        documents.append(document)
        entries.append(
            AnnotationCorpusEntry(
                source_case_id=case_id,
                annotation_language="de",
                document_id=document.document_id,
                document_sha256=document.document_sha256,
                review_import_sha256=import_sha256,
                review_record_sha256=record_sha256,
            )
        )
    documents_sha256 = store.put_bytes(
        canonical_jsonl_bytes(
            [document.model_dump(mode="json") for document in documents],
            identity_key="document_id",
        )
    )
    manifest = AnnotationCorpusManifest(
        groups_sha256=sha256_bytes(groups.canonical_bytes()),
        native_documents_sha256=native_documents_sha256,
        documents_sha256=documents_sha256,
        entries=tuple(entries),
        pending_review=tuple(pending),
    )
    return store.put_bytes(manifest.canonical_bytes())

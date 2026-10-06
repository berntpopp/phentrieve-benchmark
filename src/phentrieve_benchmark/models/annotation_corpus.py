from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class AnnotationCorpusEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_case_id: str = Field(min_length=1)
    annotation_language: Literal["de", "en", "fr", "es"]
    document_id: str = Field(min_length=1)
    document_sha256: Sha256Hex
    review_import_sha256: Sha256Hex | None = None
    translation_review_record_sha256: Sha256Hex | None = None

    @model_validator(mode="after")
    def german_entries_cite_their_review(self) -> Self:
        cites_review = (
            self.review_import_sha256 is not None
            and self.translation_review_record_sha256 is not None
        )
        no_review = (
            self.review_import_sha256 is None
            and self.translation_review_record_sha256 is None
        )
        if self.annotation_language == "de" and not cites_review:
            raise ValueError("German corpus entries must cite their review")
        if self.annotation_language != "de" and not no_review:
            raise ValueError("original-language entries have no translation review")
        return self


class AnnotationCorpusManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["e3c-annotation-corpus/v1"] = "e3c-annotation-corpus/v1"
    groups_sha256: Sha256Hex
    native_documents_sha256: Sha256Hex
    documents_sha256: Sha256Hex
    entries: tuple[AnnotationCorpusEntry, ...]
    pending_review: tuple[str, ...] = ()

    @field_validator("entries")
    @classmethod
    def sort_entries(
        cls, entries: tuple[AnnotationCorpusEntry, ...]
    ) -> tuple[AnnotationCorpusEntry, ...]:
        return tuple(sorted(entries, key=lambda entry: entry.source_case_id))

    @field_validator("pending_review")
    @classmethod
    def sort_pending(cls, pending: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(pending))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

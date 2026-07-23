from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from phentrieve_benchmark.provenance.canonical import canonical_text_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class TranslationStatus(StrEnum):
    NATIVE = "native"
    TRANSLATED = "translated"


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_case_id: str = Field(min_length=1)
    case_group_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    language: str = Field(pattern=r"^[a-z]{2}$")
    translation_status: TranslationStatus
    text: str = Field(min_length=1)
    document_sha256: Sha256Hex

    @classmethod
    def from_text(
        cls,
        *,
        source_case_id: str,
        case_group_id: str,
        document_id: str,
        language: str,
        translation_status: TranslationStatus,
        text: str,
    ) -> Self:
        canonical_bytes = canonical_text_bytes(text)
        return cls(
            source_case_id=source_case_id,
            case_group_id=case_group_id,
            document_id=document_id,
            language=language,
            translation_status=translation_status,
            text=canonical_bytes.decode(),
            document_sha256=sha256_bytes(canonical_bytes),
        )

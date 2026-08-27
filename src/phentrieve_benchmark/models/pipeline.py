import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal
from unicodedata import category, normalize

from pydantic import BaseModel, ConfigDict, Field, field_validator

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes

_SAFE_ID = re.compile(r"[a-z][a-z0-9_.:/-]*", re.ASCII)
_WINDOWS_DRIVE = re.compile(r"[A-Za-z]:")


def _safe_identifier(value: str) -> str:
    canonical = normalize("NFC", value)
    if _SAFE_ID.fullmatch(canonical) is None:
        raise ValueError("value must be a safe lowercase ASCII identifier")
    return canonical


def _canonical_relative_posix_path(value: str) -> str:
    if value != normalize("NFC", value):
        raise ValueError("path must use NFC")
    if (
        not value
        or value.startswith("/")
        or value.startswith("//")
        or _WINDOWS_DRIVE.match(value) is not None
        or "\\" in value
        or "//" in value
        or any(category(character).startswith("C") for character in value)
    ):
        raise ValueError("path must be a canonical relative POSIX path")
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("path must not contain empty, dot, or parent segments")
    if path.is_absolute() or path.as_posix() != value:
        raise ValueError("path must be a canonical relative POSIX path")
    return value


class ArchiveFormat(StrEnum):
    ZIP = "zip"
    TAR = "tar"


class ArtifactReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_id: str = Field(min_length=1)
    sha256: Sha256Hex
    byte_length: int = Field(ge=0)
    record_count: int | None = Field(default=None, ge=0)

    @field_validator("schema_id")
    @classmethod
    def schema_id_is_safe(cls, value: str) -> str:
        return _safe_identifier(value)


class WarningCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: str = Field(min_length=1)
    count: int = Field(ge=0)

    @field_validator("code")
    @classmethod
    def code_is_safe(cls, value: str) -> str:
        return _safe_identifier(value)


class SourceMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    sha256: Sha256Hex
    byte_length: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def path_is_canonical(cls, value: str) -> str:
        return _canonical_relative_posix_path(value)


class SourceSnapshotManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["source-snapshot-manifest/v1"] = (
        "source-snapshot-manifest/v1"
    )
    source_id: str = Field(min_length=1)
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    recipe_sha256: Sha256Hex
    archive_sha256: Sha256Hex
    archive_byte_length: int = Field(ge=0)
    archive_format: ArchiveFormat
    members: tuple[SourceMember, ...]

    @field_validator("source_id")
    @classmethod
    def source_id_is_safe(cls, value: str) -> str:
        return _safe_identifier(value)

    @field_validator("members")
    @classmethod
    def canonicalize_members(
        cls, members: tuple[SourceMember, ...]
    ) -> tuple[SourceMember, ...]:
        identities = [member.path for member in members]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate source member path")
        return tuple(sorted(members, key=lambda member: member.path))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())


class NormalizationCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    language: str | None = Field(default=None, pattern=r"^[a-z]{2}$")
    record_type: str = Field(min_length=1)
    count: int = Field(ge=0)

    @field_validator("record_type")
    @classmethod
    def record_type_is_safe(cls, value: str) -> str:
        return _safe_identifier(value)


class NormalizationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["normalization-manifest/v1"] = (
        "normalization-manifest/v1"
    )
    target_id: str = Field(min_length=1)
    source_snapshot_sha256: Sha256Hex
    recipe_sha256: Sha256Hex
    adapter_id: str = Field(min_length=1)
    code_sha256: Sha256Hex
    documents: ArtifactReference
    annotations: ArtifactReference | None = None
    source_annotations: ArtifactReference | None = None
    source_sidecar: ArtifactReference | None = None
    inventory: ArtifactReference
    counts: tuple[NormalizationCount, ...] = ()
    warnings: tuple[WarningCount, ...] = ()

    @field_validator("target_id", "adapter_id")
    @classmethod
    def identifiers_are_safe(cls, value: str) -> str:
        return _safe_identifier(value)

    @field_validator("counts")
    @classmethod
    def canonicalize_counts(
        cls, counts: tuple[NormalizationCount, ...]
    ) -> tuple[NormalizationCount, ...]:
        identities = [
            (count.language or "", count.record_type) for count in counts
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate normalization count identity")
        return tuple(
            sorted(
                counts,
                key=lambda count: (count.language or "", count.record_type),
            )
        )

    @field_validator("warnings")
    @classmethod
    def canonicalize_warnings(
        cls, warnings: tuple[WarningCount, ...]
    ) -> tuple[WarningCount, ...]:
        identities = [warning.code for warning in warnings]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate warning identity")
        return tuple(sorted(warnings, key=lambda warning: warning.code))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())


class ProvenanceSubjectRole(StrEnum):
    SOURCE_SNAPSHOT = "source_snapshot"
    NORMALIZATION_MANIFEST = "normalization_manifest"
    SELECTION_MANIFEST = "selection_manifest"
    TRANSLATION_MANIFEST = "translation_manifest"
    UMLS_HPO_MAPPING_MANIFEST = "umls_hpo_mapping_manifest"
    CURATED_ANNOTATION_SET = "curated_annotation_set"
    REVIEW_DECISION_SET = "review_decision_set"
    SINGLE_TERM_SELECTION = "single_term_selection"
    SINGLE_TERM_SET = "single_term_set"


class ProvenanceRunLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["provenance-run-link/v1"] = "provenance-run-link/v1"
    subject_role: ProvenanceSubjectRole
    subject_sha256: Sha256Hex
    run_manifest_sha256: Sha256Hex

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))

    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

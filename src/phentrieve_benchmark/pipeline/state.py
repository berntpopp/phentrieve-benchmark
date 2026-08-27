import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from phentrieve_benchmark.artifacts.store import (
    ArtifactCorruptionError,
    ArtifactStore,
)
from phentrieve_benchmark.models.mapping import E3cMappingStageManifest
from phentrieve_benchmark.models.pipeline import (
    NormalizationManifest,
    ProvenanceSubjectRole,
    SourceSnapshotManifest,
)
from phentrieve_benchmark.models.translation import TranslationManifest
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes


class StagePointer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["stage-pointer/v1"] = "stage-pointer/v1"
    subject_role: ProvenanceSubjectRole
    subject_sha256: Sha256Hex
    semantic_hashes: dict[str, Sha256Hex]

    @field_validator("semantic_hashes")
    @classmethod
    def semantic_hash_names_are_closed(
        cls, values: dict[str, str]
    ) -> dict[str, str]:
        if not values:
            raise ValueError("semantic hashes must not be empty")
        if any(
            not name.endswith("_sha256")
            or not name.replace("_", "").isascii()
            or not name.replace("_", "").isalnum()
            or name.lower() != name
            for name in values
        ):
            raise ValueError("invalid semantic hash name")
        return dict(sorted(values.items()))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))


class StageState:
    def __init__(self, root: Path, store: ArtifactStore) -> None:
        self.root = root
        self.store = store

    @staticmethod
    def semantic_key(semantic_hashes: dict[str, str]) -> str:
        validated = StagePointer(
            subject_role=ProvenanceSubjectRole.SOURCE_SNAPSHOT,
            subject_sha256="0" * 64,
            semantic_hashes=semantic_hashes,
        )
        return sha256_bytes(
            canonical_json_bytes(validated.semantic_hashes)
        )

    def path_for(
        self, stage: str, target: str, semantic_hashes: dict[str, str]
    ) -> Path:
        if stage not in {
            "acquire",
            "normalize",
            "select",
            "translate",
            "map-hpo",
        }:
            raise ValueError("invalid stage")
        if target not in {"e3c", "raghpo", "csc", "gsc"}:
            raise ValueError("invalid target")
        return self.root / stage / target / (
            f"{self.semantic_key(semantic_hashes)}.json"
        )

    def publish(
        self,
        *,
        stage: str,
        target: str,
        subject_role: ProvenanceSubjectRole,
        subject_sha256: str,
        semantic_hashes: dict[str, str],
    ) -> StagePointer:
        self.store.read_bytes(subject_sha256)
        pointer = StagePointer(
            subject_role=subject_role,
            subject_sha256=subject_sha256,
            semantic_hashes=semantic_hashes,
        )
        destination = self.path_for(stage, target, semantic_hashes)
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(
            prefix=".stage-pointer.", dir=destination.parent
        )
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(pointer.canonical_bytes())
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return pointer

    def reuse(
        self,
        *,
        stage: str,
        target: str,
        semantic_hashes: dict[str, str],
    ) -> StagePointer | None:
        path = self.path_for(stage, target, semantic_hashes)
        try:
            pointer = StagePointer.model_validate_json(
                path.read_bytes(), strict=True
            )
            if pointer.semantic_hashes != dict(sorted(semantic_hashes.items())):
                return None
            subject = self.store.read_bytes(pointer.subject_sha256)
            self._verify_references(pointer, subject)
        except (
            FileNotFoundError,
            OSError,
            ValueError,
            ArtifactCorruptionError,
        ):
            return None
        return pointer

    def _verify_references(
        self, pointer: StagePointer, subject: bytes
    ) -> None:
        if pointer.subject_role is ProvenanceSubjectRole.SOURCE_SNAPSHOT:
            snapshot = SourceSnapshotManifest.model_validate_json(
                subject, strict=True
            )
            for member in snapshot.members:
                value = self.store.read_bytes(member.sha256)
                if len(value) != member.byte_length:
                    raise ValueError("source member byte length mismatch")
        elif (
            pointer.subject_role
            is ProvenanceSubjectRole.NORMALIZATION_MANIFEST
        ):
            normalization = NormalizationManifest.model_validate_json(
                subject, strict=True
            )
            references = (
                normalization.documents,
                normalization.annotations,
                normalization.source_annotations,
                normalization.source_sidecar,
                normalization.inventory,
            )
            for reference in references:
                if reference is None:
                    continue
                value = self.store.read_bytes(reference.sha256)
                if len(value) != reference.byte_length:
                    raise ValueError("normalized artifact byte length mismatch")
        elif pointer.subject_role is ProvenanceSubjectRole.TRANSLATION_MANIFEST:
            manifest = TranslationManifest.model_validate_json(
                subject, strict=True
            )
            for record in manifest.records:
                self.store.read_bytes(record.source_sha256)
                self.store.read_bytes(record.translation_sha256)
        elif (
            pointer.subject_role
            is ProvenanceSubjectRole.UMLS_HPO_MAPPING_MANIFEST
        ):
            mapping_manifest = E3cMappingStageManifest.model_validate_json(
                subject, strict=True
            )
            for reference in (
                mapping_manifest.complete,
                mapping_manifest.selected,
                mapping_manifest.summary,
            ):
                value = self.store.read_bytes(reference.sha256)
                if len(value) != reference.byte_length:
                    raise ValueError("mapping artifact byte length mismatch")

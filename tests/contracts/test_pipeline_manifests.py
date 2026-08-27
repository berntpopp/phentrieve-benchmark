import json

import pytest
from pydantic import ValidationError

from phentrieve_benchmark.models.pipeline import (
    ArchiveFormat,
    ArtifactReference,
    NormalizationCount,
    NormalizationManifest,
    ProvenanceRunLink,
    ProvenanceSubjectRole,
    SourceMember,
    SourceSnapshotManifest,
    WarningCount,
)


def artifact(
    role: str, character: str, records: int | None = None
) -> ArtifactReference:
    return ArtifactReference(
        schema_id=role,
        sha256=character * 64,
        byte_length=10,
        record_count=records,
    )


def source_manifest(**updates: object) -> SourceSnapshotManifest:
    values: dict[str, object] = {
        "source_id": "synthetic",
        "source_commit": "a" * 40,
        "recipe_sha256": "b" * 64,
        "archive_sha256": "c" * 64,
        "archive_byte_length": 100,
        "archive_format": ArchiveFormat.ZIP,
        "members": (
            SourceMember(path="root/z.xml", sha256="e" * 64, byte_length=20),
            SourceMember(path="root/a.xml", sha256="d" * 64, byte_length=10),
        ),
    }
    values.update(updates)
    return SourceSnapshotManifest(**values)


def normalization_manifest(**updates: object) -> NormalizationManifest:
    values: dict[str, object] = {
        "target_id": "synthetic",
        "source_snapshot_sha256": "a" * 64,
        "recipe_sha256": "b" * 64,
        "adapter_id": "synthetic-adapter/v1",
        "code_sha256": "c" * 64,
        "documents": artifact("document-jsonl/v1", "d", 2),
        "source_annotations": artifact("source-annotation-jsonl/v1", "e", 2),
        "inventory": artifact("source-inventory/v1", "f", 2),
        "counts": (
            NormalizationCount(language="fr", record_type="document", count=1),
            NormalizationCount(language="en", record_type="document", count=1),
        ),
        "warnings": (
            WarningCount(code="z_warning", count=2),
            WarningCount(code="a_warning", count=1),
        ),
    }
    values.update(updates)
    return NormalizationManifest(**values)


def test_source_snapshot_manifest_is_sorted_and_canonical() -> None:
    first = source_manifest()
    second = source_manifest(members=tuple(reversed(first.members)))

    assert first == second
    assert [member.path for member in first.members] == [
        "root/a.xml",
        "root/z.xml",
    ]
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.sha256() == second.sha256()


@pytest.mark.parametrize(
    "path",
    [
        "/absolute.xml",
        "C:/drive.xml",
        "../parent.xml",
        "root/../escape.xml",
        "root\\windows.xml",
        "root//empty.xml",
        "root/./dot.xml",
        "root/control\u0000.xml",
        "root/cafe\u0301.xml",
    ],
)
def test_source_member_rejects_noncanonical_relative_posix_path(path: str) -> None:
    with pytest.raises(ValidationError, match="path"):
        SourceMember(path=path, sha256="a" * 64, byte_length=1)


def test_source_snapshot_rejects_duplicate_member_paths() -> None:
    member = SourceMember(path="root/a.xml", sha256="a" * 64, byte_length=1)

    with pytest.raises(ValueError, match="duplicate"):
        source_manifest(members=(member, member))


def test_normalization_manifest_sorts_counts_and_warnings() -> None:
    first = normalization_manifest()
    second = normalization_manifest(
        counts=tuple(reversed(first.counts)),
        warnings=tuple(reversed(first.warnings)),
    )

    assert first == second
    assert [(count.language, count.record_type) for count in first.counts] == [
        ("en", "document"),
        ("fr", "document"),
    ]
    assert [warning.code for warning in first.warnings] == [
        "a_warning",
        "z_warning",
    ]


@pytest.mark.parametrize(
    "updates",
    [
        {
            "counts": (
                NormalizationCount(
                    language="en",
                    record_type="document",
                    count=1,
                ),
            )
            * 2
        },
        {"warnings": (WarningCount(code="same", count=1),) * 2},
    ],
)
def test_normalization_manifest_rejects_duplicate_set_identities(
    updates: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        normalization_manifest(**updates)


@pytest.mark.parametrize("field", ["run_id", "timestamp", "host", "environment"])
def test_deterministic_manifests_reject_volatile_execution_fields(
    field: str,
) -> None:
    payload = normalization_manifest().model_dump(mode="json")
    payload[field] = "volatile"

    with pytest.raises(ValidationError, match=field):
        NormalizationManifest.model_validate_json(json.dumps(payload))


def test_provenance_run_link_is_separate_and_versioned() -> None:
    link = ProvenanceRunLink(
        subject_role=ProvenanceSubjectRole.NORMALIZATION_MANIFEST,
        subject_sha256="a" * 64,
        run_manifest_sha256="b" * 64,
    )

    assert link.model_dump(mode="json") == {
        "schema_version": "provenance-run-link/v1",
        "subject_role": "normalization_manifest",
        "subject_sha256": "a" * 64,
        "run_manifest_sha256": "b" * 64,
    }
    assert (
        ProvenanceRunLink.model_validate_json(json.dumps(link.model_dump(mode="json")))
        == link
    )


def test_pipeline_models_reject_coercive_scalars_and_unknown_versions() -> None:
    payload = source_manifest().model_dump(mode="json")
    payload["archive_byte_length"] = True
    with pytest.raises(ValidationError, match="archive_byte_length"):
        SourceSnapshotManifest.model_validate_json(json.dumps(payload))

    payload = normalization_manifest().model_dump(mode="json")
    payload["schema_version"] = "normalization-manifest/v2"
    with pytest.raises(ValidationError, match="schema_version"):
        NormalizationManifest.model_validate_json(json.dumps(payload))

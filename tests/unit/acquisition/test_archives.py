import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from phentrieve_benchmark.acquisition.archives import (
    ArchiveValidationError,
    publish_source_snapshot,
)
from phentrieve_benchmark.acquisition.downloader import DownloadedArchive
from phentrieve_benchmark.acquisition.recipes import (
    ArchiveLock,
    E3cAdapterContract,
    E3cLanguagePath,
    E3cSemanticType,
    LoadedRecipe,
    SourceRecipe,
)
from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.provenance.digests import sha256_bytes

COMMIT = "f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc"
ROOT = f"E3C-Corpus-{COMMIT}"


def _zip(entries: list[tuple[str, bytes]], *, symlink: bool = False) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in entries:
            if symlink:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = 0o120777 << 16
                archive.writestr(info, body)
            else:
                archive.writestr(name, body)
    return output.getvalue()


def _tar(
    entries: list[tuple[str, bytes]],
    *,
    member_type: bytes | None = None,
) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name, body in entries:
            info = tarfile.TarInfo(name)
            info.size = len(body)
            if member_type is not None:
                info.type = member_type
                info.linkname = f"{ROOT}/target"
                info.size = 0
            archive.addfile(info, None if member_type is not None else io.BytesIO(body))
    return output.getvalue()


def _loaded(
    body: bytes,
    *,
    archive_format: str = "zip",
    included: tuple[str, ...] = ("data/*.xml",),
    ignored: tuple[str, ...] = ("ignored",),
    maximum_member_count: int = 20,
    maximum_member_bytes: int = 1_000,
    maximum_expanded_bytes: int = 2_000,
    maximum_compression_ratio: int = 100,
) -> LoadedRecipe[SourceRecipe]:
    value = SourceRecipe(
        source_id="e3c",
        repository_url="https://github.com/hltfbk/E3C-Corpus",
        source_commit=COMMIT,
        archive=ArchiveLock(
            url=(
                "https://codeload.github.com/hltfbk/E3C-Corpus/"
                f"{archive_format}/{COMMIT}"
            ),
            format=archive_format,
            expected_byte_length=len(body),
            maximum_byte_length=len(body),
            sha256=sha256_bytes(body),
            expected_top_level_directory=ROOT,
            maximum_member_count=maximum_member_count,
            maximum_member_bytes=maximum_member_bytes,
            maximum_expanded_bytes=maximum_expanded_bytes,
            maximum_compression_ratio=maximum_compression_ratio,
        ),
        included_paths=included,
        ignored_path_prefixes=ignored,
        adapter_id="e3c-xmi/v1",
        source_schema_id="webanno-uima-xmi/v2",
        adapter_contract=E3cAdapterContract(
            kind="e3c-xmi/v1",
            language_paths=(
                E3cLanguagePath(
                    language="en",
                    path_pattern="data/*.xml",
                    expected_documents=1,
                ),
            ),
            sofa_type="cas:Sofa",
            structural_types=("Token",),
            semantic_types=(
                E3cSemanticType(
                    name="CLINENTITY",
                    kind="annotation",
                    begin_attribute="begin",
                    end_attribute="end",
                ),
            ),
        ),
        license_evidence_sha256="b" * 64,
    )
    return LoadedRecipe(value=value, sha256="c" * 64)


def _publish(
    tmp_path: Path,
    body: bytes,
    **recipe_options: object,
):
    store = ArtifactStore(tmp_path / "artifacts")
    digest, length = store.put_bytes(body), len(body)
    return publish_source_snapshot(
        _loaded(body, **recipe_options),  # type: ignore[arg-type]
        DownloadedArchive(sha256=digest, byte_length=length),
        store=store,
    )


@pytest.mark.parametrize("archive_format", ["zip", "tar"])
def test_publishes_only_selected_regular_members_sorted(
    tmp_path: Path, archive_format: str
) -> None:
    entries = [
        (f"{ROOT}/ignored/readme.txt", b"ignored"),
        (f"{ROOT}/data/b.xml", b"b"),
        (f"{ROOT}/data/a.xml", b"a"),
    ]
    body = _zip(entries) if archive_format == "zip" else _tar(entries)

    manifest = _publish(tmp_path, body, archive_format=archive_format)

    assert [member.path for member in manifest.members] == [
        "data/a.xml",
        "data/b.xml",
    ]
    assert [member.byte_length for member in manifest.members] == [1, 1]
    artifact_files = [
        path
        for path in (tmp_path / "artifacts").rglob("*")
        if path.is_file()
    ]
    assert len(artifact_files) == 3  # archive plus two selected members


@pytest.mark.parametrize(
    "name",
    [
        "/absolute.xml",
        "C:/drive.xml",
        "//server/share.xml",
        f"{ROOT}\\backslash.xml",
        f"{ROOT}/../escape.xml",
        f"{ROOT}/bad\x00name.xml",
        "",
        f"{ROOT}/de\u0301composed.xml",
    ],
)
def test_rejects_unsafe_member_paths(tmp_path: Path, name: str) -> None:
    body = _zip([(name, b"x")])
    with pytest.raises(ArchiveValidationError):
        _publish(tmp_path, body)


def test_rejects_duplicate_paths(tmp_path: Path) -> None:
    body = _zip([(f"{ROOT}/data/a.xml", b"a"), (f"{ROOT}/data/a.xml", b"b")])
    with pytest.raises(ArchiveValidationError, match="duplicate"):
        _publish(tmp_path, body)


@pytest.mark.parametrize("archive_format", ["zip", "tar"])
def test_rejects_links(tmp_path: Path, archive_format: str) -> None:
    name = f"{ROOT}/data/a.xml"
    body = (
        _zip([(name, b"target")], symlink=True)
        if archive_format == "zip"
        else _tar([(name, b"")], member_type=tarfile.SYMTYPE)
    )
    with pytest.raises(ArchiveValidationError, match="regular"):
        _publish(tmp_path, body, archive_format=archive_format)


@pytest.mark.parametrize(
    ("option", "value", "message"),
    [
        ("maximum_member_count", 1, "member count"),
        ("maximum_member_bytes", 2, "member size"),
        ("maximum_expanded_bytes", 3, "expanded"),
        ("maximum_compression_ratio", 1, "compression ratio"),
    ],
)
def test_enforces_archive_limits(
    tmp_path: Path, option: str, value: int, message: str
) -> None:
    body = _zip([(f"{ROOT}/data/a.xml", b"a" * 100), (f"{ROOT}/x", b"x")])
    with pytest.raises(ArchiveValidationError, match=message):
        _publish(tmp_path, body, **{option: value})


def test_requires_exact_top_level_and_at_least_one_match(tmp_path: Path) -> None:
    wrong_root = _zip([("wrong/data/a.xml", b"a")])
    with pytest.raises(ArchiveValidationError, match="top-level"):
        _publish(tmp_path, wrong_root)

    no_match = _zip([(f"{ROOT}/other/a.xml", b"a")])
    with pytest.raises(ArchiveValidationError, match="included path"):
        _publish(tmp_path, no_match)

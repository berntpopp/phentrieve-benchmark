from pathlib import Path

import httpx
import pytest

from phentrieve_benchmark.acquisition.downloader import (
    DownloadError,
    download_archive,
)
from phentrieve_benchmark.acquisition.recipes import (
    ArchiveLock,
    E3cAdapterContract,
    E3cLanguagePath,
    E3cSemanticType,
    SourceRecipe,
)
from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.provenance.digests import sha256_bytes
from tests.fixtures.http_server import (
    SyntheticHttpResponse,
    synthetic_http_server,
)

COMMIT = "f74bdf9eaaef7f08437d0c5b930c6dbbc25bbffc"
URL = f"https://codeload.github.com/hltfbk/E3C-Corpus/zip/{COMMIT}"


def recipe(
    body: bytes,
    *,
    expected_byte_length: int | None = None,
    maximum_byte_length: int | None = None,
    sha256: str | None = None,
) -> SourceRecipe:
    byte_length = len(body) if expected_byte_length is None else expected_byte_length
    maximum = (
        max(byte_length, len(body))
        if maximum_byte_length is None
        else maximum_byte_length
    )
    return SourceRecipe(
        source_id="e3c",
        repository_url="https://github.com/hltfbk/E3C-Corpus",
        source_commit=COMMIT,
        archive=ArchiveLock(
            url=URL,
            format="zip",
            expected_byte_length=byte_length,
            maximum_byte_length=maximum,
            sha256=sha256 or sha256_bytes(body),
            expected_top_level_directory=f"E3C-Corpus-{COMMIT}",
            maximum_member_count=10,
            maximum_member_bytes=1_000_000,
            maximum_expanded_bytes=2_000_000,
            maximum_compression_ratio=100,
        ),
        included_paths=("data_annotation/English/layer1/*.xml",),
        adapter_id="e3c-xmi/v1",
        source_schema_id="webanno-uima-xmi/v2",
        adapter_contract=E3cAdapterContract(
            kind="e3c-xmi/v1",
            language_paths=(
                E3cLanguagePath(
                    language="en",
                    path_pattern="data_annotation/English/layer1/*.xml",
                    expected_documents=1,
                ),
            ),
            sofa_type="cas:Sofa",
            structural_types=("Token", "Sentence"),
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


def client_for(
    transport: httpx.BaseTransport,
    *,
    timeout: float = 1.0,
    follow_redirects: bool = False,
) -> httpx.Client:
    return httpx.Client(
        transport=transport,
        timeout=timeout,
        follow_redirects=follow_redirects,
        trust_env=False,
    )


@pytest.mark.parametrize("include_length", [False, True])
def test_download_archive_streams_and_publishes_verified_bytes(
    tmp_path: Path, include_length: bool
) -> None:
    body = b"synthetic archive bytes" * 20
    headers = {"Content-Length": str(len(body))} if include_length else {}
    response = SyntheticHttpResponse(body=body, headers=headers, chunk_size=3)

    with (
        synthetic_http_server(response) as transport,
        client_for(transport) as client,
    ):
        result = download_archive(
            recipe(body),
            store=ArtifactStore(tmp_path / "artifacts"),
            staging_root=tmp_path / "staging",
            client=client,
        )

    assert result.sha256 == sha256_bytes(body)
    assert result.byte_length == len(body)
    assert ArtifactStore(tmp_path / "artifacts").read_bytes(result.sha256) == body
    assert not list((tmp_path / "staging").glob("*"))


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_download_archive_rejects_redirect_without_following(
    tmp_path: Path, status: int
) -> None:
    response = SyntheticHttpResponse(
        body=b"",
        status=status,
        headers={"Location": "https://example.org/redirected"},
    )

    with (
        synthetic_http_server(response) as transport,
        client_for(transport) as client,
        pytest.raises(DownloadError, match="redirect"),
    ):
        download_archive(
            recipe(b"expected"),
            store=ArtifactStore(tmp_path / "artifacts"),
            staging_root=tmp_path / "staging",
            client=client,
        )


def test_download_archive_rejects_client_configured_to_follow_redirects(
    tmp_path: Path,
) -> None:
    with (
        synthetic_http_server(SyntheticHttpResponse(body=b"expected")) as transport,
        client_for(transport, follow_redirects=True) as client,
        pytest.raises(ValueError, match="follow_redirects"),
    ):
        download_archive(
            recipe(b"expected"),
            store=ArtifactStore(tmp_path / "artifacts"),
            staging_root=tmp_path / "staging",
            client=client,
        )


def test_download_archive_rejects_declared_content_length_mismatch(
    tmp_path: Path,
) -> None:
    body = b"expected"
    response = SyntheticHttpResponse(
        body=body,
        headers={"Content-Length": str(len(body) + 1)},
    )

    with (
        synthetic_http_server(response) as transport,
        client_for(transport) as client,
        pytest.raises(DownloadError, match="content length"),
    ):
        download_archive(
            recipe(body),
            store=ArtifactStore(tmp_path / "artifacts"),
            staging_root=tmp_path / "staging",
            client=client,
        )


@pytest.mark.parametrize(
    ("configured", "message"),
    [
        ({"sha256": "0" * 63 + "1"}, "digest mismatch"),
        ({"expected_byte_length": 9}, "byte length mismatch"),
    ],
)
def test_download_archive_rejects_measured_identity_mismatch(
    tmp_path: Path,
    configured: dict[str, object],
    message: str,
) -> None:
    body = b"expected"
    response = SyntheticHttpResponse(body=body)
    source = recipe(body).model_copy(
        update={
            "archive": recipe(body).archive.model_copy(update=configured),
        }
    )

    with (
        synthetic_http_server(response) as transport,
        client_for(transport) as client,
        pytest.raises(DownloadError, match=message),
    ):
        download_archive(
            source,
            store=ArtifactStore(tmp_path / "artifacts"),
            staging_root=tmp_path / "staging",
            client=client,
        )


def test_download_archive_enforces_maximum_during_unbounded_stream(
    tmp_path: Path,
) -> None:
    body = b"too many bytes"
    source = recipe(body).model_copy(
        update={
            "archive": recipe(body).archive.model_copy(
                update={"maximum_byte_length": 4}
            ),
        }
    )

    with (
        synthetic_http_server(SyntheticHttpResponse(body=body)) as transport,
        client_for(transport) as client,
        pytest.raises(DownloadError, match="maximum"),
    ):
        download_archive(
            source,
            store=ArtifactStore(tmp_path / "artifacts"),
            staging_root=tmp_path / "staging",
            client=client,
        )


def test_download_archive_rejects_interrupted_transfer_and_cleans_staging(
    tmp_path: Path,
) -> None:
    body = b"expected complete transfer"
    response = SyntheticHttpResponse(
        body=body,
        headers={"Content-Length": str(len(body))},
        interrupt_after=4,
    )

    with (
        synthetic_http_server(response) as transport,
        client_for(transport) as client,
        pytest.raises(DownloadError, match="interrupted"),
    ):
        download_archive(
            recipe(body),
            store=ArtifactStore(tmp_path / "artifacts"),
            staging_root=tmp_path / "staging",
            client=client,
        )

    assert not list((tmp_path / "staging").glob("*"))
    artifact_root = tmp_path / "artifacts"
    assert not artifact_root.exists() or not any(
        path.is_file() for path in artifact_root.rglob("*")
    )


def test_download_archive_rejects_read_timeout(tmp_path: Path) -> None:
    body = b"expected"
    response = SyntheticHttpResponse(body=body, delay_before_body=0.2)

    with (
        synthetic_http_server(response) as transport,
        client_for(transport, timeout=0.05) as client,
        pytest.raises(DownloadError, match="timeout"),
    ):
        download_archive(
            recipe(body),
            store=ArtifactStore(tmp_path / "artifacts"),
            staging_root=tmp_path / "staging",
            client=client,
        )


def test_download_error_never_contains_response_body(tmp_path: Path) -> None:
    secret_body = b"credential-bearing response body"
    response = SyntheticHttpResponse(body=secret_body, status=500)

    with (
        synthetic_http_server(response) as transport,
        client_for(transport) as client,
        pytest.raises(DownloadError) as captured,
    ):
        download_archive(
            recipe(b"expected"),
            store=ArtifactStore(tmp_path / "artifacts"),
            staging_root=tmp_path / "staging",
            client=client,
        )

    assert "credential" not in str(captured.value)
    assert "response body" not in str(captured.value)

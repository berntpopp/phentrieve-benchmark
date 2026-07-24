import os
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from phentrieve_benchmark.acquisition.recipes import SourceRecipe
from phentrieve_benchmark.artifacts.store import (
    ArtifactIntegrityError,
    ArtifactStore,
)

_CHUNK_SIZE = 1024 * 1024


class DownloadError(RuntimeError):
    """A source archive could not be acquired with its declared identity."""


@dataclass(frozen=True)
class DownloadedArchive:
    sha256: str
    byte_length: int


def _default_client() -> httpx.Client:
    return httpx.Client(
        follow_redirects=False,
        timeout=httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0),
        trust_env=False,
        headers={
            "Accept": "application/octet-stream",
            "Accept-Encoding": "identity",
            "User-Agent": "phentrieve-benchmark/0.1 source-acquisition",
        },
    )


def _validate_runtime_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "codeload.github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("archive URL must be direct HTTPS codeload")


def _declared_content_length(response: httpx.Response) -> int | None:
    raw = response.headers.get("Content-Length")
    if raw is None:
        return None
    if not raw.isascii() or not raw.isdecimal() or str(int(raw)) != raw:
        raise DownloadError("invalid content length")
    return int(raw)


def download_archive(
    recipe: SourceRecipe,
    *,
    store: ArtifactStore,
    staging_root: Path,
    client: httpx.Client | None = None,
) -> DownloadedArchive:
    _validate_runtime_url(recipe.archive.url)
    owned_client = client is None
    active_client = _default_client() if client is None else client
    if active_client.follow_redirects:
        if owned_client:
            active_client.close()
        raise ValueError("HTTP client must use follow_redirects=False")

    staging_root.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=".download.",
        suffix=".partial",
        dir=staging_root,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    digest = sha256()
    byte_length = 0
    try:
        try:
            with active_client.stream("GET", recipe.archive.url) as response:
                if response.is_redirect:
                    raise DownloadError("source redirect is forbidden")
                if response.status_code != 200:
                    raise DownloadError(
                        f"source returned HTTP status {response.status_code}"
                    )
                declared_length = _declared_content_length(response)
                if (
                    declared_length is not None
                    and declared_length > recipe.archive.maximum_byte_length
                ):
                    raise DownloadError(
                        "declared content length exceeds maximum byte count"
                    )
                if (
                    declared_length is not None
                    and declared_length != recipe.archive.expected_byte_length
                ):
                    raise DownloadError(
                        "declared content length does not match recipe"
                    )
                with temporary_path.open("wb") as temporary_file:
                    for chunk in response.iter_bytes(chunk_size=_CHUNK_SIZE):
                        byte_length += len(chunk)
                        if byte_length > recipe.archive.maximum_byte_length:
                            raise DownloadError(
                                "download exceeds maximum byte count"
                            )
                        digest.update(chunk)
                        temporary_file.write(chunk)
        except httpx.TimeoutException as error:
            raise DownloadError("source download timeout") from error
        except httpx.HTTPError as error:
            raise DownloadError("source download interrupted") from error

        measured_digest = digest.hexdigest()
        if byte_length != recipe.archive.expected_byte_length:
            raise DownloadError(
                "byte length mismatch: "
                f"expected {recipe.archive.expected_byte_length}, "
                f"got {byte_length}"
            )
        if measured_digest != recipe.archive.sha256:
            raise DownloadError("digest mismatch")
        try:
            stored_digest, stored_length = store.put_file(
                temporary_path,
                expected_sha256=recipe.archive.sha256,
                expected_byte_length=recipe.archive.expected_byte_length,
            )
        except ArtifactIntegrityError as error:
            raise DownloadError("staged archive identity mismatch") from error
        return DownloadedArchive(
            sha256=stored_digest,
            byte_length=stored_length,
        )
    finally:
        with suppress(OSError):
            temporary_path.unlink()
        if owned_client:
            active_client.close()

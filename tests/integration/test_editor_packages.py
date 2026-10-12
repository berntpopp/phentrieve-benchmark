"""Run with ``uv run --with-editable ../ontocurator pytest``."""

import argparse
import importlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, BinaryIO

import pytest

from phentrieve_benchmark.artifacts.store import ArtifactStore

pytest.importorskip("ontocurator", reason="requires the Ontocurator overlay")
builder_module = importlib.import_module("scripts.build_editor_packages")

HP = b'{"graphs":[]}'


@pytest.fixture
def build_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[argparse.Namespace, ArtifactStore, Path, Path]:
    index = tmp_path / "current-proposals.json"
    index.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "annotation_language": "en",
                        "steps": [{"run_date": "2026-10-07"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(builder_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(builder_module, "E3C_PROPOSAL_INDEX", index)
    monkeypatch.setattr(builder_module, "E3C_BUILD_RECORD_DIR", tmp_path / "records")

    # Isolate corpus acquisition; package writing and reading use Ontocurator.
    def synthetic_group(
        builder: Any,
        store: ArtifactStore,
        entries: list[dict[str, Any]],
        *,
        with_proposals: bool,
        stats: Counter[str],
    ) -> dict[str, list[str]]:
        builder.add_document("synthetic", "Fever.", "en")
        stats["documents"] = 1
        return {"runs": [], "corpus_manifest_sha256": [], "guideline_commits": []}

    monkeypatch.setattr(builder_module, "build_e3c_group", synthetic_group)
    args = argparse.Namespace(
        language=None,
        no_proposals=True,
        limit=None,
        package_version="v1",
        hp_release="2026-06-23",
        output_dir=tmp_path / "output",
    )
    return (
        args,
        ArtifactStore(tmp_path / "objects"),
        args.output_dir / "editor-e3c-en-blind-v1.zip",
        tmp_path / "records/phentrieve-benchmark-e3c-en-blind-v1.json",
    )


@pytest.mark.parametrize("existing_zip", [True, False])
def test_conflicting_rebuild_preserves_published_artifacts(
    build_inputs: tuple[argparse.Namespace, ArtifactStore, Path, Path],
    existing_zip: bool,
) -> None:
    args, store, output, record = build_inputs
    builder_module.build_e3c(args, HP, store)
    original_zip = output.read_bytes()
    original_record = record.read_bytes()
    if not existing_zip:
        output.unlink()

    with pytest.raises(SystemExit, match="new --package-version"):
        builder_module.build_e3c(args, HP + b"\n", store)

    if existing_zip:
        assert output.read_bytes() == original_zip
    else:
        assert not output.exists()
    assert record.read_bytes() == original_record
    assert set(output.parent.iterdir()) == ({output} if existing_zip else set())


@pytest.mark.parametrize("failure_stage", ["writer", "reader", "replace"])
def test_failed_package_build_preserves_published_artifacts(
    build_inputs: tuple[argparse.Namespace, ArtifactStore, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
) -> None:
    args, store, output, record = build_inputs
    builder_module.build_e3c(args, HP, store)
    original_zip = output.read_bytes()
    original_record = record.read_bytes()

    if failure_stage == "writer":

        def fail_write(package: Any, stream: BinaryIO) -> None:
            stream.write(b"partial ZIP")
            raise OSError("synthetic write failure")

        monkeypatch.setattr(builder_module.PackageWriter, "write_to_stream", fail_write)
    elif failure_stage == "reader":

        def fail_read(self: Any, path: Path) -> None:
            raise ValueError("synthetic read failure")

        monkeypatch.setattr(builder_module.PackageReader, "read", fail_read)
    else:

        def fail_replace(source: Path, destination: Path) -> None:
            raise OSError("synthetic replace failure")

        monkeypatch.setattr(builder_module.os, "replace", fail_replace)

    with pytest.raises((OSError, ValueError), match="synthetic"):
        builder_module.build_e3c(
            args, HP if failure_stage == "replace" else HP + b"\n", store
        )

    assert output.read_bytes() == original_zip
    assert record.read_bytes() == original_record
    assert set(output.parent.iterdir()) == {output}


def test_unreadable_build_record_preserves_published_zip(
    build_inputs: tuple[argparse.Namespace, ArtifactStore, Path, Path],
) -> None:
    args, store, output, record = build_inputs
    builder_module.build_e3c(args, HP, store)
    original_zip = output.read_bytes()
    record.write_bytes(b"invalid JSON")

    with pytest.raises(json.JSONDecodeError):
        builder_module.build_e3c(args, HP + b"\n", store)

    assert output.read_bytes() == original_zip
    assert record.read_bytes() == b"invalid JSON"
    assert set(output.parent.iterdir()) == {output}


def test_identical_rebuild_retains_manifest_identity(
    build_inputs: tuple[argparse.Namespace, ArtifactStore, Path, Path],
) -> None:
    args, store, output, record = build_inputs
    builder_module.build_e3c(args, HP, store)
    original_record = record.read_bytes()

    builder_module.build_e3c(args, HP, store)

    assert record.read_bytes() == original_record
    package = builder_module.PackageReader().read(output)
    assert package.documents["synthetic"].text == "Fever."
    assert set(output.parent.iterdir()) == {output}


def test_changed_package_can_be_published_under_new_version(
    build_inputs: tuple[argparse.Namespace, ArtifactStore, Path, Path],
) -> None:
    args, store, output, record = build_inputs
    builder_module.build_e3c(args, HP, store)
    original_zip = output.read_bytes()
    original_record = record.read_bytes()
    args.package_version = "v2"

    builder_module.build_e3c(args, HP + b"\n", store)

    new_output = output.with_name("editor-e3c-en-blind-v2.zip")
    package = builder_module.PackageReader().read(new_output)
    assert package.manifest.package_id == "phentrieve-benchmark-e3c-en-blind-v2"
    assert record.with_name("phentrieve-benchmark-e3c-en-blind-v2.json").is_file()
    assert output.read_bytes() == original_zip
    assert record.read_bytes() == original_record

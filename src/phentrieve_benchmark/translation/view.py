import csv
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from phentrieve_benchmark.artifacts.store import ArtifactStore
from phentrieve_benchmark.models.pipeline import ProvenanceSubjectRole
from phentrieve_benchmark.models.translation import TranslationManifest
from phentrieve_benchmark.pipeline.state import StagePointer

_MARKER = ".phentrieve-translation-view.json"


@dataclass(frozen=True)
class TranslationViewResult:
    destination: Path
    case_count: int


def materialize_latest_translation_view(
    *, artifact_root: Path, store: ArtifactStore
) -> TranslationViewResult:
    state_root = artifact_root / "state" / "translate" / "e3c"
    candidates = sorted(
        state_root.glob("*.json"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    if not candidates:
        raise ValueError("missing published E3C translation manifest")
    pointer = StagePointer.model_validate_json(candidates[0].read_bytes())
    if pointer.subject_role is not ProvenanceSubjectRole.TRANSLATION_MANIFEST:
        raise ValueError("published E3C state is not a translation manifest")
    manifest = TranslationManifest.model_validate_json(
        store.read_bytes(pointer.subject_sha256)
    )
    return materialize_translation_view(
        manifest=manifest,
        store=store,
        destination=artifact_root / "views" / "e3c-de",
    )


def materialize_translation_view(
    *,
    manifest: TranslationManifest,
    store: ArtifactStore,
    destination: Path,
) -> TranslationViewResult:
    destination = destination.resolve()
    if destination.exists() and not (destination / _MARKER).is_file():
        raise ValueError("destination is not a generated translation view")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    try:
        rows: list[dict[str, object]] = []
        for record in sorted(
            manifest.records, key=lambda item: item.source_case_id
        ):
            source_name = (
                f"{record.source_case_id}.source.{record.source_language}.txt"
            )
            translation_name = (
                f"{record.source_case_id}.translation.{record.target_language}.txt"
            )
            (temporary / source_name).write_bytes(
                store.read_bytes(record.source_sha256)
            )
            (temporary / translation_name).write_bytes(
                store.read_bytes(record.translation_sha256)
            )
            failed = ";".join(
                check.code for check in record.checks if not check.passed
            )
            rows.append(
                {
                    "source_case_id": record.source_case_id,
                    "source_language": record.source_language,
                    "target_language": record.target_language,
                    "source_path": source_name,
                    "translation_path": translation_name,
                    "source_sha256": record.source_sha256,
                    "translation_sha256": record.translation_sha256,
                    "translation_id": record.translation_id,
                    "status": record.status.value,
                    "failed_checks": failed,
                    "provider": record.provider,
                    "api_version": record.api_version,
                    "model": record.model,
                    "project_id": record.project_id,
                    "location": record.location,
                    "created_at": record.created_at.isoformat(),
                    "input_codepoints": record.input_codepoints,
                    "output_codepoints": record.output_codepoints,
                }
            )
        fieldnames = list(rows[0]) if rows else [
            "source_case_id",
            "source_language",
            "target_language",
        ]
        with (temporary / "index.csv").open(
            "w", encoding="utf-8", newline=""
        ) as output:
            writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        (temporary / _MARKER).write_text(
            json.dumps(
                {
                    "schema_version": "translation-readable-view/v1",
                    "selection_id": manifest.selection_id,
                    "manifest_sha256": manifest.sha256(),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(temporary, destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return TranslationViewResult(
        destination=destination, case_count=len(manifest.records)
    )

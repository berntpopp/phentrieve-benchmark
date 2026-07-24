import csv
import io
import re
from collections.abc import Iterable
from unicodedata import category, normalize

from phentrieve_benchmark.acquisition.recipes import (
    ExpectedTable,
    NormalizationRecipe,
    RaghpoAdapterContract,
    SourceRecipe,
)
from phentrieve_benchmark.models.annotation import Annotation, AnnotationSet
from phentrieve_benchmark.models.document import Document, TranslationStatus
from phentrieve_benchmark.normalization.contracts import (
    NormalizedTarget,
    RagHpoSourceAnnotationRecord,
)
from phentrieve_benchmark.normalization.text import canonicalize_source_text
from phentrieve_benchmark.normalization.workbook import open_validated_workbook

_HPO_ID = re.compile(r"HP:[0-9]{7}", re.ASCII)
_SAFE_COMPONENT = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
)


class RaghpoNormalizationError(ValueError):
    """A pinned CSC or GSC source violates its exact tabular contract."""


def _identifier(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise RaghpoNormalizationError("identifier has invalid scalar type")
    if isinstance(value, int):
        if value < 0:
            raise RaghpoNormalizationError("identifier must be non-negative")
        return str(value)
    if (
        not value
        or value != normalize("NFC", value)
        or value != value.strip()
        or any(category(character).startswith("C") for character in value)
    ):
        raise RaghpoNormalizationError("identifier is not exact canonical text")
    return value


def _component(value: str) -> str:
    return "".join(
        character
        if character in _SAFE_COMPONENT
        else "".join(f"%{byte:02X}" for byte in character.encode("utf-8"))
        for character in value
    )


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise RaghpoNormalizationError("clinical text must be a string")
    return canonicalize_source_text(
        value, remove_terminal_format_newline=False
    ).canonical_text


def _table(recipe: NormalizationRecipe, sheet: str | None) -> ExpectedTable:
    matches = [
        value for value in recipe.expected_tables if value.sheet_name == sheet
    ]
    if len(matches) != 1:
        raise RaghpoNormalizationError("expected table contract is missing")
    return matches[0]


def _rows(
    sheet: object, contract: ExpectedTable
) -> list[dict[str, object]]:
    iterator = sheet.iter_rows(values_only=True)  # type: ignore[attr-defined]
    try:
        header = next(iterator)
    except StopIteration as error:
        raise RaghpoNormalizationError("table is empty") from error
    if tuple(header) != contract.columns:
        raise RaghpoNormalizationError("table headers do not match exactly")
    rows = [dict(zip(contract.columns, row, strict=True)) for row in iterator]
    if len(rows) != contract.data_rows:
        raise RaghpoNormalizationError("table data-row count mismatch")
    return rows


def _csv_rows(value: bytes, contract: ExpectedTable) -> list[dict[str, object]]:
    try:
        text = value.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if tuple(reader.fieldnames or ()) != contract.columns:
            raise RaghpoNormalizationError("CSV headers do not match exactly")
        rows = [dict(row) for row in reader]
    except (UnicodeError, csv.Error) as error:
        raise RaghpoNormalizationError("invalid source CSV") from error
    if len(rows) != contract.data_rows:
        raise RaghpoNormalizationError("CSV data-row count mismatch")
    return rows


def _hpo_ids(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, str):
        raise RaghpoNormalizationError("HPO term cell must be text")
    values = tuple(part.strip(" \t\r\n\f\v") for part in raw.split(","))
    if not values or any(_HPO_ID.fullmatch(value) is None for value in values):
        raise RaghpoNormalizationError("invalid HPO identifier cell")
    return values


def _unique_map(
    rows: Iterable[dict[str, object]], keys: tuple[str, ...]
) -> dict[tuple[str, ...], dict[str, object]]:
    result: dict[tuple[str, ...], dict[str, object]] = {}
    for row in rows:
        identity = tuple(_identifier(row[key]) for key in keys)
        if identity in result:
            raise RaghpoNormalizationError("duplicate table identity")
        result[identity] = row
    return result


def normalize_raghpo_target(
    *,
    csv_bytes: bytes,
    workbook_bytes: bytes,
    source_recipe: SourceRecipe,
    target_recipe: NormalizationRecipe,
) -> NormalizedTarget:
    if target_recipe.target_id not in {"csc", "gsc"}:
        raise ValueError("target must be csc or gsc")
    if target_recipe.hpo_release is None:
        raise ValueError("RAG-HPO target requires an HPO release")
    contract = source_recipe.adapter_contract
    if not isinstance(contract, RaghpoAdapterContract):
        raise ValueError("RAG-HPO adapter contract required")
    workbook = open_validated_workbook(
        workbook_bytes, limits=contract.workbook_limits
    )
    try:
        if target_recipe.target_id == "csc":
            csv_contract = next(
                table
                for table in target_recipe.expected_tables
                if table.source_path == "Test_Cases.csv"
            )
            csv_rows = _csv_rows(csv_bytes, csv_contract)
            input_rows = _rows(
                workbook["CSC Input"], _table(target_recipe, "CSC Input")
            )
            manual_rows = _rows(
                workbook["CSC Manual Annotations"],
                _table(target_recipe, "CSC Manual Annotations"),
            )
            csv_map = _unique_map(csv_rows, ("Case",))
            input_map = _unique_map(input_rows, ("Case",))
            if set(csv_map) != set(input_map):
                raise RaghpoNormalizationError("CSC case inventories disagree")
            for identity in csv_map:
                if _text(csv_map[identity]["clinical_note"]) != _text(
                    input_map[identity]["clinical_note"]
                ):
                    raise RaghpoNormalizationError("CSC clinical notes disagree")
            document_rows = csv_map
            manual_keys: tuple[str, ...] = ("Patient ID",)
        else:
            input_rows = _rows(
                workbook["GSC Input"], _table(target_recipe, "GSC Input")
            )
            manual_rows = _rows(
                workbook["GSC Manual Annotations "],
                _table(target_recipe, "GSC Manual Annotations "),
            )
            document_rows = _unique_map(input_rows, ("patient_id", "ID"))
            manual_keys = ("Patient ID", "ID")

        documents: dict[tuple[str, ...], Document] = {}
        annotations: dict[tuple[str, ...], list[Annotation]] = {}
        sidecar: list[RagHpoSourceAnnotationRecord] = []
        commit = source_recipe.source_commit
        target = target_recipe.target_id
        for identity, row in document_rows.items():
            case = identity[0]
            components = ":".join(_component(value) for value in identity)
            document_id = f"raghpo:{commit}:{target}:{components}:native"
            documents[identity] = Document.from_text(
                source_case_id=case,
                case_group_id=f"raghpo:{commit}:{target}:{_component(case)}",
                document_id=document_id,
                language="en",
                translation_status=TranslationStatus.NATIVE,
                text=_text(row["clinical_note"]),
            )
            annotations[identity] = []

        for ordinal, row in enumerate(manual_rows, start=1):
            identity = tuple(_identifier(row[key]) for key in manual_keys)
            if identity not in documents:
                raise RaghpoNormalizationError("manual row has no exact input join")
            row_id = f"raghpo:{commit}:{target}:manual-row:{ordinal:06d}"
            raw_term = row["hpo_term"]
            hpo_ids = _hpo_ids(raw_term)
            derived = tuple(
                f"{row_id}:hpo:{part:02d}"
                for part in range(1, len(hpo_ids) + 1)
            )
            annotations[identity].extend(
                Annotation(annotation_id=annotation_id, hpo_id=hpo_id)
                for annotation_id, hpo_id in zip(derived, hpo_ids, strict=True)
            )
            description = row["hpo_description"]
            if not isinstance(description, str) or not description:
                raise RaghpoNormalizationError("HPO description must be text")
            category = row.get("Category")
            if category is not None and not isinstance(category, str):
                raise RaghpoNormalizationError("category must be text")
            sidecar.append(
                RagHpoSourceAnnotationRecord(
                    source_row_id=row_id,
                    source_case_id=identity[0],
                    secondary_id=identity[1] if len(identity) == 2 else None,
                    hpo_description=description,
                    raw_hpo_term=str(raw_term),
                    category=category,
                    derived_annotation_ids=derived,
                )
            )

        annotation_sets: list[AnnotationSet] = []
        for identity, document in documents.items():
            components = ":".join(_component(value) for value in identity)
            annotation_sets.append(
                AnnotationSet(
                    annotation_set_id=(
                        f"raghpo:{commit}:{target}:{components}:hpo:v1"
                    ),
                    document_sha256=document.document_sha256,
                    hpo_release=target_recipe.hpo_release,
                    annotations=tuple(
                        sorted(
                            annotations[identity],
                            key=lambda value: value.annotation_id,
                        )
                    ),
                )
            )
        document_values = tuple(
            sorted(documents.values(), key=lambda value: value.document_id)
        )
        annotation_values = tuple(
            sorted(annotation_sets, key=lambda value: value.annotation_set_id)
        )
        sidecar_values = tuple(
            sorted(sidecar, key=lambda value: value.source_row_id)
        )
        annotation_count = sum(
            len(value.annotations) for value in annotation_values
        )
        return NormalizedTarget(
            documents=document_values,
            annotation_sets=annotation_values,
            source_sidecar=sidecar_values,
            counts=(
                ("annotations", annotation_count),
                ("documents", len(document_values)),
                ("source_rows", len(sidecar_values)),
            ),
            warnings=(
                ("annotations_without_evidence_spans", annotation_count),
            ),
        )
    except KeyError as error:
        raise RaghpoNormalizationError(
            "required exact workbook sheet is missing"
        ) from error
    finally:
        workbook.close()

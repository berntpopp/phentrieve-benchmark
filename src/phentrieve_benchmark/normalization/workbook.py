import io
import re
import zipfile
from pathlib import PurePosixPath
from unicodedata import category, normalize

import openpyxl  # type: ignore[import-untyped]
from defusedxml import ElementTree  # type: ignore[import-untyped]
from openpyxl.workbook.workbook import Workbook  # type: ignore[import-untyped]

from phentrieve_benchmark.acquisition.recipes import WorkbookLimits

_DRIVE = re.compile(r"[A-Za-z]:")
_FORBIDDEN_PARTS = (
    "vba",
    "activex",
    "oleobject",
    "embeddings/",
    "externallinks/",
    "connections",
    "querytables/",
    "externaldata/",
)
_CONTENT_TYPES = {
    "application/xml",
    "application/vnd.openxmlformats-package.relationships+xml",
    "application/vnd.openxmlformats-package.core-properties+xml",
    "application/vnd.openxmlformats-officedocument.extended-properties+xml",
    "application/vnd.openxmlformats-officedocument.theme+xml",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml",
}
_RELATIONSHIP_TYPES = {
    "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
}


class WorkbookValidationError(ValueError):
    """An XLSX package is unsafe or outside the declared contract."""


def _safe_member_name(name: str) -> None:
    if (
        not name
        or name != normalize("NFC", name)
        or name.startswith(("/", "//"))
        or _DRIVE.match(name) is not None
        or "\\" in name
        or "\x00" in name
        or "//" in name
        or any(category(character).startswith("C") for character in name)
    ):
        raise WorkbookValidationError("unsafe workbook member path")
    trimmed = name[:-1] if name.endswith("/") else name
    if not trimmed or any(part in {"", ".", ".."} for part in trimmed.split("/")):
        raise WorkbookValidationError("unsafe workbook member path")
    if PurePosixPath(trimmed).as_posix() != trimmed:
        raise WorkbookValidationError("unsafe workbook member path")
    if any(value in name.casefold() for value in _FORBIDDEN_PARTS):
        raise WorkbookValidationError("forbidden active workbook content")


def _validate_xml_metadata(archive: zipfile.ZipFile) -> None:
    try:
        content_types = ElementTree.fromstring(
            archive.read("[Content_Types].xml")
        )
        for element in content_types:
            content_type = element.attrib.get("ContentType")
            if content_type not in _CONTENT_TYPES:
                raise WorkbookValidationError(
                    "unsupported workbook content type"
                )
        for info in archive.infolist():
            if not info.filename.endswith(".rels"):
                continue
            relationships = ElementTree.fromstring(archive.read(info))
            for relationship in relationships:
                if relationship.attrib.get("TargetMode") == "External":
                    raise WorkbookValidationError(
                        "external workbook relationship"
                    )
                if relationship.attrib.get("Type") not in _RELATIONSHIP_TYPES:
                    raise WorkbookValidationError(
                        "unsupported workbook relationship type"
                    )
    except KeyError as error:
        raise WorkbookValidationError(
            "workbook content types are missing"
        ) from error
    except ElementTree.ParseError as error:
        raise WorkbookValidationError("invalid workbook metadata XML") from error


def _validate_package(
    archive: zipfile.ZipFile, *, limits: WorkbookLimits, archive_size: int
) -> None:
    infos = archive.infolist()
    if len(infos) > limits.maximum_member_count:
        raise WorkbookValidationError("workbook member count exceeds maximum")
    names: set[str] = set()
    expanded = 0
    for info in infos:
        _safe_member_name(info.filename)
        key = info.filename.rstrip("/")
        if key in names:
            raise WorkbookValidationError("duplicate workbook member path")
        names.add(key)
        if info.flag_bits & 0x1:
            raise WorkbookValidationError("encrypted workbook member")
        if info.file_size > limits.maximum_member_bytes:
            raise WorkbookValidationError("workbook member size exceeds maximum")
        expanded += info.file_size
        if expanded > limits.maximum_expanded_bytes:
            raise WorkbookValidationError(
                "workbook expanded size exceeds maximum"
            )
        if (
            info.file_size
            > max(info.compress_size, 1) * limits.maximum_compression_ratio
        ):
            raise WorkbookValidationError(
                "workbook compression ratio exceeds maximum"
            )
    if expanded > archive_size * limits.maximum_compression_ratio:
        raise WorkbookValidationError("workbook compression ratio exceeds maximum")
    _validate_xml_metadata(archive)


def open_validated_workbook(
    workbook_bytes: bytes,
    *,
    limits: WorkbookLimits,
) -> Workbook:
    try:
        with zipfile.ZipFile(io.BytesIO(workbook_bytes), "r") as archive:
            _validate_package(
                archive, limits=limits, archive_size=len(workbook_bytes)
            )
        workbook = openpyxl.load_workbook(
            io.BytesIO(workbook_bytes),
            read_only=True,
            data_only=False,
            keep_links=False,
        )
    except WorkbookValidationError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise WorkbookValidationError("invalid XLSX workbook") from error
    try:
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows():
                if any(cell.data_type == "f" for cell in row):
                    raise WorkbookValidationError(
                        "formula cells are forbidden"
                    )
    except BaseException:
        workbook.close()
        raise
    return workbook

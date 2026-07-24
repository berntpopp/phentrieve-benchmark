import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, ClassVar, Generic, Literal, Self, TypeVar
from unicodedata import category, normalize
from urllib.parse import urlsplit

import yaml  # type: ignore[import-untyped]
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)
from yaml.events import AliasEvent  # type: ignore[import-untyped]
from yaml.nodes import MappingNode  # type: ignore[import-untyped]

from phentrieve_benchmark.models.identifiers import HpoRelease
from phentrieve_benchmark.provenance.canonical import canonical_json_bytes
from phentrieve_benchmark.provenance.digests import Sha256Hex, sha256_bytes

_T = TypeVar("_T", bound=BaseModel)
_COMMIT = re.compile(r"[0-9a-f]{40}", re.ASCII)
_SAFE_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:/+-]*", re.ASCII)
_PATH_CHARACTER = re.compile(r"[A-Za-z0-9._*? /-]+", re.ASCII)
_HPO_PATTERN = re.compile(r"HP:[0-9]{7}", re.ASCII)


def _safe_id(value: str) -> str:
    canonical = normalize("NFC", value)
    if _SAFE_ID.fullmatch(canonical) is None:
        raise ValueError("value must be a safe ASCII identifier")
    return canonical


def _https_url(value: str, *, host: str | None = None) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise ValueError("URL must use HTTPS")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
    ):
        raise ValueError("URL must not contain userinfo or a port")
    if host is not None and parsed.hostname != host:
        raise ValueError(f"URL host must be {host}")
    if parsed.query:
        raise ValueError("URL must not contain a query")
    if parsed.fragment:
        raise ValueError("URL must not contain a fragment")
    return value


def _path_pattern(value: str, *, allow_glob: bool) -> str:
    if value != normalize("NFC", value):
        raise ValueError("path must use NFC")
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or "//" in value
        or _PATH_CHARACTER.fullmatch(value) is None
        or any(category(character).startswith("C") for character in value)
    ):
        raise ValueError("path must be a safe relative POSIX path")
    if not allow_glob and ("*" in value or "?" in value):
        raise ValueError("path prefix must not contain glob characters")
    parts = value.split("/")
    if any(
        part in {"", ".", ".."} or part != part.strip(" ") for part in parts
    ):
        raise ValueError("path must not contain empty, dot, or parent segments")
    if PurePosixPath(value).is_absolute():
        raise ValueError("path must be relative")
    return value


class ArchiveLock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    url: str
    format: Literal["zip", "tar"]
    expected_byte_length: int = Field(gt=0)
    maximum_byte_length: int = Field(gt=0)
    sha256: Sha256Hex
    expected_top_level_directory: str = Field(min_length=1)
    maximum_member_count: int = Field(gt=0)
    maximum_member_bytes: int = Field(gt=0)
    maximum_expanded_bytes: int = Field(gt=0)
    maximum_compression_ratio: int = Field(gt=0)

    @field_validator("url")
    @classmethod
    def url_is_direct_codeload(cls, value: str) -> str:
        return _https_url(value, host="codeload.github.com")

    @field_validator("sha256")
    @classmethod
    def digest_is_not_placeholder(cls, value: str) -> str:
        if value == "0" * 64:
            raise ValueError("sha256 must not be an all-zero placeholder")
        return value

    @field_validator("expected_top_level_directory")
    @classmethod
    def top_level_is_one_safe_segment(cls, value: str) -> str:
        if (
            value != normalize("NFC", value)
            or "/" in value
            or "\\" in value
            or value in {".", ".."}
            or any(category(character).startswith("C") for character in value)
        ):
            raise ValueError(
                "expected_top_level_directory must be one safe segment"
            )
        return value

    @model_validator(mode="after")
    def exact_length_fits_limit(self) -> Self:
        if self.expected_byte_length > self.maximum_byte_length:
            raise ValueError(
                "expected_byte_length must not exceed maximum_byte_length"
            )
        return self


class E3cLanguagePath(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    language: Literal["en", "fr", "es"]
    path_pattern: str
    expected_documents: int = Field(gt=0)

    @field_validator("path_pattern")
    @classmethod
    def path_is_safe_glob(cls, value: str) -> str:
        return _path_pattern(value, allow_glob=True)


class E3cSemanticType(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1)
    kind: Literal["annotation", "relation"]
    begin_attribute: str | None = None
    end_attribute: str | None = None
    concept_attribute: str | None = None
    argument_attributes: tuple[str, ...] = ()
    allowed_attributes: tuple[str, ...] = ()

    @field_validator(
        "name",
        "begin_attribute",
        "end_attribute",
        "concept_attribute",
    )
    @classmethod
    def scalar_identifiers_are_safe(cls, value: str | None) -> str | None:
        return None if value is None else _safe_id(value)

    @field_validator("argument_attributes", "allowed_attributes")
    @classmethod
    def identifier_sets_are_canonical(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        canonical = tuple(_safe_id(value) for value in values)
        if len(canonical) != len(set(canonical)):
            raise ValueError("duplicate semantic attribute")
        return tuple(sorted(canonical))

    @model_validator(mode="after")
    def span_fields_match_kind(self) -> Self:
        if self.kind == "annotation":
            if self.begin_attribute is None or self.end_attribute is None:
                raise ValueError("annotation type requires begin and end attributes")
        elif self.begin_attribute is not None or self.end_attribute is not None:
            raise ValueError("relation type cannot declare span attributes")
        return self


class E3cAdapterContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    kind: Literal["e3c-xmi/v1"]
    language_paths: tuple[E3cLanguagePath, ...]
    sofa_type: str = Field(min_length=1)
    structural_types: tuple[str, ...]
    semantic_types: tuple[E3cSemanticType, ...]

    @field_validator("sofa_type")
    @classmethod
    def sofa_type_is_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("structural_types")
    @classmethod
    def structural_types_are_canonical(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        canonical = tuple(_safe_id(value) for value in values)
        if len(canonical) != len(set(canonical)):
            raise ValueError("duplicate structural type")
        return tuple(sorted(canonical))

    @field_validator("language_paths")
    @classmethod
    def language_paths_are_canonical(
        cls, values: tuple[E3cLanguagePath, ...]
    ) -> tuple[E3cLanguagePath, ...]:
        languages = [value.language for value in values]
        if len(languages) != len(set(languages)):
            raise ValueError("duplicate E3C language")
        return tuple(sorted(values, key=lambda value: value.language))

    @field_validator("semantic_types")
    @classmethod
    def semantic_types_are_canonical(
        cls, values: tuple[E3cSemanticType, ...]
    ) -> tuple[E3cSemanticType, ...]:
        names = [value.name for value in values]
        if len(names) != len(set(names)):
            raise ValueError("duplicate semantic type")
        return tuple(sorted(values, key=lambda value: value.name))


class WorkbookLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    maximum_member_count: int = Field(gt=0)
    maximum_member_bytes: int = Field(gt=0)
    maximum_expanded_bytes: int = Field(gt=0)
    maximum_compression_ratio: int = Field(gt=0)


class RaghpoAdapterContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    kind: Literal["raghpo-tabular/v1"]
    selected_files: tuple[str, ...]
    workbook_limits: WorkbookLimits

    @field_validator("selected_files")
    @classmethod
    def selected_files_are_canonical(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        canonical = tuple(
            _path_pattern(value, allow_glob=False) for value in values
        )
        if len(canonical) != len(set(canonical)):
            raise ValueError("duplicate selected file")
        return tuple(sorted(canonical))


AdapterContract = Annotated[
    E3cAdapterContract | RaghpoAdapterContract,
    Field(discriminator="kind"),
]


class SourceRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["source-recipe/v1"] = "source-recipe/v1"
    source_id: Literal["e3c", "raghpo"]
    repository_url: str
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_tag: str | None = None
    archive: ArchiveLock
    included_paths: tuple[str, ...]
    ignored_path_prefixes: tuple[str, ...] = ()
    adapter_id: str = Field(min_length=1)
    source_schema_id: str = Field(min_length=1)
    adapter_contract: AdapterContract
    license_evidence_sha256: Sha256Hex

    @field_validator("repository_url")
    @classmethod
    def repository_is_https_github(cls, value: str) -> str:
        return _https_url(value, host="github.com")

    @field_validator("source_tag")
    @classmethod
    def tag_is_immutable_release(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.casefold() == "latest" or re.fullmatch(
            r"v[0-9][A-Za-z0-9._-]*", value, re.ASCII
        ) is None:
            raise ValueError("source_tag must be an immutable version tag")
        return value

    @field_validator("included_paths")
    @classmethod
    def included_paths_are_canonical(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        canonical = tuple(
            _path_pattern(value, allow_glob=True) for value in values
        )
        if not canonical:
            raise ValueError("included_paths must not be empty")
        if len(canonical) != len(set(canonical)):
            raise ValueError("duplicate included path")
        return tuple(sorted(canonical))

    @field_validator("ignored_path_prefixes")
    @classmethod
    def ignored_prefixes_are_canonical(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        canonical = tuple(
            _path_pattern(value, allow_glob=False) for value in values
        )
        if len(canonical) != len(set(canonical)):
            raise ValueError("duplicate ignored path prefix")
        return tuple(sorted(canonical))

    @field_validator("adapter_id", "source_schema_id")
    @classmethod
    def identifiers_are_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("license_evidence_sha256")
    @classmethod
    def license_digest_is_not_placeholder(cls, value: str) -> str:
        if value == "0" * 64:
            raise ValueError("license_evidence_sha256 must not be all-zero")
        return value

    @model_validator(mode="after")
    def identities_and_path_policies_agree(self) -> Self:
        repository = urlsplit(self.repository_url).path.strip("/").split("/")
        archive = urlsplit(self.archive.url).path.strip("/").split("/")
        if (
            len(repository) != 2
            or len(archive) != 4
            or archive[:2] != repository
            or archive[2] not in {"zip", "tar"}
            or archive[3] != self.source_commit
        ):
            raise ValueError(
                "codeload archive repository and embedded commit must match"
            )
        expected_kind = (
            "e3c-xmi/v1" if self.source_id == "e3c" else "raghpo-tabular/v1"
        )
        if self.adapter_contract.kind != expected_kind:
            raise ValueError("adapter contract does not match source_id")
        if self.adapter_id != expected_kind:
            raise ValueError("adapter_id does not match adapter contract")
        for included in self.included_paths:
            literal_prefix = re.split(r"[*?]", included, maxsplit=1)[0]
            for ignored in self.ignored_path_prefixes:
                if literal_prefix == ignored or literal_prefix.startswith(
                    f"{ignored}/"
                ):
                    raise ValueError(
                        "included and ignored path policies overlap"
                    )
        return self


class ExpectedTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_path: str
    sheet_name: str | None = None
    columns: tuple[str, ...]
    data_rows: int = Field(ge=0)

    @field_validator("source_path")
    @classmethod
    def source_path_is_safe(cls, value: str) -> str:
        return _path_pattern(value, allow_glob=False)

    @field_validator("sheet_name")
    @classmethod
    def sheet_name_is_exact(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value != normalize("NFC", value) or not value:
            raise ValueError("sheet_name must be nonempty NFC")
        return value

    @field_validator("columns")
    @classmethod
    def columns_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values or any(not value for value in values):
            raise ValueError("columns must be nonempty")
        if len(values) != len(set(values)):
            raise ValueError("duplicate column")
        return values


class ExpectedCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1)
    count: int = Field(ge=0)

    @field_validator("name")
    @classmethod
    def name_is_safe(cls, value: str) -> str:
        return _safe_id(value)


class NormalizationRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["normalization-recipe/v1"] = (
        "normalization-recipe/v1"
    )
    target_id: Literal["e3c", "csc", "gsc"]
    source_id: Literal["e3c", "raghpo"]
    adapter_id: str = Field(min_length=1)
    required_paths: tuple[str, ...]
    expected_tables: tuple[ExpectedTable, ...] = ()
    expected_counts: tuple[ExpectedCount, ...]
    hpo_release: HpoRelease | None = None

    @field_validator("adapter_id")
    @classmethod
    def adapter_id_is_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("required_paths")
    @classmethod
    def required_paths_are_canonical(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        canonical = tuple(
            _path_pattern(value, allow_glob=False) for value in values
        )
        if not canonical or len(canonical) != len(set(canonical)):
            raise ValueError("required_paths must be nonempty and unique")
        return tuple(sorted(canonical))

    @field_validator("expected_tables")
    @classmethod
    def tables_are_canonical(
        cls, values: tuple[ExpectedTable, ...]
    ) -> tuple[ExpectedTable, ...]:
        identities = [
            (value.source_path, value.sheet_name or "") for value in values
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate expected table")
        return tuple(
            sorted(
                values,
                key=lambda value: (value.source_path, value.sheet_name or ""),
            )
        )

    @field_validator("expected_counts")
    @classmethod
    def counts_are_canonical(
        cls, values: tuple[ExpectedCount, ...]
    ) -> tuple[ExpectedCount, ...]:
        identities = [value.name for value in values]
        if not values or len(identities) != len(set(identities)):
            raise ValueError("expected_counts must be nonempty and unique")
        return tuple(sorted(values, key=lambda value: value.name))

    @model_validator(mode="after")
    def target_matches_source(self) -> Self:
        expected_source = "e3c" if self.target_id == "e3c" else "raghpo"
        if self.source_id != expected_source:
            raise ValueError("target_id does not match source_id")
        return self


class LicenseEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["license-evidence/v1"] = "license-evidence/v1"
    source_id: Literal["e3c", "raghpo"]
    repository_url: str
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    license_id: str = Field(min_length=1)
    license_url: str
    access_date: date
    upstream_statement: str = Field(min_length=1)
    redistribution_decision: Literal["source_not_redistributed"]
    derivative_work_notes: str = Field(min_length=1)
    unresolved_questions: tuple[str, ...] = ()

    @field_validator("repository_url", "license_url")
    @classmethod
    def urls_are_https(cls, value: str) -> str:
        return _https_url(value)

    @field_validator("license_id")
    @classmethod
    def license_id_is_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator(
        "upstream_statement",
        "derivative_work_notes",
    )
    @classmethod
    def prose_is_nfc(cls, value: str) -> str:
        canonical = normalize("NFC", value)
        if not canonical:
            raise ValueError("value must not be empty")
        return canonical

    @field_validator("unresolved_questions")
    @classmethod
    def unresolved_questions_are_canonical(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        canonical = tuple(normalize("NFC", value) for value in values)
        if any(not value for value in canonical):
            raise ValueError("unresolved question must not be empty")
        if len(canonical) != len(set(canonical)):
            raise ValueError("duplicate unresolved question")
        return tuple(sorted(canonical))


@dataclass(frozen=True)
class LoadedRecipe(Generic[_T]):
    value: _T
    sha256: str


class _StrictSafeLoader(yaml.SafeLoader):  # type: ignore[misc]
    yaml_implicit_resolvers: ClassVar[dict[Any, Any]] = {
        key: [
            resolver
            for resolver in resolvers
            if resolver[0] != "tag:yaml.org,2002:timestamp"
        ]
        for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    def compose_node(self, parent: object, index: object) -> object:
        if self.check_event(AliasEvent):
            raise ValueError("YAML aliases are forbidden")
        return super().compose_node(parent, index)

    def construct_mapping(
        self,
        node: MappingNode,
        deep: bool = False,
    ) -> dict[str, object]:
        if not isinstance(node, MappingNode):
            raise ValueError("expected YAML mapping")
        mapping: dict[str, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("YAML mapping keys must be strings")
            canonical_key = normalize("NFC", key)
            if key != canonical_key:
                raise ValueError("YAML mapping keys must use NFC")
            if key in mapping:
                raise ValueError(f"duplicate YAML mapping key: {key}")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _load_yaml(path: Path) -> object:
    try:
        documents = list(
            yaml.load_all(
                path.read_text(encoding="utf-8"),
                Loader=_StrictSafeLoader,
            )
        )
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"invalid YAML recipe: {path.name}") from error
    if len(documents) != 1:
        raise ValueError("YAML recipe must contain exactly one document")
    if not isinstance(documents[0], dict):
        raise ValueError("YAML recipe must contain one top-level mapping")
    return documents[0]


def _load_model(path: Path, model: type[_T]) -> LoadedRecipe[_T]:
    payload = _load_yaml(path)
    canonical = canonical_json_bytes(payload)
    value = TypeAdapter(model).validate_json(canonical, strict=True)
    semantic = canonical_json_bytes(value.model_dump(mode="json"))
    return LoadedRecipe(value=value, sha256=sha256_bytes(semantic))


def load_source_recipe(path: Path) -> LoadedRecipe[SourceRecipe]:
    return _load_model(path, SourceRecipe)


def load_target_recipe(path: Path) -> LoadedRecipe[NormalizationRecipe]:
    return _load_model(path, NormalizationRecipe)


def load_license_evidence(path: Path) -> LoadedRecipe[LicenseEvidence]:
    return _load_model(path, LicenseEvidence)

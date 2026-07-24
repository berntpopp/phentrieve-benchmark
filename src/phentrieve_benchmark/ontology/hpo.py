import io
import re
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Self

from pronto.ontology import Ontology
from pydantic import BaseModel, ConfigDict, Field, model_validator

from phentrieve_benchmark.acquisition.recipes import LoadedRecipe, _load_model
from phentrieve_benchmark.provenance.digests import Sha256Hex

_HPO_ID = re.compile(r"HP:[0-9]{7}", re.ASCII)
_UMLS_CUI = re.compile(r"C[0-9]{7}", re.ASCII)
_SHA256 = re.compile(r"[0-9a-f]{64}", re.ASCII)
_RELEASE = re.compile(r"v[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)


class HpoIndexError(ValueError):
    """The supplied ontology cannot form a strict HPO revision index."""


class HpoSourceRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["hpo-source-recipe/v1"] = "hpo-source-recipe/v1"
    release: str = Field(pattern=r"^v[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    url: str
    expected_byte_length: int = Field(gt=0)
    maximum_byte_length: int = Field(gt=0)
    sha256: Sha256Hex
    format: Literal["obo-1.4"]
    parser: Literal["pronto-2"]

    @model_validator(mode="after")
    def source_identity_is_exact(self) -> Self:
        expected_url = (
            "https://github.com/obophenotype/human-phenotype-ontology/"
            f"releases/download/{self.release}/hp.obo"
        )
        if self.url != expected_url:
            raise ValueError("HPO URL must exactly match the pinned release")
        if self.expected_byte_length > self.maximum_byte_length:
            raise ValueError("expected length exceeds maximum")
        if self.sha256 == "0" * 64:
            raise ValueError("HPO SHA-256 must not be a placeholder")
        return self


def load_hpo_source_recipe(path: Path) -> LoadedRecipe[HpoSourceRecipe]:
    return _load_model(path, HpoSourceRecipe)


@dataclass(frozen=True)
class HpoTermRecord:
    hpo_id: str
    label: str | None
    obsolete: bool
    alternate_ids: tuple[str, ...]
    replaced_by: tuple[str, ...]
    consider: tuple[str, ...]
    umls_cuis: tuple[str, ...]


@dataclass(frozen=True)
class HpoIndex:
    release: str
    ontology_sha256: str
    terms: Mapping[str, HpoTermRecord]
    alternate_to_primary: Mapping[str, str]
    umls_to_hpo: Mapping[str, tuple[str, ...]]


def _validate_id(value: str) -> str:
    if _HPO_ID.fullmatch(value) is None:
        raise HpoIndexError(f"malformed HPO identifier: {value!r}")
    return value


def _assert_unique_primary_stanzas(ontology_bytes: bytes) -> None:
    try:
        text = ontology_bytes.decode("utf-8")
    except UnicodeError as error:
        raise HpoIndexError("ontology is not valid UTF-8") from error
    identifiers: list[str] = []
    in_term = False
    for line in text.splitlines():
        if line == "[Term]":
            in_term = True
        elif line.startswith("["):
            in_term = False
        elif in_term and line.startswith("id: "):
            identifiers.append(line[4:])
    if len(identifiers) != len(set(identifiers)):
        raise HpoIndexError("duplicate primary HPO identifier")


def _umls_xrefs_by_term(ontology_bytes: bytes) -> dict[str, tuple[str, ...]]:
    text = ontology_bytes.decode("utf-8")
    result: dict[str, tuple[str, ...]] = {}
    term_id: str | None = None
    cuis: list[str] = []

    def publish() -> None:
        if term_id is None:
            return
        if len(cuis) != len(set(cuis)):
            raise HpoIndexError(f"duplicate UMLS cross-reference on {term_id}")
        result[term_id] = tuple(sorted(cuis))

    for line in (*text.splitlines(), "[End]"):
        if line == "[Term]" or line.startswith("["):
            publish()
            term_id = None
            cuis = []
        elif term_id is None and line.startswith("id: HP:"):
            term_id = line[4:]
        elif line.startswith("xref: UMLS:"):
            value = line.removeprefix("xref: UMLS:")
            if _UMLS_CUI.fullmatch(value) is None:
                raise HpoIndexError(
                    f"malformed UMLS cross-reference: {value!r}"
                )
            cuis.append(value)
    return result


def _validate_graph(terms: dict[str, HpoTermRecord]) -> None:
    for record in terms.values():
        for target in (*record.replaced_by, *record.consider):
            if target not in terms:
                raise HpoIndexError(
                    f"replacement candidate does not exist: {target}"
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str) -> None:
        if identifier in visiting:
            raise HpoIndexError("replacement graph contains a cycle")
        if identifier in visited:
            return
        visiting.add(identifier)
        record = terms[identifier]
        for target in (*record.replaced_by, *record.consider):
            visit(target)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in terms:
        visit(identifier)


def load_hpo_index(
    ontology_bytes: bytes,
    *,
    release: str,
    ontology_sha256: str,
) -> HpoIndex:
    if _RELEASE.fullmatch(release) is None:
        raise HpoIndexError("invalid HPO release")
    if (
        _SHA256.fullmatch(ontology_sha256) is None
        or sha256(ontology_bytes).hexdigest() != ontology_sha256
    ):
        raise HpoIndexError("ontology SHA-256 mismatch")
    _assert_unique_primary_stanzas(ontology_bytes)
    umls_xrefs = _umls_xrefs_by_term(ontology_bytes)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UnicodeWarning)
            ontology = Ontology(
                io.BytesIO(ontology_bytes),
                import_depth=0,
                timeout=1,
                threads=1,
                encoding="utf-8",
            )
        terms: dict[str, HpoTermRecord] = {}
        alternate_owners: list[tuple[str, str]] = []
        for term in ontology.terms():
            identifier = _validate_id(term.id)
            alternate_ids = tuple(
                sorted(_validate_id(value) for value in term.alternate_ids)
            )
            replaced_by = tuple(
                sorted(_validate_id(value.id) for value in term.replaced_by)
            )
            consider = tuple(
                sorted(_validate_id(value.id) for value in term.consider)
            )
            record = HpoTermRecord(
                hpo_id=identifier,
                label=term.name,
                obsolete=term.obsolete,
                alternate_ids=alternate_ids,
                replaced_by=replaced_by,
                consider=consider,
                umls_cuis=umls_xrefs.get(identifier, ()),
            )
            if identifier in terms:
                raise HpoIndexError("duplicate primary HPO identifier")
            terms[identifier] = record
            for alternate in alternate_ids:
                alternate_owners.append((alternate, identifier))
    except HpoIndexError:
        raise
    except Exception as error:
        raise HpoIndexError("invalid OBO ontology") from error

    _validate_graph(terms)
    alternate_to_primary: dict[str, str] = {}
    for alternate, owner in alternate_owners:
        primary_collision = terms.get(alternate)
        if primary_collision is not None:
            if not primary_collision.obsolete:
                raise HpoIndexError("alternate identifier collides with primary")
            # The official HPO intentionally retains many obsolete primary
            # stanzas while also listing those identifiers as alt_ids on an
            # active term. Primary status wins so the conservative revision
            # policy can review the obsolete record instead of auto-mapping it.
            continue
        previous = alternate_to_primary.get(alternate)
        if previous is not None and previous != owner:
            raise HpoIndexError("alternate HPO identifier collision")
        alternate_to_primary[alternate] = owner
    reverse_umls: dict[str, list[str]] = {}
    for record in terms.values():
        for cui in record.umls_cuis:
            reverse_umls.setdefault(cui, []).append(record.hpo_id)
    return HpoIndex(
        release=release,
        ontology_sha256=ontology_sha256,
        terms=MappingProxyType(dict(sorted(terms.items()))),
        alternate_to_primary=MappingProxyType(
            dict(sorted(alternate_to_primary.items()))
        ),
        umls_to_hpo=MappingProxyType(
            {
                cui: tuple(sorted(identifiers))
                for cui, identifiers in sorted(reverse_umls.items())
            }
        ),
    )

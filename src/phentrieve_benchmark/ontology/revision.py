import re
from collections.abc import Iterable
from enum import StrEnum
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

from phentrieve_benchmark.ontology.hpo import HpoIndex
from phentrieve_benchmark.provenance.digests import Sha256Hex

_HPO_ID = re.compile(r"HP:[0-9]{7}", re.ASCII)


class HpoRevisionStatus(StrEnum):
    ACTIVE = "active"
    ALT_ID = "alt_id"
    OBSOLETE_REPLACED = "obsolete_replaced"
    OBSOLETE_AMBIGUOUS = "obsolete_ambiguous"
    OBSOLETE_UNRESOLVED = "obsolete_unresolved"
    UNKNOWN = "unknown"
    INVALID_FORMAT = "invalid_format"


class HpoRevisionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["hpo-revision-decision/v1"] = (
        "hpo-revision-decision/v1"
    )
    source_annotation_id: str = Field(min_length=1)
    source_hpo_id: str = Field(min_length=1)
    ontology_release: str = Field(pattern=r"^v[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    ontology_sha256: Sha256Hex
    status: HpoRevisionStatus
    canonical_hpo_id: str | None = None
    proposed_hpo_ids: tuple[str, ...] = ()
    replacement_chain: tuple[str, ...] = ()
    requires_manual_review: bool
    reason_code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")

    @field_validator("proposed_hpo_ids")
    @classmethod
    def proposals_are_canonical(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("duplicate proposed HPO identifier")
        return tuple(sorted(values))


class _DecisionCommon(TypedDict):
    source_annotation_id: str
    source_hpo_id: str
    ontology_release: str
    ontology_sha256: str


def _decision(
    annotation_id: str,
    source_id: str,
    index: HpoIndex,
) -> HpoRevisionDecision:
    common: _DecisionCommon = {
        "source_annotation_id": annotation_id,
        "source_hpo_id": source_id,
        "ontology_release": index.release,
        "ontology_sha256": index.ontology_sha256,
    }
    if _HPO_ID.fullmatch(source_id) is None:
        return HpoRevisionDecision(
            **common,
            status=HpoRevisionStatus.INVALID_FORMAT,
            requires_manual_review=True,
            reason_code="invalid_hpo_id_format",
        )
    alternate_primary = index.alternate_to_primary.get(source_id)
    if alternate_primary is not None:
        return HpoRevisionDecision(
            **common,
            status=HpoRevisionStatus.ALT_ID,
            canonical_hpo_id=alternate_primary,
            requires_manual_review=False,
            reason_code="alternate_id_canonicalized",
        )
    term = index.terms.get(source_id)
    if term is None:
        return HpoRevisionDecision(
            **common,
            status=HpoRevisionStatus.UNKNOWN,
            requires_manual_review=True,
            reason_code="identifier_not_in_release",
        )
    if not term.obsolete:
        return HpoRevisionDecision(
            **common,
            status=HpoRevisionStatus.ACTIVE,
            canonical_hpo_id=source_id,
            requires_manual_review=False,
            reason_code="active_primary_id",
        )
    if term.consider or len(term.replaced_by) > 1:
        proposals = tuple(sorted({*term.replaced_by, *term.consider}))
        return HpoRevisionDecision(
            **common,
            status=HpoRevisionStatus.OBSOLETE_AMBIGUOUS,
            proposed_hpo_ids=proposals,
            replacement_chain=term.replaced_by,
            requires_manual_review=True,
            reason_code="obsolete_has_ambiguous_candidates",
        )
    if not term.replaced_by:
        return HpoRevisionDecision(
            **common,
            status=HpoRevisionStatus.OBSOLETE_UNRESOLVED,
            requires_manual_review=True,
            reason_code="obsolete_without_candidate",
        )

    chain: list[str] = []
    current = term
    while len(current.replaced_by) == 1 and not current.consider:
        candidate = current.replaced_by[0]
        chain.append(candidate)
        current = index.terms[candidate]
        if not current.obsolete:
            return HpoRevisionDecision(
                **common,
                status=HpoRevisionStatus.OBSOLETE_REPLACED,
                proposed_hpo_ids=(candidate,),
                replacement_chain=tuple(chain),
                requires_manual_review=True,
                reason_code="obsolete_replacement_proposed",
            )
    proposals = tuple(sorted({*current.replaced_by, *current.consider}))
    return HpoRevisionDecision(
        **common,
        status=HpoRevisionStatus.OBSOLETE_AMBIGUOUS,
        proposed_hpo_ids=proposals,
        replacement_chain=tuple(chain),
        requires_manual_review=True,
        reason_code="replacement_chain_becomes_ambiguous",
    )


def audit_hpo_ids(
    values: Iterable[tuple[str, str]],
    *,
    index: HpoIndex,
) -> tuple[HpoRevisionDecision, ...]:
    materialized = list(values)
    annotation_ids = [annotation_id for annotation_id, _ in materialized]
    if len(annotation_ids) != len(set(annotation_ids)):
        raise ValueError("duplicate source annotation identifier")
    return tuple(
        sorted(
            (
                _decision(annotation_id, source_id, index)
                for annotation_id, source_id in materialized
            ),
            key=lambda decision: decision.source_annotation_id,
        )
    )

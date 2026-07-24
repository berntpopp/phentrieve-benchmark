from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from phentrieve_benchmark.models.annotation import AnnotationSet
from phentrieve_benchmark.models.document import Document
from phentrieve_benchmark.models.source_annotation import SourceAnnotationSet


class RagHpoSourceAnnotationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["raghpo-source-annotation-record/v1"] = (
        "raghpo-source-annotation-record/v1"
    )
    source_row_id: str = Field(min_length=1)
    source_case_id: str = Field(min_length=1)
    secondary_id: str | None = None
    hpo_description: str = Field(min_length=1)
    raw_hpo_term: str = Field(min_length=1)
    category: str | None = None
    derived_annotation_ids: tuple[str, ...]

    @field_validator("derived_annotation_ids")
    @classmethod
    def annotation_ids_are_unique(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        if not values or len(values) != len(set(values)):
            raise ValueError("derived annotation IDs must be nonempty and unique")
        return values


@dataclass(frozen=True)
class NormalizedTarget:
    documents: tuple[Document, ...]
    annotation_sets: tuple[AnnotationSet, ...] = ()
    source_annotation_sets: tuple[SourceAnnotationSet, ...] = ()
    source_sidecar: tuple[RagHpoSourceAnnotationRecord, ...] = ()
    counts: tuple[tuple[str, int], ...] = ()
    warnings: tuple[tuple[str, int], ...] = ()

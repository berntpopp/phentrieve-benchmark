from hashlib import sha256
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes

Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ComponentDigest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: str = Field(min_length=1)
    stable_id: str = Field(min_length=1)
    sha256: Sha256Hex


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def aggregate_sha256(
    schema_version: str, components: list[ComponentDigest]
) -> str:
    ordered_components = sorted(
        components,
        key=lambda component: (
            component.role,
            component.stable_id,
            component.sha256,
        ),
    )
    payload = {
        "schema_version": schema_version,
        "components": [
            component.model_dump(mode="json") for component in ordered_components
        ],
    }
    return sha256_bytes(canonical_json_bytes(payload))

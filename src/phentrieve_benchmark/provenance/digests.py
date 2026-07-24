from hashlib import sha256
from typing import Annotated
from unicodedata import normalize

from pydantic import BaseModel, ConfigDict, Field

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes

Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ComponentDigest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    role: str = Field(min_length=1)
    stable_id: str = Field(min_length=1)
    sha256: Sha256Hex


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def aggregate_sha256(
    schema_version: str, components: list[ComponentDigest]
) -> str:
    normalized_schema_version = normalize("NFC", schema_version)
    if not normalized_schema_version.strip():
        raise ValueError("schema version must not be blank")

    normalized_components = [
        {
            "role": normalize("NFC", component.role),
            "stable_id": normalize("NFC", component.stable_id),
            "sha256": component.sha256,
        }
        for component in components
    ]
    ordered_components = sorted(
        normalized_components,
        key=lambda component: (
            component["role"],
            component["stable_id"],
            component["sha256"],
        ),
    )
    identities = [
        (component["role"], component["stable_id"])
        for component in ordered_components
    ]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate component identity")
    payload = {
        "schema_version": normalized_schema_version,
        "components": ordered_components,
    }
    return sha256_bytes(canonical_json_bytes(payload))

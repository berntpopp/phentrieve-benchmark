import unicodedata
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Any

import rfc8785


def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        normalized_mapping: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = unicodedata.normalize("NFC", str(key))
            if normalized_key in normalized_mapping:
                message = f"normalized mapping key collision: {normalized_key!r}"
                raise ValueError(message)
            normalized_mapping[normalized_key] = normalize_value(item)
        return normalized_mapping
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        return [normalize_value(item) for item in value]
    return value


def canonical_text_bytes(text: str) -> bytes:
    normalized_text = unicodedata.normalize("NFC", text)
    return normalized_text.replace("\r\n", "\n").replace("\r", "\n").encode()


def canonical_json_bytes(value: Any) -> bytes:
    return rfc8785.dumps(normalize_value(value))


def canonical_jsonl_bytes(
    records: Sequence[Mapping[str, Any]], *, identity_key: str
) -> bytes:
    normalized_records = [normalize_value(record) for record in records]
    normalized_identity_key = unicodedata.normalize("NFC", identity_key)
    records_with_identities = sorted(
        (
            (str(record[normalized_identity_key]), record)
            for record in normalized_records
        ),
        key=lambda item: item[0],
    )
    for (identity, _), (next_identity, _) in pairwise(records_with_identities):
        if identity == next_identity:
            raise ValueError(f"duplicate canonical identity: {identity!r}")
    return b"".join(
        canonical_json_bytes(record) + b"\n" for _, record in records_with_identities
    )

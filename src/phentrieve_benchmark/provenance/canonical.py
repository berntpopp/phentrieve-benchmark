import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

import rfc8785


def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        return {
            unicodedata.normalize("NFC", str(key)): normalize_value(item)
            for key, item in value.items()
        }
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
    sorted_records = sorted(
        normalized_records, key=lambda record: str(record[identity_key])
    )
    return b"".join(canonical_json_bytes(record) + b"\n" for record in sorted_records)

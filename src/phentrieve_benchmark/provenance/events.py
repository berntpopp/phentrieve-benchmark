"""Safe append-only structured event logging.

``EventWriter`` accepts a caller-supplied, trusted local path.  It validates an
entire event and renders its canonical JSON record before opening that path, so
an unsafe event cannot create a file or alter an existing event stream.  A
single pre-rendered record is appended with one write while the file is opened
in append mode.  This preserves prior content and relies on the operating
system's normal append semantics; coordinating independent processes beyond
that is intentionally outside this small, local event-log boundary.
"""

import math
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes


class UnsafeEventError(ValueError):
    """Raised when an event could expose sensitive or non-canonical data."""


_FORBIDDEN_KEYS = frozenset(
    {"text", "full_text", "prompt", "credential", "credentials", "exception"}
)
_SAFE_EVENT_NAME = re.compile(r"[A-Za-z0-9_.:-]+", re.ASCII)


def _security_key(key: str) -> str:
    """Normalize keys for safety comparisons, including compatibility forms."""
    return unicodedata.normalize("NFKC", key).casefold()


def _validate_event_name(event: object) -> str:
    if not isinstance(event, str) or _SAFE_EVENT_NAME.fullmatch(event) is None:
        raise UnsafeEventError("event name must be a nonempty safe ASCII identifier")
    return event


def _validate_value(value: object, *, location: str) -> None:
    if isinstance(value, BaseException):
        raise UnsafeEventError(f"unsafe event value at {location}: raw exception")
    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise UnsafeEventError(f"unsafe event value at {location}: non-finite float")
    if isinstance(value, Mapping):
        _validate_mapping(value, location=location)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_value(item, location=f"{location}[{index}]")
        return
    raise UnsafeEventError(
        f"unsafe event value at {location}: {type(value).__name__} is not JSON"
    )


def _validate_mapping(mapping: Mapping[Any, Any], *, location: str) -> None:
    canonical_keys: set[str] = set()
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise UnsafeEventError(f"unsafe event field at {location}: non-string key")
        if any(unicodedata.category(character).startswith("C") for character in key):
            raise UnsafeEventError(
                f"unsafe event field at {location}: control character"
            )

        normalized_key = unicodedata.normalize("NFC", key)
        if normalized_key in canonical_keys:
            raise UnsafeEventError(
                f"unsafe event field at {location}: normalized key collision"
            )
        canonical_keys.add(normalized_key)

        safe_key = _security_key(key)
        if safe_key in _FORBIDDEN_KEYS:
            raise UnsafeEventError(f"unsafe event field at {location}: {safe_key}")
        if safe_key == "event":
            raise UnsafeEventError(
                f"unsafe event field at {location}: reserved key {key!r}"
            )
        _validate_value(value, location=f"{location}.{key}")


class EventWriter:
    """Append validated canonical JSON events to one trusted local file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, *, event: str, fields: Mapping[str, Any]) -> None:
        """Append one text-free, canonical JSONL event.

        Validation and JSON serialization happen before any filesystem mutation.
        """
        event_name = _validate_event_name(event)
        _validate_mapping(fields, location="fields")
        record: dict[str, Any] = {"event": event_name, **fields}
        try:
            encoded_record = canonical_json_bytes(record)
        except (TypeError, ValueError, OverflowError) as error:
            raise UnsafeEventError("unsafe event value: not canonical JSON") from error

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(encoded_record + b"\n")

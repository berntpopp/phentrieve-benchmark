"""Safe append-only structured event logging.

``EventWriter`` accepts a caller-supplied, trusted local path.  It validates an
entire event into an isolated built-in snapshot and renders its canonical JSON
record before opening that path. Metadata keys use ``[a-z][a-z0-9_]{0,63}``;
string values use bounded (1--256 byte) ASCII identifier/code characters and
cannot contain whitespace or prose. A single pre-rendered record is appended
with one write while the file is opened in append mode. This preserves prior
content and relies on the operating system's normal append semantics;
coordinating independent processes beyond that is intentionally outside this
small, local event-log boundary.
"""

import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from phentrieve_benchmark.provenance.canonical import canonical_json_bytes


class UnsafeEventError(ValueError):
    """Raised when an event could expose sensitive or non-canonical data."""


_FORBIDDEN_KEY_FRAGMENTS = (
    "text",
    "prompt",
    "credential",
    "exception",
    "secret",
    "password",
)
_FORBIDDEN_EXACT_KEYS = frozenset(
    {
        "api_key",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "private_key",
        "token",
    }
)
_SAFE_EVENT_NAME = re.compile(r"[a-z][a-z0-9_.:-]{0,63}", re.ASCII)
_SAFE_METADATA_KEY = re.compile(r"[a-z][a-z0-9_]{0,63}", re.ASCII)
_SAFE_STRING_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/@:+-]{0,255}", re.ASCII)


def _validate_event_name(event: object) -> str:
    if type(event) is not str or _SAFE_EVENT_NAME.fullmatch(event) is None:
        raise UnsafeEventError("event name must be a nonempty safe ASCII identifier")
    return event


def _snapshot_sequence(
    sequence: Sequence[object],
    *,
    location: str,
    active: set[int],
    memo: dict[int, Any],
) -> list[Any]:
    identity = id(sequence)
    if identity in active:
        raise UnsafeEventError(f"unsafe event value at {location}: cyclic sequence")
    existing = memo.get(identity)
    if isinstance(existing, list):
        return existing

    snapshot: list[Any] = []
    memo[identity] = snapshot
    active.add(identity)
    try:
        try:
            iterator = iter(sequence)
            for index, item in enumerate(iterator):
                snapshot.append(
                    _snapshot_value(
                        item,
                        location=f"{location}[{index}]",
                        active=active,
                        memo=memo,
                    )
                )
        except UnsafeEventError:
            raise
        except Exception as error:
            raise UnsafeEventError(
                f"unsafe event value at {location}: sequence traversal failed"
            ) from error
    finally:
        active.remove(identity)
    return snapshot


def _snapshot_mapping(
    mapping: Mapping[Any, Any],
    *,
    location: str,
    active: set[int],
    memo: dict[int, Any],
) -> dict[str, Any]:
    identity = id(mapping)
    if identity in active:
        raise UnsafeEventError(f"unsafe event value at {location}: cyclic mapping")
    existing = memo.get(identity)
    if isinstance(existing, dict):
        return existing

    snapshot: dict[str, Any] = {}
    normalized_keys: set[str] = set()
    memo[identity] = snapshot
    active.add(identity)
    try:
        try:
            items = iter(mapping.items())
            for item in items:
                try:
                    key, value = item
                except (TypeError, ValueError) as error:
                    raise UnsafeEventError(
                        f"unsafe event field at {location}: malformed mapping item"
                    ) from error
                if type(key) is not str:
                    raise UnsafeEventError(
                        f"unsafe event field at {location}: non-string key"
                    )

                normalized_key = unicodedata.normalize("NFKC", key).casefold()
                if normalized_key in normalized_keys:
                    raise UnsafeEventError(
                        f"unsafe event field at {location}: normalized key collision"
                    )
                normalized_keys.add(normalized_key)

                if _SAFE_METADATA_KEY.fullmatch(key) is None:
                    raise UnsafeEventError(
                        f"unsafe event field at {location}: "
                        f"invalid metadata key {key!r}"
                    )
                if key == "event":
                    raise UnsafeEventError(
                        f"unsafe event field at {location}: reserved key {key!r}"
                    )
                if key in _FORBIDDEN_EXACT_KEYS or any(
                    fragment in key for fragment in _FORBIDDEN_KEY_FRAGMENTS
                ):
                    raise UnsafeEventError(
                        f"unsafe event field at {location}: {key}"
                    )
                snapshot[key] = _snapshot_value(
                    value,
                    location=f"{location}.{key}",
                    active=active,
                    memo=memo,
                )
        except UnsafeEventError:
            raise
        except Exception as error:
            raise UnsafeEventError(
                f"unsafe event value at {location}: mapping traversal failed"
            ) from error
    finally:
        active.remove(identity)
    return snapshot


def _snapshot_value(
    value: object,
    *,
    location: str,
    active: set[int],
    memo: dict[int, Any],
) -> Any:
    if isinstance(value, BaseException):
        raise UnsafeEventError(f"unsafe event value at {location}: raw exception")
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        if _SAFE_STRING_VALUE.fullmatch(value) is None:
            raise UnsafeEventError(
                f"unsafe string value at {location}: expected bounded ASCII code"
            )
        return value
    if type(value) is float:
        if math.isfinite(value):
            return value
        raise UnsafeEventError(f"unsafe event value at {location}: non-finite float")
    if isinstance(value, Mapping):
        return _snapshot_mapping(
            value, location=location, active=active, memo=memo
        )
    if isinstance(value, (str, bytes, bytearray)):
        raise UnsafeEventError(
            f"unsafe event value at {location}: byte/text container is not JSON"
        )
    if isinstance(value, Sequence):
        return _snapshot_sequence(
            value, location=location, active=active, memo=memo
        )
    raise UnsafeEventError(
        f"unsafe event value at {location}: {type(value).__name__} is not JSON"
    )


class EventWriter:
    """Append validated canonical JSON events to one trusted local file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, *, event: str, fields: Mapping[str, Any]) -> None:
        """Append one text-free, canonical JSONL event.

        Validation and JSON serialization happen before any filesystem mutation.
        """
        event_name = _validate_event_name(event)
        if not isinstance(fields, Mapping):
            raise UnsafeEventError("event fields must be a mapping")
        snapshot = _snapshot_mapping(
            fields, location="fields", active=set(), memo={}
        )
        record: dict[str, Any] = {"event": event_name, **snapshot}
        try:
            encoded_record = canonical_json_bytes(record)
        except (TypeError, ValueError, OverflowError) as error:
            raise UnsafeEventError("unsafe event value: not canonical JSON") from error

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(encoded_record + b"\n")

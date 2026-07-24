"""Safe append-only structured event logging.

``EventWriter`` accepts a caller-supplied, trusted local path. It snapshots
caller-owned containers once, then validates the isolated built-ins against an
explicit event schema before rendering canonical JSON. The only current schema
is ``case_complete(case_id, duration_ms, status)``; every field is required and
``case_id`` matches ``synthetic-[1-9][0-9]*`` while ``status`` is exactly
``"ok"``. New event types require a reviewed schema rather than accepting
arbitrary metadata; non-synthetic identities require a fixed-form digest field
or a separately reviewed identifier type. One pre-rendered record is appended
with one write in append mode. This preserves prior content and relies on the
operating system's normal append semantics; coordinating independent processes
is outside this small, local event-log boundary.
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
        "api_token",
        "access_token",
        "auth_header",
        "refresh_token",
        "authorization",
        "client_key",
        "cookie",
        "id_token",
        "oauth_token",
        "private_key",
        "session_cookie",
        "token",
    }
)
_SAFE_EVENT_NAME = re.compile(r"[a-z][a-z0-9_.:-]{0,63}", re.ASCII)
_SAFE_METADATA_KEY = re.compile(r"[a-z][a-z0-9_]{0,63}", re.ASCII)
_CASE_ID = re.compile(r"synthetic-[1-9][0-9]*", re.ASCII)
_CASE_COMPLETE_FIELDS = frozenset({"case_id", "duration_ms", "status"})
_CASE_COMPLETE_STATUSES = frozenset({"ok"})


def _validate_event_name(event: object) -> str:
    if type(event) is not str or _SAFE_EVENT_NAME.fullmatch(event) is None:
        raise UnsafeEventError("event name must be a nonempty safe ASCII identifier")
    return event


def _supports_buffer_protocol(value: object) -> bool:
    """Probe the buffer protocol without requiring Python 3.12's Buffer ABC."""
    if isinstance(value, memoryview):
        return True
    try:
        view = memoryview(value)  # type: ignore[arg-type]
    except TypeError:
        return False
    except Exception:
        return True
    view.release()
    return True


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
        return value
    if type(value) is float:
        if math.isfinite(value):
            return value
        raise UnsafeEventError(f"unsafe event value at {location}: non-finite float")
    if _supports_buffer_protocol(value):
        raise UnsafeEventError(
            f"unsafe event value at {location}: buffer container is not JSON"
        )
    if isinstance(value, Mapping):
        return _snapshot_mapping(
            value, location=location, active=active, memo=memo
        )
    if isinstance(value, str):
        raise UnsafeEventError(
            f"unsafe event value at {location}: text container is not JSON"
        )
    if isinstance(value, Sequence):
        return _snapshot_sequence(
            value, location=location, active=active, memo=memo
        )
    raise UnsafeEventError(
        f"unsafe event value at {location}: {type(value).__name__} is not JSON"
    )


def _validate_case_complete(fields: dict[str, Any]) -> None:
    unknown = sorted(fields.keys() - _CASE_COMPLETE_FIELDS)
    if unknown:
        raise UnsafeEventError(
            f"case_complete field not allowed: {', '.join(unknown)}"
        )

    missing = sorted(_CASE_COMPLETE_FIELDS - fields.keys())
    if missing:
        raise UnsafeEventError(
            f"case_complete missing required field: {', '.join(missing)}"
        )

    case_id = fields["case_id"]
    if type(case_id) is not str or _CASE_ID.fullmatch(case_id) is None:
        raise UnsafeEventError(
            "case_complete case_id must match synthetic-[1-9][0-9]*"
        )

    duration_ms = fields["duration_ms"]
    if type(duration_ms) is not int or duration_ms < 0:
        raise UnsafeEventError(
            "case_complete duration_ms must be a non-negative integer"
        )

    status = fields["status"]
    if type(status) is not str or status not in _CASE_COMPLETE_STATUSES:
        raise UnsafeEventError("case_complete status must be exactly 'ok'")


def _validate_event_schema(event: str, fields: dict[str, Any]) -> None:
    if event != "case_complete":
        raise UnsafeEventError(f"unknown event type: {event}")
    _validate_case_complete(fields)


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
        _validate_event_schema(event_name, snapshot)
        record: dict[str, Any] = {"event": event_name, **snapshot}
        try:
            encoded_record = canonical_json_bytes(record)
        except (TypeError, ValueError, OverflowError) as error:
            raise UnsafeEventError("unsafe event value: not canonical JSON") from error

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(encoded_record + b"\n")

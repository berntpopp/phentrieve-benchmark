import math
from pathlib import Path
from typing import Any

import pytest

from phentrieve_benchmark.provenance.events import EventWriter, UnsafeEventError


def test_writer_emits_canonical_text_free_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    writer = EventWriter(path)

    writer.write(
        event="case_complete",
        fields={"case_id": "synthetic-1", "duration_ms": 12, "status": "ok"},
    )

    assert path.read_bytes() == (
        b'{"case_id":"synthetic-1","duration_ms":12,'
        b'"event":"case_complete","status":"ok"}\n'
    )


def test_writer_appends_one_lf_terminated_event_without_rewriting_content(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    path.write_bytes(b'{"event":"existing"}\n')

    EventWriter(path).write(event="case_complete", fields={"case_id": "synthetic-1"})

    assert path.read_bytes() == (
        b'{"event":"existing"}\n'
        b'{"case_id":"synthetic-1","event":"case_complete"}\n'
    )


@pytest.mark.parametrize(
    "fields",
    [
        {"text": "must not be logged"},
        {"context": {"full_text": "must not be logged"}},
        {"items": [{"PrOmPt": "must not be logged"}]},
        {"details": [{"credential": "must not be logged"}]},
        {"details": {"credentials": "must not be logged"}},
        {"details": [{"exception": "must not be logged"}]},
        {"details": {"\uff54\uff45\uff58\uff54": "must not be logged"}},
    ],
)
def test_writer_rejects_sensitive_field_names_recursively(
    tmp_path: Path, fields: dict[str, Any]
) -> None:
    writer = EventWriter(tmp_path / "events.jsonl")

    with pytest.raises(UnsafeEventError, match="unsafe event field"):
        writer.write(event="unsafe", fields=fields)


@pytest.mark.parametrize(
    ("event", "fields"),
    [
        ("unsafe\nevent", {}),
        ("unsafe\x1b[2J", {}),
        ("unsafe/event", {}),
        ("ok", {"event": "override"}),
        ("ok", {1: "non-string key"}),
        ("ok", {"nested": {"bad\nkey": "injected"}}),
    ],
)
def test_writer_rejects_structure_injection_and_reserved_key_collisions(
    tmp_path: Path, event: str, fields: dict[Any, Any]
) -> None:
    writer = EventWriter(tmp_path / "events.jsonl")

    with pytest.raises(UnsafeEventError):
        writer.write(event=event, fields=fields)


@pytest.mark.parametrize(
    "value",
    [
        math.nan,
        math.inf,
        -math.inf,
        ValueError("do not log raw exceptions"),
        b"not JSON",
        {"set values are not JSON"},
    ],
)
def test_writer_rejects_non_json_values(tmp_path: Path, value: object) -> None:
    writer = EventWriter(tmp_path / "events.jsonl")

    with pytest.raises(UnsafeEventError, match="unsafe event value"):
        writer.write(event="unsafe", fields={"value": value})


def test_writer_leaves_existing_file_unchanged_when_event_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)

    with pytest.raises(UnsafeEventError):
        EventWriter(path).write(
            event="case_complete", fields={"details": [{"prompt": "secret"}]}
        )

    assert path.read_bytes() == existing

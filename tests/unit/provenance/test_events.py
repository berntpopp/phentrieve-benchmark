import math
from array import array
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, overload

import pytest

from phentrieve_benchmark.provenance.events import EventWriter, UnsafeEventError


class StatefulMapping(Mapping[str, object]):
    def __init__(self, *, unsafe_first: bool = False) -> None:
        self.iterations = 0
        self.unsafe_first = unsafe_first

    def __getitem__(self, key: str) -> object:
        values: dict[str, object] = {
            "case_id": "synthetic-1",
            "duration_ms": 12,
            "status": "ok",
            "prompt": "must-not-be-written",
        }
        return values[key]

    def __iter__(self) -> Iterator[str]:
        self.iterations += 1
        if self.unsafe_first or self.iterations > 1:
            return iter(("prompt",))
        return iter(("case_id", "duration_ms", "status"))

    def __len__(self) -> int:
        return 3


class StatefulSequence(Sequence[str]):
    def __init__(self) -> None:
        self.iterations = 0
        self._safe = ("ok",)

    @overload
    def __getitem__(self, index: int) -> str: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[str]: ...

    def __getitem__(self, index: int | slice) -> str | Sequence[str]:
        return self._safe[index]

    def __iter__(self) -> Iterator[str]:
        self.iterations += 1
        if self.iterations > 1:
            return iter(("must-not-be-written",))
        return iter(self._safe)

    def __len__(self) -> int:
        return len(self._safe)


class DuplicateKeyMapping(Mapping[str, object]):
    def __getitem__(self, key: str) -> object:
        if key != "status":
            raise KeyError(key)
        return "ok"

    def __iter__(self) -> Iterator[str]:
        return iter(("status", "status"))

    def __len__(self) -> int:
        return 2


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

    EventWriter(path).write(
        event="case_complete",
        fields={"case_id": "synthetic-1", "duration_ms": 12, "status": "ok"},
    )

    assert path.read_bytes() == (
        b'{"event":"existing"}\n'
        b'{"case_id":"synthetic-1","duration_ms":12,'
        b'"event":"case_complete","status":"ok"}\n'
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
        bytearray(b"not JSON"),
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


@pytest.mark.parametrize("nested", [False, True])
def test_writer_snapshots_stateful_mapping_without_second_iteration(
    tmp_path: Path, nested: bool
) -> None:
    path = tmp_path / "events.jsonl"
    mapping = StatefulMapping()
    fields: Mapping[str, Any] = {"details": mapping} if nested else mapping

    if nested:
        existing = b'{"event":"existing"}\n'
        path.write_bytes(existing)
        with pytest.raises(UnsafeEventError, match="details"):
            EventWriter(path).write(event="case_complete", fields=fields)
        assert path.read_bytes() == existing
    else:
        EventWriter(path).write(event="case_complete", fields=fields)
        assert b"synthetic-1" in path.read_bytes()

    assert mapping.iterations == 1
    assert b"prompt" not in path.read_bytes()
    assert b"must-not-be-written" not in path.read_bytes()


def test_writer_rejects_unsafe_first_custom_mapping_without_mutation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)
    mapping = StatefulMapping(unsafe_first=True)

    with pytest.raises(UnsafeEventError, match="prompt"):
        EventWriter(path).write(event="case_complete", fields={"details": mapping})

    assert mapping.iterations == 1
    assert path.read_bytes() == existing


def test_writer_snapshots_shared_stateful_container_only_once(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)
    mapping = StatefulMapping()

    with pytest.raises(UnsafeEventError, match="field"):
        EventWriter(path).write(
            event="case_complete", fields={"first": mapping, "second": mapping}
        )

    assert mapping.iterations == 1
    assert path.read_bytes() == existing


def test_writer_rejects_duplicate_mapping_items_without_mutation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)

    with pytest.raises(UnsafeEventError, match="normalized key collision"):
        EventWriter(path).write(event="case_complete", fields=DuplicateKeyMapping())

    assert path.read_bytes() == existing


@pytest.mark.parametrize("container_kind", ["mapping", "sequence"])
def test_writer_rejects_cyclic_containers_without_mutation(
    tmp_path: Path, container_kind: str
) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)
    if container_kind == "mapping":
        cyclic_mapping: dict[str, Any] = {}
        cyclic_mapping["details"] = cyclic_mapping
        fields: Mapping[str, Any] = cyclic_mapping
    else:
        cyclic_sequence: list[Any] = []
        cyclic_sequence.append(cyclic_sequence)
        fields = {"details": cyclic_sequence}

    with pytest.raises(UnsafeEventError, match="cyclic"):
        EventWriter(path).write(event="case_complete", fields=fields)

    assert path.read_bytes() == existing


@pytest.mark.parametrize(
    "key",
    [
        "clinical_text",
        "source_text",
        "context",
        "prompt_id",
        "credential_hint",
        "raw_exception",
        "secret_name",
        "password_hash",
        "api_key",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "private_key",
        "token",
    ],
)
def test_writer_rejects_sensitive_key_names_recursively(
    tmp_path: Path, key: str
) -> None:
    with pytest.raises(UnsafeEventError, match="unsafe event field"):
        EventWriter(tmp_path / "events.jsonl").write(
            event="unsafe", fields={"details": [{key: "safe-code"}]}
        )


@pytest.mark.parametrize(
    "key",
    [
        "Case_Id",
        "case-id",
        "case\u0301_id",
        "case_id\ufe0f",
        "\u0441ase_id",
    ],
)
def test_writer_rejects_non_lowercase_ascii_metadata_keys(
    tmp_path: Path, key: str
) -> None:
    with pytest.raises(UnsafeEventError, match="metadata key"):
        EventWriter(tmp_path / "events.jsonl").write(
            event="unsafe", fields={key: "safe-code"}
        )


def test_writer_snapshots_disallowed_sequence_once_before_schema_rejection(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)
    sequence = StatefulSequence()

    with pytest.raises(UnsafeEventError, match="statuses"):
        EventWriter(path).write(
            event="case_complete",
            fields={
                "case_id": "synthetic-1",
                "duration_ms": 12,
                "status": "ok",
                "statuses": sequence,
            },
        )

    assert sequence.iterations == 1
    assert path.read_bytes() == existing


@pytest.mark.parametrize(
    "buffer_value",
    [
        memoryview(b"not JSON"),
        array("B", [1, 2, 3]),
        array("b", [-1, 0, 1]),
    ],
    ids=["memoryview", "unsigned-byte-array", "signed-byte-array"],
)
@pytest.mark.parametrize("nested", [False, True], ids=["top-level", "nested"])
def test_writer_rejects_buffer_containers_without_file_mutation(
    tmp_path: Path, buffer_value: object, nested: bool
) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    fields: Mapping[str, Any]
    if nested:
        path.write_bytes(existing)
        fields = {"details": [{"data": buffer_value}]}
    else:
        fields = {"data": buffer_value}

    with pytest.raises(UnsafeEventError, match="buffer"):
        EventWriter(path).write(event="case_complete", fields=fields)

    if nested:
        assert path.read_bytes() == existing
    else:
        assert not path.exists()


def test_writer_rejects_unreviewed_integer_sequence_fields(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)

    with pytest.raises(UnsafeEventError, match="list_values"):
        EventWriter(path).write(
            event="case_complete",
            fields={
                "case_id": "synthetic-1",
                "duration_ms": 12,
                "status": "ok",
                "list_values": [1, 2],
                "tuple_values": (3, 4),
            },
        )

    assert path.read_bytes() == existing


@pytest.mark.parametrize(
    "field",
    [
        "api_token",
        "oauth_token",
        "id_token",
        "session_cookie",
        "client_key",
        "auth_header",
    ],
)
def test_sensitive_precheck_precedes_unknown_event_schema(
    tmp_path: Path, field: str
) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)

    with pytest.raises(UnsafeEventError, match=rf"unsafe event field.*{field}"):
        EventWriter(path).write(event="unsafe", fields={field: "opaque"})

    assert path.read_bytes() == existing


@pytest.mark.parametrize(
    ("field", "value"),
    [("diagnosis", "headache"), ("patient_name", "Alice")],
)
def test_writer_rejects_unreviewed_clinical_fields_without_mutation(
    tmp_path: Path, field: str, value: object
) -> None:
    path = tmp_path / "events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)
    fields: dict[str, object] = {
        "case_id": "synthetic-1",
        "duration_ms": 12,
        "status": "ok",
        field: value,
    }

    with pytest.raises(UnsafeEventError, match=rf"field not allowed: {field}"):
        EventWriter(path).write(event="case_complete", fields=fields)

    assert path.read_bytes() == existing


def test_writer_rejects_unknown_event_before_file_mutation(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"

    with pytest.raises(UnsafeEventError, match="unknown event"):
        EventWriter(path).write(
            event="stage_complete",
            fields={"case_id": "synthetic-1", "duration_ms": 12, "status": "ok"},
        )

    assert not path.exists()


def test_writer_rejects_unknown_field_before_file_mutation(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"

    with pytest.raises(UnsafeEventError, match="attempt_count"):
        EventWriter(path).write(
            event="case_complete",
            fields={
                "case_id": "synthetic-1",
                "duration_ms": 12,
                "status": "ok",
                "attempt_count": 1,
            },
        )

    assert not path.exists()


@pytest.mark.parametrize(
    "case_id",
    [
        "",
        "patient one",
        "patient@example",
        "patient.name",
        "Größe",
        "-synthetic-1",
        "x" * 129,
        1,
    ],
)
def test_writer_rejects_invalid_case_id(tmp_path: Path, case_id: object) -> None:
    path = tmp_path / "events.jsonl"

    with pytest.raises(UnsafeEventError, match="case_id"):
        EventWriter(path).write(
            event="case_complete",
            fields={"case_id": case_id, "duration_ms": 12, "status": "ok"},
        )

    assert not path.exists()


@pytest.mark.parametrize("duration_ms", [-1, True, False, 1.0, "1"])
def test_writer_rejects_invalid_duration_ms(
    tmp_path: Path, duration_ms: object
) -> None:
    path = tmp_path / "events.jsonl"

    with pytest.raises(UnsafeEventError, match="duration_ms"):
        EventWriter(path).write(
            event="case_complete",
            fields={
                "case_id": "synthetic-1",
                "duration_ms": duration_ms,
                "status": "ok",
            },
        )

    assert not path.exists()


@pytest.mark.parametrize("status", ["failed", "headache", "OK", "", 1])
def test_writer_rejects_invalid_status(tmp_path: Path, status: object) -> None:
    path = tmp_path / "events.jsonl"

    with pytest.raises(UnsafeEventError, match="status"):
        EventWriter(path).write(
            event="case_complete",
            fields={
                "case_id": "synthetic-1",
                "duration_ms": 12,
                "status": status,
            },
        )

    assert not path.exists()


@pytest.mark.parametrize("missing", ["case_id", "duration_ms", "status"])
def test_writer_requires_all_case_complete_fields(
    tmp_path: Path, missing: str
) -> None:
    path = tmp_path / "events.jsonl"
    fields: dict[str, object] = {
        "case_id": "synthetic-1",
        "duration_ms": 12,
        "status": "ok",
    }
    del fields[missing]

    with pytest.raises(UnsafeEventError, match=missing):
        EventWriter(path).write(event="case_complete", fields=fields)

    assert not path.exists()

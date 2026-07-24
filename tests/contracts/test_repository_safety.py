from __future__ import annotations

import hashlib
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.check_repository_safety as safety
from scripts.check_repository_safety import (
    MAX_BLOB_BYTES,
    SafetyViolation,
    contains_credential,
    parse_index_snapshot,
    scan_repository,
)


def run_git(
    root: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        input=input_bytes,
        env=env,
        check=True,
        capture_output=True,
    )


def initialise_repository(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    run_git(root, "init", "--quiet")
    run_git(root, "config", "core.autocrlf", "false")


def track(root: Path, relative: str, content: bytes, *, force: bool = False) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    arguments = ["add"]
    if force:
        arguments.append("--force")
    arguments.extend(["--", relative])
    run_git(root, *arguments)
    return path


def secret_assignment(name: bytes = b"api_key") -> bytes:
    return name + b"=" + b"q9P4m7V2x8L5n3R6\n"


def index_bytes(
    *,
    extensions: tuple[tuple[bytes, bytes], ...] = (),
    hash_name: str = "sha1",
) -> bytes:
    body = b"DIRC" + struct.pack(">II", 2, 0)
    for signature, content in extensions:
        body += signature + struct.pack(">I", len(content)) + content
    return signed_index(body, hash_name=hash_name)


def signed_index(payload: bytes, *, hash_name: str = "sha1") -> bytes:
    return payload + hashlib.new(hash_name, payload).digest()


def test_clean_index_snapshot_is_allowed(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "src/module.py", b'MODEL = "general/nmt"\n')

    scan_repository(tmp_path)


def test_empty_repository_without_index_file_is_allowed(tmp_path: Path) -> None:
    initialise_repository(tmp_path)

    scan_repository(tmp_path)


def test_version_four_index_is_allowed(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "src/first.py", b"FIRST = 1\n")
    track(tmp_path, "src/second.py", b"SECOND = 2\n")
    run_git(tmp_path, "update-index", "--index-version", "4")
    index = (tmp_path / ".git" / "index").read_bytes()
    assert struct.unpack(">I", index[4:8])[0] == 4

    scan_repository(tmp_path)


def test_sha256_index_is_allowed_when_supported(tmp_path: Path) -> None:
    result = subprocess.run(
        ["git", "init", "--quiet", "--object-format=sha256"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.skip("installed Git does not support SHA-256 repositories")
    run_git(tmp_path, "config", "core.autocrlf", "false")
    track(tmp_path, "safe.txt", b"safe\n")

    scan_repository(tmp_path)


@pytest.mark.parametrize(
    "relative",
    [
        ".artifacts/sha256/payload",
        "records/local/run.json",
        "releases/local/bundle.zip",
        "configs/providers/local/provider.env",
    ],
)
def test_restricted_tracked_paths_are_rejected(
    tmp_path: Path, relative: str
) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, relative, b"synthetic", force=True)

    with pytest.raises(SafetyViolation, match="forbidden tracked path"):
        scan_repository(tmp_path)


def test_staged_secret_is_scanned_even_when_worktree_copy_is_safe(
    tmp_path: Path,
) -> None:
    initialise_repository(tmp_path)
    path = track(tmp_path, "config.env", secret_assignment())
    path.write_bytes(b"MODEL=general/nmt\n")

    with pytest.raises(SafetyViolation, match="possible credential"):
        scan_repository(tmp_path)


def test_dirty_tracked_worktree_fails_closed(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    path = track(tmp_path, "config.env", b"MODEL=general/nmt\n")
    path.write_bytes(b"MODEL=changed\n")

    with pytest.raises(SafetyViolation, match="worktree differs from index"):
        scan_repository(tmp_path)


def test_assume_unchanged_cannot_hide_dirty_tracked_file(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    path = track(tmp_path, "config.env", b"MODEL=general/nmt\n")
    run_git(tmp_path, "update-index", "--assume-unchanged", "--", "config.env")
    path.write_bytes(secret_assignment())

    try:
        with pytest.raises(SafetyViolation, match="unsafe index comparison flag"):
            scan_repository(tmp_path)
    finally:
        run_git(
            tmp_path,
            "update-index",
            "--no-assume-unchanged",
            "--",
            "config.env",
        )


def test_skip_worktree_cannot_hide_dirty_tracked_file(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    path = track(tmp_path, "config.env", b"MODEL=general/nmt\n")
    run_git(tmp_path, "update-index", "--skip-worktree", "--", "config.env")
    path.write_bytes(secret_assignment())

    try:
        with pytest.raises(SafetyViolation, match="unsafe index comparison flag"):
            scan_repository(tmp_path)
    finally:
        run_git(
            tmp_path,
            "update-index",
            "--no-skip-worktree",
            "--",
            "config.env",
        )


def test_real_fsmonitor_index_extension_is_rejected(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "config.env", b"MODEL=general/nmt\n")
    run_git(tmp_path, "config", "core.fsmonitor", "true")
    run_git(tmp_path, "update-index", "--fsmonitor")
    run_git(tmp_path, "update-index", "--fsmonitor-valid", "--", "config.env")
    run_git(
        tmp_path,
        "config",
        "core.fsmonitor",
        "must-not-execute-arbitrary-hook",
    )

    try:
        with pytest.raises(SafetyViolation, match="fsmonitor index extension"):
            scan_repository(tmp_path)
    finally:
        run_git(tmp_path, "config", "core.fsmonitor", "true")
        run_git(
            tmp_path,
            "update-index",
            "--no-fsmonitor-valid",
            "--",
            "config.env",
        )
        run_git(tmp_path, "update-index", "--no-fsmonitor")


def test_real_split_index_is_rejected(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "safe.txt", b"safe\n")
    run_git(tmp_path, "update-index", "--split-index")

    primary_index = (tmp_path / ".git" / "index").read_bytes()
    assert b"link" in primary_index
    assert list((tmp_path / ".git").glob("sharedindex.*"))

    with pytest.raises(SafetyViolation, match="required index extension"):
        scan_repository(tmp_path)


def test_index_bytes_reject_fsmonitor_extension_portably() -> None:
    snapshot = index_bytes(extensions=((b"FSMN", b"\0" * 12),))

    with pytest.raises(SafetyViolation, match="fsmonitor index extension"):
        safety._validate_index_bytes(snapshot, hash_name="sha1")


@pytest.mark.parametrize("signature", [b"link", b"sdir", b"xnew"])
def test_index_bytes_reject_required_extensions(signature: bytes) -> None:
    snapshot = index_bytes(extensions=((signature, b""),))

    with pytest.raises(SafetyViolation, match="required index extension"):
        safety._validate_index_bytes(snapshot, hash_name="sha1")


def test_index_bytes_accept_extension_data_containing_fsmonitor_signature() -> None:
    snapshot = index_bytes(extensions=((b"TREE", b"prefix-FSMN-suffix"),))

    safety._validate_index_bytes(snapshot, hash_name="sha1")


def test_version_four_varint_decoder_handles_multibyte_value() -> None:
    assert safety._decode_v4_strip_count(b"\x80\x00", 0, 2) == (128, 2)


@pytest.mark.parametrize(
    "encoded",
    [
        b"",
        b"\x80",
        b"\xff" * 9 + b"\x00",
        b"\x80" * 10 + b"\x00",
    ],
)
def test_version_four_varint_decoder_fails_closed(encoded: bytes) -> None:
    with pytest.raises(SafetyViolation, match="malformed"):
        safety._decode_v4_strip_count(encoded, 0, len(encoded))


def malformed_index_payloads() -> list[bytes]:
    header_v2 = b"DIRC" + struct.pack(">II", 2, 1)
    header_v3 = b"DIRC" + struct.pack(">II", 3, 1)
    header_v4 = b"DIRC" + struct.pack(">II", 4, 1)
    fixed = b"\0" * 40 + b"a" * 20
    return [
        signed_index(b"NOPE" + struct.pack(">II", 2, 0)),
        signed_index(b"DIRC" + struct.pack(">II", 5, 0)),
        signed_index(b"DIRC" + struct.pack(">II", 2, 1)),
        signed_index(header_v2 + fixed + struct.pack(">H", 0x4000)),
        signed_index(
            header_v3
            + fixed
            + struct.pack(">HH", 0x4000, 0x0001)
            + b"\0" * 8
        ),
        signed_index(header_v4 + fixed + struct.pack(">H", 1) + b"\x01a\0"),
        signed_index(header_v4 + fixed + struct.pack(">H", 1) + b"\0a"),
        signed_index(header_v4 + fixed + struct.pack(">H", 2) + b"\0a\0"),
        signed_index(header_v2 + fixed + struct.pack(">H", 1) + b"ab"),
        signed_index(header_v2 + fixed + struct.pack(">H", 0x0FFF) + b"a"),
        signed_index(header_v2 + fixed + struct.pack(">H", 1) + b"a\0x\0\0\0\0\0"),
        signed_index(
            b"DIRC"
            + struct.pack(">II", 2, 0)
            + b"TREE"
            + struct.pack(">I", 100)
        ),
    ]


@pytest.mark.parametrize(
    "snapshot",
    [
        b"",
        *malformed_index_payloads(),
    ],
)
def test_index_bytes_reject_malformed_structures(snapshot: bytes) -> None:
    with pytest.raises(SafetyViolation):
        safety._validate_index_bytes(snapshot, hash_name="sha1")


def test_index_bytes_reject_unsupported_hash_algorithm() -> None:
    with pytest.raises(SafetyViolation, match="object format"):
        safety._validate_index_bytes(index_bytes(), hash_name="md5")


@pytest.mark.parametrize(
    ("snapshot", "message"),
    [
        (index_bytes()[:-1] + b"x", "checksum"),
        (
            index_bytes(extensions=((b"TREE", b"data"),))[:-25]
            + hashlib.sha1(
                index_bytes(extensions=((b"TREE", b"data"),))[:-25]
            ).digest(),
            "malformed",
        ),
    ],
)
def test_index_bytes_fail_closed_on_corruption(
    snapshot: bytes, message: str
) -> None:
    with pytest.raises(SafetyViolation, match=message):
        safety._validate_index_bytes(snapshot, hash_name="sha1")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        (b"api-key", b"q9P4m7V2x8L5n3R6"),
        (b"client_secret", b"m8T2w5K9z4C7p6H3"),
        (b"secret", b"s3cr3t-value-for-prod"),
        (b"token", b"tok_live_82Jsd72mQp19"),
        (b"password", b"correct-horse-9381"),
        (b"credential", b"cred_6pQ9wM3nT7xR"),
        (b"private_key", b"private-value-8mQ2"),
        (b"access-key-id", b"access-value-7Pq4"),
    ],
)
def test_generic_env_and_yaml_assignments_are_detected(
    name: bytes, value: bytes
) -> None:
    env_content = b"export " + name + b"='" + value + b"'\n"
    yaml_content = name + b': "' + value + b'"\n'
    unquoted_content = name + b"=" + value + b"\n"

    assert contains_credential(env_content)
    assert contains_credential(yaml_content)
    assert contains_credential(unquoted_content)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        (b"OPENAI" + b"_API_KEY", b"sk-live-9Pq4mN7xT2vK"),
        (
            b"AWS" + b"_SECRET_ACCESS_KEY",
            b"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        ),
    ],
)
def test_prefixed_provider_credentials_are_detected(
    name: bytes, value: bytes
) -> None:
    assert contains_credential(name + b"=" + value + b"\n")


def test_aws_temporary_access_key_id_is_detected() -> None:
    assert contains_credential(b"ASIA" + b"1A2B3C4D5E6F7G8H")


def test_json_credential_assignment_with_comma_is_detected() -> None:
    name = b"api" + b"_key"
    value = b"q9P4m7V2x8L5n3R6"

    assert contains_credential(b'"' + name + b'": "' + value + b'",\n')


def test_yaml_credential_assignment_with_comment_is_detected() -> None:
    name = b"openai" + b"_api_key"
    value = b"q9P4m7V2x8L5n3R6"

    assert contains_credential(name + b": " + value + b"  # local only\n")


@pytest.mark.parametrize(
    "content",
    [
        b"ghp_" + b"A" * 36,
        b"gho_" + b"B" * 36,
        b"github_pat_" + b"C" * 70,
        b"AKIA" + b"1A2B3C4D5E6F7G8H",
        b"Authorization: Bearer " + b"eyJhbGciOiJIUzI1NiJ9.payload.signature",
    ],
)
def test_provider_token_families_are_detected(content: bytes) -> None:
    assert contains_credential(content)


@pytest.mark.parametrize(
    "kind",
    [b"RSA", b"EC", b"OPENSSH", b"DSA", b"ENCRYPTED"],
)
def test_private_key_headers_are_detected(kind: bytes) -> None:
    assert contains_credential(b"-----BEGIN " + kind + b" PRIVATE KEY-----")


def test_pgp_private_key_header_is_detected() -> None:
    assert contains_credential(
        b"-----BEGIN PGP " + b"PRIVATE KEY BLOCK-----"
    )


def test_pkcs8_private_key_header_is_detected() -> None:
    assert contains_credential(b"-----BEGIN " + b"PRIVATE KEY-----")


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be"])
def test_utf16_credentials_are_detected(encoding: str) -> None:
    content = "password: 'correct-horse-9381'\n".encode(encoding)

    assert contains_credential(content)


@pytest.mark.parametrize(
    "content",
    [
        b"API_KEY=<your-api-key>\n",
        b'password: "${PASSWORD}"\n',
        b'token = "REDACTED"\n',
        b"secret: placeholder\n",
        b"credential = example\n",
        b"client_secret = short\n",
    ],
)
def test_documented_placeholders_are_allowed(content: bytes) -> None:
    assert not contains_credential(content)


@pytest.mark.parametrize(
    "content",
    [
        (b"OPENAI" + b'_API_KEY="<your-api-key>"\n'),
        (b'"api' + b'_key": "placeholder",\n'),
        (b"ASIA" + b"TOO_SHORT"),
        b"secret = secret_assignment()\n",
        b"OPENAI_API_KEY_FINGERPRINT=sha256:0123456789abcdef\n",
    ],
)
def test_provider_detector_boundaries_remain_allowed(content: bytes) -> None:
    assert not contains_credential(content)


def test_non_utf8_binary_without_signature_is_allowed(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "fixtures/binary.dat", b"\xff\xfe\x00\x81")

    scan_repository(tmp_path)


def test_repository_root_is_bound_by_nearest_git_marker(tmp_path: Path) -> None:
    root = tmp_path / "repository with spaces"
    initialise_repository(root)
    track(root, "src/module.py", b"VALUE = 1\n")
    nested = root / "src" / "nested"
    nested.mkdir()

    scan_repository(nested)


def test_linked_git_worktree_marker_is_supported(tmp_path: Path) -> None:
    main = tmp_path / "main"
    linked = tmp_path / "linked"
    initialise_repository(main)
    track(main, "safe.txt", b"safe\n")
    run_git(main, "config", "user.name", "Safety Test")
    run_git(main, "config", "user.email", "safety@example.invalid")
    run_git(main, "commit", "--quiet", "-m", "fixture")
    run_git(main, "worktree", "add", "--quiet", "--detach", str(linked), "HEAD")
    nested = linked / "nested"
    nested.mkdir()

    scan_repository(nested)


def test_git_environment_redirection_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    intended = tmp_path / "intended"
    redirected = tmp_path / "redirected"
    initialise_repository(intended)
    initialise_repository(redirected)
    track(intended, "safe.txt", b"safe\n")
    track(redirected, "secret.env", secret_assignment())
    monkeypatch.setenv("GIT_DIR", str(redirected / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(redirected))
    monkeypatch.setenv("GIT_INDEX_FILE", str(redirected / ".git" / "index"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.worktree")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(redirected))

    scan_repository(intended)


def test_every_git_invocation_disables_fsmonitor_hooks() -> None:
    arguments = safety._git_arguments(["rev-parse", "--show-object-format"])

    assert "core.fsmonitor=false" in arguments
    assert "core.fsmonitor=true" not in arguments


@pytest.mark.parametrize(
    "snapshot",
    [
        b"100644 " + b"a" * 40 + b" 1\tfile.txt\0",
        (
            b"100644 "
            + b"a" * 40
            + b" 0\tfile.txt\0"
            + b"100644 "
            + b"b" * 40
            + b" 0\tfile.txt\0"
        ),
        b"160000 " + b"a" * 40 + b" 0\tsubmodule\0",
        b"100600 " + b"a" * 40 + b" 0\tfile.txt\0",
    ],
)
def test_index_snapshot_rejects_unmerged_duplicate_and_unsupported_modes(
    snapshot: bytes,
) -> None:
    with pytest.raises(SafetyViolation):
        parse_index_snapshot(snapshot)


def test_index_snapshot_accepts_regular_executable_and_symlink_modes() -> None:
    snapshot = (
        b"100644 "
        + b"a" * 40
        + b" 0\tregular\0"
        + b"100755 "
        + b"b" * 40
        + b" 0\texecutable\0"
        + b"120000 "
        + b"c" * 40
        + b" 0\tlink\0"
    )

    assert [entry.mode for entry in parse_index_snapshot(snapshot)] == [
        b"100755",
        b"120000",
        b"100644",
    ]


@pytest.mark.parametrize(
    "snapshot",
    [
        b"missing-nul",
        b"malformed\0",
        b"100644 " + b"z" * 40 + b" 0\tfile.txt\0",
        b"100644 " + b"a" * 40 + b" 0\t../escape.txt\0",
    ],
)
def test_malformed_index_snapshots_fail_closed(snapshot: bytes) -> None:
    with pytest.raises(SafetyViolation):
        parse_index_snapshot(snapshot)


def test_git_execution_failure_is_redacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_git(*args: object, **kwargs: object) -> None:
        raise OSError("sensitive subprocess detail")

    monkeypatch.setattr(subprocess, "run", fail_git)

    with pytest.raises(SafetyViolation) as error:
        safety.index_snapshot(tmp_path)

    assert "sensitive subprocess detail" not in str(error.value)


def test_git_nonzero_exit_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = subprocess.CompletedProcess[bytes](
        args=["git"], returncode=128, stdout=b"", stderr=b"sensitive"
    )
    monkeypatch.setattr(
        safety,
        "_git_process",
        lambda root, arguments, **kwargs: result,
    )

    with pytest.raises(SafetyViolation) as error:
        safety.index_snapshot(tmp_path)

    assert "sensitive" not in str(error.value)


def test_unexpected_worktree_comparison_status_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = subprocess.CompletedProcess[bytes](
        args=["git"], returncode=2, stdout=b"", stderr=b"sensitive"
    )
    monkeypatch.setattr(
        safety,
        "_git_process",
        lambda root, arguments, **kwargs: result,
    )

    with pytest.raises(SafetyViolation, match="compare tracked worktree"):
        safety._worktree_differs_from_index(tmp_path)


def test_invalid_blob_size_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = safety.IndexEntry(mode=b"100644", oid=b"a" * 40, path=b"file")
    monkeypatch.setattr(safety, "_git_output", lambda root, arguments: b"invalid")

    with pytest.raises(SafetyViolation, match="invalid tracked blob size"):
        safety.read_blob(tmp_path, entry)


def test_inconsistent_blob_length_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = safety.IndexEntry(mode=b"100644", oid=b"a" * 40, path=b"file")
    outputs = iter([b"2\n", b"x"])
    monkeypatch.setattr(
        safety, "_git_output", lambda root, arguments: next(outputs)
    )

    with pytest.raises(SafetyViolation, match="inconsistent tracked blob"):
        safety.read_blob(tmp_path, entry)


def test_index_mutation_during_scan_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "first.txt", b"safe\n")
    original = safety.scan_entries

    def mutate_after_scan(root: Path, entries: list[safety.IndexEntry]) -> None:
        original(root, entries)
        track(tmp_path, "second.txt", b"also safe\n")

    monkeypatch.setattr(safety, "scan_entries", mutate_after_scan)

    with pytest.raises(SafetyViolation, match="index changed during scan"):
        scan_repository(tmp_path)


def test_fsmonitor_flag_enabled_during_scan_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "config.env", b"MODEL=general/nmt\n")
    original = safety.scan_entries

    def enable_fsmonitor_after_scan(
        root: Path, entries: list[safety.IndexEntry]
    ) -> None:
        original(root, entries)
        run_git(tmp_path, "config", "core.fsmonitor", "true")
        run_git(tmp_path, "update-index", "--fsmonitor")
        run_git(
            tmp_path,
            "update-index",
            "--fsmonitor-valid",
            "--",
            "config.env",
        )

    monkeypatch.setattr(safety, "scan_entries", enable_fsmonitor_after_scan)

    with pytest.raises(SafetyViolation, match="fsmonitor index extension"):
        scan_repository(tmp_path)


def test_oversized_blob_fails_closed(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "large.bin", b"x" * (MAX_BLOB_BYTES + 1))

    with pytest.raises(SafetyViolation, match="exceeds safety size limit"):
        scan_repository(tmp_path)


def test_cli_failure_escapes_path_and_redacts_secret(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    secret = secret_assignment()
    track(tmp_path, "bad%name.env", secret)
    script = Path(__file__).parents[2] / "scripts" / "check_repository_safety.py"

    result = subprocess.run(
        [sys.executable, script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "bad%25name.env" in result.stderr
    assert secret.decode("ascii").strip() not in result.stderr
    assert "repository safety check passed" not in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="raw-byte filenames require POSIX")
def test_posix_raw_byte_and_backslash_filenames_are_escaped(
    tmp_path: Path,
) -> None:
    initialise_repository(tmp_path)
    raw_name = b"bad-\xff-\\-line\n.env"
    name = os.fsdecode(raw_name)
    track(tmp_path, name, secret_assignment())

    with pytest.raises(SafetyViolation) as error:
        scan_repository(tmp_path)

    message = str(error.value)
    assert "%FF" in message
    assert "%5C" in message
    assert "%0A" in message
    assert "\n" not in message
    assert "\x1b" not in message


def test_outside_repository_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(SafetyViolation, match="Git repository"):
        scan_repository(tmp_path)


def test_main_success_has_only_success_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "safe.txt", b"safe\n")
    monkeypatch.chdir(tmp_path)

    assert safety.main() == 0
    captured = capsys.readouterr()
    assert captured.out == "repository safety check passed\n"
    assert captured.err == ""


def test_main_safety_failure_has_only_redacted_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    assert safety.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no Git repository found" in captured.err


def test_main_unexpected_failure_is_generic(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_scan(start: Path) -> None:
        raise ValueError("sensitive unexpected detail")

    monkeypatch.setattr(safety, "scan_repository", fail_scan)

    assert safety.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "repository safety check failed\n"

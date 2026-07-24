from __future__ import annotations

import os
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


def test_clean_index_snapshot_is_allowed(tmp_path: Path) -> None:
    initialise_repository(tmp_path)
    track(tmp_path, "src/module.py", b'MODEL = "general/nmt"\n')

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


def test_fsmonitor_valid_tag_is_rejected_if_git_reports_it() -> None:
    with pytest.raises(SafetyViolation, match="unsafe index comparison flag"):
        safety._reject_unsafe_index_flags(
            b"h config.env\0",
            reject_skip_worktree=False,
        )


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
    monkeypatch.setattr(safety, "_git_process", lambda root, arguments: result)

    with pytest.raises(SafetyViolation) as error:
        safety.index_snapshot(tmp_path)

    assert "sensitive" not in str(error.value)


def test_unexpected_worktree_comparison_status_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = subprocess.CompletedProcess[bytes](
        args=["git"], returncode=2, stdout=b"", stderr=b"sensitive"
    )
    monkeypatch.setattr(safety, "_git_process", lambda root, arguments: result)

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

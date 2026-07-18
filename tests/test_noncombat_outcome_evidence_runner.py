import base64
import importlib
import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from analysis_scripts.noncombat_outcome_evidence_expansion import (
    LEGACY_REGISTRATION_SCHEMA_VERSION,
    build_registration,
    render_registration_json,
)
from spirecomm.ai.noncombat_exploration import (
    ExplorationConfigurationError,
    create_exploration_session_manifest,
    parse_exploration_config,
)
from spirecomm.communication.study_handshake import (
    HANDSHAKE_ATTEMPT_ENV,
    build_ready_record,
    load_attempt_record,
    publish_record_once as publish_handshake_record_once,
)


STUDY_ID = "noncombat-outcome-evidence-expansion-20260715"
SEED_BASE = 2_026_071_500
WINDOWS_PYTHON = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_COMMIT = "a" * 40
REVIEW_COMMIT = "c" * 40
RUN_LOCK_HASH = "b" * 64
REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_VECTOR_ROOT = "C:\\qualification-bootstrap-fixture"
BOOTSTRAP_VECTOR_REQUEST = {
    "bootstrap": {
        "claim_path": (
            "C:\\qualification-bootstrap-fixture\\qualification-bootstrap-claim.json"
        ),
        "failure_path": (
            "C:\\qualification-bootstrap-fixture\\qualification-bootstrap-failure.json"
        ),
        "handoff_path": (
            "C:\\qualification-bootstrap-fixture\\qualification-bootstrap-handoff.json"
        ),
        "schema_version": (
            "noncombat-outcome-evidence-qualification-bootstrap-evidence-v1"
        ),
        "stage_paths": [
            {
                "index": 1,
                "name": "launcher_verified",
                "path": (
                    "C:\\qualification-bootstrap-fixture\\qualification-bootstrap-stage-01-launcher-verified.json"
                ),
            },
            {
                "index": 2,
                "name": "runner_entered",
                "path": (
                    "C:\\qualification-bootstrap-fixture\\qualification-bootstrap-stage-02-runner-entered.json"
                ),
            },
            {
                "index": 3,
                "name": "source_verified",
                "path": (
                    "C:\\qualification-bootstrap-fixture\\qualification-bootstrap-stage-03-source-verified.json"
                ),
            },
            {
                "index": 4,
                "name": "request_reviewed",
                "path": (
                    "C:\\qualification-bootstrap-fixture\\qualification-bootstrap-stage-04-request-reviewed.json"
                ),
            },
            {
                "index": 5,
                "name": "isolation_verified",
                "path": (
                    "C:\\qualification-bootstrap-fixture\\qualification-bootstrap-stage-05-isolation-verified.json"
                ),
            },
        ],
        "token_schema_version": (
            "noncombat-outcome-evidence-qualification-bootstrap-token-v1"
        ),
    },
    "qualification_id": "fixture-qualification",
    "qualification_root": BOOTSTRAP_VECTOR_ROOT,
    "request_hash": "a" * 64,
    "source_commit": "b" * 40,
}
BOOTSTRAP_VECTOR_ENVELOPE_B64 = (
    "eyJib290c3RyYXAiOnsiY2xhaW1fcGF0aCI6IkM6XFxxdWFsaWZpY2F0aW9uLWJvb3RzdHJhcC1maXh0dXJlXFxxdWFsaWZp"
    "Y2F0aW9uLWJvb3RzdHJhcC1jbGFpbS5qc29uIiwiZmFpbHVyZV9wYXRoIjoiQzpcXHF1YWxpZmljYXRpb24tYm9vdHN0cmFw"
    "LWZpeHR1cmVcXHF1YWxpZmljYXRpb24tYm9vdHN0cmFwLWZhaWx1cmUuanNvbiIsImhhbmRvZmZfcGF0aCI6IkM6XFxxdWFs"
    "aWZpY2F0aW9uLWJvb3RzdHJhcC1maXh0dXJlXFxxdWFsaWZpY2F0aW9uLWJvb3RzdHJhcC1oYW5kb2ZmLmpzb24iLCJzY2hl"
    "bWFfdmVyc2lvbiI6Im5vbmNvbWJhdC1vdXRjb21lLWV2aWRlbmNlLXF1YWxpZmljYXRpb24tYm9vdHN0cmFwLWV2aWRlbmNl"
    "LXYxIiwic3RhZ2VfcGF0aHMiOlt7ImluZGV4IjoxLCJuYW1lIjoibGF1bmNoZXJfdmVyaWZpZWQiLCJwYXRoIjoiQzpcXHF1"
    "YWxpZmljYXRpb24tYm9vdHN0cmFwLWZpeHR1cmVcXHF1YWxpZmljYXRpb24tYm9vdHN0cmFwLXN0YWdlLTAxLWxhdW5jaGVy"
    "LXZlcmlmaWVkLmpzb24ifSx7ImluZGV4IjoyLCJuYW1lIjoicnVubmVyX2VudGVyZWQiLCJwYXRoIjoiQzpcXHF1YWxpZmlj"
    "YXRpb24tYm9vdHN0cmFwLWZpeHR1cmVcXHF1YWxpZmljYXRpb24tYm9vdHN0cmFwLXN0YWdlLTAyLXJ1bm5lci1lbnRlcmVk"
    "Lmpzb24ifSx7ImluZGV4IjozLCJuYW1lIjoic291cmNlX3ZlcmlmaWVkIiwicGF0aCI6IkM6XFxxdWFsaWZpY2F0aW9uLWJv"
    "b3RzdHJhcC1maXh0dXJlXFxxdWFsaWZpY2F0aW9uLWJvb3RzdHJhcC1zdGFnZS0wMy1zb3VyY2UtdmVyaWZpZWQuanNvbiJ9"
    "LHsiaW5kZXgiOjQsIm5hbWUiOiJyZXF1ZXN0X3Jldmlld2VkIiwicGF0aCI6IkM6XFxxdWFsaWZpY2F0aW9uLWJvb3RzdHJh"
    "cC1maXh0dXJlXFxxdWFsaWZpY2F0aW9uLWJvb3RzdHJhcC1zdGFnZS0wNC1yZXF1ZXN0LXJldmlld2VkLmpzb24ifSx7Imlu"
    "ZGV4Ijo1LCJuYW1lIjoiaXNvbGF0aW9uX3ZlcmlmaWVkIiwicGF0aCI6IkM6XFxxdWFsaWZpY2F0aW9uLWJvb3RzdHJhcC1m"
    "aXh0dXJlXFxxdWFsaWZpY2F0aW9uLWJvb3RzdHJhcC1zdGFnZS0wNS1pc29sYXRpb24tdmVyaWZpZWQuanNvbiJ9XSwidG9r"
    "ZW5fc2NoZW1hX3ZlcnNpb24iOiJub25jb21iYXQtb3V0Y29tZS1ldmlkZW5jZS1xdWFsaWZpY2F0aW9uLWJvb3RzdHJhcC10"
    "b2tlbi12MSJ9LCJxdWFsaWZpY2F0aW9uX2lkIjoiZml4dHVyZS1xdWFsaWZpY2F0aW9uIiwicXVhbGlmaWNhdGlvbl9yb290"
    "IjoiQzpcXHF1YWxpZmljYXRpb24tYm9vdHN0cmFwLWZpeHR1cmUiLCJyZXF1ZXN0X2ZpbGVfc2hhMjU2IjoiY2NjY2NjY2Nj"
    "Y2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjYyIsInJlcXVlc3RfaGFzaCI6"
    "ImFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWEiLCJyZXF1"
    "ZXN0X3NpemUiOjEyMywicmV2aWV3X2NvbW1pdCI6ImRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQi"
    "LCJydW5uZXJfc2hhMjU2IjoiZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVlZWVl"
    "ZWVlZWVlZWVlZSIsInNjaGVtYV92ZXJzaW9uIjoibm9uY29tYmF0LW91dGNvbWUtZXZpZGVuY2UtcXVhbGlmaWNhdGlvbi1i"
    "b290c3RyYXAtdG9rZW4tdjEiLCJzb3VyY2VfY29tbWl0IjoiYmJiYmJiYmJiYmJiYmJiYmJiYmJiYmJiYmJiYmJiYmJiYmJi"
    "YmJiYiJ9"
)
BOOTSTRAP_VECTOR_TOKEN = "6f21f2b4324bea5277ef12e03b87e2ab84f3ead09b1def0fda52d3f201aa4089"


def _module():
    try:
        return importlib.import_module(
            "scripts.run_noncombat_outcome_evidence_expansion"
        )
    except ModuleNotFoundError as exc:
        pytest.fail(f"outcome evidence runner is missing: {exc}")


def _trusted_qualification_command(runner_path, *arguments):
    runner_path = Path(runner_path)
    return [
        sys.executable,
        "-I",
        "-S",
        "-c",
        _module().QUALIFICATION_TRUSTED_LAUNCHER_CODE,
        str(runner_path),
        hashlib.sha256(runner_path.read_bytes()).hexdigest(),
        *arguments,
    ]


def _bootstrap_library_namespace():
    namespace = {}
    exec(_module()._QUALIFICATION_BOOTSTRAP_LIBRARY_SOURCE, namespace)
    return namespace


def _bootstrap_launcher_fixture(tmp_path, runner_bytes=None):
    module = _module()
    qualification_root = (tmp_path / "qualification").resolve()
    qualification_root.mkdir()
    marker_path = (tmp_path / "runner-entry.txt").resolve()
    if runner_bytes is None:
        runner_bytes = (
            "import os, sys\n"
            "from pathlib import Path\n"
            "assert os.environ['STS_OUTCOME_EVIDENCE_QUALIFICATION_RUNNER_SHA256'] == sys.orig_argv[6]\n"
            "assert os.environ['STS_OUTCOME_EVIDENCE_QUALIFICATION_BOOTSTRAP_ENVELOPE_B64'] == sys.orig_argv[7]\n"
            "assert os.environ['STS_OUTCOME_EVIDENCE_QUALIFICATION_BOOTSTRAP_LAUNCH_TOKEN'] == sys.orig_argv[8]\n"
            "assert sys.argv[1] == 'qualify'\n"
            "assert sys.orig_argv[7] not in sys.argv\n"
            "assert sys.orig_argv[8] not in sys.argv\n"
            "claim = Path(os.environ['STS_TEST_CLAIM_PATH'])\n"
            "stage = Path(os.environ['STS_TEST_STAGE_PATH'])\n"
            "assert claim.is_file()\n"
            "assert stage.is_file()\n"
            "Path(os.environ['STS_TEST_MARKER_PATH']).write_bytes(b'entered\\n')\n"
        ).encode("ascii")
    runner_path = (tmp_path / "reviewed_runner.py").resolve()
    runner_path.write_bytes(runner_bytes)
    runner_sha256 = hashlib.sha256(runner_bytes).hexdigest()
    request_bytes = b'{"reviewed":true}\n'
    request_path = (tmp_path / "reviewed-request.json").resolve()
    request_path.write_bytes(request_bytes)
    request_hash = "a" * 64
    review_commit = "b" * 40
    request = {
        "bootstrap": module._qualification_bootstrap_paths(qualification_root),
        "qualification_id": "fixture-qualification",
        "qualification_root": str(qualification_root),
        "request_hash": request_hash,
        "source_commit": "c" * 40,
    }
    envelope = module._qualification_bootstrap_envelope(
        request=request,
        expected_request_file_sha256=hashlib.sha256(request_bytes).hexdigest(),
        expected_request_size=len(request_bytes),
        review_commit=review_commit,
        runner_sha256=runner_sha256,
    )
    envelope_b64 = module._qualification_bootstrap_encode_envelope(envelope)
    launch_token = module._qualification_bootstrap_token(envelope)
    qualifier_arguments = [
        "qualify",
        "--registration",
        str((tmp_path / "registration.json").resolve()),
        "--request",
        str(request_path),
        "--request-hash",
        request_hash,
        "--request-file-sha256",
        hashlib.sha256(request_bytes).hexdigest(),
        "--request-size",
        str(len(request_bytes)),
        "--review-commit",
        review_commit,
    ]
    command = [
        sys.executable,
        "-I",
        "-S",
        "-c",
        module.QUALIFICATION_TRUSTED_LAUNCHER_CODE,
        str(runner_path),
        runner_sha256,
        envelope_b64,
        launch_token,
        *qualifier_arguments,
    ]
    environment = os.environ.copy()
    environment.update(
        {
            "STS_TEST_CLAIM_PATH": envelope["bootstrap"]["claim_path"],
            "STS_TEST_STAGE_PATH": envelope["bootstrap"]["stage_paths"][0][
                "path"
            ],
            "STS_TEST_MARKER_PATH": str(marker_path),
        }
    )
    return {
        "command": command,
        "envelope": envelope,
        "environment": environment,
        "marker_path": marker_path,
        "qualification_root": qualification_root,
        "runner_path": runner_path,
    }


def _assert_silent_qualification_failure(completed):
    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_bootstrap_publisher_source_builds_exact_ascii_lf_self_hashed_record():
    namespace = _bootstrap_library_namespace()
    anchors = {
        "envelope_sha256": "0" * 64,
        "launch_token": "1" * 64,
        "qualification_id": "fixture-qualification",
        "request_file_sha256": "2" * 64,
        "request_hash": "3" * 64,
        "request_size": 17,
        "review_commit": "4" * 40,
        "runner_sha256": "5" * 64,
        "source_commit": "6" * 40,
    }

    record = namespace["_qualification_bootstrap_record"](
        record_type="claim",
        anchors=anchors,
        created_unix_ns=1,
        pid=2,
        previous_hash=None,
        stage_index=0,
        stage_name="claim",
        payload={},
    )
    raw = namespace["_qualification_bootstrap_record_bytes"](record)

    assert raw.endswith(b"\n")
    assert b"\r" not in raw
    assert raw.decode("ascii").encode("ascii") == raw
    assert {
        name for name, value in namespace.items() if hasattr(value, "__spec__")
    } == {"hashlib", "json", "os", "stat", "time"}
    replay = dict(record)
    replay["record_hash"] = None
    expected_hash = hashlib.sha256(
        json.dumps(
            replay,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()
    assert record["record_hash"] == expected_hash
    assert json.loads(raw) == record


def test_bootstrap_library_runtime_is_bound_to_private_namespace(
    tmp_path,
    monkeypatch,
):
    module = _module()
    assert module._qualification_bootstrap_library_record.__globals__ is not (
        module.__dict__
    )
    monkeypatch.setattr(module, "hashlib", None)
    monkeypatch.setattr(module, "stat", None)
    monkeypatch.setattr(
        module,
        "QUALIFICATION_BOOTSTRAP_EVIDENCE_SCHEMA_VERSION",
        "tampered-module-schema",
    )
    monkeypatch.setattr(module, "QUALIFICATION_BOOTSTRAP_STAGE_NAMES", ())
    anchors = {
        "envelope_sha256": "0" * 64,
        "launch_token": "1" * 64,
        "qualification_id": "fixture-qualification",
        "request_file_sha256": "2" * 64,
        "request_hash": "3" * 64,
        "request_size": 17,
        "review_commit": "4" * 40,
        "runner_sha256": "5" * 64,
        "source_commit": "6" * 40,
    }

    record = module._qualification_bootstrap_record(
        record_type="claim",
        anchors=anchors,
        created_unix_ns=1,
        pid=2,
        previous_hash=None,
        stage_index=0,
        stage_name="claim",
        payload={},
    )
    raw = module._qualification_bootstrap_record_bytes(record)
    target = (tmp_path / "qualification-bootstrap-claim.json").resolve()
    module._qualification_bootstrap_publish_bytes_once(str(target), raw)

    assert record["schema_version"] == (
        "noncombat-outcome-evidence-qualification-bootstrap-evidence-v1"
    )
    assert target.read_bytes() == raw


def test_bootstrap_publisher_uses_exclusive_same_descriptor_durable_write(
    tmp_path,
    monkeypatch,
):
    namespace = _bootstrap_library_namespace()
    target = (tmp_path / "qualification-bootstrap-claim.json").resolve()
    raw = b'{"claim":true}\n'
    observed = []
    real_open = os.open
    real_write = os.write
    real_fsync = os.fsync
    real_lseek = os.lseek
    real_read = os.read
    real_fstat = os.fstat
    real_close = os.close

    def record_open(path, flags, mode=0o777):
        observed.append(("open", path, flags))
        return real_open(path, flags, mode)

    def record_write(descriptor, block):
        observed.append(("write", descriptor, bytes(block)))
        return real_write(descriptor, block)

    def record_fsync(descriptor):
        observed.append(("fsync", descriptor))
        return real_fsync(descriptor)

    def record_fstat(descriptor):
        observed.append(("fstat", descriptor))
        return real_fstat(descriptor)

    def record_lseek(descriptor, offset, whence):
        observed.append(("lseek", descriptor, offset, whence))
        return real_lseek(descriptor, offset, whence)

    def record_read(descriptor, count):
        observed.append(("read", descriptor, count))
        return real_read(descriptor, count)

    def record_close(descriptor):
        observed.append(("close", descriptor))
        return real_close(descriptor)

    monkeypatch.setattr(namespace["os"], "open", record_open)
    monkeypatch.setattr(namespace["os"], "write", record_write)
    monkeypatch.setattr(namespace["os"], "fsync", record_fsync)
    monkeypatch.setattr(namespace["os"], "fstat", record_fstat)
    monkeypatch.setattr(namespace["os"], "lseek", record_lseek)
    monkeypatch.setattr(namespace["os"], "read", record_read)
    monkeypatch.setattr(namespace["os"], "close", record_close)

    namespace["_qualification_bootstrap_publish_bytes_once"](str(target), raw)

    assert target.read_bytes() == raw
    assert sorted(tmp_path.iterdir()) == [target]
    open_event = next(event for event in observed if event[0] == "open")
    assert open_event[2] & os.O_CREAT
    assert open_event[2] & os.O_EXCL
    assert open_event[2] & os.O_RDWR
    descriptor_events = [event[0] for event in observed if len(event) > 1]
    assert descriptor_events.count("open") == 1
    assert descriptor_events.count("fsync") == 1
    assert descriptor_events.count("close") == 1
    io_descriptors = {
        event[1]
        for event in observed
        if event[0] in {"write", "fsync", "fstat", "lseek", "read", "close"}
    }
    assert len(io_descriptors) == 1


@pytest.mark.parametrize("existing", (b"", b"{", b'{"partial":true}', b'{"valid":true}\n'))
def test_claim_collision_consumes_identity_without_changing_existing_bytes(
    tmp_path,
    existing,
):
    namespace = _bootstrap_library_namespace()
    target = (tmp_path / "qualification-bootstrap-claim.json").resolve()
    target.write_bytes(existing)

    with pytest.raises(FileExistsError):
        namespace["_qualification_bootstrap_publish_bytes_once"](
            str(target),
            b'{"replacement":true}\n',
        )

    assert target.read_bytes() == existing
    assert sorted(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize(
    "path_text",
    (
        "relative\\qualification-bootstrap-claim.json",
        r"\\server\share\qualification-bootstrap-claim.json",
        r"C:\qualification\..\qualification-bootstrap-claim.json",
        r"C:\qualification\qualification-bootstrap-claim.json:stream",
        "C:\\qualification\\qualification-bootstrap-claim.json.",
        "C:\\qualification\\qualification-bootstrap-claim.json ",
    ),
)
def test_bootstrap_publisher_rejects_unsafe_lexical_paths_without_probe(
    path_text,
    monkeypatch,
):
    namespace = _bootstrap_library_namespace()
    monkeypatch.setattr(
        namespace["os"],
        "lstat",
        lambda _path: pytest.fail("unsafe publisher path reached filesystem"),
    )

    with pytest.raises(Exception):
        namespace["_qualification_bootstrap_publish_bytes_once"](
            path_text,
            b"claim\n",
        )


def test_bootstrap_publisher_rejects_missing_parent_without_creating_it(tmp_path):
    namespace = _bootstrap_library_namespace()
    parent = tmp_path / "missing"
    target = (parent / "qualification-bootstrap-claim.json").resolve()

    with pytest.raises(OSError):
        namespace["_qualification_bootstrap_publish_bytes_once"](
            str(target),
            b"claim\n",
        )

    assert not parent.exists()


def test_bootstrap_publisher_rejects_linked_parent_without_writing_target(tmp_path):
    namespace = _bootstrap_library_namespace()
    target_parent = tmp_path / "outside"
    target_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    _create_directory_junction(linked_parent, target_parent)
    target = linked_parent / "qualification-bootstrap-claim.json"

    try:
        with pytest.raises(Exception):
            namespace["_qualification_bootstrap_publish_bytes_once"](
                str(target),
                b"claim\n",
            )
    finally:
        os.rmdir(linked_parent)

    assert list(target_parent.iterdir()) == []


def test_bootstrap_publisher_rejects_linked_or_nonregular_final_entry(tmp_path):
    namespace = _bootstrap_library_namespace()
    target_directory = tmp_path / "outside"
    target_directory.mkdir()
    target = tmp_path / "qualification-bootstrap-claim.json"
    _create_directory_junction(target, target_directory)

    try:
        with pytest.raises(Exception):
            namespace["_qualification_bootstrap_publish_bytes_once"](
                str(target),
                b"claim\n",
            )
    finally:
        os.rmdir(target)

    assert target_directory.is_dir()
    assert list(target_directory.iterdir()) == []


@pytest.mark.parametrize("failure", ("short_write", "fsync", "reread"))
def test_bootstrap_publisher_keeps_created_identity_after_io_failure(
    tmp_path,
    monkeypatch,
    failure,
):
    namespace = _bootstrap_library_namespace()
    target = (tmp_path / "qualification-bootstrap-claim.json").resolve()
    raw = b'{"claim":true}\n'
    if failure == "short_write":
        monkeypatch.setattr(namespace["os"], "write", lambda *_args: 0)
    elif failure == "fsync":
        monkeypatch.setattr(
            namespace["os"],
            "fsync",
            lambda _descriptor: (_ for _ in ()).throw(OSError("fsync failed")),
        )
    else:
        monkeypatch.setattr(namespace["os"], "read", lambda *_args: b"mismatch")

    with pytest.raises(Exception):
        namespace["_qualification_bootstrap_publish_bytes_once"](
            str(target),
            raw,
        )

    assert target.exists()
    assert sorted(tmp_path.iterdir()) == [target]


def test_bootstrap_publisher_rejects_parent_identity_drift_and_keeps_bytes(
    tmp_path,
    monkeypatch,
):
    namespace = _bootstrap_library_namespace()
    target = (tmp_path / "qualification-bootstrap-claim.json").resolve()
    raw = b'{"claim":true}\n'
    real_lstat = os.lstat
    parent_calls = 0

    class DriftedStat:
        def __init__(self, original):
            self.__dict__.update(
                {
                    name: getattr(original, name)
                    for name in dir(original)
                    if name.startswith("st_")
                }
            )
            self.st_ino = original.st_ino + 1

    def drift_parent(path):
        nonlocal parent_calls
        result = real_lstat(path)
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(
            os.path.abspath(tmp_path)
        ):
            parent_calls += 1
            if parent_calls >= 3:
                return DriftedStat(result)
        return result

    monkeypatch.setattr(namespace["os"], "lstat", drift_parent)

    with pytest.raises(Exception):
        namespace["_qualification_bootstrap_publish_bytes_once"](
            str(target),
            raw,
        )

    assert target.read_bytes() == raw


def test_bootstrap_publisher_rejects_final_identity_drift_and_keeps_bytes(
    tmp_path,
    monkeypatch,
):
    namespace = _bootstrap_library_namespace()
    target = (tmp_path / "qualification-bootstrap-claim.json").resolve()
    raw = b'{"claim":true}\n'
    real_lstat = os.lstat

    class DriftedStat:
        def __init__(self, original):
            self.__dict__.update(
                {
                    name: getattr(original, name)
                    for name in dir(original)
                    if name.startswith("st_")
                }
            )
            self.st_ino = original.st_ino + 1

    def drift_final(path):
        result = real_lstat(path)
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(
            os.path.abspath(target)
        ):
            return DriftedStat(result)
        return result

    monkeypatch.setattr(namespace["os"], "lstat", drift_final)

    with pytest.raises(Exception):
        namespace["_qualification_bootstrap_publish_bytes_once"](
            str(target),
            raw,
        )

    assert target.read_bytes() == raw


def test_trusted_launcher_claim_precedes_runner_and_launcher_verified(tmp_path):
    fixture = _bootstrap_launcher_fixture(tmp_path)

    completed = subprocess.run(
        fixture["command"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=fixture["environment"],
    )

    assert completed.returncode == 0
    assert completed.stdout == b""
    assert completed.stderr == b""
    bootstrap = fixture["envelope"]["bootstrap"]
    claim_path = Path(bootstrap["claim_path"])
    launcher_stage_path = Path(bootstrap["stage_paths"][0]["path"])
    assert claim_path.is_file()
    assert launcher_stage_path.is_file()
    assert fixture["marker_path"].read_bytes() == b"entered\n"
    claim = json.loads(claim_path.read_bytes())
    launcher_stage = json.loads(launcher_stage_path.read_bytes())
    assert claim["record_type"] == "claim"
    assert launcher_stage["stage_name"] == "launcher_verified"
    assert launcher_stage["previous_hash"] == claim["record_hash"]
    assert not Path(bootstrap["stage_paths"][1]["path"]).exists()


@pytest.mark.parametrize("existing", (b"", b"{", b'{"wrong":true}\n'))
def test_trusted_launcher_claim_collision_is_silent_and_stops_before_runner(
    tmp_path,
    existing,
):
    fixture = _bootstrap_launcher_fixture(tmp_path)
    bootstrap = fixture["envelope"]["bootstrap"]
    claim_path = Path(bootstrap["claim_path"])
    claim_path.write_bytes(existing)

    completed = subprocess.run(
        fixture["command"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=fixture["environment"],
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b""
    assert claim_path.read_bytes() == existing
    assert not fixture["marker_path"].exists()
    assert not Path(bootstrap["failure_path"]).exists()
    assert all(not Path(stage["path"]).exists() for stage in bootstrap["stage_paths"])


def test_trusted_launcher_second_claim_attempt_is_silent_and_creates_nothing_later(
    tmp_path,
):
    fixture = _bootstrap_launcher_fixture(tmp_path)
    first = subprocess.run(
        fixture["command"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=fixture["environment"],
    )
    bootstrap = fixture["envelope"]["bootstrap"]
    claim_path = Path(bootstrap["claim_path"])
    first_claim = claim_path.read_bytes()
    first_marker = fixture["marker_path"].read_bytes()

    second = subprocess.run(
        fixture["command"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=fixture["environment"],
    )

    assert first.returncode == 0
    assert second.returncode == 2
    assert second.stdout == b""
    assert second.stderr == b""
    assert claim_path.read_bytes() == first_claim
    assert fixture["marker_path"].read_bytes() == first_marker
    assert not Path(bootstrap["failure_path"]).exists()
    assert not Path(bootstrap["stage_paths"][1]["path"]).exists()


def _create_directory_junction(link_path, target_path):
    completed = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(link_path), str(target_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def _qualification_review_kwargs(request):
    source_bytes = Path(request["request_source_path"]).read_bytes()
    return {
        "expected_request_file_sha256": hashlib.sha256(
            source_bytes
        ).hexdigest(),
        "expected_request_size": len(source_bytes),
        "expected_review_commit": REVIEW_COMMIT,
    }


def test_qualification_file_reader_rejects_path_identity_change(
    tmp_path,
    monkeypatch,
):
    module = _module()
    evidence_path = tmp_path / "evidence.log"
    evidence_path.write_bytes(b"stable evidence\n")
    monkeypatch.setattr(module.os.path, "samestat", lambda *_args: False)

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="changed while being read",
    ):
        module._qualification_read_file_bytes(
            evidence_path,
            "isolation evidence",
        )


def test_qualification_observation_reads_communication_bytes_once(
    tmp_path,
    monkeypatch,
):
    module, _registration_path, _request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    communication_path = Path(
        request["isolation"]["communication_mod"]["path"]
    )
    original_reader = module._qualification_read_file_bytes
    read_count = 0

    def read_once(path, label):
        nonlocal read_count
        if Path(path) == communication_path:
            read_count += 1
            if read_count > 1:
                pytest.fail("CommunicationMod was reread for derived fields")
        return original_reader(path, label)

    monkeypatch.setattr(module, "_qualification_read_file_bytes", read_once)

    module._qualification_observe_isolation(request["isolation"])

    assert read_count == 1


def test_qualification_observation_derives_marker_count_from_hashed_bytes(
    tmp_path,
    monkeypatch,
):
    module, _registration_path, _request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    monkeypatch.setattr(
        module,
        "_ai_marker_count",
        lambda _path: pytest.fail("marker was reread for line_count"),
    )

    observation = module._qualification_observe_isolation(
        request["isolation"]
    )

    assert observation["marker"]["line_count"] == 2


def test_runner_supports_direct_script_execution(tmp_path):
    script_path = (
        REPO_ROOT / "scripts" / "run_noncombat_outcome_evidence_expansion.py"
    )
    shadow_root = tmp_path / "shadow"
    shadow_package = shadow_root / "analysis_scripts"
    shadow_package.mkdir(parents=True)
    (shadow_package / "__init__.py").write_text("", encoding="utf-8")
    (shadow_package / "noncombat_outcome_evidence_expansion.py").write_text(
        "raise RuntimeError('shadowed analysis_scripts import')\n",
        encoding="utf-8",
    )
    shadow_archive = tmp_path / "shadow.zip"
    with zipfile.ZipFile(shadow_archive, "w") as archive:
        archive.writestr("analysis_scripts/__init__.py", "")
        archive.writestr(
            "analysis_scripts/noncombat_outcome_evidence_expansion.py",
            "raise RuntimeError('shadowed zipped analysis_scripts import')\n",
        )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(shadow_root), str(shadow_archive), str(REPO_ROOT))
    )

    completed = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "dry-run" in completed.stdout


def test_qualification_cli_requires_isolation_before_argparse(tmp_path):
    script_path = (
        REPO_ROOT / "scripts" / "run_noncombat_outcome_evidence_expansion.py"
    )
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    marker_path = tmp_path / "argparse-imported.txt"
    (shadow_root / "argparse.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker_path)!r}).write_text('executed')\n"
        "raise RuntimeError('shadow argparse executed')\n",
        encoding="utf-8",
        newline="",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(shadow_root)

    completed = subprocess.run(
        [sys.executable, str(script_path), "qualify"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    _assert_silent_qualification_failure(completed)
    assert not marker_path.exists()


@pytest.mark.parametrize(
    "case",
    (
        "missing_qualifier_arguments",
        "extra_qualifier_argument",
        "empty_runner",
        "empty_runner_hash",
        "tampered_runner",
        "relative_runner",
        "runner_ads",
        "runner_win32_alias",
        "runner_win32_alias_space",
        "malformed_qualifier_order",
    ),
)
def test_trusted_qualification_launcher_post_claim_rejection_consumes_identity(
    tmp_path,
    case,
):
    fixture = _bootstrap_launcher_fixture(tmp_path)
    command = list(fixture["command"])
    if case == "missing_qualifier_arguments":
        command = command[:9]
    elif case == "extra_qualifier_argument":
        command.append("--unexpected")
    elif case == "empty_runner":
        command[5] = ""
    elif case == "empty_runner_hash":
        command[6] = ""
    elif case == "tampered_runner":
        original = fixture["runner_path"].read_bytes()
        metadata = fixture["runner_path"].stat()
        malicious_prefix = (
            "from pathlib import Path\n"
            f"Path({str(fixture['marker_path'])!r}).write_bytes(b'tampered\\n')\n"
        ).encode("ascii")
        assert len(malicious_prefix) < len(original)
        fixture["runner_path"].write_bytes(
            malicious_prefix + b"#" * (len(original) - len(malicious_prefix))
        )
        os.utime(
            fixture["runner_path"],
            ns=(metadata.st_atime_ns, metadata.st_mtime_ns),
        )
    elif case == "relative_runner":
        command[5] = fixture["runner_path"].name
    elif case == "runner_ads":
        command[5] = f"{fixture['runner_path']}:qualification-runner"
    elif case == "runner_win32_alias":
        command[5] = f"{fixture['runner_path']}."
    elif case == "runner_win32_alias_space":
        command[5] = f"{fixture['runner_path']} "
    else:
        command[10] = "--request"

    first = subprocess.run(
        command,
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=fixture["environment"],
    )

    bootstrap = fixture["envelope"]["bootstrap"]
    claim_path = Path(bootstrap["claim_path"])
    assert first.returncode == 2
    assert first.stdout == b""
    assert first.stderr == b""
    assert claim_path.is_file()
    claim_bytes = claim_path.read_bytes()
    claim = json.loads(claim_bytes)
    assert claim["record_type"] == "claim"
    assert claim["anchors"]["launch_token"] == fixture["command"][8]
    assert not fixture["marker_path"].exists()
    assert not Path(bootstrap["failure_path"]).exists()
    assert all(not Path(stage["path"]).exists() for stage in bootstrap["stage_paths"])

    second = subprocess.run(
        command,
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=fixture["environment"],
    )

    assert second.returncode == 2
    assert second.stdout == b""
    assert second.stderr == b""
    assert claim_path.read_bytes() == claim_bytes
    assert not fixture["marker_path"].exists()
    assert not Path(bootstrap["failure_path"]).exists()
    assert all(not Path(stage["path"]).exists() for stage in bootstrap["stage_paths"])


def _assert_launcher_vector_claim_only_rejection(tmp_path, fixture, command):
    first = subprocess.run(
        command,
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=fixture["environment"],
    )

    bootstrap = fixture["envelope"]["bootstrap"]
    claim_path = Path(bootstrap["claim_path"])
    assert first.returncode == 2
    assert first.stdout == b""
    assert first.stderr == b""
    assert claim_path.is_file()
    claim_bytes = claim_path.read_bytes()
    claim = json.loads(claim_bytes)
    assert claim["record_type"] == "claim"
    assert claim["anchors"]["launch_token"] == fixture["command"][8]
    assert not fixture["marker_path"].exists()
    assert not Path(bootstrap["failure_path"]).exists()
    assert all(not Path(stage["path"]).exists() for stage in bootstrap["stage_paths"])

    second = subprocess.run(
        command,
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=fixture["environment"],
    )

    assert second.returncode == 2
    assert second.stdout == b""
    assert second.stderr == b""
    assert claim_path.read_bytes() == claim_bytes
    assert not fixture["marker_path"].exists()
    assert not Path(bootstrap["failure_path"]).exists()
    assert all(not Path(stage["path"]).exists() for stage in bootstrap["stage_paths"])


def test_site_enabled_v3_launcher_claims_only_before_vector_rejection(tmp_path):
    fixture = _bootstrap_launcher_fixture(tmp_path)
    command = [
        fixture["command"][0],
        fixture["command"][1],
        *fixture["command"][3:],
    ]

    _assert_launcher_vector_claim_only_rejection(tmp_path, fixture, command)


def test_modified_trusted_launcher_code_claims_only_before_identity_rejection(
    tmp_path,
):
    fixture = _bootstrap_launcher_fixture(tmp_path)
    command = list(fixture["command"])
    command[4] += ";pass"

    _assert_launcher_vector_claim_only_rejection(tmp_path, fixture, command)


def test_trusted_qualification_launcher_survives_communicationmod_split(
    tmp_path,
):
    fixture = _bootstrap_launcher_fixture(tmp_path)
    command = fixture["command"]
    communicationmod_command = " ".join(command)
    split_command = communicationmod_command.split()

    assert split_command == command
    completed = subprocess.run(
        split_command,
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=fixture["environment"],
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""
    assert completed.stderr == ""
    assert fixture["marker_path"].read_bytes() == b"entered\n"


def test_qualification_cli_rejects_direct_unanchored_runner():
    script_path = (
        REPO_ROOT / "scripts" / "run_noncombat_outcome_evidence_expansion.py"
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(script_path),
            "qualify",
            "--review-commit",
            "a" * 40,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    _assert_silent_qualification_failure(completed)


def test_trusted_qualification_cli_silences_argparse_rejection(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ignored = shutil.ignore_patterns("__pycache__", "*.pyc")
    for directory_name in ("analysis_scripts", "scripts", "spirecomm"):
        shutil.copytree(
            REPO_ROOT / directory_name,
            repo_root / directory_name,
            ignore=ignored,
        )
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "."),
        ("git", "commit", "-m", "source snapshot"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    review_commit = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    runner_path = repo_root / "scripts" / (
        "run_noncombat_outcome_evidence_expansion.py"
    )

    completed = subprocess.run(
        _trusted_qualification_command(
            runner_path,
            "qualify",
            "--review-commit",
            review_commit,
        ),
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )

    _assert_silent_qualification_failure(completed)


@pytest.mark.parametrize("index_flag", (None, "--assume-unchanged"))
def test_qualification_cli_validates_source_before_project_imports(
    tmp_path,
    index_flag,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ignored = shutil.ignore_patterns("__pycache__", "*.pyc")
    for directory_name in ("analysis_scripts", "scripts", "spirecomm"):
        shutil.copytree(
            REPO_ROOT / directory_name,
            repo_root / directory_name,
            ignore=ignored,
        )
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "."),
        ("git", "commit", "-m", "source snapshot"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    review_commit = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    imported_source = repo_root / "analysis_scripts" / (
        "noncombat_outcome_evidence_expansion.py"
    )
    if index_flag is not None:
        subprocess.run(
            [
                "git",
                "update-index",
                index_flag,
                imported_source.relative_to(repo_root).as_posix(),
            ],
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    marker_path = tmp_path / "drifted-project-source-executed.txt"
    imported_source.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker_path)!r}).write_text('executed')\n"
        "raise RuntimeError('drifted project source executed')\n",
        encoding="utf-8",
        newline="",
    )
    runner_path = repo_root / "scripts" / (
        "run_noncombat_outcome_evidence_expansion.py"
    )

    completed = subprocess.run(
        _trusted_qualification_command(
            runner_path,
            "qualify",
            "--review-commit",
            review_commit,
        ),
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )

    _assert_silent_qualification_failure(completed)
    assert not marker_path.exists()


def test_qualification_cli_rejects_clean_wrong_head_before_project_imports(
    tmp_path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ignored = shutil.ignore_patterns("__pycache__", "*.pyc")
    for directory_name in ("analysis_scripts", "scripts", "spirecomm"):
        shutil.copytree(
            REPO_ROOT / directory_name,
            repo_root / directory_name,
            ignore=ignored,
        )
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "."),
        ("git", "commit", "-m", "review commit"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    review_commit = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    imported_source = repo_root / "analysis_scripts" / (
        "noncombat_outcome_evidence_expansion.py"
    )
    marker_path = tmp_path / "wrong-head-project-source-executed.txt"
    imported_source.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker_path)!r}).write_text('executed')\n"
        "raise RuntimeError('wrong-head project source executed')\n",
        encoding="utf-8",
        newline="",
    )
    subprocess.run(
        ("git", "add", imported_source.relative_to(repo_root).as_posix()),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    )
    subprocess.run(
        ("git", "commit", "-m", "wrong head"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    )
    runner_path = repo_root / "scripts" / (
        "run_noncombat_outcome_evidence_expansion.py"
    )

    completed = subprocess.run(
        _trusted_qualification_command(
            runner_path,
            "qualify",
            "--review-commit",
            review_commit,
        ),
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )

    _assert_silent_qualification_failure(completed)
    assert not marker_path.exists()


def test_qualification_cli_hashes_stat_clean_source_before_project_imports(
    tmp_path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ignored = shutil.ignore_patterns("__pycache__", "*.pyc")
    for directory_name in ("analysis_scripts", "scripts", "spirecomm"):
        shutil.copytree(
            REPO_ROOT / directory_name,
            repo_root / directory_name,
            ignore=ignored,
        )
    imported_source = repo_root / "analysis_scripts" / (
        "noncombat_outcome_evidence_expansion.py"
    )
    original_bytes = imported_source.read_bytes()
    old_timestamp_ns = 1_700_000_000_000_000_000
    os.utime(
        imported_source,
        ns=(old_timestamp_ns, old_timestamp_ns),
    )
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "."),
        ("git", "commit", "-m", "review commit"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    review_commit = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    marker_path = tmp_path / "stat-clean-project-source-executed.txt"
    malicious_prefix = (
        "from pathlib import Path\n"
        f"Path({str(marker_path)!r}).write_text('executed')\n"
        "raise RuntimeError('stat-clean project source executed')\n"
    ).encode("utf-8")
    assert len(malicious_prefix) < len(original_bytes)
    imported_source.write_bytes(
        malicious_prefix
        + b"#" * (len(original_bytes) - len(malicious_prefix))
    )
    os.utime(
        imported_source,
        ns=(old_timestamp_ns, old_timestamp_ns),
    )
    status = subprocess.run(
        ("git", "status", "--porcelain=v1", "--untracked-files=no"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    )
    assert status.stdout == ""
    runner_path = repo_root / "scripts" / (
        "run_noncombat_outcome_evidence_expansion.py"
    )

    completed = subprocess.run(
        _trusted_qualification_command(
            runner_path,
            "qualify",
            "--review-commit",
            review_commit,
        ),
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )

    _assert_silent_qualification_failure(completed)
    assert not marker_path.exists()


def test_qualification_cli_hashes_stat_clean_powershell_before_imports(
    tmp_path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ignored = shutil.ignore_patterns("__pycache__", "*.pyc")
    for directory_name in ("analysis_scripts", "scripts", "spirecomm"):
        shutil.copytree(
            REPO_ROOT / directory_name,
            repo_root / directory_name,
            ignore=ignored,
        )
    powershell_path = repo_root / "scripts" / "restart_sts_modded.ps1"
    original_bytes = powershell_path.read_bytes()
    old_timestamp_ns = 1_700_000_000_000_000_000
    os.utime(
        powershell_path,
        ns=(old_timestamp_ns, old_timestamp_ns),
    )
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "."),
        ("git", "commit", "-m", "review commit"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    review_commit = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    malicious_prefix = b"throw 'stat-clean PowerShell executed'\r\n"
    assert len(malicious_prefix) < len(original_bytes)
    powershell_path.write_bytes(
        malicious_prefix
        + b"#" * (len(original_bytes) - len(malicious_prefix))
    )
    os.utime(
        powershell_path,
        ns=(old_timestamp_ns, old_timestamp_ns),
    )
    status = subprocess.run(
        ("git", "status", "--porcelain=v1", "--untracked-files=no"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    )
    assert status.stdout == ""
    runner_path = repo_root / "scripts" / (
        "run_noncombat_outcome_evidence_expansion.py"
    )

    completed = subprocess.run(
        _trusted_qualification_command(
            runner_path,
            "qualify",
            "--review-commit",
            review_commit,
        ),
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )

    _assert_silent_qualification_failure(completed)


def test_runner_real_subprocess_does_not_self_pollute_source_guard(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ignored = shutil.ignore_patterns("__pycache__", "*.pyc")
    for directory_name in ("analysis_scripts", "scripts", "spirecomm"):
        shutil.copytree(
            REPO_ROOT / directory_name,
            repo_root / directory_name,
            ignore=ignored,
        )
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "."),
        ("git", "commit", "-m", "source snapshot"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    review_commit = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    environment = os.environ.copy()
    environment.pop("PYTHONDONTWRITEBYTECODE", None)
    completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                (
                    "import runpy,sys; from pathlib import Path; "
                    "sys.argv = ['runner', 'qualify', '--review-commit', "
                    f"{review_commit!r}]; "
                    "runner = runpy.run_path("
                "'scripts/run_noncombat_outcome_evidence_expansion.py', "
                "run_name='qualification_source_guard'); "
                    "print(runner['_tracked_source_commit'](Path.cwd())); "
                    "print(sys.pycache_prefix)"
            ),
        ],
        cwd=repo_root,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output_lines = completed.stdout.splitlines()
    assert len(output_lines[0]) == 40
    assert output_lines[1] == os.path.join(
        os.devnull,
        "sts-qualification-pycache",
    )
    assert list(repo_root.rglob("*.pyc")) == []


def test_qualification_runner_does_not_execute_repository_bytecode(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ignored = shutil.ignore_patterns("__pycache__", "*.pyc")
    for directory_name in ("analysis_scripts", "scripts", "spirecomm"):
        shutil.copytree(
            REPO_ROOT / directory_name,
            repo_root / directory_name,
            ignore=ignored,
        )
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "."),
        ("git", "commit", "-m", "source snapshot"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )

    source_path = repo_root / "analysis_scripts" / (
        "noncombat_outcome_evidence_expansion.py"
    )
    marker_path = tmp_path / "repository-pyc-executed.txt"
    malicious_bytes = (
        "from pathlib import Path\n"
        f"Path({str(marker_path)!r}).write_text('executed')\n"
        "raise RuntimeError('repository bytecode executed')\n"
    ).encode("utf-8")
    source_path.write_bytes(malicious_bytes)
    py_compile.compile(
        str(source_path),
        cfile=str(source_path.with_suffix(".pyc")),
        doraise=True,
    )
    source_path.unlink()

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-c",
            (
                "import runpy,sys; from pathlib import Path; "
                "sys.argv = ['runner', 'qualify']; "
                "runner = runpy.run_path("
                "'scripts/run_noncombat_outcome_evidence_expansion.py', "
                "run_name='qualification_source_guard'); "
                "runner['_tracked_source_commit'](Path.cwd())"
            ),
        ],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode != 0
    assert not marker_path.exists()


def test_qualification_bootstrap_accepts_git_normalized_autocrlf_text(tmp_path):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_path = repo_root / "settings.yaml"
    source_path.write_bytes(b"alpha\nbeta\n")
    (repo_root / ".gitattributes").write_bytes(
        b".gitattributes text eol=lf\n*.yaml text eol=crlf\n"
    )
    for arguments in (
        ("init", "--object-format=sha1"),
        ("config", "user.email", "runner@example.invalid"),
        ("config", "user.name", "Runner Fixture"),
        ("config", "core.autocrlf", "false"),
        ("add", "."),
        ("commit", "-m", "source snapshot"),
    ):
        subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            capture_output=True,
            check=True,
            text=True,
        )
    review_commit = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "core.autocrlf", "true"],
        capture_output=True,
        check=True,
        text=True,
    )
    source_path.write_bytes(b"alpha\r\nbeta\r\n")
    git_root = module._qualification_bootstrap_validate_git_metadata(repo_root)

    module._qualification_bootstrap_validate_reviewed_source_bytes(
        repo_root,
        git_root,
        review_commit,
    )


def test_qualification_bootstrap_does_not_normalize_binary_tamper(tmp_path):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_path = repo_root / "payload.bin"
    source_path.write_bytes(b"\x00alpha\nbeta\n")
    for arguments in (
        ("init", "--object-format=sha1"),
        ("config", "user.email", "runner@example.invalid"),
        ("config", "user.name", "Runner Fixture"),
        ("config", "core.autocrlf", "true"),
        ("add", "payload.bin"),
        ("commit", "-m", "binary snapshot"),
    ):
        subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            capture_output=True,
            check=True,
            text=True,
        )
    review_commit = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    source_path.write_bytes(b"\x00alpha\r\nbeta\r\n")
    git_root = module._qualification_bootstrap_validate_git_metadata(repo_root)

    with pytest.raises(
        module._QualificationBootstrapError,
        match="reviewed source bytes changed",
    ):
        module._qualification_bootstrap_validate_reviewed_source_bytes(
            repo_root,
            git_root,
            review_commit,
        )


def test_qualification_bootstrap_rejects_worktree_attributes(tmp_path):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_path = repo_root / "source.py"
    source_path.write_text("VALUE = 1\n", encoding="utf-8", newline="")
    for arguments in (
        ("init", "--object-format=sha1"),
        ("config", "user.email", "runner@example.invalid"),
        ("config", "user.name", "Runner Fixture"),
        ("add", "source.py"),
        ("commit", "-m", "source snapshot"),
    ):
        subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            capture_output=True,
            check=True,
            text=True,
        )
    review_commit = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    (repo_root / ".gitattributes").write_text(
        "*.py filter=untrusted\n",
        encoding="utf-8",
        newline="",
    )
    git_root = module._qualification_bootstrap_validate_git_metadata(repo_root)

    with pytest.raises(
        module._QualificationBootstrapError,
        match="worktree attributes are forbidden",
    ):
        module._qualification_bootstrap_validate_reviewed_source_bytes(
            repo_root,
            git_root,
            review_commit,
        )


@pytest.mark.parametrize(
    "module_name",
    (
        "scripts.run_noncombat_outcome_evidence_expansion",
        "main",
        "analysis_scripts.verify_noncombat_outcome_evidence_expansion",
    ),
)
def test_qualification_source_loader_rejects_package_junction_before_read(
    tmp_path,
    module_name,
):
    import_root = tmp_path / "import-root"
    import_root.mkdir()
    package_target = tmp_path / "package-target"
    package_target.mkdir()
    marker_path = tmp_path / "junction-source-executed.txt"
    (package_target / "__init__.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker_path)!r}).write_text('executed')\n",
        encoding="utf-8",
        newline="",
    )
    package_alias = import_root / "qualification_alias_package"
    _create_directory_junction(package_alias, package_target)
    probe = (
        "import importlib,sys; from pathlib import Path; "
        f"sys.path.insert(0, {str(REPO_ROOT)!r}); "
        "module=importlib.import_module(sys.argv[1]); "
        "root=Path(sys.argv[2]); "
        "module._qualification_install_source_only_repo_imports(root); "
        "sys.path.insert(0, str(root)); "
        "import qualification_alias_package"
    )

    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", probe, module_name, str(import_root)],
            cwd=tmp_path,
            capture_output=True,
            check=False,
            text=True,
        )
    finally:
        os.rmdir(package_alias)

    assert completed.returncode != 0
    assert not marker_path.exists()


def test_qualification_cli_keeps_result_off_communication_stdout(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = _module()
    registration_path = tmp_path / "registration.json"
    request_path = tmp_path / "qualification-request.json"
    request_hash = "a" * 64
    request_file_sha256 = "b" * 64
    request_size = 123
    review_commit = "c" * 40
    result = {"schema_version": "sentinel", "status": "passed"}
    monkeypatch.setattr(
        module,
        "_qualify_command",
        lambda observed_registration, observed_request, observed_hash,
        observed_file_hash, observed_size, observed_review_commit: (
            result
            if (
                observed_registration == registration_path
                and observed_request == request_path
                and observed_hash == request_hash
                and observed_file_hash == request_file_sha256
                and observed_size == request_size
                and observed_review_commit == review_commit
            )
            else pytest.fail("qualify CLI paths changed")
        ),
        raising=False,
    )

    exit_code = module.main(
        [
            "qualify",
            "--registration",
            str(registration_path),
            "--request",
            str(request_path),
            "--request-hash",
            request_hash,
            "--request-file-sha256",
            request_file_sha256,
            "--request-size",
            str(request_size),
            "--review-commit",
            review_commit,
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


def test_qualification_cli_keeps_failure_off_communication_streams(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = _module()

    def reject_qualification(*_args):
        raise module.OutcomeEvidenceRunnerError("prelaunch isolation drift")

    monkeypatch.setattr(module, "_qualify_command", reject_qualification)

    exit_code = module.main(
        [
            "qualify",
            "--registration",
            str(tmp_path / "registration.json"),
            "--request",
            str(tmp_path / "qualification-request.json"),
            "--request-hash",
            "a" * 64,
            "--request-file-sha256",
            "b" * 64,
            "--request-size",
            "123",
            "--review-commit",
            "c" * 40,
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == ""


def test_qualification_request_uses_isolated_child_command(
    tmp_path,
    monkeypatch,
):
    _module_value, _registration_path, _source_path, request = (
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )
    )

    assert request["child_command"][1:3] == ["-I", "-S"]


def test_qualification_child_environment_drops_ambient_python(monkeypatch):
    module = _module()
    monkeypatch.setenv("PYTHONPATH", r"C:\untrusted")
    monkeypatch.setenv("PYTHONHOME", r"C:\untrusted-python")
    monkeypatch.setenv("PYTHONINSPECT", "1")
    monkeypatch.setenv("GIT_WORK_TREE", r"C:\untrusted-worktree")

    environment = module._qualification_child_environment(
        config_path=r"D:\qualification\config.json",
        attempt_path=r"D:\qualification\attempt.json",
        attempt_hash="a" * 64,
    )

    assert not any(
        key.upper().startswith("PYTHON")
        for key in environment
        if key != "PYTHONDONTWRITEBYTECODE"
    )
    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
    assert not any(key.upper().startswith("GIT_") for key in environment)


def test_qualify_default_child_inherits_communication_streams(
    tmp_path,
    monkeypatch,
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    sentinel_process = object()
    popen_calls = []

    monkeypatch.setattr(
        module,
        "_load_runner_registration",
        lambda _path: registration,
    )

    def fake_popen(command, **kwargs):
        popen_calls.append((command, kwargs))
        return sentinel_process

    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)

    def fake_execute(**kwargs):
        assert kwargs["expected_request_hash"] == "a" * 64
        assert kwargs["expected_request_file_sha256"] == "b" * 64
        assert kwargs["expected_request_size"] == 123
        assert kwargs["expected_review_commit"] == "c" * 40
        process = kwargs["process_starter"](
            ("python.exe", "main.py"),
            {"BOUND": "1"},
        )
        assert process is sentinel_process
        return {"status": "passed"}

    monkeypatch.setattr(module, "execute_prelock_qualification", fake_execute)

    result = module._qualify_command(
        registration_path,
        tmp_path / "qualification-request.json",
        "a" * 64,
        "b" * 64,
        123,
        "c" * 40,
    )

    assert result == {"status": "passed"}
    assert popen_calls == [
        (
            ["python.exe", "main.py"],
            {
                "cwd": str(Path(registration.checkpoint_root).parent),
                "env": {"BOUND": "1"},
                "stderr": sys.stderr,
                "stdin": sys.stdin,
                "stdout": sys.stdout,
            },
        )
    ]


def test_dry_run_rejects_registration_for_another_checkout(tmp_path):
    module = _module()
    registration = build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=tmp_path / "other-checkout",
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        communication_config_path=tmp_path / "config.properties",
        checkpoint_root=tmp_path / "checkpoints",
    )
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="runner checkout",
    ):
        module._dry_run_command(registration_path)


def _legacy_registration_path(tmp_path):
    module = _module()
    registration = build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "legacy-study",
        repo_root=REPO_ROOT,
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        communication_config_path=tmp_path / "config.properties",
        checkpoint_root=tmp_path / "checkpoints",
        schema_version=LEGACY_REGISTRATION_SCHEMA_VERSION,
    )
    path = tmp_path / "legacy-registration.json"
    path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    return path


@pytest.mark.parametrize("command_name", ("_start_command", "_run_next_command"))
def test_launch_commands_reject_legacy_v1_before_writing_state(
    tmp_path,
    command_name,
):
    module = _module()
    registration_path = _legacy_registration_path(tmp_path)

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="v1 registration is read-only",
    ):
        getattr(module, command_name)(registration_path)

    artifact_root = tmp_path / "legacy-study"
    assert not (artifact_root / "run-lock.json").exists()
    assert not (artifact_root / "study-ledger.jsonl").exists()


def test_dry_run_keeps_legacy_v1_read_only_support(tmp_path):
    result = _module()._dry_run_command(_legacy_registration_path(tmp_path))

    assert result["launch_count"] == 24


def test_run_next_rejects_ambient_qualification_before_registration_access(
    tmp_path,
    monkeypatch,
):
    module = _module()
    monkeypatch.setenv(module.QUALIFICATION_ATTEMPT_HASH_ENV, "a" * 64)
    monkeypatch.setattr(
        module,
        "_load_runner_registration",
        lambda _path: pytest.fail("run-next loaded registration before env guard"),
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="ambient qualification",
    ):
        module._run_next_command(tmp_path / "registration.json")


def _study(tmp_path):
    registration = build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=REPO_ROOT,
        seed_base=SEED_BASE,
        python_executable=WINDOWS_PYTHON,
        communication_config_path=tmp_path / "config.properties",
        checkpoint_root=tmp_path / "checkpoints",
    )
    run_lock = {
        "registration": {"canonical_hash": registration.registration_hash},
        "run_lock_hash": RUN_LOCK_HASH,
        "source": {"commit": SOURCE_COMMIT},
        "study_id": STUDY_ID,
    }
    return registration, run_lock


def _qualification_request_fixture(
    tmp_path,
    monkeypatch,
    *,
    source_only=False,
    config_name="qualification-config.json",
    manifest_name="qualification-manifest.json",
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    communication_path = tmp_path / "config.properties"
    communication_path.write_bytes(
        b"verbose=false\ncommand=normal-agent\nrunAtGameStart=true\n"
    )
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    (checkpoint_root / "rl_model_ep1.pth").write_bytes(b"checkpoint")
    run_root = tmp_path / "runs"
    (run_root / "IRONCLAD").mkdir(parents=True)
    (run_root / "IRONCLAD" / "100.run").write_bytes(b"{}\n")
    (tmp_path / "ai_debug.log").write_bytes(b"debug baseline\n")
    (tmp_path / "communication_mod_errors.log").write_bytes(b"")
    qualification_root = tmp_path / "qualification-bootstrap-fixture"
    qualification_root.mkdir()
    qualification_id = f"{STUDY_ID}-qualification-bootstrap-fixture"
    config_path = qualification_root / config_name
    config_path.write_text(
        json.dumps(
            {
                "category_rates_bps": {"card_reward": 300, "shop": 1000},
                "enabled_categories": ["card_reward", "shop"],
                "manifest_path": str(
                    (qualification_root / manifest_name).resolve()
                ),
                "per_run_alternative_budget": 2,
                "schema_version": "noncombat-exploration-config-v1",
                "seed": SEED_BASE + 1,
                "session_id": f"{qualification_id}-s01",
                "source_commit": SOURCE_COMMIT,
                "study_id": qualification_id,
                "study_registration_hash": registration.registration_hash,
                "study_run_lock_hash": "0" * 64,
                "study_slot_number": 1,
                "trace_path": str(
                    (qualification_root / "qualification-trace.jsonl").resolve()
                ),
            },
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="",
    )
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir(exist_ok=True)
    marker_path.write_text("10\n11\n", encoding="utf-8", newline="")
    current_commit = [SOURCE_COMMIT]
    monkeypatch.setattr(
        module,
        "_tracked_source_commit",
        lambda _repo_root, **_kwargs: current_commit[0],
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_require_committed_qualification_registration",
        lambda _registration_path, _repo_root, _source_commit: None,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_require_committed_qualification_request_source",
        lambda *_args, **_kwargs: REVIEW_COMMIT,
        raising=False,
    )
    def validate_review_chain(**kwargs):
        request_record = kwargs["request"]
        if request_record["source_commit"] != SOURCE_COMMIT:
            raise module.OutcomeEvidenceRunnerError(
                "qualification source commit mismatch"
            )
        source_path = Path(request_record["request_source_path"])
        source_bytes = source_path.read_bytes()
        if (
            kwargs["expected_review_commit"] != REVIEW_COMMIT
            or kwargs["expected_request_file_sha256"]
            != hashlib.sha256(source_bytes).hexdigest()
            or kwargs["expected_request_size"] != len(source_bytes)
        ):
            raise module.OutcomeEvidenceRunnerError(
                "qualification external review binding mismatch"
            )
        return module._build_qualification_review_binding(
            request=request_record,
            review_commit=REVIEW_COMMIT,
            request_source_path=source_path,
            request_source_relative=source_path.relative_to(REPO_ROOT).as_posix(),
            request_bytes=source_bytes,
        )

    monkeypatch.setattr(
        module,
        "_validate_qualification_review_chain",
        validate_review_chain,
        raising=False,
    )
    reviewed_request_path = (tmp_path / "reviewed-qualification-request.json").resolve()
    request = module.build_qualification_request(
        registration_path=registration_path,
        qualification_id=qualification_id,
        qualification_root=qualification_root,
        config_path=config_path,
        marker_path=marker_path,
        request_source_path=reviewed_request_path,
        created_unix_ns=1,
    )
    current_commit[0] = REVIEW_COMMIT
    request_path = Path(request["request_path"])
    reviewed_request_path.write_text(
        module._canonical_json(request) + "\n",
        encoding="utf-8",
        newline="",
    )
    if source_only:
        original_publish_text_once = module._publish_text_once
        active_request_path = Path(request["request_path"])

        def publish_with_bootstrap_handoff(path, text, label):
            result = original_publish_text_once(path, text, label)
            if Path(path) == active_request_path and label == "qualification request":
                _write_bootstrap_phase(request, stage_count=5, handoff=True)
            return result

        monkeypatch.setattr(
            module,
            "_publish_text_once",
            publish_with_bootstrap_handoff,
        )
    if not source_only:
        request_path.write_bytes(reviewed_request_path.read_bytes())
        _write_bootstrap_phase(request, stage_count=5, handoff=True)
    return (
        module,
        registration_path,
        reviewed_request_path if source_only else request_path,
        request,
    )


def _write_bootstrap_phase(
    request,
    *,
    stage_count,
    handoff=False,
    failure=False,
):
    module = _module()
    bootstrap = request["bootstrap"]
    request_bytes = (
        module._canonical_json(request) + "\n"
    ).encode("ascii")
    runner_sha256 = request["implementation_sha256"][
        module.QUALIFICATION_RUNNER_RELATIVE_PATH
    ]
    envelope = module._qualification_bootstrap_envelope(
        request=request,
        expected_request_file_sha256=hashlib.sha256(
            request_bytes
        ).hexdigest(),
        expected_request_size=len(request_bytes),
        review_commit=REVIEW_COMMIT,
        runner_sha256=runner_sha256,
    )
    anchors = {
        "envelope_sha256": hashlib.sha256(
            module._canonical_json(envelope).encode("ascii")
        ).hexdigest(),
        "launch_token": module._qualification_bootstrap_token(envelope),
        "qualification_id": request["qualification_id"],
        "request_file_sha256": hashlib.sha256(request_bytes).hexdigest(),
        "request_hash": request["request_hash"],
        "request_size": len(request_bytes),
        "review_commit": REVIEW_COMMIT,
        "runner_sha256": runner_sha256,
        "source_commit": request["source_commit"],
    }
    claim = module._qualification_bootstrap_record(
        anchors=anchors,
        created_unix_ns=1,
        payload={},
        pid=1234,
        previous_hash=None,
        record_type="claim",
        stage_index=0,
        stage_name="claim",
    )

    def write_record(path, record):
        Path(path).write_bytes(
            module._canonical_json(record).encode("ascii") + b"\n"
        )

    write_record(bootstrap["claim_path"], claim)
    stages = []
    previous_hash = claim["record_hash"]
    for stage in bootstrap["stage_paths"][:stage_count]:
        record = module._qualification_bootstrap_record(
            anchors=anchors,
            created_unix_ns=stage["index"] + 1,
            payload={},
            pid=1234,
            previous_hash=previous_hash,
            record_type="stage",
            stage_index=stage["index"],
            stage_name=stage["name"],
        )
        write_record(stage["path"], record)
        stages.append(record)
        previous_hash = record["record_hash"]
    if handoff:
        assert stage_count == len(module.QUALIFICATION_BOOTSTRAP_STAGE_NAMES)
        record = module._qualification_bootstrap_record(
            anchors=anchors,
            created_unix_ns=7,
            payload={
                "active_request_file_sha256": hashlib.sha256(
                    request_bytes
                ).hexdigest(),
                "active_request_size": len(request_bytes),
                "claim_hash": claim["record_hash"],
                "final_stage_hash": stages[-1]["record_hash"],
                "request_hash": request["request_hash"],
            },
            pid=1234,
            previous_hash=stages[-1]["record_hash"],
            record_type="handoff",
            stage_index=6,
            stage_name="active_request_handoff",
        )
        write_record(bootstrap["handoff_path"], record)
    if failure:
        last_stage_index = len(stages)
        last_stage_name = (
            "claim"
            if not stages
            else module.QUALIFICATION_BOOTSTRAP_STAGE_NAMES[last_stage_index - 1]
        )
        record = module._qualification_bootstrap_record(
            anchors=anchors,
            created_unix_ns=7,
            payload={
                "code": "source_validation_failed",
                "detail": "reviewed source validation failed",
                "errno": None,
                "exception_type": "OutcomeEvidenceRunnerError",
                "winerror": None,
            },
            pid=1234,
            previous_hash=previous_hash,
            record_type="failure",
            stage_index=last_stage_index,
            stage_name=last_stage_name,
        )
        write_record(bootstrap["failure_path"], record)


def _bootstrap_runtime_state(request, *, stage_count):
    module = _module()
    bootstrap = request["bootstrap"]
    _write_bootstrap_phase(request, stage_count=stage_count)
    claim = json.loads(Path(bootstrap["claim_path"]).read_text(encoding="ascii"))
    if stage_count:
        last = json.loads(
            Path(bootstrap["stage_paths"][stage_count - 1]["path"]).read_text(
                encoding="ascii"
            )
        )
    else:
        last = claim
    request_bytes = (module._canonical_json(request) + "\n").encode("ascii")
    envelope = module._qualification_bootstrap_envelope(
        request=request,
        expected_request_file_sha256=hashlib.sha256(request_bytes).hexdigest(),
        expected_request_size=len(request_bytes),
        review_commit=REVIEW_COMMIT,
        runner_sha256=request["implementation_sha256"][
            module.QUALIFICATION_RUNNER_RELATIVE_PATH
        ],
    )
    return {
        "anchors": claim["anchors"],
        "claim_hash": claim["record_hash"],
        "consumed": False,
        "envelope": envelope,
        "last_record_hash": last["record_hash"],
        "last_stage_index": last["stage_index"],
        "last_stage_name": last["stage_name"],
        "paths": bootstrap,
    }


def test_qualification_request_round_trips_exact_current_bindings(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )

    loaded = module.load_qualification_request(
        request_path,
        registration_path=registration_path,
    )

    assert loaded == request
    assert loaded["schema_version"] == (
        "noncombat-outcome-evidence-qualification-request-v3"
    )
    assert loaded["source_commit"] == SOURCE_COMMIT
    assert loaded["request_source_path"] == str(
        (tmp_path / "reviewed-qualification-request.json").resolve()
    )
    assert loaded["registration"]["canonical_hash"]
    assert loaded["implementation_sha256"] == {
        relative_path: hashlib.sha256(
            (REPO_ROOT / relative_path).read_bytes()
        ).hexdigest()
        for relative_path in build_registration(
            study_id=STUDY_ID,
            artifact_root=tmp_path / "unused-study",
            repo_root=REPO_ROOT,
            seed_base=SEED_BASE,
            python_executable=WINDOWS_PYTHON,
            communication_config_path=tmp_path / "unused.properties",
            checkpoint_root=tmp_path / "unused-checkpoints",
        ).to_record()["integrity_rules"]["implementation_paths"]
    }
    assert loaded["handshake"]["readiness_timeout_seconds"] == 120
    assert loaded["handshake"]["release_timeout_seconds"] == 10
    assert loaded["marker"]["start_count"] == 2


def test_bootstrap_schema_locks_v3_request_fields_and_canonical_bytes(
    tmp_path,
    monkeypatch,
):
    module, _registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )

    assert module.QUALIFICATION_REQUEST_V1_SCHEMA_VERSION == (
        "noncombat-outcome-evidence-qualification-request-v1"
    )
    assert module.QUALIFICATION_REQUEST_V2_SCHEMA_VERSION == (
        "noncombat-outcome-evidence-qualification-request-v2"
    )
    assert module.QUALIFICATION_REQUEST_SCHEMA_VERSION == (
        "noncombat-outcome-evidence-qualification-request-v3"
    )
    assert set(request) == {
        "bootstrap",
        "child_command",
        "completion_path",
        "config",
        "created_unix_ns",
        "failure_path",
        "forbidden_paths",
        "handshake",
        "implementation_sha256",
        "isolation",
        "marker",
        "preexisting_files",
        "qualification_id",
        "qualification_root",
        "registration",
        "request_hash",
        "request_path",
        "request_source_path",
        "review_allowed_paths",
        "schema_version",
        "source_commit",
    }
    assert request["created_unix_ns"] == 1
    raw = request_path.read_bytes()
    assert raw == module._canonical_json(request).encode("ascii") + b"\n"
    assert raw.isascii()


def test_bootstrap_paths_are_fixed_direct_children_and_do_not_collide(tmp_path):
    module = _module()
    qualification_root = (tmp_path / "qualification-bootstrap-fixture").resolve()
    qualification_root.mkdir()

    bootstrap = module._qualification_bootstrap_paths(qualification_root)

    assert bootstrap["claim_path"] == str(
        qualification_root / "qualification-bootstrap-claim.json"
    )
    assert bootstrap["failure_path"] == str(
        qualification_root / "qualification-bootstrap-failure.json"
    )
    assert bootstrap["handoff_path"] == str(
        qualification_root / "qualification-bootstrap-handoff.json"
    )
    assert [stage["index"] for stage in bootstrap["stage_paths"]] == [1, 2, 3, 4, 5]
    assert [stage["name"] for stage in bootstrap["stage_paths"]] == list(
        module.QUALIFICATION_BOOTSTRAP_STAGE_NAMES
    )
    paths = [
        bootstrap["claim_path"],
        bootstrap["failure_path"],
        bootstrap["handoff_path"],
        *(stage["path"] for stage in bootstrap["stage_paths"]),
    ]
    assert len(paths) == len(set(paths))
    assert all(Path(path).parent == qualification_root for path in paths)
    reserved = {
        str(qualification_root / "qualification-request.json"),
        str(qualification_root / "qualification-communication-attempt.json"),
        str(qualification_root / "qualification-communication-ready.json"),
        str(qualification_root / "qualification-communication-release.json"),
        str(qualification_root / "qualification-completion.json"),
        str(qualification_root / "qualification-failure.json"),
        str(qualification_root / "qualification-config.json"),
        str(qualification_root / "qualification-manifest.json"),
        str(qualification_root / "qualification-trace.jsonl"),
    }
    assert set(paths).isdisjoint(reserved)


@pytest.mark.parametrize(
    "unsafe_root",
    (
        r"\\server\share\qualification",
        r"C:\qualification:stream",
        r"C:\qualification.\root",
        r"C:\safe\..\qualification",
    ),
)
def test_bootstrap_unsafe_lexical_roots_are_rejected_before_normalization(
    unsafe_root,
):
    module = _module()

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap.*root|unsafe",
    ):
        module._qualification_bootstrap_paths(Path(unsafe_root))


@pytest.mark.parametrize(
    ("config_name", "manifest_name"),
    (
        ("qualification-bootstrap-claim.json", "qualification-manifest.json"),
        ("qualification-config.json", "qualification-bootstrap-handoff.json"),
    ),
)
def test_bootstrap_collision_rejects_config_and_forbidden_paths(
    tmp_path,
    monkeypatch,
    config_name,
    manifest_name,
):
    module = _module()

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap path collision",
    ):
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
            config_name=config_name,
            manifest_name=manifest_name,
        )


@pytest.mark.parametrize(
    "collision_name",
    (
        "qualification-request.json",
        "QUALIFICATION-REQUEST.JSON",
        "qualification-communication-attempt.json",
        "qualification-communication-ready.json",
        "qualification-communication-release.json",
        "qualification-completion.json",
        "qualification-failure.json",
    ),
)
def test_bootstrap_collision_rejects_request_handshake_and_terminal_paths(
    tmp_path,
    monkeypatch,
    collision_name,
):
    module = _module()
    fixed_bootstrap_paths = module._qualification_bootstrap_paths

    def colliding_bootstrap_paths(qualification_root):
        bootstrap = fixed_bootstrap_paths(qualification_root)
        bootstrap["claim_path"] = str(
            Path(qualification_root) / collision_name
        )
        return bootstrap

    monkeypatch.setattr(
        module,
        "_qualification_bootstrap_paths",
        colliding_bootstrap_paths,
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap path collision",
    ):
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )


def test_bootstrap_phase_source_mode_allows_contiguous_stage_prefix(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    _write_bootstrap_phase(request, stage_count=3)

    loaded = module.load_qualification_request_source(
        request_source_path,
        registration_path=registration_path,
        expected_request_hash=request["request_hash"],
        **_qualification_review_kwargs(request),
    )

    assert loaded == request


def test_bootstrap_phase_active_mode_requires_complete_handoff(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )

    loaded = module.load_qualification_request(
        request_path,
        registration_path=registration_path,
    )

    assert loaded == request


@pytest.mark.parametrize(
    "unexpected",
    ("gap", "failure", "handoff", "entry", "case_entry"),
)
def test_bootstrap_phase_rejects_gaps_and_unexpected_entries(
    tmp_path,
    monkeypatch,
    unexpected,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    bootstrap = request["bootstrap"]
    if unexpected == "gap":
        Path(bootstrap["claim_path"]).write_bytes(b"claim\n")
        Path(bootstrap["stage_paths"][1]["path"]).write_bytes(b"stage two\n")
    elif unexpected == "failure":
        _write_bootstrap_phase(request, stage_count=2, failure=True)
    elif unexpected == "handoff":
        _write_bootstrap_phase(request, stage_count=5, handoff=True)
    else:
        entry_name = (
            "QUALIFICATION-BOOTSTRAP-EXTRA.JSON"
            if unexpected == "case_entry"
            else "qualification-bootstrap-extra.json"
        )
        Path(request["qualification_root"], entry_name).write_bytes(
            b"unexpected\n"
        )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap lifecycle",
    ):
        module.load_qualification_request_source(
            request_source_path,
            registration_path=registration_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
        )


def test_bootstrap_phase_active_mode_rejects_missing_handoff(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    Path(request["bootstrap"]["handoff_path"]).unlink()

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap lifecycle",
    ):
        module.load_qualification_request(
            request_path,
            registration_path=registration_path,
        )


def _rewrite_bootstrap_record(module, path, mutate, *, canonical=True):
    record = json.loads(Path(path).read_text(encoding="ascii"))
    mutate(record)
    if canonical:
        raw = module._canonical_json(record).encode("ascii") + b"\n"
    else:
        raw = json.dumps(
            record,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ).encode("ascii") + b"\n"
    Path(path).write_bytes(raw)


@pytest.mark.parametrize(
    "case",
    (
        "arbitrary_text",
        "malformed_json",
        "noncanonical_json",
        "claim_shape",
        "self_hash",
        "anchors",
        "previous_hash",
        "handoff_payload",
    ),
)
def test_bootstrap_active_load_rejects_invalid_chain_bytes(
    tmp_path,
    monkeypatch,
    case,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    bootstrap = request["bootstrap"]
    if case == "arbitrary_text":
        Path(bootstrap["claim_path"]).write_bytes(b"arbitrary text\n")
    elif case == "malformed_json":
        Path(bootstrap["claim_path"]).write_bytes(b'{"anchors":\n')
    elif case == "noncanonical_json":
        _rewrite_bootstrap_record(
            module,
            bootstrap["claim_path"],
            lambda _record: None,
            canonical=False,
        )
    elif case == "claim_shape":
        claim = json.loads(
            Path(bootstrap["claim_path"]).read_text(encoding="ascii")
        )
        previous = module._qualification_bootstrap_record(
            anchors=claim["anchors"],
            created_unix_ns=claim["created_unix_ns"],
            payload={},
            pid=claim["pid"],
            previous_hash="0" * 64,
            record_type="stage",
            stage_index=1,
            stage_name="launcher_verified",
        )
        Path(bootstrap["claim_path"]).write_bytes(
            module._canonical_json(previous).encode("ascii") + b"\n"
        )
        claim_hash = previous["record_hash"]
        for stage in bootstrap["stage_paths"]:
            original = json.loads(
                Path(stage["path"]).read_text(encoding="ascii")
            )
            previous = module._qualification_bootstrap_record(
                anchors=original["anchors"],
                created_unix_ns=original["created_unix_ns"],
                payload={},
                pid=original["pid"],
                previous_hash=previous["record_hash"],
                record_type="stage",
                stage_index=stage["index"],
                stage_name=stage["name"],
            )
            Path(stage["path"]).write_bytes(
                module._canonical_json(previous).encode("ascii") + b"\n"
            )
        handoff_path = Path(bootstrap["handoff_path"])
        original_handoff = json.loads(
            handoff_path.read_text(encoding="ascii")
        )
        handoff = module._qualification_bootstrap_record(
            anchors=original_handoff["anchors"],
            created_unix_ns=original_handoff["created_unix_ns"],
            payload={
                **original_handoff["payload"],
                "claim_hash": claim_hash,
                "final_stage_hash": previous["record_hash"],
            },
            pid=original_handoff["pid"],
            previous_hash=previous["record_hash"],
            record_type="handoff",
            stage_index=6,
            stage_name="active_request_handoff",
        )
        handoff_path.write_bytes(
            module._canonical_json(handoff).encode("ascii") + b"\n"
        )
    elif case == "self_hash":
        _rewrite_bootstrap_record(
            module,
            bootstrap["claim_path"],
            lambda record: record.__setitem__("record_hash", "f" * 64),
        )
    elif case == "anchors":
        _rewrite_bootstrap_record(
            module,
            bootstrap["stage_paths"][1]["path"],
            lambda record: (
                record["anchors"].__setitem__("review_commit", "d" * 40),
                record.__setitem__(
                    "record_hash",
                    module._self_hash(record, "record_hash"),
                ),
            ),
        )
    elif case == "previous_hash":
        _rewrite_bootstrap_record(
            module,
            bootstrap["stage_paths"][2]["path"],
            lambda record: (
                record.__setitem__("previous_hash", "f" * 64),
                record.__setitem__(
                    "record_hash",
                    module._self_hash(record, "record_hash"),
                ),
            ),
        )
    else:
        _rewrite_bootstrap_record(
            module,
            bootstrap["handoff_path"],
            lambda record: (
                record["payload"].__setitem__(
                    "active_request_size",
                    record["payload"]["active_request_size"] + 1,
                ),
                record.__setitem__(
                    "record_hash",
                    module._self_hash(record, "record_hash"),
                ),
            ),
        )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap",
    ):
        module.load_qualification_request(
            request_path,
            registration_path=registration_path,
        )


@pytest.mark.parametrize("entry_kind", ("directory", "junction"))
def test_bootstrap_active_load_rejects_nonregular_or_reparse_record(
    tmp_path,
    monkeypatch,
    entry_kind,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    claim_path = Path(request["bootstrap"]["claim_path"])
    claim_path.unlink()
    target_path = tmp_path / "bootstrap-record-target"
    if entry_kind == "directory":
        claim_path.mkdir()
    else:
        target_path.mkdir()
        _create_directory_junction(claim_path, target_path)

    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="bootstrap claim.*(?:regular file|reparse|symbolic link)",
        ):
            module.load_qualification_request(
                request_path,
                registration_path=registration_path,
            )
    finally:
        os.rmdir(claim_path)
        if target_path.exists():
            target_path.rmdir()


def test_bootstrap_active_load_rejects_case_aliased_record_name(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    claim_path = Path(request["bootstrap"]["claim_path"])
    aliased_path = claim_path.with_name(claim_path.name.upper())
    claim_path.rename(aliased_path)
    assert aliased_path.name in {
        entry.name for entry in os.scandir(aliased_path.parent)
    }

    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="bootstrap.*case alias",
        ):
            module.load_qualification_request(
                request_path,
                registration_path=registration_path,
            )
    finally:
        aliased_path.rename(claim_path)


def test_bootstrap_invalid_handoff_blocks_attempt_and_child_start(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    publish_with_handoff = module._publish_text_once

    def publish_corrupt_handoff(path, text, label):
        result = publish_with_handoff(path, text, label)
        if label == "qualification request":
            _rewrite_bootstrap_record(
                module,
                request["bootstrap"]["handoff_path"],
                lambda record: (
                    record["payload"].__setitem__("claim_hash", "f" * 64),
                    record.__setitem__(
                        "record_hash",
                        module._self_hash(record, "record_hash"),
                    ),
                ),
            )
        return result

    monkeypatch.setattr(module, "_publish_text_once", publish_corrupt_handoff)

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args, **_kwargs: pytest.fail(
                "invalid handoff started a qualification child"
            ),
        )

    assert not Path(request["handshake"]["attempt_path"]).exists()


def test_bootstrap_token_is_frozen_and_binds_every_contract_anchor():
    module = _module()
    envelope = module._qualification_bootstrap_envelope(
        request=BOOTSTRAP_VECTOR_REQUEST,
        expected_request_file_sha256="c" * 64,
        expected_request_size=123,
        review_commit="d" * 40,
        runner_sha256="e" * 64,
    )

    encoded = module._qualification_bootstrap_encode_envelope(envelope)
    token = module._qualification_bootstrap_token(envelope)

    assert encoded == BOOTSTRAP_VECTOR_ENVELOPE_B64
    assert token == BOOTSTRAP_VECTOR_TOKEN
    assert module._qualification_bootstrap_decode_envelope(encoded) == envelope
    assert module._qualification_bootstrap_token(dict(reversed(envelope.items()))) == token
    for field, replacement in (
        ("qualification_id", "different-qualification"),
        ("qualification_root", "C:\\different-root"),
        ("request_file_sha256", "f" * 64),
        ("request_hash", "f" * 64),
        ("request_size", 124),
        ("review_commit", "f" * 40),
        ("runner_sha256", "f" * 64),
        ("source_commit", "f" * 40),
        (
            "schema_version",
            "noncombat-outcome-evidence-qualification-bootstrap-token-v0",
        ),
    ):
        changed = json.loads(json.dumps(envelope))
        changed[field] = replacement
        assert module._qualification_bootstrap_token(changed) != token
    bootstrap_mutations = [
        (("claim_path",), "C:\\different-root\\claim.json"),
        (("failure_path",), "C:\\different-root\\failure.json"),
        (("handoff_path",), "C:\\different-root\\handoff.json"),
        (("schema_version",), "qualification-bootstrap-evidence-v0"),
        (("token_schema_version",), "qualification-bootstrap-token-v0"),
        *(
            (("stage_paths", index, "path"), f"C:\\different-root\\stage-{index}.json")
            for index in range(5)
        ),
    ]
    for location, replacement in bootstrap_mutations:
        changed = json.loads(json.dumps(envelope))
        target = changed["bootstrap"]
        for part in location[:-1]:
            target = target[part]
        target[location[-1]] = replacement
        assert module._qualification_bootstrap_token(changed) != token


@pytest.mark.parametrize(
    "unsafe_root",
    (
        r"\\server\share\qualification",
        r"C:\qualification:stream",
        r"C:\qualification.\root",
        r"C:\safe\..\qualification",
    ),
)
def test_bootstrap_unsafe_envelope_paths_are_rejected(unsafe_root):
    module = _module()
    envelope = module._qualification_bootstrap_envelope(
        request=BOOTSTRAP_VECTOR_REQUEST,
        expected_request_file_sha256="c" * 64,
        expected_request_size=123,
        review_commit="d" * 40,
        runner_sha256="e" * 64,
    )
    changed = json.loads(json.dumps(envelope))
    changed["qualification_root"] = unsafe_root
    root = Path(unsafe_root)
    changed["bootstrap"] = {
        **changed["bootstrap"],
        "claim_path": str(root / "qualification-bootstrap-claim.json"),
        "failure_path": str(root / "qualification-bootstrap-failure.json"),
        "handoff_path": str(root / "qualification-bootstrap-handoff.json"),
        "stage_paths": [
            {
                **stage,
                "path": str(
                    root
                    / f"qualification-bootstrap-stage-{stage['index']:02d}-"
                    f"{stage['name'].replace('_', '-')}.json"
                ),
            }
            for stage in changed["bootstrap"]["stage_paths"]
        ],
    }
    encoded = base64.b64encode(
        module._canonical_json(changed).encode("ascii")
    ).decode("ascii")

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap.*root|unsafe",
    ):
        module._qualification_bootstrap_decode_envelope(encoded)


def test_bootstrap_record_schema_and_self_hash_bytes_are_frozen():
    module = _module()
    sha256_vector = "0" * 64
    commit_vector = "1" * 40
    anchors = {
        "envelope_sha256": sha256_vector,
        "launch_token": sha256_vector,
        "qualification_id": "fixture-qualification",
        "request_file_sha256": sha256_vector,
        "request_hash": sha256_vector,
        "request_size": 1,
        "review_commit": commit_vector,
        "runner_sha256": sha256_vector,
        "source_commit": commit_vector,
    }
    claim = module._qualification_bootstrap_record(
        anchors=anchors,
        created_unix_ns=1,
        payload={},
        pid=1,
        previous_hash=None,
        record_type="claim",
        stage_index=0,
        stage_name="claim",
    )
    stage = module._qualification_bootstrap_record(
        anchors=anchors,
        created_unix_ns=1,
        payload={},
        pid=1,
        previous_hash=claim["record_hash"],
        record_type="stage",
        stage_index=1,
        stage_name="launcher_verified",
    )
    stage_two = module._qualification_bootstrap_record(
        anchors=anchors,
        created_unix_ns=1,
        payload={},
        pid=1,
        previous_hash=stage["record_hash"],
        record_type="stage",
        stage_index=2,
        stage_name="runner_entered",
    )
    failure = module._qualification_bootstrap_record(
        anchors=anchors,
        created_unix_ns=1,
        payload={
            "code": "source_validation_failed",
            "detail": "reviewed source validation failed",
            "errno": None,
            "exception_type": "OutcomeEvidenceRunnerError",
            "winerror": None,
        },
        pid=1,
        previous_hash=stage_two["record_hash"],
        record_type="failure",
        stage_index=2,
        stage_name="runner_entered",
    )
    handoff = module._qualification_bootstrap_record(
        anchors=anchors,
        created_unix_ns=1,
        payload={
            "active_request_file_sha256": sha256_vector,
            "active_request_size": 1,
            "claim_hash": claim["record_hash"],
            "final_stage_hash": sha256_vector,
            "request_hash": sha256_vector,
        },
        pid=1,
        previous_hash=sha256_vector,
        record_type="handoff",
        stage_index=6,
        stage_name="active_request_handoff",
    )

    assert module.QUALIFICATION_BOOTSTRAP_FAILURE_CODES == frozenset(
        {
            "bootstrap_envelope_invalid",
            "bootstrap_claim_publish_failed",
            "runner_validation_failed",
            "runner_entry_validation_failed",
            "source_validation_failed",
            "request_validation_failed",
            "prelaunch_isolation_failed",
            "unexpected_pre_request_failure",
        }
    )
    assert module.QUALIFICATION_BOOTSTRAP_FAILURE_DETAILS == {
        "bootstrap_envelope_invalid": "bootstrap envelope validation failed",
        "bootstrap_claim_publish_failed": "bootstrap claim publication failed",
        "runner_validation_failed": "reviewed runner validation failed",
        "runner_entry_validation_failed": "runner entry validation failed",
        "source_validation_failed": "reviewed source validation failed",
        "request_validation_failed": "reviewed request validation failed",
        "prelaunch_isolation_failed": "prelaunch isolation validation failed",
        "unexpected_pre_request_failure": "unexpected pre-request failure",
    }
    assert failure["stage_index"] == stage_two["stage_index"]
    assert failure["stage_name"] == stage_two["stage_name"]
    assert failure["previous_hash"] == stage_two["record_hash"]
    expected = {
        "claim": b'{"anchors":{"envelope_sha256":"0000000000000000000000000000000000000000000000000000000000000000","launch_token":"0000000000000000000000000000000000000000000000000000000000000000","qualification_id":"fixture-qualification","request_file_sha256":"0000000000000000000000000000000000000000000000000000000000000000","request_hash":"0000000000000000000000000000000000000000000000000000000000000000","request_size":1,"review_commit":"1111111111111111111111111111111111111111","runner_sha256":"0000000000000000000000000000000000000000000000000000000000000000","source_commit":"1111111111111111111111111111111111111111"},"created_unix_ns":1,"payload":{},"pid":1,"previous_hash":null,"record_hash":"6f50bfdced41d515ae33f7f402a36d38d337c39ccbecba1ca8dec926c69c42b5","record_type":"claim","schema_version":"noncombat-outcome-evidence-qualification-bootstrap-evidence-v1","stage_index":0,"stage_name":"claim"}\n',
        "stage": b'{"anchors":{"envelope_sha256":"0000000000000000000000000000000000000000000000000000000000000000","launch_token":"0000000000000000000000000000000000000000000000000000000000000000","qualification_id":"fixture-qualification","request_file_sha256":"0000000000000000000000000000000000000000000000000000000000000000","request_hash":"0000000000000000000000000000000000000000000000000000000000000000","request_size":1,"review_commit":"1111111111111111111111111111111111111111","runner_sha256":"0000000000000000000000000000000000000000000000000000000000000000","source_commit":"1111111111111111111111111111111111111111"},"created_unix_ns":1,"payload":{},"pid":1,"previous_hash":"6f50bfdced41d515ae33f7f402a36d38d337c39ccbecba1ca8dec926c69c42b5","record_hash":"c3543ab7758923ef33d7570468127267aace386d73bb3ee408cc4ef4c014058f","record_type":"stage","schema_version":"noncombat-outcome-evidence-qualification-bootstrap-evidence-v1","stage_index":1,"stage_name":"launcher_verified"}\n',
        "stage_two": b'{"anchors":{"envelope_sha256":"0000000000000000000000000000000000000000000000000000000000000000","launch_token":"0000000000000000000000000000000000000000000000000000000000000000","qualification_id":"fixture-qualification","request_file_sha256":"0000000000000000000000000000000000000000000000000000000000000000","request_hash":"0000000000000000000000000000000000000000000000000000000000000000","request_size":1,"review_commit":"1111111111111111111111111111111111111111","runner_sha256":"0000000000000000000000000000000000000000000000000000000000000000","source_commit":"1111111111111111111111111111111111111111"},"created_unix_ns":1,"payload":{},"pid":1,"previous_hash":"c3543ab7758923ef33d7570468127267aace386d73bb3ee408cc4ef4c014058f","record_hash":"8a7de07962f96dd0d41a4b8dbdca1a3325949fa0a625ba33eb183960fb1336af","record_type":"stage","schema_version":"noncombat-outcome-evidence-qualification-bootstrap-evidence-v1","stage_index":2,"stage_name":"runner_entered"}\n',
        "failure": b'{"anchors":{"envelope_sha256":"0000000000000000000000000000000000000000000000000000000000000000","launch_token":"0000000000000000000000000000000000000000000000000000000000000000","qualification_id":"fixture-qualification","request_file_sha256":"0000000000000000000000000000000000000000000000000000000000000000","request_hash":"0000000000000000000000000000000000000000000000000000000000000000","request_size":1,"review_commit":"1111111111111111111111111111111111111111","runner_sha256":"0000000000000000000000000000000000000000000000000000000000000000","source_commit":"1111111111111111111111111111111111111111"},"created_unix_ns":1,"payload":{"code":"source_validation_failed","detail":"reviewed source validation failed","errno":null,"exception_type":"OutcomeEvidenceRunnerError","winerror":null},"pid":1,"previous_hash":"8a7de07962f96dd0d41a4b8dbdca1a3325949fa0a625ba33eb183960fb1336af","record_hash":"cb574c32306810c1ac9538a20ce34a37f23b777449b245db62d0258b27944e7c","record_type":"failure","schema_version":"noncombat-outcome-evidence-qualification-bootstrap-evidence-v1","stage_index":2,"stage_name":"runner_entered"}\n',
        "handoff": b'{"anchors":{"envelope_sha256":"0000000000000000000000000000000000000000000000000000000000000000","launch_token":"0000000000000000000000000000000000000000000000000000000000000000","qualification_id":"fixture-qualification","request_file_sha256":"0000000000000000000000000000000000000000000000000000000000000000","request_hash":"0000000000000000000000000000000000000000000000000000000000000000","request_size":1,"review_commit":"1111111111111111111111111111111111111111","runner_sha256":"0000000000000000000000000000000000000000000000000000000000000000","source_commit":"1111111111111111111111111111111111111111"},"created_unix_ns":1,"payload":{"active_request_file_sha256":"0000000000000000000000000000000000000000000000000000000000000000","active_request_size":1,"claim_hash":"6f50bfdced41d515ae33f7f402a36d38d337c39ccbecba1ca8dec926c69c42b5","final_stage_hash":"0000000000000000000000000000000000000000000000000000000000000000","request_hash":"0000000000000000000000000000000000000000000000000000000000000000"},"pid":1,"previous_hash":"0000000000000000000000000000000000000000000000000000000000000000","record_hash":"a56eaffd46dc7aa6af84bac9313a0cb325c0c535d446dc1101a7568873d79d65","record_type":"handoff","schema_version":"noncombat-outcome-evidence-qualification-bootstrap-evidence-v1","stage_index":6,"stage_name":"active_request_handoff"}\n',
    }
    for name, record in (
        ("claim", claim),
        ("stage", stage),
        ("stage_two", stage_two),
        ("failure", failure),
        ("handoff", handoff),
    ):
        assert module._canonical_json(record).encode("ascii") + b"\n" == expected[name]


def test_bootstrap_stage_publication_is_immutable_contiguous_and_anchor_stable(
    tmp_path,
    monkeypatch,
):
    module, _registration_path, _request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    state = _bootstrap_runtime_state(request, stage_count=1)
    original = json.loads(json.dumps(state))
    states = [state]

    for created_unix_ns, stage_name in enumerate(
        module.QUALIFICATION_BOOTSTRAP_STAGE_NAMES[1:],
        start=20,
    ):
        states.append(
            module._qualification_bootstrap_publish_stage(
                states[-1],
                stage_name,
                created_unix_ns=created_unix_ns,
            )
        )

    assert state == original
    assert [item["last_stage_index"] for item in states] == [1, 2, 3, 4, 5]
    assert [item["last_stage_name"] for item in states] == list(
        module.QUALIFICATION_BOOTSTRAP_STAGE_NAMES
    )
    previous_hash = json.loads(
        Path(request["bootstrap"]["claim_path"]).read_text(encoding="ascii")
    )["record_hash"]
    for stage, expected_state in zip(
        request["bootstrap"]["stage_paths"],
        states,
        strict=True,
    ):
        record = json.loads(Path(stage["path"]).read_text(encoding="ascii"))
        assert record["anchors"] == state["anchors"]
        assert record["previous_hash"] == previous_hash
        assert record["record_hash"] == expected_state["last_record_hash"]
        previous_hash = record["record_hash"]
    assert not Path(request["bootstrap"]["failure_path"]).exists()
    assert not Path(request["bootstrap"]["handoff_path"]).exists()
    assert not Path(request["request_path"]).exists()
    assert not Path(request["handshake"]["attempt_path"]).exists()


def test_bootstrap_controlled_failure_is_sanitized_and_never_overwrites(
    tmp_path,
    monkeypatch,
):
    module, _registration_path, _request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    state = _bootstrap_runtime_state(request, stage_count=2)
    failure_path = Path(request["bootstrap"]["failure_path"])
    secret = "SECRET=do-not-publish gameplay=victory"
    error = OSError(5, secret)
    error.winerror = 123

    published_hash = module._qualification_bootstrap_publish_failure(
        state,
        "source_validation_failed",
        error,
    )
    first_bytes = failure_path.read_bytes()
    failure = json.loads(first_bytes)

    assert published_hash == failure["record_hash"]
    assert failure["stage_index"] == 2
    assert failure["stage_name"] == "runner_entered"
    assert failure["previous_hash"] == state["last_record_hash"]
    assert failure["anchors"] == state["anchors"]
    assert failure["payload"] == {
        "code": "source_validation_failed",
        "detail": "reviewed source validation failed",
        "errno": 5,
        "exception_type": "OSError",
        "winerror": 123,
    }
    assert secret.encode("ascii") not in first_bytes
    assert module._qualification_bootstrap_publish_failure(
        state,
        "unexpected_pre_request_failure",
        RuntimeError("SECOND_SECRET"),
    ) is None
    assert failure_path.read_bytes() == first_bytes


def test_bootstrap_controlled_failure_keeps_partial_entry_consumed(
    tmp_path,
    monkeypatch,
):
    module, _registration_path, _request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    state = _bootstrap_runtime_state(request, stage_count=3)
    failure_path = Path(request["bootstrap"]["failure_path"])
    failure_path.write_bytes(b"{")

    assert module._qualification_bootstrap_publish_failure(
        state,
        "unexpected_pre_request_failure",
        RuntimeError("must remain private"),
    ) is None
    assert failure_path.read_bytes() == b"{"


def test_bootstrap_controlled_failure_maps_unexpected_without_private_detail(
    tmp_path,
    monkeypatch,
):
    module, _registration_path, _request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    state = _bootstrap_runtime_state(request, stage_count=3)

    module._qualification_bootstrap_publish_failure(
        state,
        "not-a-public-code",
        RuntimeError("SECRET unexpected exception detail"),
    )

    raw = Path(request["bootstrap"]["failure_path"]).read_bytes()
    failure = json.loads(raw)
    assert failure["payload"] == {
        "code": "unexpected_pre_request_failure",
        "detail": "unexpected pre-request failure",
        "errno": None,
        "exception_type": "RuntimeError",
        "winerror": None,
    }
    assert b"SECRET" not in raw


def test_pre_request_stage_boundary_runner_entry_failure_links_launcher_stage(
    tmp_path,
    monkeypatch,
    capsys,
):
    module, _registration_path, _request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    state = _bootstrap_runtime_state(request, stage_count=1)
    envelope_b64 = module._qualification_bootstrap_encode_envelope(
        state["envelope"]
    )
    token = state["anchors"]["launch_token"]
    runner_path = Path(module.__file__).resolve()
    runner_sha256 = hashlib.sha256(runner_path.read_bytes()).hexdigest()
    qualifier_arguments = (
        "qualify",
        "--registration",
        str((tmp_path / "registration.json").resolve()),
        "--request",
        str((tmp_path / "reviewed-request.json").resolve()),
        "--request-hash",
        state["anchors"]["request_hash"],
        "--request-file-sha256",
        state["anchors"]["request_file_sha256"],
        "--request-size",
        str(state["anchors"]["request_size"]),
        "--review-commit",
        state["anchors"]["review_commit"],
    )
    monkeypatch.setenv(module.QUALIFICATION_RUNNER_SHA256_ENV, runner_sha256)
    monkeypatch.setenv(module.QUALIFICATION_BOOTSTRAP_ENVELOPE_ENV, envelope_b64)
    monkeypatch.setenv(module.QUALIFICATION_BOOTSTRAP_LAUNCH_TOKEN_ENV, token)
    monkeypatch.setattr(
        module.sys,
        "orig_argv",
        [
            sys.executable,
            "-I",
            "-S",
            "-c",
            module.QUALIFICATION_TRUSTED_LAUNCHER_CODE,
            str(runner_path),
            runner_sha256,
            envelope_b64,
            token,
            *qualifier_arguments,
        ],
    )
    monkeypatch.setattr(
        module.sys,
        "argv",
        [str(runner_path), *qualifier_arguments, "--unexpected"],
    )

    with pytest.raises(SystemExit) as raised:
        module._qualification_require_trusted_launcher()

    assert raised.value.code == 2
    failure = json.loads(
        Path(request["bootstrap"]["failure_path"]).read_text(encoding="ascii")
    )
    assert failure["stage_index"] == 1
    assert failure["stage_name"] == "launcher_verified"
    assert failure["payload"]["code"] == "runner_entry_validation_failed"
    assert not Path(request["bootstrap"]["stage_paths"][1]["path"]).exists()
    assert not Path(request["request_path"]).exists()
    assert not Path(request["handshake"]["attempt_path"]).exists()
    assert capsys.readouterr() == ("", "")


def test_pre_request_stage_boundary_source_failure_links_runner_stage(
    tmp_path,
    monkeypatch,
    capsys,
):
    module, _registration_path, _request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    state = _bootstrap_runtime_state(request, stage_count=2)
    monkeypatch.setattr(
        module,
        "_qualification_bootstrap_validate_source",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            module._QualificationBootstrapError("tracked bytes drift")
        ),
    )

    with pytest.raises(SystemExit) as raised:
        module._qualification_bootstrap_verify_source(
            state,
            module.REPO_ROOT,
            expected_review_commit=REVIEW_COMMIT,
        )

    assert raised.value.code == 2
    failure = json.loads(
        Path(request["bootstrap"]["failure_path"]).read_text(encoding="ascii")
    )
    assert failure["stage_index"] == 2
    assert failure["stage_name"] == "runner_entered"
    assert failure["payload"]["code"] == "source_validation_failed"
    assert not Path(request["bootstrap"]["stage_paths"][2]["path"]).exists()
    assert not Path(request["request_path"]).exists()
    assert not Path(request["handshake"]["attempt_path"]).exists()
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    ("boundary", "last_stage", "failure_code"),
    (
        ("request", "source_verified", "request_validation_failed"),
        ("isolation", "request_reviewed", "prelaunch_isolation_failed"),
    ),
)
def test_pre_request_stage_boundary_request_and_isolation_failures(
    tmp_path,
    monkeypatch,
    boundary,
    last_stage,
    failure_code,
    capsys,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    state = _bootstrap_runtime_state(request, stage_count=3)
    monkeypatch.setattr(module, "_QUALIFICATION_CLI_REQUESTED", True)
    monkeypatch.setattr(module, "_QUALIFICATION_BOOTSTRAP_STATE", state)
    monkeypatch.setenv(
        module.QUALIFICATION_RUNNER_SHA256_ENV,
        request["implementation_sha256"][module.QUALIFICATION_RUNNER_RELATIVE_PATH],
    )
    protected_paths = (
        Path(request["isolation"]["communication_mod"]["path"]),
        Path(request["isolation"]["marker"]["path"]),
        Path(request["isolation"]["runs"]["root"]) / "IRONCLAD" / "100.run",
        Path(request["isolation"]["checkpoints"]["root"]) / "rl_model_ep1.pth",
        *(Path(path) for path in request["isolation"]["global_logs"]),
        Path(registration_path),
        Path(request["config"]["path"]),
    )
    protected_before = {path: path.read_bytes() for path in protected_paths}
    if boundary == "request":
        request_source_path.write_bytes(b"{\n")
    else:
        run_path = Path(request["isolation"]["runs"]["root"]) / "IRONCLAD" / "100.run"
        run_path.write_bytes(b'{"drift":true}\n')
        protected_before[run_path] = run_path.read_bytes()

    with pytest.raises(module.OutcomeEvidenceRunnerError):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args, **_kwargs: pytest.fail(
                "pre-request failure started a child"
            ),
        )

    failure = json.loads(
        Path(request["bootstrap"]["failure_path"]).read_text(encoding="ascii")
    )
    assert failure["stage_name"] == last_stage
    assert failure["payload"]["code"] == failure_code
    assert not Path(request["request_path"]).exists()
    assert not Path(request["handshake"]["attempt_path"]).exists()
    assert not Path(request["handshake"]["ready_path"]).exists()
    assert not Path(request["handshake"]["release_path"]).exists()
    assert not Path(request["completion_path"]).exists()
    assert not Path(request["failure_path"]).exists()
    assert not Path(request["bootstrap"]["handoff_path"]).exists()
    assert all(not Path(path).exists() for path in request["forbidden_paths"])
    assert {path: path.read_bytes() for path in protected_paths} == protected_before
    assert capsys.readouterr() == ("", "")


def test_pre_request_stage_boundary_success_stops_after_isolation_stage(
    tmp_path,
    monkeypatch,
    capsys,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    state = _bootstrap_runtime_state(request, stage_count=3)
    monkeypatch.setattr(module, "_QUALIFICATION_CLI_REQUESTED", True)
    monkeypatch.setattr(module, "_QUALIFICATION_BOOTSTRAP_STATE", state)
    monkeypatch.setenv(
        module.QUALIFICATION_RUNNER_SHA256_ENV,
        request["implementation_sha256"][module.QUALIFICATION_RUNNER_RELATIVE_PATH],
    )
    counts = {
        "inventory": 0,
        "isolation": 0,
        "registration": 0,
        "review": 0,
    }

    def count_call(name, function):
        def counted(*args, **kwargs):
            counts[name] += 1
            return function(*args, **kwargs)

        return counted

    for name, function_name in (
        ("inventory", "_qualification_root_inventory"),
        ("isolation", "_qualification_observe_isolation"),
        ("registration", "_load_qualification_registration"),
        ("review", "_validate_qualification_review_chain"),
    ):
        monkeypatch.setattr(
            module,
            function_name,
            count_call(name, getattr(module, function_name)),
        )

    with pytest.raises(SystemExit) as raised:
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args, **_kwargs: pytest.fail(
                "Task 3 started a child"
            ),
        )

    assert raised.value.code == 2
    bootstrap = request["bootstrap"]
    isolation_stage = json.loads(
        Path(bootstrap["stage_paths"][4]["path"]).read_text(encoding="ascii")
    )
    assert isolation_stage["stage_index"] == 5
    assert isolation_stage["stage_name"] == "isolation_verified"
    assert not Path(bootstrap["failure_path"]).exists()
    assert not Path(bootstrap["handoff_path"]).exists()
    assert not Path(request["request_path"]).exists()
    assert not Path(request["handshake"]["attempt_path"]).exists()
    assert not Path(request["handshake"]["ready_path"]).exists()
    assert not Path(request["handshake"]["release_path"]).exists()
    assert not Path(request["completion_path"]).exists()
    assert not Path(request["failure_path"]).exists()
    assert all(not Path(path).exists() for path in request["forbidden_paths"])
    assert counts == {
        "inventory": 1,
        "isolation": 1,
        "registration": 1,
        "review": 1,
    }
    assert capsys.readouterr() == ("", "")


def test_live_qualification_rejects_v1_request_before_consumption(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    legacy_request = json.loads(json.dumps(request))
    legacy_request.pop("isolation")
    legacy_request["schema_version"] = (
        module.LEGACY_QUALIFICATION_REQUEST_SCHEMA_VERSION
    )
    legacy_request["request_hash"] = module._self_hash(
        legacy_request,
        "request_hash",
    )
    request_path.write_text(
        module._canonical_json(legacy_request) + "\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="schema",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=legacy_request["request_hash"],
            **_qualification_review_kwargs(legacy_request),
            process_starter=lambda *_args, **_kwargs: pytest.fail(
                "v1 request started a qualification child"
            ),
        )

    assert not Path(legacy_request["request_path"]).exists()
    assert not Path(legacy_request["handshake"]["attempt_path"]).exists()
    assert not Path(legacy_request["completion_path"]).exists()
    assert not Path(legacy_request["failure_path"]).exists()


def test_qualification_request_binds_complete_isolation_baseline(
    tmp_path,
    monkeypatch,
):
    _module_value, _registration_path, _source_path, request = (
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )
    )

    isolation = request["isolation"]
    assert set(isolation) == {
        "baseline_hash",
        "checkpoints",
        "communication_mod",
        "global_logs",
        "marker",
        "runs",
        "schema_version",
    }
    assert base64.b64decode(
        isolation["communication_mod"]["original_bytes_b64"],
        validate=True,
    ) == (tmp_path / "config.properties").read_bytes()
    assert isolation["marker"]["line_count"] == 2
    assert isolation["runs"]["entry_count"] == 2
    assert isolation["checkpoints"]["entry_count"] == 1
    assert set(isolation["global_logs"]) == {
        str((tmp_path / "ai_debug.log").resolve()),
        str((tmp_path / "communication_mod_errors.log").resolve()),
    }


def test_qualification_cli_binds_launcher_anchor_to_reviewed_runner(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )
    )
    monkeypatch.setattr(module, "_QUALIFICATION_CLI_REQUESTED", True)
    monkeypatch.setenv(module.QUALIFICATION_RUNNER_SHA256_ENV, "f" * 64)

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="launcher anchor.*reviewed runner",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args: pytest.fail(
                "mismatched launcher anchor started a child"
            ),
        )


def test_qualification_request_rejects_rehashed_source_drift(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    request["source_commit"] = "f" * 40
    request["request_hash"] = module._self_hash(request, "request_hash")
    request_path.write_text(
        module._canonical_json(request) + "\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="source commit|config binding",
    ):
        module.load_qualification_request(
            request_path,
            registration_path=registration_path,
        )


def test_qualification_request_rejects_noncanonical_bytes(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    request_path.write_text(
        json.dumps(request, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="canonical"):
        module.load_qualification_request(
            request_path,
            registration_path=registration_path,
        )


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("implementation", "implementation"),
        ("child_command", "child command"),
        ("config", "config"),
        ("config_behavior", "configuration behavior"),
        ("config_extra", "configuration fields"),
        ("marker", "marker"),
        ("marker_path", "marker path"),
        ("handshake", "handshake"),
        ("registration", "registration"),
    ),
)
def test_qualification_request_rejects_rehashed_binding_drift(
    tmp_path,
    monkeypatch,
    case,
    message,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    if case == "implementation":
        request["implementation_sha256"]["main.py"] = "f" * 64
    elif case == "child_command":
        request["child_command"].append("--train")
    elif case == "config":
        request["config"]["sha256"] = "f" * 64
    elif case == "config_behavior":
        config_path = Path(request["config"]["path"])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["category_rates_bps"]["card_reward"] = 299
        config_path.write_text(
            module._canonical_json(config) + "\n",
            encoding="utf-8",
            newline="",
        )
        config_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
        request["config"]["sha256"] = config_sha256
        request["preexisting_files"][str(config_path.resolve())] = config_sha256
    elif case == "config_extra":
        config_path = Path(request["config"]["path"])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["unexpected"] = True
        config_path.write_text(
            module._canonical_json(config) + "\n",
            encoding="utf-8",
            newline="",
        )
        config_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
        request["config"]["sha256"] = config_sha256
        request["preexisting_files"][str(config_path.resolve())] = config_sha256
    elif case == "marker":
        request["marker"]["start_count"] += 1
    elif case == "marker_path":
        decoy_marker = (tmp_path / "decoy" / "ai_games.txt").resolve()
        decoy_marker.parent.mkdir()
        decoy_marker.write_text("10\n11\n", encoding="utf-8", newline="")
        request["marker"]["path"] = str(decoy_marker)
    elif case == "handshake":
        request["handshake"]["release_timeout_seconds"] = 11
    else:
        request["registration"]["file_sha256"] = "f" * 64
    request["request_hash"] = module._self_hash(request, "request_hash")
    request_path.write_text(
        module._canonical_json(request) + "\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match=message):
        module.load_qualification_request(
            request_path,
            registration_path=registration_path,
        )


def test_qualification_request_rejects_duplicate_json_key(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, _request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    raw = request_path.read_text(encoding="utf-8")
    needle = f'"source_commit":"{SOURCE_COMMIT}"'
    request_path.write_text(
        raw.replace(needle, f'{needle},{needle}'),
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="duplicate JSON key"):
        module.load_qualification_request(
            request_path,
            registration_path=registration_path,
        )


def test_qualification_request_rejects_stale_attempt(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    Path(request["handshake"]["attempt_path"]).write_text(
        "{}\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="control artifact"):
        module.load_qualification_request(
            request_path,
            registration_path=registration_path,
        )


def test_qualification_request_rejects_unregistered_preexisting_file(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    (Path(request["qualification_root"]) / "unexpected.txt").write_text(
        "unexpected\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="inventory"):
        module.load_qualification_request(
            request_path,
            registration_path=registration_path,
        )


def test_qualification_request_rejects_registered_study_root(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, _request = (
        _qualification_request_fixture(tmp_path, monkeypatch)
    )
    (tmp_path / "study").mkdir()

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="forbidden"):
        module.load_qualification_request(
            request_path,
            registration_path=registration_path,
        )


def test_qualification_registration_must_be_committed_in_source_repository(tmp_path):
    module = _module()
    registration_path = (tmp_path / "registration.json").resolve()
    registration_path.write_text("{}\n", encoding="utf-8", newline="")

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="outside the source repository|not committed",
    ):
        module._require_committed_qualification_registration(
            registration_path,
            REPO_ROOT,
            SOURCE_COMMIT,
        )


def test_qualification_request_source_accepts_exact_tracked_commit_bytes(
    tmp_path,
    monkeypatch,
):
    module = _module()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir()
    request_source_path = (repo_root / "reviewed-request.json").resolve()
    committed_bytes = b'{"reviewed":true}\n'
    request_source_path.write_bytes(committed_bytes)
    observed_commands = []

    def fake_git_source_output(root, *arguments, binary=False, **_kwargs):
        observed_commands.append((root, arguments, binary))
        assert root == repo_root
        if arguments[0] == "ls-files":
            assert binary is False
            return "reviewed-request.json\n"
        assert arguments == (
            "show",
            f"{REVIEW_COMMIT}:reviewed-request.json",
        )
        assert binary is True
        return committed_bytes

    monkeypatch.setattr(
        module,
        "_qualification_git_source_output",
        fake_git_source_output,
    )

    module._require_committed_qualification_request_source(
        request_source_path,
        repo_root,
        REVIEW_COMMIT,
        committed_bytes,
    )

    assert len(observed_commands) == 2


@pytest.mark.parametrize(
    "case",
    ("outside", "untracked", "drift"),
)
def test_qualification_request_source_rejects_unreviewed_bytes(
    tmp_path,
    monkeypatch,
    case,
):
    module = _module()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir()
    request_source_path = (
        (tmp_path / "outside-request.json").resolve()
        if case == "outside"
        else (repo_root / "reviewed-request.json").resolve()
    )
    request_source_path.write_bytes(b'{"reviewed":false}\n')

    def fake_git_source_output(_root, *arguments, **_kwargs):
        if case == "untracked" and arguments[0] == "ls-files":
            raise module.OutcomeEvidenceRunnerError("not committed")
        if arguments[0] == "ls-files":
            return "reviewed-request.json\n"
        return b'{"reviewed":true}\n'

    monkeypatch.setattr(
        module,
        "_qualification_git_source_output",
        fake_git_source_output,
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match=(
            "outside the source repository|not committed|differs|"
            "review must follow|unrelated"
        ),
    ):
        module._require_committed_qualification_request_source(
            request_source_path,
            repo_root,
            REVIEW_COMMIT,
            b'{"reviewed":false}\n',
        )


@pytest.mark.parametrize(
    "case",
    (
        "clean",
        "registration_drift",
        "implementation_drift",
        "wrong_parent",
        "extra_diff",
    ),
)
def test_qualification_review_chain_allows_only_review_material_changes(
    tmp_path,
    monkeypatch,
    case,
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = (tmp_path / "registration.json").resolve()
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    request_source_path = (tmp_path / "reviewed-request.json").resolve()
    request_bytes = b'{"request":true}\n'
    request_source_path.write_bytes(request_bytes)
    review_head = REVIEW_COMMIT
    implementation_paths = registration.to_record()["integrity_rules"][
        "implementation_paths"
    ]
    implementation_sha256 = {
        relative_path: hashlib.sha256(
            (REPO_ROOT / relative_path).read_bytes()
        ).hexdigest()
        for relative_path in implementation_paths
    }
    registration_relative = registration_path.relative_to(REPO_ROOT).as_posix()
    request_source_relative = request_source_path.relative_to(REPO_ROOT).as_posix()
    drift_path = implementation_paths[0]
    request = {
        "implementation_sha256": implementation_sha256,
        "registration": {
            "canonical_hash": registration.registration_hash,
            "file_sha256": hashlib.sha256(
                registration_path.read_bytes()
            ).hexdigest(),
            "path": str(registration_path),
        },
        "request_hash": "e" * 64,
        "request_path": str((tmp_path / "active-request.json").resolve()),
        "request_source_path": str(request_source_path),
        "review_allowed_paths": [request_source_relative],
        "source_commit": SOURCE_COMMIT,
    }
    monkeypatch.setattr(
        module,
        "_tracked_source_commit",
        lambda _repo_root, **_kwargs: review_head,
    )
    monkeypatch.setattr(
        module,
        "_require_committed_qualification_request_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        module,
        "_require_committed_qualification_registration",
        lambda *_args, **_kwargs: None,
    )

    def committed_bytes(_repo_root, commit, relative_path, _label):
        if relative_path == registration_relative:
            if case == "registration_drift" and commit == REVIEW_COMMIT:
                return b"registration drift"
            return registration_path.read_bytes()
        if (
            case == "implementation_drift"
            and commit == REVIEW_COMMIT
            and relative_path == drift_path
        ):
            return b"implementation drift"
        return (REPO_ROOT / relative_path).read_bytes()

    monkeypatch.setattr(
        module,
        "_qualification_committed_bytes",
        committed_bytes,
    )
    monkeypatch.setattr(
        module,
        "_qualification_git_source_output",
        lambda _root, *arguments, **_kwargs: (
            (
                f"{REVIEW_COMMIT} "
                f"{('f' * 40) if case == 'wrong_parent' else SOURCE_COMMIT}\n"
            )
            if arguments[0] == "rev-list"
            else (
                f"{request_source_relative}\nreports/unreviewed.json\n"
                if case == "extra_diff"
                else f"{request_source_relative}\n"
            )
        ),
    )

    call = lambda: module._validate_qualification_review_chain(
        request=request,
        request_source_path=request_source_path,
        expected_request_bytes=request_bytes,
        expected_review_commit=REVIEW_COMMIT,
        expected_request_file_sha256=hashlib.sha256(request_bytes).hexdigest(),
        expected_request_size=len(request_bytes),
        registration=registration,
        registration_path=registration_path,
        implementation_sha256=implementation_sha256,
    )

    if case == "clean":
        review_binding = call()
        assert review_binding["source_commit"] == SOURCE_COMMIT
        assert review_binding["review_commit"] == REVIEW_COMMIT
        assert review_binding["request_source"]["file_sha256"] == (
            hashlib.sha256(request_bytes).hexdigest()
        )
    else:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match=(
                "registration changed|implementation changed|"
                "direct child|allowed path set"
            ),
        ):
            call()


@pytest.mark.parametrize(
    ("untracked_path", "allowed"),
    (
        ("reports/local-note.json", True),
        ("scripts/untracked_launcher.py", False),
        ("spirecomm/untracked_native.pyd", False),
        ("ops/untracked_launcher.ps1", False),
        ("ops/untracked_launcher.scr", False),
        ("ops/untracked_launcher", False),
    ),
)
def test_qualification_live_source_rejects_untracked_executable_paths(
    tmp_path,
    monkeypatch,
    untracked_path,
    allowed,
):
    module = _module()
    path = tmp_path / untracked_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"untracked")

    def fake_git_source_output(_repo_root, *arguments, **_kwargs):
        if arguments[0] == "status":
            return ""
        if arguments[0] == "rev-parse":
            return REVIEW_COMMIT + "\n"
        return b""

    monkeypatch.setattr(
        module,
        "_qualification_git_source_output",
        fake_git_source_output,
    )

    if allowed:
        assert module._tracked_source_commit(tmp_path) == REVIEW_COMMIT
    else:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="untracked executable",
        ):
            module._tracked_source_commit(tmp_path)


@pytest.mark.parametrize(
    "executable_path",
    (
        "ops/qualification-launch.ps1",
        "ops/qualification-launch.cmd",
        "ops/qualification-launch.pyz",
        "ops/qualification-launch.whl",
        "ops/qualification-launch.scr",
        "ops/qualification-launch",
    ),
)
def test_qualification_review_allowlist_rejects_all_executable_suffixes(
    executable_path,
):
    module = _module()
    request_source = "reports/qualification-request.json"

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="executable path",
    ):
        module._validate_qualification_review_allowed_paths(
            sorted((executable_path, request_source)),
            request_source_relative=request_source,
            protected_paths=set(),
        )


def test_qualification_live_source_rejects_ignored_importable_paths(tmp_path):
    module = _module()
    subprocess.run(
        ["git", "init", "--object-format=sha1", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    for key, value in (
        ("user.email", "guard@example.invalid"),
        ("user.name", "Guard Fixture"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", key, value],
            check=True,
            capture_output=True,
            text=True,
        )
    (tmp_path / ".gitignore").write_text(
        "*.pyc\n",
        encoding="utf-8",
        newline="",
    )
    (tmp_path / "tracked.txt").write_text(
        "tracked\n",
        encoding="utf-8",
        newline="",
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", ".gitignore", "tracked.txt"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "guard fixture"],
        check=True,
        capture_output=True,
        text=True,
    )
    (tmp_path / "ignored_module.pyc").write_bytes(b"unbound bytecode")

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="untracked executable",
    ):
        module._tracked_source_commit(tmp_path)


def test_qualification_live_source_rejects_untracked_directory_junction(
    tmp_path,
):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "tracked.txt").write_text(
        "tracked\n",
        encoding="utf-8",
        newline="",
    )
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "junction@example.invalid"),
        ("git", "config", "user.name", "Junction Fixture"),
        ("git", "add", "."),
        ("git", "commit", "-m", "source snapshot"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    target_path = tmp_path / "outside-source"
    target_path.mkdir()
    junction_path = repo_root / "ignored-junction"
    _create_directory_junction(junction_path, target_path)
    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="untracked executable paths.*ignored-junction",
        ):
            module._tracked_source_commit(repo_root)
    finally:
        os.rmdir(junction_path)


def test_qualification_root_inventory_rejects_directory_junction(tmp_path):
    module = _module()
    qualification_root = tmp_path / "qualification"
    qualification_root.mkdir()
    target_path = tmp_path / "outside-root"
    target_path.mkdir()
    (target_path / "outside.txt").write_text(
        "outside\n",
        encoding="utf-8",
        newline="",
    )
    junction_path = qualification_root / "linked-directory"
    _create_directory_junction(junction_path, target_path)
    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="symbolic link|reparse",
        ):
            module._qualification_root_inventory(
                qualification_root,
                excluded_paths=set(),
            )
    finally:
        os.rmdir(junction_path)


def test_qualification_request_rejects_root_junction_before_target_read(
    tmp_path,
    monkeypatch,
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    qualification_target = tmp_path / "qualification-target"
    qualification_target.mkdir()
    qualification_root = tmp_path / "qualification-junction"
    _create_directory_junction(qualification_root, qualification_target)
    qualification_id = f"{STUDY_ID}-qualification-r4"
    config_path = qualification_target / "qualification-config.json"
    config_path.write_text(
        json.dumps(
            {
                "category_rates_bps": {"card_reward": 300, "shop": 1000},
                "enabled_categories": ["card_reward", "shop"],
                "manifest_path": str(
                    qualification_target / "qualification-manifest.json"
                ),
                "per_run_alternative_budget": 2,
                "schema_version": "noncombat-exploration-config-v1",
                "seed": SEED_BASE + 1,
                "session_id": f"{qualification_id}-s01",
                "source_commit": SOURCE_COMMIT,
                "study_id": qualification_id,
                "study_registration_hash": registration.registration_hash,
                "study_run_lock_hash": "0" * 64,
                "study_slot_number": 1,
                "trace_path": str(
                    qualification_target / "qualification-trace.jsonl"
                ),
            },
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="",
    )
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8", newline="")
    monkeypatch.setattr(
        module,
        "_tracked_source_commit",
        lambda _repo_root, **_kwargs: SOURCE_COMMIT,
    )
    monkeypatch.setattr(
        module,
        "_require_committed_qualification_registration",
        lambda *_args, **_kwargs: None,
    )

    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="symbolic link|reparse",
        ):
            module.build_qualification_request(
                registration_path=registration_path,
                qualification_id=qualification_id,
                qualification_root=qualification_root,
                config_path=qualification_root / config_path.name,
                marker_path=marker_path,
                request_source_path=(
                    tmp_path / "reviewed-qualification-request.json"
                ),
                created_unix_ns=100,
            )
    finally:
        os.rmdir(qualification_root)


def test_qualification_request_source_rejects_junction_alias_before_read(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )
    )
    source_alias = tmp_path / "reviewed-source-alias"
    _create_directory_junction(source_alias, tmp_path)

    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="symbolic link|reparse",
        ):
            module.load_qualification_request_source(
                source_alias / request_source_path.name,
                registration_path=registration_path,
                expected_request_hash=request["request_hash"],
                **_qualification_review_kwargs(request),
            )
    finally:
        os.rmdir(source_alias)


def test_qualification_absence_check_rejects_dangling_junction(tmp_path):
    module = _module()
    target_path = tmp_path / "junction-target"
    target_path.mkdir()
    junction_path = tmp_path / "qualification-attempt.json"
    _create_directory_junction(junction_path, target_path)
    target_path.rmdir()
    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="control artifact",
        ):
            module._require_paths_absent(
                (junction_path,),
                "qualification control artifact exists",
            )
    finally:
        os.rmdir(junction_path)


def test_qualification_live_source_rejects_git_warning(
    tmp_path,
    monkeypatch,
):
    module = _module()
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["git"],
            returncode=0,
            stdout="",
            stderr="warning: source traversal incomplete",
        ),
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="source traversal incomplete",
    ):
        module._tracked_source_commit(tmp_path)


def test_qualification_git_uses_pinned_absolute_executable(
    tmp_path,
    monkeypatch,
):
    module = _module()
    (tmp_path / ".git").mkdir()
    observed = {}

    def run(command, **_kwargs):
        observed["command"] = list(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", run)

    module._qualification_git_source_output(tmp_path, "status")

    executable = Path(observed["command"][0])
    assert executable.is_absolute()
    assert executable == module.QUALIFICATION_GIT_EXECUTABLE


def test_qualification_git_uses_sterile_environment(tmp_path, monkeypatch):
    module = _module()
    (tmp_path / ".git").mkdir()
    observed = {}
    monkeypatch.setenv("GIT_DIR", r"C:\untrusted-git")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", r"C:\untrusted.gitconfig")
    monkeypatch.setenv("HOME", r"C:\untrusted-home")

    def run(command, **kwargs):
        observed["command"] = list(command)
        observed["environment"] = dict(kwargs["env"])
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", run)

    module._qualification_git_source_output(tmp_path, "status")

    assert "--no-replace-objects" in observed["command"]
    assert "--no-lazy-fetch" in observed["command"]
    assert "core.fsmonitor=false" in observed["command"]
    assert observed["environment"]["GIT_DIR"] == str(tmp_path / ".git")
    assert observed["environment"]["GIT_WORK_TREE"] == str(tmp_path)
    assert "HOME" not in observed["environment"]
    assert observed["environment"]["GIT_CONFIG_NOSYSTEM"] == "1"
    assert observed["environment"]["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert observed["environment"]["GIT_NO_LAZY_FETCH"] == "1"


def test_qualification_git_ignores_ambient_work_tree(tmp_path, monkeypatch):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    tracked_path = repo_root / "tracked.txt"
    tracked_path.write_text("source\n", encoding="utf-8", newline="")
    subprocess.run(
        ["git", "add", "tracked.txt"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "source"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    )
    shadow_work_tree = tmp_path / "shadow-work-tree"
    shadow_work_tree.mkdir()
    (shadow_work_tree / "tracked.txt").write_text(
        "source\n",
        encoding="utf-8",
        newline="",
    )
    tracked_path.write_text("drift\n", encoding="utf-8", newline="")
    monkeypatch.setenv("GIT_WORK_TREE", str(shadow_work_tree))

    status = module._qualification_git_source_output(
        repo_root,
        "status",
        "--short",
        "--untracked-files=no",
    )

    assert "tracked.txt" in status


@pytest.mark.parametrize(
    "index_flag",
    ("--assume-unchanged", "--skip-worktree"),
)
def test_qualification_source_rejects_hidden_git_index_flags(
    tmp_path,
    index_flag,
):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tracked_path = repo_root / "tracked.py"
    tracked_path.write_text("VALUE = 'reviewed'\n", encoding="utf-8", newline="")
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "tracked.py"),
        ("git", "commit", "-m", "source"),
        ("git", "update-index", index_flag, "tracked.py"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    tracked_path.write_text(
        "VALUE = 'unreviewed'\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="index flag|assume|skip-worktree",
    ):
        module._tracked_source_commit(repo_root)


def test_qualification_source_rejects_clean_filter_before_execution(tmp_path):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tracked_path = repo_root / "tracked.txt"
    tracked_path.write_text("reviewed\n", encoding="utf-8", newline="")
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "tracked.txt"),
        ("git", "commit", "-m", "source"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    marker_path = tmp_path / "clean-filter-executed.txt"
    filter_path = tmp_path / "clean_filter.py"
    filter_path.write_text(
        "import pathlib,sys\n"
        f"pathlib.Path({str(marker_path)!r}).write_text('executed')\n"
        "sys.stdout.buffer.write(sys.stdin.buffer.read())\n",
        encoding="utf-8",
        newline="",
    )
    filter_command = f'"{sys.executable}" "{filter_path}"'
    subprocess.run(
        ["git", "config", "filter.sideeffect.clean", filter_command],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    )
    info_attributes = repo_root / ".git" / "info" / "attributes"
    info_attributes.write_text(
        "tracked.txt filter=sideeffect\n",
        encoding="utf-8",
        newline="",
    )
    tracked_path.write_text("drifted\n", encoding="utf-8", newline="")

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="unsafe|attribute"):
        module._tracked_source_commit(repo_root)

    assert not marker_path.exists()


def test_qualification_git_rejects_promisor_helper_before_missing_blob_fetch(
    tmp_path,
):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tracked_path = repo_root / "tracked.py"
    tracked_path.write_text("VALUE = 'reviewed'\n", encoding="utf-8", newline="")
    for command in (
        ("git", "init", "--object-format=sha1"),
        ("git", "config", "user.email", "runner@example.invalid"),
        ("git", "config", "user.name", "Runner Fixture"),
        ("git", "add", "tracked.py"),
        ("git", "commit", "-m", "source"),
    ):
        subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    blob_oid = subprocess.run(
        ("git", "rev-parse", "HEAD:tracked.py"),
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    object_path = repo_root / ".git" / "objects" / blob_oid[:2] / blob_oid[2:]
    assert object_path.is_file()
    os.chmod(object_path, 0o666)
    object_path.unlink()
    marker_path = tmp_path / "promisor-helper-executed.txt"
    helper_path = tmp_path / "promisor-helper.cmd"
    helper_path.write_text(
        f'@echo executed>"{marker_path}"\r\n@exit /b 1\r\n',
        encoding="utf-8",
        newline="",
    )
    for key, value in (
        ("extensions.partialClone", "origin"),
        ("remote.origin.promisor", "true"),
        ("remote.origin.partialCloneFilter", "blob:none"),
        ("protocol.ext.allow", "always"),
        ("remote.origin.url", f"ext::{helper_path}"),
    ):
        subprocess.run(
            ("git", "config", key, value),
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="unsafe.*directive",
    ):
        module._qualification_git_source_output(
            repo_root,
            "show",
            "HEAD:tracked.py",
        )

    assert not marker_path.exists()


def test_qualification_git_rejects_metadata_junction_before_run(
    tmp_path,
    monkeypatch,
):
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    metadata_target = tmp_path / "metadata-target"
    metadata_target.mkdir()
    metadata_path = repo_root / ".git"
    _create_directory_junction(metadata_path, metadata_target)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "Git ran before metadata validation"
        ),
    )

    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="symbolic link|reparse",
        ):
            module._qualification_git_source_output(repo_root, "status")
    finally:
        os.rmdir(metadata_path)


def test_qualification_git_rejects_grafts_before_run(tmp_path, monkeypatch):
    module = _module()
    git_root = tmp_path / ".git"
    (git_root / "info").mkdir(parents=True)
    (git_root / "info" / "grafts").write_text(
        "a" * 40 + " " + "b" * 40 + "\n",
        encoding="ascii",
        newline="",
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "Git ran with graft metadata present"
        ),
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="graft"):
        module._qualification_git_source_output(tmp_path, "status")


@pytest.mark.parametrize(
    "metadata_relative_path",
    (
        "commondir",
        "objects/info/alternates",
        "objects/info/http-alternates",
    ),
)
def test_qualification_git_rejects_metadata_indirection_before_run(
    tmp_path,
    monkeypatch,
    metadata_relative_path,
):
    module = _module()
    metadata_path = tmp_path / ".git" / metadata_relative_path
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        r"C:\untrusted-git-metadata" + "\n",
        encoding="utf-8",
        newline="",
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "Git ran with metadata indirection present"
        ),
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="indirection",
    ):
        module._qualification_git_source_output(tmp_path, "status")


@pytest.mark.parametrize("config_name", ("config", "config.worktree"))
def test_qualification_git_rejects_spaced_external_config_before_run(
    tmp_path,
    monkeypatch,
    config_name,
):
    module = _module()
    config_path = tmp_path / ".git" / config_name
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "[diff]\n\texternal    = untrusted-command\n",
        encoding="utf-8",
        newline="",
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "Git ran with unsafe repository config"
        ),
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="unsafe"):
        module._qualification_git_source_output(tmp_path, "status")


@pytest.mark.parametrize(
    "config_text",
    (
        "[extensions]\n\tpartialClone = origin\n",
        '[remote "origin"]\n\tpromisor = true\n',
        '[protocol "ext"]\n\tallow = always\n',
    ),
)
def test_qualification_git_rejects_lazy_fetch_config_before_run(
    tmp_path,
    monkeypatch,
    config_text,
):
    module = _module()
    config_path = tmp_path / ".git" / "config"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config_text, encoding="utf-8", newline="")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "Git ran with lazy-fetch repository config"
        ),
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="unsafe"):
        module._qualification_git_source_output(tmp_path, "status")


def test_qualify_command_rejects_registration_junction_before_load(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )
    )
    registration_alias = tmp_path / "registration-alias"
    _create_directory_junction(registration_alias, tmp_path)
    monkeypatch.setattr(
        module,
        "execute_prelock_qualification",
        lambda **_kwargs: {"status": "unexpected"},
    )

    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="symbolic link|reparse",
        ):
            module._qualify_command(
                registration_alias / registration_path.name,
                request_source_path,
                request["request_hash"],
                hashlib.sha256(request_source_path.read_bytes()).hexdigest(),
                request_source_path.stat().st_size,
                REVIEW_COMMIT,
            )
    finally:
        os.rmdir(registration_alias)


def test_qualification_safe_marker_count_does_not_follow_junction(tmp_path):
    module = _module()
    marker_target = tmp_path / "marker-target"
    marker_target.mkdir()
    (marker_target / "ai_games.txt").write_text(
        "10\n11\n",
        encoding="utf-8",
        newline="",
    )
    marker_parent = tmp_path / "marker-parent"
    _create_directory_junction(marker_parent, marker_target)

    try:
        assert module._safe_marker_count(
            marker_parent / "ai_games.txt"
        ) is None
    finally:
        os.rmdir(marker_parent)


def test_qualification_live_source_rejects_filesystem_walk_error(
    tmp_path,
    monkeypatch,
):
    module = _module()

    def fail_walk(*_args, **_kwargs):
        raise PermissionError("source directory denied")

    monkeypatch.setattr(module.os, "scandir", fail_walk)

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="source directory denied",
    ):
        module._qualification_untracked_executable_paths(
            tmp_path,
            tracked_paths=set(),
        )


def _ledger(tmp_path):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    ledger = module.StudyLedger(
        path=tmp_path / "study" / "ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)
    return ledger, registration


class _FakeHandshakeChild:
    def __init__(self, *, pid=321, exit_code=0, initial_returncode=None, on_wait=None):
        self.pid = pid
        self.exit_code = exit_code
        self.returncode = initial_returncode
        self.on_wait = on_wait
        self.terminated = False
        self.killed = False
        self.wait_calls = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if self.on_wait is not None:
            callback, self.on_wait = self.on_wait, None
            callback()
        if self.returncode is not None:
            return self.returncode
        self.returncode = self.exit_code
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_qualification_ready_guard_runs_before_handshake_loader(
    tmp_path,
    monkeypatch,
):
    module = _module()
    ready_target = tmp_path / "ready-target"
    ready_target.mkdir()
    ready_path = tmp_path / "qualification-ready.json"
    _create_directory_junction(ready_path, ready_target)
    monkeypatch.setattr(
        module,
        "load_ready_record",
        lambda _path: pytest.fail("ready loader followed an unguarded path"),
    )

    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="symbolic link|reparse",
        ):
            module._wait_for_child_readiness(
                process=_FakeHandshakeChild(initial_returncode=None),
                child_pid=321,
                attempt={},
                ready_path=ready_path,
                ready_path_validator=lambda path: (
                    module._qualification_require_no_follow_path(
                        path,
                        "ready artifact",
                        expected_kind="file",
                    )
                ),
                timeout_seconds=120,
                monotonic=lambda: 0.0,
                sleep=lambda _seconds: None,
            )
    finally:
        os.rmdir(ready_path)


def test_qualification_runner_rejects_unc_before_filesystem_probe(
    monkeypatch,
):
    module = _module()
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _path: pytest.fail("qualification attempted a UNC probe"),
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="UNC|local drive",
    ):
        module._qualification_require_no_follow_path(
            r"\\qualification.invalid\share\ready.json",
            "ready artifact",
            expected_kind="file",
        )


def test_qualification_runner_rejects_ads_before_filesystem_probe(
    tmp_path,
    monkeypatch,
):
    module = _module()
    source_path = tmp_path / "ready.json"
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _path: pytest.fail("qualification attempted an ADS probe"),
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="alternate data stream",
    ):
        module._qualification_require_no_follow_path(
            f"{source_path}:qualification-ready",
            "ready artifact",
            expected_kind="file",
            allow_missing=True,
        )


def test_qualification_bootstrap_rejects_ads_before_filesystem_probe(
    tmp_path,
    monkeypatch,
):
    module = _module()
    source_path = tmp_path / "request.json"
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _path: pytest.fail("qualification attempted an ADS probe"),
    )

    with pytest.raises(
        module._QualificationBootstrapError,
        match="alternate data stream",
    ):
        module._qualification_bootstrap_require_path(
            f"{source_path}:qualification-request",
            "request source",
            expected_kind="file",
        )


@pytest.mark.parametrize("suffix", [".", " "])
def test_qualification_runner_rejects_win32_alias_before_filesystem_probe(
    tmp_path,
    monkeypatch,
    suffix,
):
    module = _module()
    source_path = tmp_path / f"ready.json{suffix}"
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _path: pytest.fail("qualification attempted an alias probe"),
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="Win32 alias",
    ):
        module._qualification_require_no_follow_path(
            source_path,
            "ready artifact",
            expected_kind="file",
            allow_missing=True,
        )


def _handshake_slot(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    module.write_slot_config_once(launch)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8")
    return module, ledger, registration, run_lock, launch, marker_path


def _publish_ready_from_environment(environment, *, child_pid, mutate=None):
    attempt = load_attempt_record(Path(environment[HANDSHAKE_ATTEMPT_ENV]))
    ready = build_ready_record(
        attempt,
        child_pid=child_pid,
        created_unix_ns=attempt["created_unix_ns"] + 1,
    )
    if mutate is not None:
        ready = mutate(attempt, ready)
    publish_handshake_record_once(Path(attempt["ready_path"]), ready)
    return attempt


def test_qualification_orchestrator_accepts_ready_published_during_owned_start(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    forbidden_study_path = lambda *_args, **_kwargs: pytest.fail(
        "qualification entered a registered study path"
    )
    monkeypatch.setattr(module, "_start_command", forbidden_study_path)
    monkeypatch.setattr(module, "StudyLedger", forbidden_study_path)
    monkeypatch.setattr(
        module,
        "execute_handshaken_registered_slot",
        forbidden_study_path,
    )
    events = []
    release_path = Path(request["handshake"]["release_path"])

    def observe_release_and_exit():
        assert release_path.is_file()
        events.extend(("release", "exit"))

    child = _FakeHandshakeChild(pid=321, on_wait=observe_release_and_exit)

    def process_starter(command, environment):
        assert list(command) == request["child_command"]
        assert Path(request["handshake"]["attempt_path"]).is_file()
        events.append("start")
        attempt = _publish_ready_from_environment(
            environment,
            child_pid=child.pid,
        )
        assert environment[module.QUALIFICATION_ATTEMPT_HASH_ENV] == (
            attempt["attempt_hash"]
        )
        assert environment[module.QUALIFICATION_LOG_PATH_ENV] == os.devnull
        assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
        events.append("ready")
        return child

    timestamps = iter(range(200, 220))
    result = module.execute_prelock_qualification(
        registration_path=registration_path,
        request_path=request_path,
        expected_request_hash=request["request_hash"],
        **_qualification_review_kwargs(request),
        process_starter=process_starter,
        time_ns=lambda: next(timestamps),
    )

    assert events == ["start", "ready", "release", "exit"]
    assert result["status"] == "passed"
    assert result["schema_version"] == (
        "noncombat-outcome-evidence-qualification-result-v3"
    )
    assert result["isolation"]["baseline_hash"] == (
        request["isolation"]["baseline_hash"]
    )
    assert result["isolation"]["communication_restored"] is True
    assert result["isolation"]["child_alive"] is False
    assert result["isolation"]["matched"] is True
    assert result["isolation"]["mismatches"] == []
    assert (tmp_path / "config.properties").read_bytes() == base64.b64decode(
        request["isolation"]["communication_mod"]["original_bytes_b64"],
        validate=True,
    )
    assert result["process"] == {
        "cleanup_attempted": False,
        "cleanup_error": None,
        "exit_code": 0,
        "launch_count": 1,
        "pid": child.pid,
    }
    assert all(result["handshake"][name]["sha256"] for name in (
        "attempt",
        "ready",
        "release",
    ))
    assert set(result["authority"].values()) == {False}
    assert Path(request["completion_path"]).is_file()
    assert not Path(request["failure_path"]).exists()
    numeric_authority = json.loads(json.dumps(result))
    numeric_authority["authority"]["study_start"] = 0
    numeric_authority["result_hash"] = module._self_hash(
        numeric_authority,
        "result_hash",
    )
    with pytest.raises(module.OutcomeEvidenceRunnerError, match="authority"):
        module._validate_qualification_result(numeric_authority)
    relabelled_failure = json.loads(json.dumps(result))
    relabelled_failure["status"] = "failed"
    relabelled_failure["failure"] = {
        "exception_type": "RuntimeError",
        "message": "invented failure",
        "stage": "wait_for_qualification_exit",
    }
    relabelled_failure["result_hash"] = module._self_hash(
        relabelled_failure,
        "result_hash",
    )
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="failed result does not contradict success evidence",
    ):
        module._validate_qualification_result(relabelled_failure)
    forged_launch_count = json.loads(json.dumps(relabelled_failure))
    forged_launch_count["process"]["launch_count"] = 0
    forged_launch_count["result_hash"] = module._self_hash(
        forged_launch_count,
        "result_hash",
    )
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="launch|process",
    ):
        module._validate_qualification_result(forged_launch_count)
    forged_missing_attempt = json.loads(json.dumps(relabelled_failure))
    for name in ("attempt", "ready", "release"):
        forged_missing_attempt["handshake"][name]["sha256"] = None
    forged_missing_attempt["result_hash"] = module._self_hash(
        forged_missing_attempt,
        "result_hash",
    )
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="attempt|launch",
    ):
        module._validate_qualification_result(forged_missing_attempt)
    active_request_path = Path(request["request_path"])
    reordered_request = json.loads(
        active_request_path.read_text(encoding="utf-8")
    )
    reordered_request["created_unix_ns"] = result["ended_unix_ns"] + 1
    reordered_request["request_hash"] = module._self_hash(
        reordered_request,
        "request_hash",
    )
    active_request_path.write_text(
        module._canonical_json(reordered_request) + "\n",
        encoding="utf-8",
        newline="",
    )
    reordered_result = json.loads(json.dumps(result))
    reordered_result["request"]["hash"] = reordered_request["request_hash"]
    reordered_bytes = (
        module._canonical_json(reordered_request) + "\n"
    ).encode("utf-8")
    reordered_file_hash = hashlib.sha256(reordered_bytes).hexdigest()
    for binding_name in ("request_source", "active_request"):
        reordered_result["review_binding"][binding_name][
            "request_hash"
        ] = reordered_request["request_hash"]
        reordered_result["review_binding"][binding_name][
            "file_sha256"
        ] = reordered_file_hash
        reordered_result["review_binding"][binding_name]["size"] = len(
            reordered_bytes
        )
    reordered_result["review_binding"]["review_binding_hash"] = (
        module._self_hash(
            reordered_result["review_binding"],
            "review_binding_hash",
        )
    )
    reordered_result["result_hash"] = module._self_hash(
        reordered_result,
        "result_hash",
    )
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="lifecycle timestamp order",
    ):
        module._validate_qualification_result(reordered_result)
    active_request_path.write_text(
        module._canonical_json(request) + "\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap lifecycle",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda _command, _environment: pytest.fail(
                "completed qualification retried a child"
            ),
        )


@pytest.mark.parametrize(
    "case",
    ("child_alive", "restoration_error", "observation_error", "unmatched_exact"),
)
def test_qualification_result_rejects_contradictory_isolation_evidence(
    tmp_path,
    monkeypatch,
    case,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    child = _FakeHandshakeChild(pid=327)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(700, 740))
    result = module.execute_prelock_qualification(
        registration_path=registration_path,
        request_path=request_path,
        expected_request_hash=request["request_hash"],
        **_qualification_review_kwargs(request),
        process_starter=process_starter,
        time_ns=lambda: next(timestamps),
    )
    forged = json.loads(json.dumps(result))
    forged["status"] = "failed"
    forged["failure"] = {
        "exception_type": "RuntimeError",
        "message": "invented isolation failure",
        "stage": "restore_isolation",
    }
    forged["isolation"]["matched"] = False
    if case == "child_alive":
        forged["isolation"]["child_alive"] = True
    elif case == "restoration_error":
        forged["isolation"]["restoration_error"] = "invented restore error"
    elif case == "observation_error":
        forged["isolation"]["observation_error"] = "invented observe error"
    forged["result_hash"] = module._self_hash(forged, "result_hash")

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="isolation"):
        module._validate_qualification_result(forged)


def test_qualification_rejects_run_drift_before_attempt_publication(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    (tmp_path / "runs" / "IRONCLAD" / "100.run").write_bytes(
        b'{"drift":true}\n'
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="isolation.*run|run.*isolation",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args, **_kwargs: pytest.fail(
                "qualification launched after preflight isolation drift"
            ),
        )

    assert not Path(request["request_path"]).exists()
    assert not Path(request["handshake"]["attempt_path"]).exists()
    assert not Path(request["failure_path"]).exists()


@pytest.mark.parametrize(
    "resource",
    ("marker", "checkpoints", "ai_debug_log", "communication_error_log"),
)
def test_qualification_rejects_other_isolation_drift_before_attempt(
    tmp_path,
    monkeypatch,
    resource,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    baseline = request["isolation"]
    if resource == "marker":
        Path(baseline["marker"]["path"]).write_text(
            "10\n11\n12\n",
            encoding="utf-8",
            newline="",
        )
    elif resource == "checkpoints":
        (
            Path(baseline["checkpoints"]["root"]) / "rl_model_ep1.pth"
        ).write_bytes(b"checkpoint-drift\n")
    else:
        suffix = (
            "ai_debug.log"
            if resource == "ai_debug_log"
            else "communication_mod_errors.log"
        )
        log_path = next(
            Path(path)
            for path in baseline["global_logs"]
            if Path(path).name == suffix
        )
        log_path.write_bytes(b"prelaunch log drift\n")

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="prelaunch isolation mismatch|isolation marker count mismatch",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args, **_kwargs: pytest.fail(
                "qualification launched after preflight isolation drift"
            ),
        )

    assert not Path(request["request_path"]).exists()
    assert not Path(request["handshake"]["attempt_path"]).exists()
    assert not Path(request["failure_path"]).exists()


def test_qualification_restores_live_communication_config_exactly(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    launch_command = ("python.exe", "-I", "-S", "qualification")
    communication_path = tmp_path / "config.properties"
    communication_path.write_bytes(
        (
            "verbose=false\n"
            f"command={' '.join(launch_command)}\n"
            "runAtGameStart=true\n"
        ).encode("iso-8859-1")
    )
    child = _FakeHandshakeChild(pid=322)

    def process_starter(_command, environment):
        _publish_ready_from_environment(
            environment,
            child_pid=child.pid,
        )
        return child

    timestamps = iter(range(300, 320))
    result = module.execute_prelock_qualification(
        registration_path=registration_path,
        request_path=request_path,
        expected_request_hash=request["request_hash"],
        **_qualification_review_kwargs(request),
        process_starter=process_starter,
        qualification_launch_command=launch_command,
        time_ns=lambda: next(timestamps),
    )

    assert result["status"] == "passed"
    assert communication_path.read_bytes() == base64.b64decode(
        request["isolation"]["communication_mod"]["original_bytes_b64"],
        validate=True,
    )


def test_qualification_restoration_rejects_parent_identity_change(
    tmp_path,
    monkeypatch,
):
    module, _registration_path, _request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    original_samestat = module.os.path.samestat

    def reject_directory_identity(left, right):
        if module.stat.S_ISDIR(left.st_mode):
            return False
        return original_samestat(left, right)

    monkeypatch.setattr(
        module.os.path,
        "samestat",
        reject_directory_identity,
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="parent changed during restoration",
    ):
        module._qualification_restore_communication_config(
            request["isolation"]
        )


def test_qualification_restores_communication_config_after_ordinary_failure(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    launch_command = ("python.exe", "-I", "-S", "qualification")
    communication_path = tmp_path / "config.properties"
    communication_path.write_bytes(
        (
            "verbose=false\n"
            f"command={' '.join(launch_command)}\n"
            "runAtGameStart=true\n"
        ).encode("iso-8859-1")
    )
    child = _FakeHandshakeChild(pid=324)
    clock = [0.0]

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="readiness"):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda _command, _environment: child,
            qualification_launch_command=launch_command,
            monotonic=lambda: clock[0],
            sleep=lambda _seconds: clock.__setitem__(0, 121.0),
        )

    assert communication_path.read_bytes() == base64.b64decode(
        request["isolation"]["communication_mod"]["original_bytes_b64"],
        validate=True,
    )
    failure = json.loads(Path(request["failure_path"]).read_text(encoding="utf-8"))
    assert failure["isolation"]["communication_restored"] is True
    assert failure["isolation"]["child_alive"] is False


def test_qualification_rejects_global_log_drift_after_child_exit(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )

    def mutate_log_after_release():
        assert Path(request["handshake"]["release_path"]).is_file()
        (tmp_path / "ai_debug.log").write_bytes(b"unexpected log output\n")

    child = _FakeHandshakeChild(pid=323, on_wait=mutate_log_after_release)

    def process_starter(_command, environment):
        _publish_ready_from_environment(
            environment,
            child_pid=child.pid,
        )
        return child

    timestamps = iter(range(400, 440))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="isolation.*global|global.*log|post.*isolation",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            time_ns=lambda: next(timestamps),
        )

    assert not Path(request["completion_path"]).exists()
    assert Path(request["failure_path"]).is_file()


@pytest.mark.parametrize(
    "resource",
    ("marker", "runs", "checkpoints", "communication_error_log"),
)
def test_qualification_rejects_other_isolation_drift_after_child_exit(
    tmp_path,
    monkeypatch,
    resource,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    baseline = request["isolation"]

    def mutate_after_release():
        assert Path(request["handshake"]["release_path"]).is_file()
        if resource == "marker":
            Path(baseline["marker"]["path"]).write_text(
                "10\n11\n12\n",
                encoding="utf-8",
                newline="",
            )
        elif resource == "runs":
            (
                Path(baseline["runs"]["root"]) / "IRONCLAD" / "100.run"
            ).write_bytes(b'{"drift":true}\n')
        elif resource == "checkpoints":
            (
                Path(baseline["checkpoints"]["root"]) / "rl_model_ep1.pth"
            ).write_bytes(b"checkpoint-drift\n")
        else:
            log_path = next(
                Path(path)
                for path in baseline["global_logs"]
                if Path(path).name == "communication_mod_errors.log"
            )
            log_path.write_bytes(b"post-exit log drift\n")

    child = _FakeHandshakeChild(pid=325, on_wait=mutate_after_release)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(500, 540))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="post isolation mismatch|post_exit_validation.*partial",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            time_ns=lambda: next(timestamps),
        )

    assert not Path(request["completion_path"]).exists()
    if resource == "marker":
        assert not Path(request["failure_path"]).exists()
    else:
        assert Path(request["failure_path"]).is_file()


def test_qualification_rejects_child_that_remains_alive_after_zero_exit(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )

    class StubbornChild(_FakeHandshakeChild):
        def wait(self, timeout=None):
            self.wait_calls.append(timeout)
            if self.on_wait is not None:
                callback, self.on_wait = self.on_wait, None
                callback()
            return 0

    child = StubbornChild(pid=326)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(600, 640))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="post isolation mismatch.*child_process",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            time_ns=lambda: next(timestamps),
        )

    assert child.terminated is True
    assert not Path(request["completion_path"]).exists()
    assert Path(request["failure_path"]).is_file()


def test_qualification_pre_release_uses_bounded_live_source_validation(
    tmp_path,
    monkeypatch,
):
    module, registration_path, reviewed_request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    release_path = Path(request["handshake"]["release_path"])
    active_request_path = Path(request["request_path"])
    original_review = module._validate_qualification_review_chain

    def guard_immutable_review(**kwargs):
        if active_request_path.exists() and not release_path.exists():
            pytest.fail("pre-release path replayed immutable S/R Git blobs")
        return original_review(**kwargs)

    live_calls = []

    def validate_live_review(**kwargs):
        live_calls.append(kwargs)
        assert kwargs["deadline"] == 7.0
        assert kwargs["monotonic"]() == 2.0

    monkeypatch.setattr(
        module,
        "_validate_qualification_review_chain",
        guard_immutable_review,
    )
    monkeypatch.setattr(
        module,
        "_validate_qualification_live_review_boundaries",
        validate_live_review,
        raising=False,
    )
    child = _FakeHandshakeChild(pid=654, exit_code=0)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(250, 280))
    result = module.execute_prelock_qualification(
        registration_path=registration_path,
        request_path=reviewed_request_path,
        expected_request_hash=request["request_hash"],
        **_qualification_review_kwargs(request),
        process_starter=process_starter,
        monotonic=lambda: 2.0,
        time_ns=lambda: next(timestamps),
    )

    assert result["status"] == "passed"
    assert len(live_calls) == 1
    assert live_calls[0]["request"] == request
    assert release_path.is_file()


def test_qualification_git_metadata_scan_receives_release_deadline(
    tmp_path,
    monkeypatch,
):
    module = _module()
    (tmp_path / ".git").mkdir()
    observed = {}

    def bounded_scan(_root, **kwargs):
        observed.update(kwargs)
        raise module.OutcomeEvidenceRunnerError(
            "qualification live source validation exceeded its release budget"
        )

    monkeypatch.setattr(
        module,
        "_qualification_no_follow_entries",
        bounded_scan,
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "Git ran after metadata scan exhausted its budget"
        ),
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="release budget"):
        module._qualification_git_source_output(
            tmp_path,
            "status",
            deadline=7.0,
            monotonic=lambda: 2.0,
        )

    assert observed["deadline"] == 7.0
    assert observed["monotonic"]() == 2.0


def test_qualification_root_inventory_hash_receives_release_deadline(
    tmp_path,
    monkeypatch,
):
    module = _module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text("{}\n", encoding="utf-8", newline="")
    observed = {}

    def bounded_hash(_path, _label, **kwargs):
        observed.update(kwargs)
        raise module.OutcomeEvidenceRunnerError(
            "qualification live source validation exceeded its release budget"
        )

    monkeypatch.setattr(module, "_path_sha256", bounded_hash)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="release budget"):
        module._qualification_root_inventory(
            tmp_path,
            excluded_paths=set(),
            deadline=7.0,
            monotonic=lambda: 2.0,
        )

    assert observed["deadline"] == 7.0
    assert observed["monotonic"]() == 2.0


def test_qualification_pre_release_budget_uses_ready_timestamp(
    tmp_path,
    monkeypatch,
):
    module, registration_path, reviewed_request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    captured_deadlines = []

    def capture_live_deadline(**kwargs):
        captured_deadlines.append(kwargs["deadline"])
        raise module.OutcomeEvidenceRunnerError("stop after budget capture")

    monkeypatch.setattr(
        module,
        "_validate_qualification_live_review_boundaries",
        capture_live_deadline,
    )
    child = _FakeHandshakeChild(pid=655, exit_code=0)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(
        (
            1_000_000_000,
            9_000_000_000,
            10_000_000_000,
            11_000_000_000,
        )
    )
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="stop after budget capture",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=reviewed_request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            monotonic=lambda: 2.0,
            time_ns=lambda: next(timestamps),
        )

    assert captured_deadlines == [pytest.approx(4.000000001)]
    assert not Path(request["handshake"]["release_path"]).exists()


def test_qualification_pre_release_rejects_budget_expiry_after_source_check(
    tmp_path,
    monkeypatch,
):
    module, registration_path, reviewed_request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    clock = [2.0]

    def exhaust_budget(**_kwargs):
        clock[0] = 7.0

    monkeypatch.setattr(
        module,
        "_validate_qualification_live_review_boundaries",
        exhaust_budget,
    )
    child = _FakeHandshakeChild(pid=656, exit_code=0)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(260, 290))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="release budget",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=reviewed_request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            monotonic=lambda: clock[0],
            time_ns=lambda: next(timestamps),
        )

    failure = json.loads(
        Path(request["failure_path"]).read_text(encoding="utf-8")
    )
    assert failure["failure"]["stage"] == "pre_release_validation"
    assert not Path(request["handshake"]["release_path"]).exists()


def test_qualification_pre_release_rechecks_budget_immediately_before_release(
    tmp_path,
    monkeypatch,
):
    module, registration_path, reviewed_request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    clock = [2.0]
    original_require_child_running = module._require_child_running

    def exhaust_budget_before_release(process, *, stage):
        original_require_child_running(process, stage=stage)
        if stage == "qualification release":
            clock[0] = 7.0

    monkeypatch.setattr(
        module,
        "_require_child_running",
        exhaust_budget_before_release,
    )
    child = _FakeHandshakeChild(pid=657, exit_code=0)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(270, 300))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="release budget",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=reviewed_request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            monotonic=lambda: clock[0],
            time_ns=lambda: next(timestamps),
        )

    assert not Path(request["handshake"]["release_path"]).exists()


def test_qualification_publishes_reviewed_request_once_before_launch(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )
    )
    child = _FakeHandshakeChild(pid=323)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(280, 310))
    result = module.execute_prelock_qualification(
        registration_path=registration_path,
        request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
        time_ns=lambda: next(timestamps),
    )

    active_request_path = Path(request["request_path"])
    assert result["status"] == "passed"
    assert active_request_path.read_bytes() == request_source_path.read_bytes()

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="request.*already exists|control artifact",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args: pytest.fail(
                "consumed request launched another child"
            ),
        )


def test_qualification_request_only_host_crash_cannot_be_retried(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )
    )
    active_request_path = Path(request["request_path"])
    real_load = module.load_qualification_request

    def crash_after_active_request(path, **kwargs):
        if Path(path).resolve() == active_request_path:
            raise SystemExit("simulated host crash after request publication")
        return real_load(path, **kwargs)

    monkeypatch.setattr(
        module,
        "load_qualification_request",
        crash_after_active_request,
    )
    with pytest.raises(SystemExit, match="simulated host crash"):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args: pytest.fail(
                "request-only crash started a child"
            ),
        )

    assert active_request_path.is_file()
    assert not Path(request["handshake"]["attempt_path"]).exists()
    assert not Path(request["completion_path"]).exists()
    assert not Path(request["failure_path"]).exists()

    monkeypatch.setattr(module, "load_qualification_request", real_load)
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="bootstrap lifecycle",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args: pytest.fail(
                "request-only identity launched another child"
            ),
        )


def test_qualification_rejects_unreviewed_request_hash_before_publication(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="reviewed hash",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash="f" * 64,
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args: pytest.fail(
                "unreviewed request launched a child"
            ),
        )

    assert not Path(request["request_path"]).exists()
    assert not Path(request["handshake"]["attempt_path"]).exists()


@pytest.mark.parametrize("case", ("review_commit", "file_hash", "size"))
def test_qualification_rejects_external_review_anchor_drift_before_publication(
    tmp_path,
    monkeypatch,
    case,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(
            tmp_path,
            monkeypatch,
            source_only=True,
        )
    )
    review = _qualification_review_kwargs(request)
    if case == "review_commit":
        review["expected_review_commit"] = "f" * 40
    elif case == "file_hash":
        review["expected_request_file_sha256"] = "f" * 64
    else:
        review["expected_request_size"] += 1

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="external review binding|file binding|review commit",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **review,
            process_starter=lambda *_args: pytest.fail(
                "unreviewed external anchor launched a child"
            ),
        )

    assert not Path(request["request_path"]).exists()
    assert not Path(request["handshake"]["attempt_path"]).exists()


def test_qualification_orchestrator_rejects_runtime_terminal_collision(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    failure_path = Path(request["failure_path"])

    def inject_failure_branch_after_release():
        failure_path.write_text(
            "{\"external\":true}\n",
            encoding="utf-8",
            newline="",
        )

    child = _FakeHandshakeChild(
        pid=322,
        on_wait=inject_failure_branch_after_release,
    )

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(250, 280))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="post_exit_validation.*partial",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            time_ns=lambda: next(timestamps),
        )

    assert failure_path.read_text(encoding="utf-8") == "{\"external\":true}\n"
    assert Path(request["handshake"]["release_path"]).is_file()
    assert not Path(request["completion_path"]).exists()


def test_qualification_completion_publication_failure_remains_partial(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_source_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    child = _FakeHandshakeChild(pid=324)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    def fail_completion(path, _result):
        assert Path(path) == Path(request["completion_path"])
        raise OSError("forced completion publication failure")

    monkeypatch.setattr(
        module,
        "publish_qualification_result_once",
        fail_completion,
    )
    timestamps = iter(range(330, 360))

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="consumed evidence remains partial",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_source_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            time_ns=lambda: next(timestamps),
        )

    assert Path(request["handshake"]["release_path"]).is_file()
    assert not Path(request["completion_path"]).exists()
    assert not Path(request["failure_path"]).exists()


def test_qualification_orchestrator_timeout_terminates_once_without_release(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    child = _FakeHandshakeChild(pid=654)
    starts = []
    clock = [0.0]

    def process_starter(_command, _environment):
        starts.append(child.pid)
        return child

    def sleep(_seconds):
        clock[0] = 121.0

    timestamps = iter(range(300, 320))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="readiness.*deadline",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            monotonic=lambda: clock[0],
            sleep=sleep,
            time_ns=lambda: next(timestamps),
        )

    failure = json.loads(Path(request["failure_path"]).read_text(encoding="utf-8"))
    assert starts == [child.pid]
    assert child.terminated is True
    assert not Path(request["handshake"]["release_path"]).exists()
    assert not Path(request["completion_path"]).exists()
    assert failure["status"] == "failed"
    assert failure["process"]["launch_count"] == 1
    assert failure["failure"]["stage"] == "wait_for_ready"
    assert set(failure["authority"].values()) == {False}

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="control artifact",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda _command, _environment: pytest.fail(
                "failed qualification retried a child"
            ),
        )


def test_qualification_orchestrator_bounds_post_release_child_exit(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )

    class StuckAfterReleaseChild:
        pid = 655

        def __init__(self):
            self.returncode = None
            self.terminated = False
            self.wait_calls = []

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.wait_calls.append(timeout)
            if self.returncode is not None:
                return self.returncode
            if timeout is None:
                self.returncode = 0
                return 0
            raise subprocess.TimeoutExpired("stuck-after-release", timeout)

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def kill(self):
            self.returncode = -9

    child = StuckAfterReleaseChild()

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(350, 380))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="wait_for_qualification_exit.*did not exit within 10 seconds",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            time_ns=lambda: next(timestamps),
        )

    failure = json.loads(
        Path(request["failure_path"]).read_text(encoding="utf-8")
    )
    assert child.wait_calls == [10, 5.0]
    assert child.terminated is True
    assert Path(request["handshake"]["release_path"]).is_file()
    assert failure["failure"]["stage"] == "wait_for_qualification_exit"
    assert failure["process"]["cleanup_attempted"] is True
    assert not Path(request["completion_path"]).exists()


@pytest.mark.parametrize(
    ("case", "expected_stage", "release_expected", "cleanup_expected"),
    (
        ("early_exit", "wait_for_ready", False, False),
        ("pid_mismatch", "wait_for_ready", False, True),
        ("config_drift", "pre_release_validation", False, True),
        ("release_failure", "publish_release", False, True),
        ("nonzero_exit", "wait_for_qualification_exit", True, False),
    ),
)
def test_qualification_orchestrator_failure_matrix_is_one_shot(
    tmp_path,
    monkeypatch,
    case,
    expected_stage,
    release_expected,
    cleanup_expected,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    child = _FakeHandshakeChild(
        pid=777,
        exit_code=9 if case == "nonzero_exit" else 0,
        initial_returncode=17 if case == "early_exit" else None,
    )
    starts = []

    def process_starter(_command, environment):
        starts.append(child.pid)
        if case != "early_exit":
            _publish_ready_from_environment(
                environment,
                child_pid=child.pid + (1 if case == "pid_mismatch" else 0),
            )
        if case == "config_drift":
            Path(request["config"]["path"]).write_text(
                "{\"changed\":true}\n",
                encoding="utf-8",
                newline="",
            )
        return child

    if case == "release_failure":
        real_publish = module.publish_record_once

        def fail_release(path, record):
            if Path(path) == Path(request["handshake"]["release_path"]):
                raise module.OutcomeEvidenceRunnerError(
                    "forced qualification release failure"
                )
            return real_publish(path, record)

        monkeypatch.setattr(module, "publish_record_once", fail_release)

    timestamps = iter(range(400, 430))
    with pytest.raises(module.OutcomeEvidenceRunnerError):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            time_ns=lambda: next(timestamps),
        )

    failure_path = Path(request["failure_path"])
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    assert starts == [child.pid]
    assert failure["status"] == "failed"
    assert failure["failure"]["stage"] == expected_stage
    assert failure["process"]["launch_count"] == 1
    assert failure["process"]["cleanup_attempted"] is cleanup_expected
    assert Path(request["handshake"]["release_path"]).exists() is release_expected
    assert not Path(request["completion_path"]).exists()
    assert not (tmp_path / "study").exists()
    assert not Path(request["forbidden_paths"][-1]).exists()
    assert set(failure["authority"].values()) == {False}


def test_qualification_post_exit_validation_failure_remains_partial(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    child = _FakeHandshakeChild(
        pid=778,
        exit_code=0,
        on_wait=lambda: Path(request["config"]["path"]).write_text(
            "{\"changed\":true}\n",
            encoding="utf-8",
            newline="",
        ),
    )

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(430, 460))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="post_exit_validation.*partial",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=process_starter,
            time_ns=lambda: next(timestamps),
        )

    assert Path(request["handshake"]["release_path"]).is_file()
    assert not Path(request["completion_path"]).exists()
    assert not Path(request["failure_path"]).exists()


def test_qualification_post_exit_dangling_forbidden_entry_remains_partial(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    qualification_root = Path(request["qualification_root"])
    forbidden_path = next(
        Path(path)
        for path in request["forbidden_paths"]
        if (
            not Path(path).is_relative_to(qualification_root)
            and Path(path).parent.exists()
        )
    )
    target_path = tmp_path / "dangling-forbidden-target"
    original_validate = module._validate_qualification_runtime_boundaries

    def create_forbidden_after_validation(**kwargs):
        original_validate(**kwargs)
        if kwargs["release_allowed"]:
            target_path.mkdir()
            _create_directory_junction(forbidden_path, target_path)
            target_path.rmdir()

    monkeypatch.setattr(
        module,
        "_validate_qualification_runtime_boundaries",
        create_forbidden_after_validation,
    )
    child = _FakeHandshakeChild(pid=779, exit_code=0)

    def process_starter(_command, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter(range(460, 490))
    try:
        with pytest.raises(
            module.OutcomeEvidenceRunnerError,
            match="post_exit_validation.*partial",
        ):
            module.execute_prelock_qualification(
                registration_path=registration_path,
                request_path=request_path,
                expected_request_hash=request["request_hash"],
                **_qualification_review_kwargs(request),
                process_starter=process_starter,
                time_ns=lambda: next(timestamps),
            )
    finally:
        os.rmdir(forbidden_path)

    assert Path(request["handshake"]["release_path"]).is_file()
    assert not Path(request["completion_path"]).exists()
    assert not Path(request["failure_path"]).exists()


def test_qualification_orchestrator_surfaces_cleanup_failure(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    clock = [0.0]

    class UnstoppableChild:
        pid = 888

        def poll(self):
            return None

        def terminate(self):
            raise RuntimeError("terminate denied")

        def kill(self):
            raise RuntimeError("kill denied")

        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired("unstoppable", timeout)

    child = UnstoppableChild()

    def advance_clock(_seconds):
        clock[0] = 121.0

    timestamps = iter(range(500, 530))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="child cleanup failed",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda _command, _environment: child,
            monotonic=lambda: clock[0],
            sleep=advance_clock,
            time_ns=lambda: next(timestamps),
        )

    failure = json.loads(
        Path(request["failure_path"]).read_text(encoding="utf-8")
    )
    assert failure["status"] == "failed"
    assert failure["process"]["cleanup_attempted"] is True
    assert "terminate denied" in failure["process"]["cleanup_error"]
    assert "kill denied" in failure["process"]["cleanup_error"]
    assert not Path(request["handshake"]["release_path"]).exists()


def test_qualification_orchestrator_records_child_start_exception(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )

    def fail_start(_command, _environment):
        raise OSError("forced child start failure")

    timestamps = iter(range(600, 630))
    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="start_child.*forced child start failure",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=fail_start,
            time_ns=lambda: next(timestamps),
        )

    failure = json.loads(
        Path(request["failure_path"]).read_text(encoding="utf-8")
    )
    assert failure["failure"]["stage"] == "start_child"
    assert failure["process"] == {
        "cleanup_attempted": False,
        "cleanup_error": None,
        "exit_code": None,
        "launch_count": 1,
        "pid": None,
    }
    assert Path(request["handshake"]["attempt_path"]).is_file()
    assert not Path(request["handshake"]["ready_path"]).exists()
    assert not Path(request["handshake"]["release_path"]).exists()


def test_qualification_orchestrator_records_attempt_build_exception(
    tmp_path,
    monkeypatch,
):
    module, registration_path, request_path, request = (
        _qualification_request_fixture(tmp_path, monkeypatch, source_only=True)
    )
    starts = []

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="build_attempt.*invalid timestamp",
    ):
        module.execute_prelock_qualification(
            registration_path=registration_path,
            request_path=request_path,
            expected_request_hash=request["request_hash"],
            **_qualification_review_kwargs(request),
            process_starter=lambda *_args: starts.append(True),
            time_ns=lambda: 0,
        )

    failure = json.loads(
        Path(request["failure_path"]).read_text(encoding="utf-8")
    )
    assert starts == []
    assert failure["failure"]["stage"] == "build_attempt"
    assert failure["process"] == {
        "cleanup_attempted": False,
        "cleanup_error": None,
        "exit_code": None,
        "launch_count": 0,
        "pid": None,
    }
    assert not Path(request["handshake"]["attempt_path"]).exists()
    assert not Path(request["handshake"]["ready_path"]).exists()
    assert not Path(request["handshake"]["release_path"]).exists()


def test_slot_launch_uses_exact_registered_eval_command_and_config(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    command_record = registration.to_record()["command"]

    assert list(launch.command) == [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]
    assert "--max-games" in launch.command
    assert launch.command[launch.command.index("--max-games") + 1] == "25"
    assert "--eval" in launch.command
    assert "--train" not in launch.command
    assert "--model" not in launch.command
    assert launch.environment == {
        "STS_NONCOMBAT_EXPLORATION_CONFIG": launch.config_path
    }
    assert launch.config_record == {
        "category_rates_bps": {"card_reward": 300, "shop": 1000},
        "enabled_categories": ["card_reward", "shop"],
        "manifest_path": registration.slots[0].manifest_path,
        "per_run_alternative_budget": 2,
        "schema_version": "noncombat-exploration-config-v1",
        "seed": SEED_BASE + 1,
        "session_id": f"{STUDY_ID}-s01",
        "source_commit": SOURCE_COMMIT,
        "study_id": STUDY_ID,
        "study_registration_hash": registration.registration_hash,
        "study_run_lock_hash": RUN_LOCK_HASH,
        "study_slot_number": 1,
        "trace_path": registration.slots[0].trace_path,
    }


def test_registered_config_binding_survives_runtime_manifest_creation(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 2)
    module.write_slot_config_once(launch)
    config = parse_exploration_config(
        launch.config_record,
        config_path=Path(launch.config_path),
    )

    manifest = create_exploration_session_manifest(
        config,
        source_clean=True,
        python_executable=str(WINDOWS_PYTHON),
        command=list(launch.command),
        isolation_hashes={"locked": True},
    )

    assert config.study_run_lock_hash == RUN_LOCK_HASH
    assert config.study_registration_hash == registration.registration_hash
    assert manifest["effective_config"]["study_run_lock_hash"] == RUN_LOCK_HASH
    assert manifest["effective_config"]["study_slot_number"] == 2


def test_registered_config_requires_complete_study_binding(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    incomplete = dict(launch.config_record)
    incomplete.pop("study_run_lock_hash")

    with pytest.raises(ExplorationConfigurationError, match="supplied together"):
        parse_exploration_config(incomplete)


@pytest.mark.parametrize(
    "mutated_command",
    [
        lambda command: [*command, "--train"],
        lambda command: [*command, "--model", "other.pth"],
        lambda command: [*command[:-1], "--epsilon", "0.1"],
        lambda command: [
            *command[: command.index("--max-games") + 1],
            "26",
            *command[command.index("--max-games") + 2 :],
        ],
    ],
)
def test_registered_command_rejects_training_or_mutation_flags(
    tmp_path, mutated_command
):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="command"):
        module.validate_registered_command(
            registration,
            mutated_command(list(launch.command)),
        )


def test_ledger_appends_hash_chained_lifecycle_records(tmp_path):
    ledger, registration = _ledger(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    terminal = ledger.finish_slot(
        1,
        process_exit_code=0,
        complete_trajectories=25,
        ended_unix_ns=300,
    )

    lines = ledger.path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert ledger.path.read_bytes().endswith(b"\n")
    assert [record["sequence"] for record in records] == [1, 2, 3]
    assert [record["event"] for record in records] == [
        "study_started",
        "slot_started",
        "slot_terminal",
    ]
    assert records[0]["previous_record_hash"] is None
    assert records[1]["previous_record_hash"] == records[0]["record_hash"]
    assert records[2]["previous_record_hash"] == records[1]["record_hash"]
    assert terminal["terminal_status"] == "completed"


def test_ledger_enforces_order_identity_and_launch_at_most_once(tmp_path):
    ledger, registration = _ledger(tmp_path)

    with pytest.raises(ledger.error_type, match="next.*slot|out of order"):
        ledger.start_slot(2, registration.slots[1].session_id, started_unix_ns=200)
    with pytest.raises(ledger.error_type, match="session"):
        ledger.start_slot(1, "unregistered-session", started_unix_ns=200)

    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)
    ledger.finish_slot(
        1,
        process_exit_code=0,
        complete_trajectories=25,
        ended_unix_ns=300,
    )
    with pytest.raises(ledger.error_type, match="next.*slot|already launched"):
        ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=400)


def test_early_exit_is_terminally_interrupted_and_cannot_restart(tmp_path):
    ledger, registration = _ledger(tmp_path)
    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)
    terminal = ledger.finish_slot(
        1,
        process_exit_code=17,
        complete_trajectories=7,
        ended_unix_ns=300,
    )

    assert terminal["terminal_status"] == "interrupted"
    assert ledger.next_slot().slot_number == 2
    with pytest.raises(ledger.error_type, match="next.*slot|already launched"):
        ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=400)


def test_crash_recovery_marks_active_slot_interrupted_without_relaunch(tmp_path):
    ledger, registration = _ledger(tmp_path)
    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)

    recovered = type(ledger)(
        path=ledger.path,
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    terminal = recovered.recover_active_slot(
        reason="runner process disappeared",
        complete_trajectories=3,
        ended_unix_ns=400,
    )

    assert terminal["terminal_status"] == "interrupted"
    assert recovered.next_slot().slot_number == 2


def test_ledger_rejects_duplicate_terminal_and_run_lock_mismatch(tmp_path):
    ledger, registration = _ledger(tmp_path)
    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)
    ledger.finish_slot(
        1,
        process_exit_code=0,
        complete_trajectories=25,
        ended_unix_ns=300,
    )

    with pytest.raises(ledger.error_type, match="active slot|duplicate"):
        ledger.finish_slot(
            1,
            process_exit_code=0,
            complete_trajectories=25,
            ended_unix_ns=400,
        )
    mismatched = type(ledger)(
        path=ledger.path,
        registration=registration,
        run_lock_hash="c" * 64,
    )
    with pytest.raises(ledger.error_type, match="run lock"):
        mismatched.snapshot()


def test_ledger_rejects_rehashed_registered_session_identity_tamper(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=200)
    records = [
        json.loads(line)
        for line in ledger.path.read_text(encoding="utf-8").splitlines()
    ]
    records[1]["session_id"] = registration.slots[1].session_id
    records[1]["record_hash"] = module._record_hash(records[1])
    ledger.path.write_text(
        "".join(module._canonical_json(record) + "\n" for record in records),
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(ledger.error_type, match="session"):
        ledger.snapshot()


def test_global_stop_blocks_every_later_launch(tmp_path):
    ledger, registration = _ledger(tmp_path)
    stop = ledger.global_stop(
        reason="checkpoint drift",
        created_unix_ns=200,
    )

    assert stop["reason"] == "checkpoint drift"
    with pytest.raises(ledger.error_type, match="global.*stop"):
        ledger.start_slot(1, registration.slots[0].session_id, started_unix_ns=300)


def test_repeated_lock_failure_preserves_first_global_stop(tmp_path):
    module = _module()
    ledger, _registration = _ledger(tmp_path)
    ledger.global_stop(reason="first integrity failure", created_unix_ns=200)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="second failure"):
        module.validate_run_lock_or_stop(
            ledger,
            validator=lambda: (_ for _ in ()).throw(RuntimeError("second failure")),
        )

    assert ledger.snapshot()["global_stop"] == {"reason": "first integrity failure"}


def test_schedule_has_no_post_slot_24_extension(tmp_path):
    ledger, registration = _ledger(tmp_path)
    for slot in registration.slots:
        ledger.start_slot(
            slot.slot_number,
            slot.session_id,
            started_unix_ns=slot.slot_number * 10,
        )
        ledger.finish_slot(
            slot.slot_number,
            process_exit_code=0,
            complete_trajectories=25,
            ended_unix_ns=slot.slot_number * 10 + 1,
        )

    snapshot = ledger.snapshot()
    assert snapshot["all_slots_terminal"] is True
    assert snapshot["terminal_slot_count"] == 24
    with pytest.raises(ledger.error_type, match="schedule.*complete|no later slot"):
        ledger.next_slot()


def test_slot_config_is_create_once_and_byte_stable(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    first = module.write_slot_config_once(launch)

    assert Path(launch.config_path).read_text(encoding="utf-8") == first
    assert first.endswith("\n")
    assert "\r" not in first
    with pytest.raises(module.OutcomeEvidenceRunnerError, match="already exists"):
        module.write_slot_config_once(launch)


def test_run_lock_validation_failure_records_global_stop_before_launch(tmp_path):
    module = _module()
    ledger, _registration = _ledger(tmp_path)
    launched = []

    def fail_validation():
        raise RuntimeError("source file drift")

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="validation"):
        module.validate_run_lock_or_stop(
            ledger,
            validator=fail_validation,
        )

    assert launched == []
    assert ledger.snapshot()["global_stop"]["reason"].startswith(
        "run lock validation failed"
    )


def test_existing_ledger_preserves_original_run_lock_binding_on_validation_failure(
    tmp_path,
):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    reopened = module.StudyLedger.open_existing(
        path=ledger.path,
        registration=registration,
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="differs"):
        module.validate_run_lock_or_stop(
            reopened,
            validator=lambda: {"run_lock_hash": "c" * 64},
        )

    snapshot = reopened.snapshot()
    assert reopened.run_lock_hash == RUN_LOCK_HASH
    assert "differs from the ledger binding" in snapshot["global_stop"]["reason"]


@pytest.mark.parametrize(
    ("new_markers", "exit_code", "terminal_status"),
    [(25, 0, "completed"), (7, 0, "interrupted"), (25, 3, "interrupted")],
)
def test_execute_slot_uses_ai_marker_delta_for_terminal_status(
    tmp_path, new_markers, exit_code, terminal_status
):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8")

    def process_runner(_launch):
        with marker_path.open("a", encoding="utf-8") as handle:
            for index in range(new_markers):
                handle.write(f"{100 + index}\n")
        return exit_code

    terminal = module.execute_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_runner=process_runner,
        started_unix_ns=200,
        ended_unix_ns=300,
    )

    assert terminal["complete_trajectories"] == new_markers
    assert terminal["terminal_status"] == terminal_status
    terminal_slot = ledger.snapshot()["terminal_slots"][0]
    assert terminal_slot["marker_start_count"] == 2
    assert terminal_slot["marker_end_count"] == 2 + new_markers


def test_execute_slot_rejects_marker_truncation_as_global_stop(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8")

    def process_runner(_launch):
        marker_path.write_text("12\n", encoding="utf-8")
        return 0

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="marker"):
        module.execute_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_runner=process_runner,
            started_unix_ns=200,
            ended_unix_ns=300,
        )

    snapshot = ledger.snapshot()
    assert snapshot["global_stop"] is not None
    assert snapshot["active_slot"] is None


def test_handshaken_slot_claims_only_after_verified_child_readiness(
    tmp_path,
    monkeypatch,
):
    module, ledger, registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    events = []

    def add_complete_markers():
        with marker_path.open("a", encoding="utf-8") as handle:
            for index in range(25):
                handle.write(f"{100 + index}\n")

    child = _FakeHandshakeChild(on_wait=add_complete_markers)
    original_start_slot = ledger.start_slot

    def recording_start_slot(*args, **kwargs):
        events.append("claim")
        return original_start_slot(*args, **kwargs)

    monkeypatch.setattr(ledger, "start_slot", recording_start_slot)

    def recording_publish(path, record):
        schema = record["schema_version"]
        events.append("attempt" if "attempt" in schema else "release")
        publish_handshake_record_once(path, record)

    monkeypatch.setattr(module, "publish_record_once", recording_publish)

    def process_starter(observed_launch, environment):
        events.append("popen")
        assert observed_launch is launch
        assert ledger.snapshot()["active_slot"] is None
        attempt = load_attempt_record(Path(environment[HANDSHAKE_ATTEMPT_ENV]))
        assert attempt["marker_start_count"] == 2
        assert Path(attempt["attempt_path"]).is_file()
        assert not Path(registration.slots[0].manifest_path).exists()
        assert not Path(registration.slots[0].trace_path).exists()
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    timestamps = iter((150, 200, 225, 300))
    terminal = module.execute_handshaken_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_starter=process_starter,
        time_ns=lambda: next(timestamps),
    )

    assert events == ["attempt", "popen", "claim", "release"]
    assert child.wait_calls == [None]
    assert terminal == {
        "complete_trajectories": 25,
        "marker_end_count": 27,
        "marker_start_count": 2,
        "process_exit_code": 0,
        "terminal_status": "completed",
    }
    records = [
        json.loads(line)
        for line in ledger.path.read_text(encoding="utf-8").splitlines()
    ]
    assert records[1]["event"] == "slot_started"
    assert records[1]["payload"] == {"marker_start_count": 2}
    attempt = load_attempt_record(
        Path(launch.config_path).with_name(
            f"{launch.session_id}-communication-attempt.json"
        )
    )
    assert Path(attempt["release_path"]).is_file()


def test_handshake_revalidates_run_lock_after_readiness_before_claim(tmp_path):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    def fail_preclaim_validation():
        raise module.OutcomeEvidenceRunnerError("forced run-lock drift")

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="forced run-lock drift"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
            preclaim_validator=fail_preclaim_validation,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert "forced run-lock drift" in snapshot["global_stop"]["reason"]


def test_handshake_rejects_child_exit_between_ready_validation_and_claim(
    tmp_path,
    monkeypatch,
):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    original_validate = module._validate_preclaim_handshake_state

    def exit_after_preclaim_validation(**kwargs):
        original_validate(**kwargs)
        child.returncode = 17

    monkeypatch.setattr(
        module,
        "_validate_preclaim_handshake_state",
        exit_after_preclaim_validation,
    )

    with pytest.raises(
        module.OutcomeEvidenceRunnerError,
        match="exited.*slot claim",
    ):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    snapshot = ledger.snapshot()
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert snapshot["global_stop"] is not None


def test_handshake_rechecks_outputs_after_claim_before_release(
    tmp_path,
    monkeypatch,
):
    module, ledger, registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()
    manifest_path = Path(registration.slots[0].manifest_path)
    release_path = Path(launch.config_path).with_name(
        f"{launch.session_id}-communication-release.json"
    )

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    original_start_slot = ledger.start_slot

    def create_output_after_claim(*args, **kwargs):
        result = original_start_slot(*args, **kwargs)
        manifest_path.write_text("{}\n", encoding="utf-8", newline="")
        return result

    monkeypatch.setattr(ledger, "start_slot", create_output_after_claim)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="gameplay output"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert release_path.exists() is False
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 1
    assert snapshot["terminal_slots"][0]["terminal_status"] == "interrupted"
    assert snapshot["global_stop"] is not None


def test_handshake_surfaces_child_cleanup_failure_in_global_stop(tmp_path):
    module, ledger, registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )

    class UnkillableChild(_FakeHandshakeChild):
        def terminate(self):
            raise OSError("terminate denied")

        def kill(self):
            raise OSError("kill denied")

    child = UnkillableChild()

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        Path(registration.slots[0].manifest_path).write_text(
            "{}\n",
            encoding="utf-8",
            newline="",
        )
        return child

    with pytest.raises(module.OutcomeEvidenceRunnerError) as error:
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    assert "child cleanup failed" in str(error.value)
    snapshot = ledger.snapshot()
    assert "child cleanup failed" in snapshot["global_stop"]["reason"]


def test_handshake_timeout_stops_without_claim_or_retry(tmp_path):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()
    starts = []
    clock = [0.0]

    def process_starter(_launch, _environment):
        starts.append(child.pid)
        return child

    def sleep(_seconds):
        clock[0] = 121.0

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="readiness.*deadline"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
            monotonic=lambda: clock[0],
            sleep=sleep,
        )

    snapshot = ledger.snapshot()
    assert starts == [child.pid]
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert "readiness" in snapshot["global_stop"]["reason"]


@pytest.mark.parametrize("ready_at", (120.0, 121.0))
def test_handshake_rejects_ready_at_or_after_readiness_deadline(
    tmp_path,
    ready_at,
):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()
    clock = [0.0]
    attempt_environment = {}

    def process_starter(_launch, environment):
        attempt_environment.update(environment)
        return child

    def publish_late_ready(_seconds):
        clock[0] = ready_at
        _publish_ready_from_environment(
            attempt_environment,
            child_pid=child.pid,
        )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="readiness.*deadline"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
            monotonic=lambda: clock[0],
            sleep=publish_late_ready,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert "readiness" in snapshot["global_stop"]["reason"]


def test_handshake_early_child_exit_stops_before_claim(tmp_path):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild(initial_returncode=17)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="exited.*readiness"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=lambda _launch, _environment: child,
        )

    snapshot = ledger.snapshot()
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert snapshot["global_stop"] is not None


@pytest.mark.parametrize(
    "failure_mode",
    ("malformed", "pid_mismatch", "marker_growth", "manifest", "trace"),
)
def test_handshake_rejects_invalid_preclaim_evidence(
    tmp_path,
    failure_mode,
):
    module, ledger, registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()

    def process_starter(_launch, environment):
        attempt = load_attempt_record(Path(environment[HANDSHAKE_ATTEMPT_ENV]))
        if failure_mode == "malformed":
            Path(attempt["ready_path"]).write_text("{broken\n", encoding="utf-8")
            return child
        ready_pid = child.pid + 1 if failure_mode == "pid_mismatch" else child.pid
        _publish_ready_from_environment(environment, child_pid=ready_pid)
        if failure_mode == "marker_growth":
            with marker_path.open("a", encoding="utf-8") as handle:
                handle.write("12\n")
        elif failure_mode == "manifest":
            Path(registration.slots[0].manifest_path).write_text(
                "{}\n",
                encoding="utf-8",
            )
        elif failure_mode == "trace":
            Path(registration.slots[0].trace_path).write_text(
                "{}\n",
                encoding="utf-8",
            )
        return child

    with pytest.raises(module.OutcomeEvidenceRunnerError):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 0
    assert snapshot["global_stop"] is not None


@pytest.mark.parametrize("artifact", ("attempt", "ready", "release"))
def test_stale_handshake_artifact_is_an_orphaned_global_stop_without_popen(
    tmp_path,
    artifact,
):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    suffix = {
        "attempt": "-communication-attempt.json",
        "ready": "-communication-ready.json",
        "release": "-communication-release.json",
    }[artifact]
    stale_path = Path(launch.config_path).with_name(f"{launch.session_id}{suffix}")
    stale_path.write_text("{}\n", encoding="utf-8")
    starts = []

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="handshake artifact"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=lambda *_args: starts.append(True),
        )

    assert starts == []
    snapshot = ledger.snapshot()
    assert snapshot["terminal_slot_count"] == 0
    assert snapshot["global_stop"] is not None


def test_release_publication_failure_consumes_claimed_slot_and_stops(
    tmp_path,
    monkeypatch,
):
    module, ledger, _registration, _run_lock, launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    child = _FakeHandshakeChild()

    def process_starter(_launch, environment):
        _publish_ready_from_environment(environment, child_pid=child.pid)
        return child

    def fail_release(path, record):
        if "release" in record["schema_version"]:
            raise module.OutcomeEvidenceRunnerError("forced release publication failure")
        publish_handshake_record_once(path, record)

    monkeypatch.setattr(module, "publish_record_once", fail_release)

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="release"):
        module.execute_handshaken_registered_slot(
            ledger=ledger,
            launch=launch,
            marker_path=marker_path,
            process_starter=process_starter,
        )

    snapshot = ledger.snapshot()
    assert child.terminated is True
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 1
    assert snapshot["terminal_slots"][0]["terminal_status"] == "interrupted"
    assert snapshot["terminal_slots"][0]["marker_start_count"] == 2
    assert snapshot["terminal_slots"][0]["marker_end_count"] == 2
    assert "release" in snapshot["global_stop"]["reason"]


def test_host_recovery_consumes_active_handshaken_slot_before_global_stop(tmp_path):
    module, ledger, registration, _run_lock, _launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    ledger.start_slot(
        1,
        registration.slots[0].session_id,
        marker_start_count=2,
        started_unix_ns=200,
    )
    with marker_path.open("a", encoding="utf-8") as handle:
        handle.write("12\n")

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="active slot recovery"):
        module._recover_active_slot_after_host_failure(
            ledger=ledger,
            marker_path=marker_path,
            ended_unix_ns=300,
        )

    snapshot = ledger.snapshot()
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 1
    assert snapshot["terminal_slots"][0]["complete_trajectories"] == 1
    assert snapshot["terminal_slots"][0]["marker_start_count"] == 2
    assert snapshot["terminal_slots"][0]["marker_end_count"] == 3
    assert snapshot["global_stop"] is not None


def test_run_next_recovers_active_slot_before_revalidating_run_lock(
    tmp_path,
    monkeypatch,
):
    module, ledger, registration, _run_lock, _launch, marker_path = (
        _handshake_slot(tmp_path)
    )
    ledger.start_slot(
        1,
        registration.slots[0].session_id,
        marker_start_count=2,
        started_unix_ns=200,
    )
    validation_calls = []

    monkeypatch.setattr(
        module,
        "_load_runner_registration",
        lambda _path: registration,
    )
    monkeypatch.setattr(
        module,
        "_require_launchable_runner_registration",
        lambda value: value,
    )
    monkeypatch.setattr(module, "_registered_command", lambda _value: ["python"])
    monkeypatch.setattr(module, "_run_lock_path", lambda _value: tmp_path / "lock")
    monkeypatch.setattr(
        module.StudyLedger,
        "open_existing",
        classmethod(lambda cls, **_kwargs: ledger),
    )

    def unexpected_run_lock_validation(*_args, **_kwargs):
        validation_calls.append(True)
        pytest.fail("run lock validation ran before active-slot recovery")

    monkeypatch.setattr(
        module,
        "validate_run_lock_or_stop",
        unexpected_run_lock_validation,
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="active slot recovery"):
        module._run_next_command(tmp_path / "registration.json")

    snapshot = ledger.snapshot()
    assert validation_calls == []
    assert marker_path.read_text(encoding="utf-8") == "10\n11\n"
    assert snapshot["active_slot"] is None
    assert snapshot["terminal_slot_count"] == 1
    assert snapshot["global_stop"] is not None


@pytest.mark.parametrize(
    "subcommand",
    ["start", "dry-run", "run-next", "monitor", "finalize"],
)
def test_cli_exposes_only_registered_study_subcommands(tmp_path, subcommand):
    module = _module()
    registration_path = tmp_path / "registration.json"
    args = module.parse_args(
        [subcommand, "--registration", str(registration_path)]
    )

    assert args.subcommand == subcommand
    assert args.registration == registration_path


def test_run_next_cli_keeps_audit_json_off_communication_stdout(
    tmp_path, monkeypatch, capsys
):
    module = _module()
    registration_path = tmp_path / "registration.json"
    result = {"slot_number": 1, "status": "completed"}
    monkeypatch.setattr(module, "_run_next_command", lambda _path: result)

    assert module.main(
        ["run-next", "--registration", str(registration_path)]
    ) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def test_finalize_command_replays_every_registered_slot_and_runs_pipeline(
    tmp_path, monkeypatch
):
    module = _module()
    registration, run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
    )
    ledger_snapshot = {
        "all_slots_terminal": True,
        "global_stop": None,
        "terminal_slots": [
            {
                "session_id": slot.session_id,
                "slot_number": slot.slot_number,
                "terminal_status": "completed",
            }
            for slot in registration.slots
        ],
    }
    sessions = tuple(object() for _slot in registration.slots)
    pool = object()
    finalization = {
        "closeout": {"status": "ready"},
        "paths": {"closeout_json": "closeout.json"},
        "study_id": STUDY_ID,
    }
    calls = {}

    class FakeLedger:
        run_lock_hash = RUN_LOCK_HASH

        def snapshot(self):
            return ledger_snapshot

    monkeypatch.setattr(module, "load_registration", lambda _path: registration)
    monkeypatch.setattr(
        module.StudyLedger,
        "open_existing",
        lambda **_kwargs: FakeLedger(),
    )
    monkeypatch.setattr(module, "_load_run_lock_record", lambda _path: run_lock)

    def validate_lock(**kwargs):
        calls["validate_lock"] = kwargs
        return run_lock

    def collect(registration_value, **kwargs):
        assert registration_value is registration
        calls["collect"] = kwargs
        return sessions

    def build_pool(registration_value, **kwargs):
        assert registration_value is registration
        assert kwargs["sessions"] is sessions
        calls["pool"] = kwargs
        return pool

    def finalize(registration_value, **kwargs):
        assert registration_value is registration
        assert kwargs["pool"] is pool
        calls["finalize"] = kwargs
        return finalization

    monkeypatch.setattr(module, "validate_run_lock", validate_lock)
    monkeypatch.setattr(module, "collect_registered_session_evidence", collect)
    monkeypatch.setattr(module, "build_registered_pool", build_pool)
    monkeypatch.setattr(module, "finalize_registered_outcome_evidence", finalize)

    result = module._finalize_gate_command(registration_path)

    assert result is finalization
    assert calls["collect"]["run_lock"] is run_lock
    assert calls["collect"]["ledger_snapshot"] is ledger_snapshot
    assert calls["pool"] == {
        "ledger_snapshot": ledger_snapshot,
        "run_lock_hash": RUN_LOCK_HASH,
        "sessions": sessions,
    }
    assert calls["finalize"] == {
        "ledger_snapshot": ledger_snapshot,
        "pool": pool,
        "run_lock_hash": RUN_LOCK_HASH,
    }


def test_finalize_command_writes_blocked_closeout_after_global_stop(
    tmp_path, monkeypatch
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    snapshot = {
        "active_slot": None,
        "all_slots_terminal": False,
        "global_stop": {"reason": "checkpoint drift"},
        "initialized": True,
        "terminal_slot_count": 0,
        "terminal_slots": [],
    }
    blocked = {
        "closeout": {"status": "blocked"},
        "paths": {"closeout_json": "closeout.json"},
        "study_id": STUDY_ID,
    }
    calls = {}

    class FakeLedger:
        run_lock_hash = RUN_LOCK_HASH

        def snapshot(self):
            return snapshot

    monkeypatch.setattr(module, "load_registration", lambda _path: registration)
    monkeypatch.setattr(
        module.StudyLedger,
        "open_existing",
        lambda **_kwargs: FakeLedger(),
    )

    def finalize(registration_value, **kwargs):
        assert registration_value is registration
        calls.update(kwargs)
        return blocked

    monkeypatch.setattr(module, "finalize_registered_integrity_stop", finalize)
    monkeypatch.setattr(
        module,
        "collect_registered_session_evidence",
        lambda *_args, **_kwargs: pytest.fail("blocked closeout must not pool"),
    )

    result = module._finalize_gate_command(registration_path)

    assert result is blocked
    assert calls == {
        "ledger_snapshot": snapshot,
        "run_lock_hash": RUN_LOCK_HASH,
    }


@pytest.mark.parametrize(
    "validation_result",
    [
        pytest.param(RuntimeError("source drift"), id="validation-error"),
        pytest.param({"run_lock_hash": "c" * 64}, id="ledger-hash-mismatch"),
    ],
)
def test_finalize_command_converts_late_run_lock_failure_to_blocked_closeout(
    tmp_path, monkeypatch, validation_result
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    terminal_slots = [
        {
            "session_id": slot.session_id,
            "slot_number": slot.slot_number,
            "terminal_status": "completed",
        }
        for slot in registration.slots
    ]

    class FakeLedger:
        run_lock_hash = RUN_LOCK_HASH

        def __init__(self):
            self.stop = None

        def snapshot(self):
            return {
                "all_slots_terminal": True,
                "global_stop": self.stop,
                "initialized": True,
                "terminal_slot_count": len(terminal_slots),
                "terminal_slots": terminal_slots,
            }

        def global_stop(self, *, reason):
            self.stop = {"reason": reason}

    ledger = FakeLedger()
    blocked = {"closeout": {"status": "blocked"}}
    calls = {}

    monkeypatch.setattr(module, "load_registration", lambda _path: registration)
    monkeypatch.setattr(
        module.StudyLedger,
        "open_existing",
        lambda **_kwargs: ledger,
    )

    def validate_lock(**_kwargs):
        if isinstance(validation_result, Exception):
            raise validation_result
        return validation_result

    def finalize(registration_value, **kwargs):
        assert registration_value is registration
        calls.update(kwargs)
        return blocked

    monkeypatch.setattr(module, "validate_run_lock", validate_lock)
    monkeypatch.setattr(module, "finalize_registered_integrity_stop", finalize)
    monkeypatch.setattr(
        module,
        "collect_registered_session_evidence",
        lambda *_args, **_kwargs: pytest.fail("failed lock must not pool"),
    )

    result = module._finalize_gate_command(registration_path)

    assert result is blocked
    assert calls["run_lock_hash"] == RUN_LOCK_HASH
    assert calls["ledger_snapshot"]["global_stop"]["reason"].startswith(
        "run lock validation failed"
    )


def _structural_observation(slot, **extra):
    observation = {
        "candidate_legal_records": 4,
        "config_exists": True,
        "config_sha256": "1" * 64,
        "confirmed_records": 4,
        "handshake_attempt_exists": True,
        "handshake_attempt_sha256": "5" * 64,
        "handshake_ready_exists": True,
        "handshake_ready_sha256": "6" * 64,
        "handshake_release_exists": True,
        "handshake_release_sha256": "7" * 64,
        "isolation_verified": True,
        "manifest_exists": True,
        "manifest_hash": "2" * 64,
        "manifest_sha256": "3" * 64,
        "proposed_records": 5,
        "replay_valid_records": 4,
        "run_join_complete_count": 1,
        "session_id": slot.session_id,
        "slot_number": slot.slot_number,
        "trace_exists": True,
        "trace_sha256": "4" * 64,
    }
    observation.update(extra)
    return observation


def test_blinded_monitor_drops_outcome_and_policy_evaluation_fields(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    forbidden_values = {
        "victory": "SECRET_VICTORY",
        "floor_reached": "SECRET_FLOOR",
        "killed_by": "SECRET_KILLER",
        "target_weight": "SECRET_WEIGHT",
        "ess": "SECRET_ESS",
        "ope_estimate": "SECRET_OPE",
        "bootstrap": "SECRET_BOOTSTRAP",
        "influence": "SECRET_INFLUENCE",
        "policy_comparison": "SECRET_COMPARISON",
    }
    observation = _structural_observation(slot, **forbidden_values)

    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[observation],
    )
    rendered_json = module.render_blinded_monitor_json(monitor)
    rendered_markdown = module.render_blinded_monitor_markdown(monitor)
    combined = rendered_json + rendered_markdown

    for field, value in forbidden_values.items():
        assert f'"{field}":' not in rendered_json
        assert value not in combined
    assert monitor["slots"][0]["confirmed_records"] == 4
    assert monitor["slots"][0]["lifecycle"] == "active"


def test_blinded_monitor_reports_only_structural_validity_and_process_exit(
    tmp_path,
):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    ledger.finish_slot(
        1,
        process_exit_code=7,
        complete_trajectories=3,
        ended_unix_ns=300,
    )

    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        run_lock_valid=True,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[_structural_observation(slot)],
    )

    assert monitor["registration_valid"] is True
    assert monitor["run_lock_valid"] is True
    assert monitor["slots"][0]["process_exit_code"] == 7
    assert "| 7 |" in module.render_blinded_monitor_markdown(monitor)

    blocked = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        run_lock_valid=False,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[_structural_observation(slot)],
    )
    assert blocked["integrity_valid"] is False
    assert "run_lock_invalid" in blocked["blockers"]


def test_blinded_monitor_reports_unlaunched_handshake_artifact_progress(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    module.write_slot_config_once(launch)
    attempt_path = Path(launch.config_path).with_name(
        f"{launch.session_id}-communication-attempt.json"
    )
    ready_path = Path(launch.config_path).with_name(
        f"{launch.session_id}-communication-ready.json"
    )
    release_path = Path(launch.config_path).with_name(
        f"{launch.session_id}-communication-release.json"
    )
    attempt_bytes = b'{"stage":"attempt"}\n'
    attempt_path.write_bytes(attempt_bytes)
    ledger.global_stop(reason="orphaned preclaim attempt", created_unix_ns=200)

    observations = module.collect_structural_observations(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
    )
    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=observations,
    )

    assert monitor["schema_version"] == (
        "noncombat-outcome-evidence-blinded-monitor-v2"
    )
    assert len(observations) == 1
    slot = monitor["slots"][0]
    assert slot["lifecycle"] == "unlaunched"
    assert slot["handshake_status"] == "attempted"
    assert slot["handshake_attempt_path"] == str(attempt_path.resolve())
    assert slot["handshake_attempt_exists"] is True
    assert slot["handshake_attempt_sha256"] == hashlib.sha256(
        attempt_bytes
    ).hexdigest()
    assert slot["handshake_ready_path"] == str(ready_path.resolve())
    assert slot["handshake_ready_exists"] is False
    assert slot["handshake_ready_sha256"] is None
    assert slot["handshake_release_path"] == str(release_path.resolve())
    assert slot["handshake_release_exists"] is False
    assert slot["handshake_release_sha256"] is None
    rendered = module.render_blinded_monitor_json(monitor)
    assert '"victory":' not in rendered
    assert '"ope_estimate":' not in rendered
    assert "| attempted |" in module.render_blinded_monitor_markdown(monitor)


def test_blinded_monitor_is_byte_stable_under_observation_reordering(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    for slot in registration.slots[:2]:
        ledger.start_slot(
            slot.slot_number,
            slot.session_id,
            started_unix_ns=slot.slot_number * 100,
        )
        ledger.finish_slot(
            slot.slot_number,
            process_exit_code=0,
            complete_trajectories=25,
            ended_unix_ns=slot.slot_number * 100 + 1,
        )
    observations = [
        _structural_observation(registration.slots[0]),
        _structural_observation(registration.slots[1]),
    ]

    first = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=observations,
    )
    second = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=list(reversed(observations)),
    )

    assert module.render_blinded_monitor_json(first) == (
        module.render_blinded_monitor_json(second)
    )
    assert module.render_blinded_monitor_markdown(first) == (
        module.render_blinded_monitor_markdown(second)
    )


@pytest.mark.parametrize("failure_mode", ["missing", "malformed", "unregistered"])
def test_blinded_monitor_fails_closed_on_structural_input_errors(
    tmp_path, failure_mode
):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    if failure_mode == "missing":
        observations = []
    elif failure_mode == "malformed":
        observations = [_structural_observation(slot, confirmed_records="four")]
    else:
        observations = [
            _structural_observation(
                slot,
                slot_number=99,
                session_id="unregistered-session",
            )
        ]

    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=observations,
    )

    assert monitor["integrity_valid"] is False
    assert monitor["blockers"]
    assert "four" not in module.render_blinded_monitor_json(monitor)


def test_blinded_monitor_redacts_global_stop_reason(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    ledger.global_stop(
        reason="victory=SECRET_STOP_OUTCOME",
        created_unix_ns=200,
    )

    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[],
    )
    rendered = module.render_blinded_monitor_json(monitor)

    assert monitor["global_integrity_stop"] is True
    assert monitor["integrity_valid"] is False
    assert "SECRET_STOP_OUTCOME" not in rendered
    assert "victory" not in rendered


def test_blinded_monitor_artifacts_are_atomically_replaced_with_exact_bytes(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=[],
    )
    json_path = tmp_path / "monitor.json"
    markdown_path = tmp_path / "monitor.md"
    json_path.write_text("stale", encoding="utf-8")
    markdown_path.write_text("stale", encoding="utf-8")

    result = module.write_blinded_monitor_artifacts(
        monitor,
        json_path=json_path,
        markdown_path=markdown_path,
    )

    assert result == {
        "json_path": str(json_path.resolve()),
        "markdown_path": str(markdown_path.resolve()),
    }
    assert json_path.read_text(encoding="utf-8") == (
        module.render_blinded_monitor_json(monitor)
    )
    assert markdown_path.read_text(encoding="utf-8") == (
        module.render_blinded_monitor_markdown(monitor)
    )


def test_structural_scanner_fails_closed_on_malformed_artifact_without_echo(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    slot = registration.slots[0]
    ledger.start_slot(1, slot.session_id, started_unix_ns=200)
    Path(slot.config_path).parent.mkdir(parents=True, exist_ok=True)
    Path(slot.config_path).write_text(
        '{"victory":"SECRET_ARTIFACT_OUTCOME"}\n',
        encoding="utf-8",
    )

    observations = module.collect_structural_observations(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
    )
    monitor = module.build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
        structural_observations=observations,
    )
    rendered = module.render_blinded_monitor_json(monitor)

    assert monitor["integrity_valid"] is False
    assert "SECRET_ARTIFACT_OUTCOME" not in rendered
    assert '"victory":' not in rendered


def test_manifest_pre_isolation_matches_registered_run_lock_semantically(tmp_path):
    module = _module()
    communication_path = str((tmp_path / "config.properties").resolve())
    checkpoint_path = str((tmp_path / "checkpoints" / "model.pth").resolve())
    run_lock = {
        "checkpoints": {
            "files": [{"path": checkpoint_path, "sha256": "1" * 64, "size": 7}],
            "patterns": ["*.pth"],
            "root": str((tmp_path / "checkpoints").resolve()),
        },
        "communication_mod": {
            "path": communication_path,
            "semantic_sha256": "2" * 64,
        },
    }
    manifest = {
        "pre_session_isolation_hashes": {
            checkpoint_path: {
                "exists": True,
                "is_file": True,
                "mtime_ns": 123,
                "sha256": "1" * 64,
                "size": 7,
            },
            communication_path: {
                "exists": True,
                "is_file": True,
                "mtime_ns": 456,
                "semantic_sha256": "2" * 64,
                "sha256": "3" * 64,
                "size": 99,
            },
        }
    }

    assert module.manifest_isolation_matches_run_lock(manifest, run_lock) is True
    manifest["pre_session_isolation_hashes"][checkpoint_path]["sha256"] = "4" * 64
    assert module.manifest_isolation_matches_run_lock(manifest, run_lock) is False


def test_conservative_run_join_count_requires_unique_nearby_run_files():
    module = _module()

    assert module.conservative_run_join_count(
        marker_timestamps=[100, 200],
        run_timestamps=[97, 198],
        tolerance_seconds=10,
    ) == 2
    assert module.conservative_run_join_count(
        marker_timestamps=[100, 200],
        run_timestamps=[98, 99, 198],
        tolerance_seconds=10,
    ) == 1


def test_structural_scanner_joins_only_registered_slot_marker_slice(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n11\n", encoding="utf-8")
    run_dir = tmp_path / "runs" / "IRONCLAD"
    run_dir.mkdir()

    def process_runner(_launch):
        with marker_path.open("a", encoding="utf-8") as handle:
            handle.write("100\n200\n")
        (run_dir / "97.run").write_text("{}", encoding="utf-8")
        (run_dir / "198.run").write_text("{}", encoding="utf-8")
        (run_dir / "10.run").write_text("{}", encoding="utf-8")
        return 0

    module.execute_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_runner=process_runner,
        started_unix_ns=200,
        ended_unix_ns=300,
    )

    observations = module.collect_structural_observations(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=ledger.snapshot(),
    )
    assert observations[0]["run_join_complete_count"] == 2


def test_ledger_rejects_rehashed_marker_bound_tamper(tmp_path):
    module = _module()
    ledger, registration = _ledger(tmp_path)
    _registration, run_lock = _study(tmp_path)
    launch = module.build_slot_launch(registration, run_lock, 1)
    marker_path = tmp_path / "runs" / "ai_games.txt"
    marker_path.parent.mkdir()
    marker_path.write_text("10\n", encoding="utf-8")

    def process_runner(_launch):
        with marker_path.open("a", encoding="utf-8") as handle:
            handle.write("20\n")
        return 0

    module.execute_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_runner=process_runner,
        started_unix_ns=200,
        ended_unix_ns=300,
    )
    records = [
        json.loads(line)
        for line in ledger.path.read_text(encoding="utf-8").splitlines()
    ]
    records[-1]["payload"]["marker_end_count"] = 99
    records[-1]["record_hash"] = module._record_hash(records[-1])
    ledger.path.write_text(
        "".join(module._canonical_json(record) + "\n" for record in records),
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(ledger.error_type, match="marker"):
        ledger.snapshot()


def test_no_game_dry_run_enumerates_exact_registered_24_slot_plan(
    tmp_path, monkeypatch
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    monkeypatch.setattr(
        module.subprocess,
        "check_output",
        lambda *_args, **_kwargs: SOURCE_COMMIT,
    )
    monkeypatch.setattr(
        module.subprocess,
        "call",
        lambda *_args, **_kwargs: pytest.fail("dry-run launched a child process"),
    )

    plan = module._dry_run_command(registration_path)

    assert plan["launch_count"] == 24
    assert [launch["slot_number"] for launch in plan["launches"]] == list(
        range(1, 25)
    )
    assert len({launch["session_id"] for launch in plan["launches"]}) == 24
    assert len({launch["config_path"] for launch in plan["launches"]}) == 24
    for expected_slot, launch in enumerate(plan["launches"], start=1):
        assert launch["config_record"]["seed"] == SEED_BASE + expected_slot
        assert launch["config_record"]["category_rates_bps"] == {
            "card_reward": 300,
            "shop": 1000,
        }
        assert launch["config_record"]["per_run_alternative_budget"] == 2
        assert launch["environment"] == {
            "STS_NONCOMBAT_EXPLORATION_CONFIG": launch["config_path"]
        }
        session_id = launch["session_id"]
        artifact_root = Path(registration.artifact_root)
        assert launch["handshake"] == {
            "attempt_path": str(
                (artifact_root / f"{session_id}-communication-attempt.json").resolve()
            ),
            "protocol_version": "noncombat-outcome-evidence-handshake-v1",
            "readiness_timeout_seconds": 120,
            "ready_path": str(
                (artifact_root / f"{session_id}-communication-ready.json").resolve()
            ),
            "release_path": str(
                (artifact_root / f"{session_id}-communication-release.json").resolve()
            ),
            "release_timeout_seconds": 10,
        }
        assert "--max-games" in launch["command"]
        assert launch["command"][launch["command"].index("--max-games") + 1] == "25"
        assert "--eval" in launch["command"]
        assert "--train" not in launch["command"]
        assert "--model" not in launch["command"]


def test_existing_study_dry_run_revalidates_lock_against_ledger(
    tmp_path, monkeypatch
):
    module = _module()
    registration, run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    artifact_root = Path(registration.artifact_root)
    artifact_root.mkdir(parents=True)
    (artifact_root / "run-lock.json").write_text(
        json.dumps(run_lock),
        encoding="utf-8",
    )
    ledger = module.StudyLedger(
        path=artifact_root / "study-ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)
    validation_calls = []

    def validate_lock(**kwargs):
        validation_calls.append(kwargs)
        return run_lock

    monkeypatch.setattr(module, "validate_run_lock", validate_lock)
    monkeypatch.setattr(
        module.subprocess,
        "call",
        lambda *_args, **_kwargs: pytest.fail("dry-run launched a child process"),
    )

    plan = module._dry_run_command(registration_path)

    assert plan["launch_count"] == 24
    assert len(validation_calls) == 1
    assert ledger.snapshot()["global_stop"] is None


def test_existing_study_dry_run_missing_lock_records_global_stop(
    tmp_path, monkeypatch
):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    artifact_root = Path(registration.artifact_root)
    ledger = module.StudyLedger(
        path=artifact_root / "study-ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)
    monkeypatch.setattr(
        module.subprocess,
        "call",
        lambda *_args, **_kwargs: pytest.fail("dry-run launched a child process"),
    )

    with pytest.raises(module.OutcomeEvidenceRunnerError, match="run lock"):
        module._dry_run_command(registration_path)

    assert ledger.snapshot()["global_stop"] is not None


def test_monitor_records_malformed_run_lock_and_writes_blocked_artifact(tmp_path):
    module = _module()
    registration, _run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    artifact_root = Path(registration.artifact_root)
    artifact_root.mkdir(parents=True)
    (artifact_root / "run-lock.json").write_text("{malformed", encoding="utf-8")
    ledger = module.StudyLedger(
        path=artifact_root / "study-ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)

    monitor = module._monitor_command(registration_path)

    assert monitor["phase"] == "blocked"
    assert monitor["run_lock_valid"] is False
    assert "run_lock_invalid" in monitor["blockers"]
    assert ledger.snapshot()["global_stop"] is not None
    assert (artifact_root / "blinded-monitor.json").is_file()
    assert (artifact_root / "blinded-monitor.md").is_file()


def test_monitor_keeps_ledger_binding_when_run_lock_hash_is_replaced(tmp_path):
    module = _module()
    registration, run_lock = _study(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        render_registration_json(registration),
        encoding="utf-8",
        newline="",
    )
    artifact_root = Path(registration.artifact_root)
    artifact_root.mkdir(parents=True)
    replaced = dict(run_lock)
    replaced["run_lock_hash"] = "c" * 64
    (artifact_root / "run-lock.json").write_text(
        json.dumps(replaced),
        encoding="utf-8",
    )
    ledger = module.StudyLedger(
        path=artifact_root / "study-ledger.jsonl",
        registration=registration,
        run_lock_hash=RUN_LOCK_HASH,
    )
    ledger.initialize(created_unix_ns=100)

    monitor = module._monitor_command(registration_path)

    assert monitor["run_lock_valid"] is False
    assert monitor["run_lock_hash"] == RUN_LOCK_HASH

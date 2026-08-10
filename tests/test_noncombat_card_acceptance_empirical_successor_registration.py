from __future__ import annotations

import copy
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path

import pytest

from analysis_scripts import (
    noncombat_card_acceptance_empirical_successor_registration as registration,
)


ROOT = Path(__file__).resolve().parents[1]


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def _input_files(tmp_path: Path):
    payloads = {
        "inventory": _json_bytes(
            {"kind": "inventory", "repository_commit": "b" * 40}
        ),
        "build_receipt": _json_bytes({"kind": "build-receipt"}),
        "verification_receipt": _json_bytes({"kind": "verification-receipt"}),
        "verification_completion": _json_bytes(
            {"kind": "verification-completion"}
        ),
        "standalone_result": _json_bytes({"kind": "standalone-result"}),
        "verification_review": _json_bytes(
            {"review": "No findings", "verified": True}
        ),
    }
    bindings = {}
    for name, payload in payloads.items():
        path = tmp_path / f"{name}.json"
        path.write_bytes(payload)
        bindings[name] = {
            "content_kind": "canonical_json",
            "path": path.resolve().as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    return payloads, bindings


def _request(tmp_path: Path):
    _payloads, bindings = _input_files(tmp_path)
    return registration.build_registration_request(
        implementation_source_commit="a" * 40,
        inventory_source_commit="b" * 40,
        preflight_sha256="c" * 64,
        input_bindings=bindings,
        receipt_path=(tmp_path / "started.json").resolve().as_posix(),
        output_path=(tmp_path / "registration.json").resolve().as_posix(),
    )


def _execute_request(
    tmp_path: Path,
    request: dict,
    *,
    request_bytes: bytes | None = None,
    expected_request_sha256: str | None = None,
    repo_root: str | None = None,
    trusted_repo_root: str | None = None,
    isolated_mode: bool = True,
):
    request_path = (tmp_path / "registration_request.json").resolve()
    request_path.write_bytes(
        _json_bytes(request) if request_bytes is None else request_bytes
    )
    return registration._execute_registration(
        repo_root=repo_root or tmp_path.resolve().as_posix(),
        trusted_repo_root=trusted_repo_root or tmp_path.resolve().as_posix(),
        request_path=request_path.as_posix(),
        expected_request_sha256=(
            expected_request_sha256 or request["request_sha256"]
        ),
        receipt_path=request["receipt_path"],
        isolated_mode=isolated_mode,
    )


def _stub_validators(monkeypatch):
    artifact = {
        "registration_id": registration.REGISTRATION_ID,
        "registration_sha256": "d" * 64,
        "schema_version": registration.REGISTRATION_SCHEMA_VERSION,
    }
    calls = []

    def build(**evidence):
        calls.append(("build", copy.deepcopy(evidence)))
        return copy.deepcopy(artifact)

    def producer_verify(value, inventory, **kwargs):
        calls.append(("producer", copy.deepcopy(inventory), copy.deepcopy(kwargs)))
        assert value == artifact
        return copy.deepcopy(value)

    def standalone_verify(value, inventory):
        calls.append(("standalone", copy.deepcopy(inventory)))
        assert value == artifact
        return {
            "inventory_sha256": inventory["kind"],
            "registration_sha256": value["registration_sha256"],
            "verified": True,
        }

    monkeypatch.setattr(registration.producer, "build_inventory_registration", build)
    monkeypatch.setattr(
        registration.producer, "validate_inventory_registration", producer_verify
    )
    monkeypatch.setattr(
        registration.standalone, "verify_inventory_registration", standalone_verify
    )
    monkeypatch.setattr(
        registration.standalone,
        "parse_canonical_registration_bytes",
        lambda payload: json.loads(payload),
    )
    monkeypatch.setattr(
        registration.standalone,
        "verify_seed_inventory_evidence",
        lambda inventory: {
            "cohort_counts": {
                "training": 512,
                "canary": 128,
                "holdout": 512,
            },
            "excluded_seed_count": 0,
            "inventory_sha256": inventory["kind"],
            "source_count": 1,
            "verified": True,
        },
    )
    return artifact, calls


def test_registration_request_requires_canonical_exact_allowlist(tmp_path):
    request = _request(tmp_path)
    raw = _json_bytes(request)
    assert registration.parse_canonical_request_bytes(raw) == request

    with pytest.raises(registration.RegistrationBlocked, match="duplicate"):
        registration.parse_canonical_request_bytes(
            b'{"schema_version":"x","schema_version":"y"}\n'
        )
    with pytest.raises(registration.RegistrationBlocked, match="canonical"):
        registration.parse_canonical_request_bytes(raw.replace(b'":', b'": ', 1))

    changed = copy.deepcopy(request)
    changed["input_bindings"]["extra"] = copy.deepcopy(
        changed["input_bindings"]["inventory"]
    )
    changed["request_sha256"] = registration.canonical_json_sha256(
        {key: value for key, value in changed.items() if key != "request_sha256"}
    )
    with pytest.raises(registration.RegistrationBlocked, match="input binding"):
        registration.validate_registration_request(changed)


def test_registered_command_identity_is_exact(tmp_path):
    root = tmp_path.resolve().as_posix()
    request_path = (tmp_path / "request.json").resolve().as_posix()
    receipt_path = (tmp_path / "started.json").resolve().as_posix()
    expected = "e" * 64
    assert registration.registered_command_identity(
        root, request_path, expected, receipt_path
    ) == [
        Path(sys.executable).resolve().as_posix(),
        "-I",
        Path(registration.__file__).resolve().as_posix(),
        "publish-registration",
        "--repo-root",
        root,
        "--request",
        request_path,
        "--expected-request-sha256",
        expected,
        "--receipt-path",
        receipt_path,
    ]


def test_expected_request_digest_rejects_self_digested_substitute(tmp_path):
    request = _request(tmp_path)
    trusted_digest = request["request_sha256"]
    request["preflight_sha256"] = "f" * 64
    request["request_sha256"] = registration.canonical_json_sha256(
        {key: value for key, value in request.items() if key != "request_sha256"}
    )

    with pytest.raises(registration.RegistrationBlocked, match="trusted digest"):
        _execute_request(
            tmp_path,
            request,
            expected_request_sha256=trusted_digest,
        )
    receipt = json.loads(
        Path(request["receipt_path"]).read_text(encoding="utf-8")
    )
    assert receipt["expected_request_sha256"] == trusted_digest


@pytest.mark.parametrize(
    "failure", ("malformed_request", "missing_request", "wrong_root", "nonisolated")
)
def test_pre_request_failures_leave_terminal_receipt(tmp_path, failure):
    request = _request(tmp_path)
    kwargs = {}
    if failure == "malformed_request":
        kwargs["request_bytes"] = b"{\n"
    elif failure == "missing_request":
        request_path = (tmp_path / "missing-request.json").resolve().as_posix()
        with pytest.raises(registration.RegistrationBlocked, match="request read"):
            registration._execute_registration(
                repo_root=tmp_path.resolve().as_posix(),
                trusted_repo_root=tmp_path.resolve().as_posix(),
                request_path=request_path,
                expected_request_sha256=request["request_sha256"],
                receipt_path=request["receipt_path"],
                isolated_mode=True,
            )
        receipt = json.loads(
            Path(request["receipt_path"]).read_text(encoding="utf-8")
        )
        assert receipt["expected_request_sha256"] == request["request_sha256"]
        assert not Path(request["output_path"]).exists()
        return
    elif failure == "wrong_root":
        kwargs["repo_root"] = (tmp_path / "wrong-root").resolve().as_posix()
        kwargs["trusted_repo_root"] = tmp_path.resolve().as_posix()
    else:
        kwargs["isolated_mode"] = False

    with pytest.raises(registration.RegistrationBlocked):
        _execute_request(tmp_path, request, **kwargs)
    receipt = json.loads(
        Path(request["receipt_path"]).read_text(encoding="utf-8")
    )
    assert receipt["expected_request_sha256"] == request["request_sha256"]
    assert not Path(request["output_path"]).exists()


def test_driver_receipt_precedes_exact_one_open_and_no_enumeration(
    tmp_path, monkeypatch
):
    request = _request(tmp_path)
    artifact, calls = _stub_validators(monkeypatch)
    receipt_path = Path(request["receipt_path"])
    opened = []
    original_read = registration._read_bound_file_once

    def observed_read(name, binding):
        assert receipt_path.is_file()
        opened.append(name)
        return original_read(name, binding)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("registration driver attempted directory discovery")

    monkeypatch.setattr(registration, "_read_bound_file_once", observed_read)
    monkeypatch.setattr(Path, "iterdir", forbidden)
    monkeypatch.setattr(Path, "glob", forbidden)
    monkeypatch.setattr(Path, "rglob", forbidden)
    monkeypatch.setattr(os, "walk", forbidden)

    result = _execute_request(tmp_path, request)

    assert opened == list(registration.INPUT_NAMES)
    assert result["access_counts"] == {name: 1 for name in registration.INPUT_NAMES}
    assert result["producer_validated"] is True
    assert result["standalone_validated"] is True
    assert result["request_access_count"] == 1
    assert Path(request["output_path"]).read_bytes() == _json_bytes(artifact)
    assert [name for name, *_rest in calls] == [
        "build",
        "producer",
        "standalone",
    ]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["expected_request_sha256"] == request["request_sha256"]
    assert request["request_sha256"] == registration.canonical_json_sha256(
        {key: value for key, value in request.items() if key != "request_sha256"}
    )


def test_driver_end_to_end_success_uses_real_composed_validators(
    tmp_path, monkeypatch
):
    helpers = runpy.run_path(
        str(
            ROOT
            / "tests"
            / "test_noncombat_card_acceptance_empirical_successor_seed_inventory.py"
        )
    )
    source_inventory = copy.deepcopy(helpers["_SOURCE_INVENTORY"])
    monkeypatch.setattr(
        helpers["control"],
        "build_source_inventory",
        lambda _repo_root: copy.deepcopy(source_inventory),
    )
    evidence = helpers["_registration_evidence"](tmp_path)
    inventory = evidence["inventory"]
    repo = tmp_path / "repo"
    output = Path(inventory["authority_evidence"]["request"]["output_root"])
    attempts = output.with_name(f"{output.name}_attempts")
    build_receipt_path = (
        attempts / evidence["build_receipt"]["request_sha256"] / "started.json"
    )
    verification_receipt_path = (
        attempts
        / evidence["verification_receipt"]["request_sha256"]
        / "started.json"
    )
    r6_root = repo / "reports" / "registration-e2e"
    r6_root.mkdir()
    completion_path = r6_root / "verification_completion.json"
    standalone_path = r6_root / "standalone_result.json"
    review_path = r6_root / "verification_review.json"
    completion_path.write_bytes(_json_bytes(evidence["verification_completion"]))
    standalone_path.write_bytes(_json_bytes(evidence["standalone_result"]))
    review_path.write_bytes(
        _json_bytes({"review": "No findings", "verified": True})
    )
    paths = {
        "inventory": output / "seed_inventory.json",
        "build_receipt": build_receipt_path,
        "verification_receipt": verification_receipt_path,
        "verification_completion": completion_path,
        "standalone_result": standalone_path,
        "verification_review": review_path,
    }
    bindings = {}
    for name, path in paths.items():
        payload = path.read_bytes()
        bindings[name] = {
            "content_kind": "canonical_json",
            "path": path.resolve().as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    request = registration.build_registration_request(
        implementation_source_commit="a" * 40,
        inventory_source_commit=inventory["repository_commit"],
        preflight_sha256="c" * 64,
        input_bindings=bindings,
        receipt_path=(r6_root / "started.json").resolve().as_posix(),
        output_path=(r6_root / "registration.json").resolve().as_posix(),
    )
    request_path = r6_root / "request.json"
    request_path.write_bytes(_json_bytes(request))

    result = registration._execute_registration(
        repo_root=repo.resolve().as_posix(),
        trusted_repo_root=repo.resolve().as_posix(),
        request_path=request_path.resolve().as_posix(),
        expected_request_sha256=request["request_sha256"],
        receipt_path=request["receipt_path"],
        isolated_mode=True,
    )

    artifact = json.loads(Path(request["output_path"]).read_text(encoding="ascii"))
    assert result["request_access_count"] == 1
    assert result["access_counts"] == {name: 1 for name in registration.INPUT_NAMES}
    assert result["registration_sha256"] == artifact["registration_sha256"]
    assert artifact["cohorts"] == inventory["cohorts"]
    assert artifact["authority"] == {
        key: False for key in sorted(registration.producer.REGISTRATION_AUTHORITY_KEYS)
    }


def test_driver_rejects_symlink_before_input_open(tmp_path, monkeypatch):
    request = _request(tmp_path)
    _stub_validators(monkeypatch)
    target = Path(request["input_bindings"]["inventory"]["path"])
    original_is_symlink = Path.is_symlink
    opened = []

    def is_symlink(path):
        if path == target:
            return True
        return original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", is_symlink)
    monkeypatch.setattr(
        registration,
        "_read_bound_file_once",
        lambda name, binding: opened.append(name),
    )

    with pytest.raises(registration.RegistrationBlocked, match="symlink"):
        _execute_request(tmp_path, request)
    assert opened == []
    assert Path(request["receipt_path"]).is_file()
    assert not Path(request["output_path"]).exists()


def test_driver_rejects_existing_receipt_before_input_open(tmp_path, monkeypatch):
    request = _request(tmp_path)
    Path(request["receipt_path"]).write_bytes(b"partial")
    opened = []
    monkeypatch.setattr(
        registration,
        "_read_bound_file_once",
        lambda name, binding: opened.append(name),
    )

    with pytest.raises(registration.RegistrationBlocked, match="already exists"):
        _execute_request(tmp_path, request)
    assert opened == []
    assert Path(request["receipt_path"]).read_bytes() == b"partial"


def test_driver_exposes_no_independent_start_or_publish_stage():
    assert not hasattr(registration, "_start_registration_invocation")
    assert not hasattr(registration, "_publish_registration")


def test_driver_rejects_hardlink_alias_before_input_open(tmp_path, monkeypatch):
    request = _request(tmp_path)
    source = Path(request["input_bindings"]["verification_completion"]["path"])
    alias = Path(request["input_bindings"]["standalone_result"]["path"])
    alias.unlink()
    os.link(source, alias)
    payload = alias.read_bytes()
    request["input_bindings"]["standalone_result"].update(
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
    request["request_sha256"] = registration.canonical_json_sha256(
        {key: value for key, value in request.items() if key != "request_sha256"}
    )
    opened = []
    monkeypatch.setattr(
        registration,
        "_read_bound_file_once",
        lambda name, binding: opened.append(name),
    )

    with pytest.raises(registration.RegistrationBlocked, match="alias"):
        _execute_request(tmp_path, request)
    assert opened == []
    assert Path(request["receipt_path"]).is_file()


def test_driver_preserves_output_collision_after_receipt(tmp_path, monkeypatch):
    request = _request(tmp_path)
    _stub_validators(monkeypatch)
    output = Path(request["output_path"])
    output.write_bytes(b"existing")

    with pytest.raises(registration.RegistrationBlocked, match="already exists"):
        _execute_request(tmp_path, request)
    assert Path(request["receipt_path"]).is_file()
    assert output.read_bytes() == b"existing"


class _WriteProbe:
    def __init__(self, *, write_result=None, flush_error=None, fileno=123):
        self.write_result = write_result
        self.flush_error = flush_error
        self._fileno = fileno
        self.flushed = False

    def write(self, payload):
        return len(payload) if self.write_result is None else self.write_result

    def flush(self):
        self.flushed = True
        if self.flush_error is not None:
            raise self.flush_error

    def fileno(self):
        return self._fileno


def test_exclusive_write_rejects_short_write():
    handle = _WriteProbe(write_result=2)
    with pytest.raises(registration.RegistrationBlocked, match="short write"):
        registration._write_flush_fsync(handle, b"three", "registration")
    assert handle.flushed is False


def test_exclusive_write_wraps_flush_and_fsync_failures(monkeypatch):
    with pytest.raises(registration.RegistrationBlocked, match="flush"):
        registration._write_flush_fsync(
            _WriteProbe(flush_error=OSError("flush denied")),
            b"payload",
            "registration",
        )

    monkeypatch.setattr(
        os, "fsync", lambda _fileno: (_ for _ in ()).throw(OSError("fsync denied"))
    )
    with pytest.raises(registration.RegistrationBlocked, match="fsync"):
        registration._write_flush_fsync(
            _WriteProbe(), b"payload", "registration"
        )

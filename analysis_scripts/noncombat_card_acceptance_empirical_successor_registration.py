"""One-shot publication of the card-acceptance inventory registration."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PureWindowsPath
from typing import Any, BinaryIO


def _bootstrap_direct_script_imports() -> None:
    if __package__:
        return
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root in sys.path:
        sys.path.remove(repo_root)
    sys.path.insert(0, repo_root)


if __name__ == "__main__":
    _bootstrap_direct_script_imports()


from analysis_scripts import (  # noqa: E402
    noncombat_card_acceptance_empirical_successor_seed_inventory as producer,
)
from analysis_scripts import (  # noqa: E402
    verify_noncombat_card_acceptance_empirical_successor as standalone,
)


REQUEST_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-registration-request-v1"
)
REQUEST_ID = (
    "noncombat-card-acceptance-empirical-successor-20260811-r6-"
    "registration-request-v1"
)
REGISTRATION_SCHEMA_VERSION = producer.REGISTRATION_SCHEMA_VERSION
REGISTRATION_ID = producer.REGISTRATION_ID
STARTED_RECEIPT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-registration-started-receipt-v1"
)
COMPLETION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-registration-completion-v1"
)
REQUEST_MAX_BYTES = 64 * 1024
INPUT_MAX_BYTES = 64 * 1024 * 1024

INPUT_NAMES = (
    "inventory",
    "build_receipt",
    "verification_receipt",
    "verification_completion",
    "standalone_result",
    "verification_review",
)
JSON_INPUT_NAMES = frozenset(INPUT_NAMES)
_INPUT_BINDING_FIELDS = {"content_kind", "path", "sha256", "size_bytes"}
_REQUEST_FIELDS = {
    "downstream_authority",
    "implementation_source_commit",
    "input_bindings",
    "inventory_source_commit",
    "output_path",
    "preflight_sha256",
    "receipt_path",
    "registration_id",
    "registration_schema_version",
    "request_id",
    "request_sha256",
    "schema_version",
}
_RECEIPT_FIELDS = {
    "command_identity",
    "expected_request_sha256",
    "receipt_path",
    "receipt_sha256",
    "registration_id",
    "registration_schema_version",
    "request_id",
    "schema_version",
}
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")


class RegistrationBlocked(RuntimeError):
    """Raised when the frozen registration boundary cannot be satisfied."""


def canonical_json_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise RegistrationBlocked("value is not canonical JSON") from exc


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RegistrationBlocked(f"{label} must be a mapping")
    return copy.deepcopy(dict(value))


def _exact_fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise RegistrationBlocked(f"{label} fields mismatch")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RegistrationBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise RegistrationBlocked(f"non-finite JSON constant: {value}")


def _parse_json_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise RegistrationBlocked(f"non-finite JSON number: {value}")
    return result


def _strict_mapping_bytes(payload: bytes, label: str) -> dict[str, Any]:
    if not isinstance(payload, bytes):
        raise RegistrationBlocked(f"{label} must be bytes")
    try:
        decoded = payload.decode("utf-8", errors="strict")
        value = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
            parse_float=_parse_json_float,
        )
    except RegistrationBlocked:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistrationBlocked(f"{label} is invalid strict JSON") from exc
    mapping = _mapping(value, label)
    if payload != canonical_json_bytes(mapping):
        raise RegistrationBlocked(f"{label} is not canonical")
    return mapping


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise RegistrationBlocked(f"{label} must be 64 lowercase hex characters")
    return value


def _commit(value: object, label: str) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise RegistrationBlocked(f"{label} must be 40 lowercase hex characters")
    return value


def _absolute_lexical_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise RegistrationBlocked(f"{label} must be an absolute canonical path")
    path = PureWindowsPath(value)
    if (
        not path.is_absolute()
        or path.as_posix() != value
        or "." in path.parts
        or ".." in path.parts
    ):
        raise RegistrationBlocked(f"{label} must be an absolute canonical path")
    return value


def _all_false_downstream(value: object) -> dict[str, bool]:
    downstream = _mapping(value, "downstream authority")
    _exact_fields(
        downstream,
        producer.REGISTRATION_AUTHORITY_KEYS,
        "downstream authority",
    )
    if any(item is not False for item in downstream.values()):
        raise RegistrationBlocked("downstream authority must contain only false booleans")
    return downstream


def validate_registration_request(value: object) -> dict[str, Any]:
    request = _mapping(value, "registration request")
    _exact_fields(request, _REQUEST_FIELDS, "registration request")
    if (
        request["schema_version"] != REQUEST_SCHEMA_VERSION
        or request["request_id"] != REQUEST_ID
        or request["registration_id"] != REGISTRATION_ID
        or request["registration_schema_version"] != REGISTRATION_SCHEMA_VERSION
    ):
        raise RegistrationBlocked("registration request identity mismatch")
    request["implementation_source_commit"] = _commit(
        request["implementation_source_commit"], "implementation source commit"
    )
    request["inventory_source_commit"] = _commit(
        request["inventory_source_commit"], "inventory source commit"
    )
    request["preflight_sha256"] = _digest(
        request["preflight_sha256"], "preflight digest"
    )
    request["receipt_path"] = _absolute_lexical_path(
        request["receipt_path"], "receipt path"
    )
    request["output_path"] = _absolute_lexical_path(
        request["output_path"], "output path"
    )
    if request["receipt_path"] == request["output_path"]:
        raise RegistrationBlocked("receipt and output paths must differ")
    raw_bindings = _mapping(request["input_bindings"], "input bindings")
    _exact_fields(raw_bindings, set(INPUT_NAMES), "input bindings")
    bindings: dict[str, dict[str, Any]] = {}
    paths: set[str] = {request["receipt_path"], request["output_path"]}
    for name in INPUT_NAMES:
        binding = _mapping(raw_bindings[name], f"input binding {name}")
        _exact_fields(binding, _INPUT_BINDING_FIELDS, f"input binding {name}")
        if binding["content_kind"] != "canonical_json":
            raise RegistrationBlocked(f"input binding {name} content kind mismatch")
        binding["path"] = _absolute_lexical_path(
            binding["path"], f"input binding {name} path"
        )
        binding["sha256"] = _digest(
            binding["sha256"], f"input binding {name} digest"
        )
        size = binding["size_bytes"]
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size <= 0
            or size > INPUT_MAX_BYTES
        ):
            raise RegistrationBlocked(f"input binding {name} size is invalid")
        if binding["path"] in paths:
            raise RegistrationBlocked("input binding paths must be unique")
        paths.add(binding["path"])
        bindings[name] = binding
    downstream = _all_false_downstream(request["downstream_authority"])
    normalized = {
        **request,
        "downstream_authority": downstream,
        "input_bindings": bindings,
    }
    body = {key: item for key, item in normalized.items() if key != "request_sha256"}
    if _digest(normalized["request_sha256"], "registration request digest") != (
        canonical_json_sha256(body)
    ):
        raise RegistrationBlocked("registration request digest mismatch")
    return normalized


def build_registration_request(
    *,
    implementation_source_commit: str,
    inventory_source_commit: str,
    preflight_sha256: str,
    input_bindings: object,
    receipt_path: str,
    output_path: str,
) -> dict[str, Any]:
    body = {
        "downstream_authority": {
            key: False for key in sorted(producer.REGISTRATION_AUTHORITY_KEYS)
        },
        "implementation_source_commit": implementation_source_commit,
        "input_bindings": copy.deepcopy(input_bindings),
        "inventory_source_commit": inventory_source_commit,
        "output_path": output_path,
        "preflight_sha256": preflight_sha256,
        "receipt_path": receipt_path,
        "registration_id": REGISTRATION_ID,
        "registration_schema_version": REGISTRATION_SCHEMA_VERSION,
        "request_id": REQUEST_ID,
        "schema_version": REQUEST_SCHEMA_VERSION,
    }
    return validate_registration_request(
        {**body, "request_sha256": canonical_json_sha256(body)}
    )


def parse_canonical_request_bytes(payload: bytes) -> dict[str, Any]:
    if len(payload) > REQUEST_MAX_BYTES:
        raise RegistrationBlocked("registration request exceeds byte limit")
    return validate_registration_request(
        _strict_mapping_bytes(payload, "registration request")
    )


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_bound_file_once(name: str, binding: Mapping[str, Any]) -> bytes:
    path = Path(binding["path"])
    if path.is_symlink():
        raise RegistrationBlocked(f"input {name} must not be a symlink")
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise RegistrationBlocked(f"input {name} must be a regular file")
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if _file_identity(before) != _file_identity(opened):
                raise RegistrationBlocked(f"input {name} identity changed before read")
            payload = handle.read(INPUT_MAX_BYTES + 1)
            closed = os.fstat(handle.fileno())
        after = path.stat()
    except RegistrationBlocked:
        raise
    except OSError as exc:
        raise RegistrationBlocked(f"input {name} read failed: {exc}") from exc
    if (
        _file_identity(opened) != _file_identity(closed)
        or _file_identity(closed) != _file_identity(after)
    ):
        raise RegistrationBlocked(f"input {name} identity changed during read")
    if (
        len(payload) != binding["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != binding["sha256"]
    ):
        raise RegistrationBlocked(f"input {name} byte identity mismatch")
    return payload


def _write_flush_fsync(handle: BinaryIO, payload: bytes, label: str) -> None:
    try:
        written = handle.write(payload)
    except OSError as exc:
        raise RegistrationBlocked(f"{label} write failed: {exc}") from exc
    if written != len(payload):
        raise RegistrationBlocked(f"{label} short write")
    try:
        handle.flush()
    except OSError as exc:
        raise RegistrationBlocked(f"{label} flush failed: {exc}") from exc
    try:
        os.fsync(handle.fileno())
    except OSError as exc:
        raise RegistrationBlocked(f"{label} fsync failed: {exc}") from exc


def _publish_exclusive(path: Path, payload: bytes, label: str) -> None:
    try:
        with path.open("xb") as handle:
            _write_flush_fsync(handle, payload, label)
    except FileExistsError as exc:
        raise RegistrationBlocked(f"{label} already exists") from exc
    except RegistrationBlocked:
        raise
    except OSError as exc:
        raise RegistrationBlocked(f"{label} publication failed: {exc}") from exc


def _command_identity(value: object) -> list[str]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise RegistrationBlocked("command identity is invalid")
    return list(value)


def _invocation_receipt(
    *,
    command_identity: object,
    expected_request_sha256: object,
    receipt_path: object,
) -> dict[str, Any]:
    body = {
        "command_identity": _command_identity(command_identity),
        "expected_request_sha256": _digest(
            expected_request_sha256, "expected registration request digest"
        ),
        "receipt_path": _absolute_lexical_path(receipt_path, "receipt path"),
        "registration_id": REGISTRATION_ID,
        "registration_schema_version": REGISTRATION_SCHEMA_VERSION,
        "request_id": REQUEST_ID,
        "schema_version": STARTED_RECEIPT_SCHEMA_VERSION,
    }
    receipt = {**body, "receipt_sha256": canonical_json_sha256(body)}
    _exact_fields(receipt, _RECEIPT_FIELDS, "registration started receipt")
    return receipt


def registered_command_identity(
    repo_root: str,
    request_path: str,
    expected_request_sha256: str,
    receipt_path: str,
) -> list[str]:
    return [
        Path(sys.executable).resolve().as_posix(),
        "-I",
        Path(__file__).resolve().as_posix(),
        "publish-registration",
        "--repo-root",
        _absolute_lexical_path(repo_root, "repository root"),
        "--request",
        _absolute_lexical_path(request_path, "request path"),
        "--expected-request-sha256",
        _digest(expected_request_sha256, "expected registration request digest"),
        "--receipt-path",
        _absolute_lexical_path(receipt_path, "receipt path"),
    ]


def _require_distinct_regular_inputs(request: Mapping[str, Any]) -> None:
    identities: set[tuple[int, int]] = set()
    for name in INPUT_NAMES:
        path = Path(request["input_bindings"][name]["path"])
        if path.is_symlink():
            raise RegistrationBlocked(f"input {name} must not be a symlink")
        try:
            observed = path.stat()
        except OSError as exc:
            raise RegistrationBlocked(f"input {name} identity read failed: {exc}") from exc
        if not stat.S_ISREG(observed.st_mode):
            raise RegistrationBlocked(f"input {name} must be a regular file")
        if path.resolve().as_posix() != request["input_bindings"][name]["path"]:
            raise RegistrationBlocked(f"input {name} path resolution differs")
        identity = (observed.st_dev, observed.st_ino)
        if identity in identities:
            raise RegistrationBlocked("input paths contain a file alias")
        identities.add(identity)


def _read_request_once(path: Path) -> bytes:
    if path.is_symlink():
        raise RegistrationBlocked("registration request must not be a symlink")
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > REQUEST_MAX_BYTES:
            raise RegistrationBlocked("registration request file is invalid")
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if _file_identity(before) != _file_identity(opened):
                raise RegistrationBlocked("registration request identity changed")
            payload = handle.read(REQUEST_MAX_BYTES + 1)
            closed = os.fstat(handle.fileno())
        after = path.stat()
    except RegistrationBlocked:
        raise
    except OSError as exc:
        raise RegistrationBlocked(f"registration request read failed: {exc}") from exc
    if (
        _file_identity(opened) != _file_identity(closed)
        or _file_identity(closed) != _file_identity(after)
    ):
        raise RegistrationBlocked("registration request identity changed during read")
    return payload


def _require_paths_within_repo(request: Mapping[str, Any], repo_root: Path) -> None:
    for label, raw in (
        ("receipt", request["receipt_path"]),
        ("output", request["output_path"]),
        *((name, request["input_bindings"][name]["path"]) for name in INPUT_NAMES),
    ):
        try:
            Path(raw).resolve().relative_to(repo_root)
        except ValueError as exc:
            raise RegistrationBlocked(f"{label} path is outside repository") from exc


def _execute_registration(
    *,
    repo_root: str,
    trusted_repo_root: str,
    request_path: str,
    expected_request_sha256: str,
    receipt_path: str,
    isolated_mode: bool,
) -> dict[str, Any]:
    """Execute the registered CLI lifecycle with a pre-request durable receipt."""
    command = registered_command_identity(
        repo_root,
        request_path,
        expected_request_sha256,
        receipt_path,
    )
    receipt = _invocation_receipt(
        command_identity=command,
        expected_request_sha256=expected_request_sha256,
        receipt_path=receipt_path,
    )
    receipt_payload = canonical_json_bytes(receipt)
    handle: BinaryIO | None = None
    try:
        try:
            handle = Path(receipt["receipt_path"]).open("x+b")
        except FileExistsError as exc:
            raise RegistrationBlocked(
                "registration started receipt already exists"
            ) from exc
        _write_flush_fsync(
            handle, receipt_payload, "registration started receipt"
        )
        handle.seek(0)
        if handle.read(len(receipt_payload) + 1) != receipt_payload:
            raise RegistrationBlocked(
                "registration started receipt canonical readback mismatch"
            )
        receipt_identity = _file_identity(os.fstat(handle.fileno()))

        if not isolated_mode:
            raise RegistrationBlocked(
                "registration driver requires Python isolated mode"
            )
        resolved_root = Path(repo_root).resolve()
        trusted_root = Path(trusted_repo_root).resolve()
        if resolved_root != trusted_root:
            raise RegistrationBlocked("registration repository root differs")
        request_file = Path(request_path)
        if request_file.resolve().as_posix() != request_path:
            raise RegistrationBlocked("registration request path resolution differs")
        request = parse_canonical_request_bytes(_read_request_once(request_file))
        if request["receipt_path"] != receipt_path:
            raise RegistrationBlocked("registration request receipt path differs")
        _require_paths_within_repo(request, trusted_root)

        expected_digest = _digest(
            expected_request_sha256, "expected registration request digest"
        )
        if request["request_sha256"] != expected_digest:
            raise RegistrationBlocked("registration request trusted digest mismatch")
        receipt_body = {
            key: item for key, item in receipt.items() if key != "receipt_sha256"
        }
        if (
            receipt["schema_version"] != STARTED_RECEIPT_SCHEMA_VERSION
            or receipt["request_id"] != REQUEST_ID
            or receipt["registration_id"] != REGISTRATION_ID
            or receipt["registration_schema_version"]
            != REGISTRATION_SCHEMA_VERSION
            or receipt["expected_request_sha256"] != expected_digest
            or receipt["receipt_path"] != request["receipt_path"]
            or _digest(receipt["receipt_sha256"], "registration receipt digest")
            != canonical_json_sha256(receipt_body)
        ):
            raise RegistrationBlocked(
                "registration started receipt binding mismatch"
            )
        current_receipt_identity = _file_identity(os.fstat(handle.fileno()))
        handle.seek(0)
        if (
            current_receipt_identity != receipt_identity
            or handle.read(len(receipt_payload) + 1) != receipt_payload
        ):
            raise RegistrationBlocked("registration started receipt bytes changed")

        _require_distinct_regular_inputs(request)
        evidence: dict[str, dict[str, Any]] = {}
        access_counts: dict[str, int] = {}
        for name in INPUT_NAMES:
            input_payload = _read_bound_file_once(
                name, request["input_bindings"][name]
            )
            access_counts[name] = access_counts.get(name, 0) + 1
            evidence[name] = producer.parse_canonical_mapping_bytes(
                input_payload, name
            )
        if access_counts != {name: 1 for name in INPUT_NAMES}:
            raise RegistrationBlocked(
                "registration input access accounting mismatch"
            )
        if (
            evidence["inventory"].get("repository_commit")
            != request["inventory_source_commit"]
        ):
            raise RegistrationBlocked(
                "inventory source commit request binding mismatch"
            )

        reconstructed_standalone = standalone.verify_seed_inventory_evidence(
            evidence["inventory"]
        )
        artifact = producer.build_inventory_registration(
            inventory=evidence["inventory"],
            build_receipt=evidence["build_receipt"],
            verification_receipt=evidence["verification_receipt"],
            verification_completion=evidence["verification_completion"],
            standalone_result=reconstructed_standalone,
        )
        producer_validated = producer.validate_inventory_registration(
            artifact,
            evidence["inventory"],
            expected_receipt_sha256=evidence["build_receipt"].get(
                "receipt_sha256"
            ),
        )
        standalone_validated = standalone.verify_inventory_registration(
            artifact, evidence["inventory"]
        )
        if (
            producer_validated != artifact
            or standalone_validated.get("verified") is not True
            or standalone_validated.get("registration_sha256")
            != artifact.get("registration_sha256")
        ):
            raise RegistrationBlocked(
                "registration validator agreement mismatch"
            )
        output_payload = producer.canonical_json_bytes(artifact)
        if (
            producer.parse_canonical_mapping_bytes(
                output_payload, "inventory registration"
            )
            != artifact
        ):
            raise RegistrationBlocked(
                "producer canonical registration mismatch"
            )
        standalone.parse_canonical_registration_bytes(output_payload)
        _publish_exclusive(
            Path(request["output_path"]),
            output_payload,
            "inventory registration",
        )
        return {
            "access_counts": access_counts,
            "completion_schema_version": COMPLETION_SCHEMA_VERSION,
            "output_sha256": hashlib.sha256(output_payload).hexdigest(),
            "producer_validated": True,
            "receipt_sha256": receipt["receipt_sha256"],
            "registration_sha256": artifact["registration_sha256"],
            "request_access_count": 1,
            "standalone_validated": True,
        }
    finally:
        if handle is not None:
            handle.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    publish = subparsers.add_parser("publish-registration")
    publish.add_argument("--repo-root", required=True)
    publish.add_argument("--request", required=True)
    publish.add_argument("--expected-request-sha256", required=True)
    publish.add_argument("--receipt-path", required=True)
    args = parser.parse_args(argv)
    try:
        result = _execute_registration(
            repo_root=args.repo_root,
            trusted_repo_root=Path(__file__).resolve().parents[1].as_posix(),
            request_path=args.request,
            expected_request_sha256=args.expected_request_sha256,
            receipt_path=args.receipt_path,
            isolated_mode=bool(sys.flags.isolated),
        )
    except (OSError, RegistrationBlocked, producer.SeedInventoryBlocked, standalone.VerificationError) as exc:
        parser.error(str(exc))
    payload = canonical_json_bytes(result)
    if sys.stdout.buffer.write(payload) != len(payload):
        raise OSError("registration completion stdout write was incomplete")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPLETION_SCHEMA_VERSION",
    "INPUT_NAMES",
    "JSON_INPUT_NAMES",
    "REGISTRATION_ID",
    "REGISTRATION_SCHEMA_VERSION",
    "REQUEST_ID",
    "REQUEST_SCHEMA_VERSION",
    "RegistrationBlocked",
    "build_registration_request",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "parse_canonical_request_bytes",
    "registered_command_identity",
    "validate_registration_request",
]

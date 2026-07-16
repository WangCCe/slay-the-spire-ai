"""Fail-closed CommunicationMod handshake for registered study children."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HANDSHAKE_ATTEMPT_ENV = "STS_OUTCOME_EVIDENCE_HANDSHAKE_ATTEMPT"
HANDSHAKE_SCHEMA_VERSION = "noncombat-outcome-evidence-handshake-v1"
ATTEMPT_SCHEMA_VERSION = "noncombat-outcome-evidence-handshake-attempt-v1"
READY_SCHEMA_VERSION = "noncombat-outcome-evidence-handshake-ready-v1"
RELEASE_SCHEMA_VERSION = "noncombat-outcome-evidence-handshake-release-v1"
READINESS_TIMEOUT_SECONDS = 30
RELEASE_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 0.05


class StudyHandshakeError(ValueError):
    """Raised when a registered child handshake cannot be proven exactly."""


class _DuplicateJsonKeyError(ValueError):
    pass


@dataclass(frozen=True)
class HandshakePaths:
    attempt: Path
    ready: Path
    release: Path


def derive_slot_token(
    *,
    registration_hash: str,
    run_lock_hash: str,
    slot_number: int,
    session_id: str,
    config_sha256: str,
) -> str:
    body = {
        "config_sha256": _required_sha256(config_sha256, "config_sha256"),
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "registration_hash": _required_sha256(
            registration_hash,
            "registration_hash",
        ),
        "run_lock_hash": _required_sha256(run_lock_hash, "run_lock_hash"),
        "session_id": _required_string(session_id, "session_id"),
        "slot_number": _positive_int(slot_number, "slot_number"),
    }
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def build_attempt_record(
    *,
    study_id: str,
    registration_hash: str,
    run_lock_hash: str,
    slot_number: int,
    session_id: str,
    config_path: Path | str,
    config_sha256: str,
    marker_start_count: int,
    paths: HandshakePaths,
    readiness_timeout_seconds: int,
    release_timeout_seconds: int,
    created_unix_ns: int,
) -> dict[str, Any]:
    if not isinstance(paths, HandshakePaths):
        raise StudyHandshakeError("paths must be HandshakePaths")
    attempt_path = _absolute_path(paths.attempt, "attempt path")
    ready_path = _absolute_path(paths.ready, "ready path")
    release_path = _absolute_path(paths.release, "release path")
    resolved_config_path = _absolute_path(config_path, "config path")
    if len({attempt_path, ready_path, release_path}) != 3:
        raise StudyHandshakeError("handshake paths must be distinct")
    if len({path.parent for path in (attempt_path, ready_path, release_path)}) != 1:
        raise StudyHandshakeError("handshake paths must share one parent")
    if resolved_config_path.parent != attempt_path.parent:
        raise StudyHandshakeError("config and handshake paths must share one parent")
    readiness_timeout = _exact_int(
        readiness_timeout_seconds,
        "readiness timeout",
    )
    release_timeout = _exact_int(
        release_timeout_seconds,
        "release timeout",
    )
    if readiness_timeout != READINESS_TIMEOUT_SECONDS:
        raise StudyHandshakeError(
            f"readiness timeout must be {READINESS_TIMEOUT_SECONDS} seconds"
        )
    if release_timeout != RELEASE_TIMEOUT_SECONDS:
        raise StudyHandshakeError(
            f"release timeout must be {RELEASE_TIMEOUT_SECONDS} seconds"
        )
    normalized_registration_hash = _required_sha256(
        registration_hash,
        "registration_hash",
    )
    normalized_run_lock_hash = _required_sha256(run_lock_hash, "run_lock_hash")
    normalized_config_hash = _required_sha256(config_sha256, "config_sha256")
    normalized_slot = _positive_int(slot_number, "slot_number")
    normalized_session = _required_string(session_id, "session_id")
    record = {
        "attempt_hash": None,
        "attempt_path": str(attempt_path),
        "config_path": str(resolved_config_path),
        "config_sha256": normalized_config_hash,
        "created_unix_ns": _nonnegative_int(created_unix_ns, "created_unix_ns"),
        "marker_start_count": _nonnegative_int(
            marker_start_count,
            "marker_start_count",
        ),
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "readiness_timeout_seconds": readiness_timeout,
        "ready_path": str(ready_path),
        "registration_hash": normalized_registration_hash,
        "release_path": str(release_path),
        "release_timeout_seconds": release_timeout,
        "run_lock_hash": normalized_run_lock_hash,
        "schema_version": ATTEMPT_SCHEMA_VERSION,
        "session_id": normalized_session,
        "slot_number": normalized_slot,
        "slot_token": derive_slot_token(
            registration_hash=normalized_registration_hash,
            run_lock_hash=normalized_run_lock_hash,
            slot_number=normalized_slot,
            session_id=normalized_session,
            config_sha256=normalized_config_hash,
        ),
        "study_id": _required_string(study_id, "study_id"),
    }
    record["attempt_hash"] = _self_hash(record, "attempt_hash")
    return _validate_attempt_record(record)


def build_ready_record(
    attempt: Mapping[str, Any],
    *,
    child_pid: int,
    created_unix_ns: int,
) -> dict[str, Any]:
    bound_attempt = _validate_attempt_record(attempt)
    record = {
        "attempt_hash": bound_attempt["attempt_hash"],
        "child_pid": _positive_int(child_pid, "child_pid"),
        "communication_state_received": True,
        "config_path": bound_attempt["config_path"],
        "config_sha256": bound_attempt["config_sha256"],
        "created_unix_ns": _nonnegative_int(created_unix_ns, "created_unix_ns"),
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "ready_hash": None,
        "ready_path": bound_attempt["ready_path"],
        "registration_hash": bound_attempt["registration_hash"],
        "run_lock_hash": bound_attempt["run_lock_hash"],
        "schema_version": READY_SCHEMA_VERSION,
        "session_id": bound_attempt["session_id"],
        "slot_number": bound_attempt["slot_number"],
        "slot_token": bound_attempt["slot_token"],
        "study_id": bound_attempt["study_id"],
    }
    record["ready_hash"] = _self_hash(record, "ready_hash")
    return _validate_ready_shape(record)


def validate_ready_record(
    record: Mapping[str, Any],
    *,
    attempt: Mapping[str, Any],
    child_pid: int,
) -> dict[str, Any]:
    ready = _validate_ready_shape(record)
    bound_attempt = _validate_attempt_record(attempt)
    expected = build_ready_record(
        bound_attempt,
        child_pid=child_pid,
        created_unix_ns=ready["created_unix_ns"],
    )
    if ready != expected:
        raise StudyHandshakeError("ready binding mismatch")
    return ready


def build_release_record(
    attempt: Mapping[str, Any],
    ready: Mapping[str, Any],
    *,
    created_unix_ns: int,
) -> dict[str, Any]:
    bound_attempt = _validate_attempt_record(attempt)
    bound_ready = validate_ready_record(
        ready,
        attempt=bound_attempt,
        child_pid=_positive_int(ready.get("child_pid"), "child_pid"),
    )
    record = {
        "attempt_hash": bound_attempt["attempt_hash"],
        "child_pid": bound_ready["child_pid"],
        "created_unix_ns": _nonnegative_int(created_unix_ns, "created_unix_ns"),
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "ready_hash": bound_ready["ready_hash"],
        "registration_hash": bound_attempt["registration_hash"],
        "release_hash": None,
        "release_path": bound_attempt["release_path"],
        "run_lock_hash": bound_attempt["run_lock_hash"],
        "schema_version": RELEASE_SCHEMA_VERSION,
        "session_id": bound_attempt["session_id"],
        "slot_number": bound_attempt["slot_number"],
        "slot_token": bound_attempt["slot_token"],
        "study_id": bound_attempt["study_id"],
    }
    record["release_hash"] = _self_hash(record, "release_hash")
    return _validate_release_shape(record)


def validate_release_record(
    record: Mapping[str, Any],
    *,
    attempt: Mapping[str, Any],
    ready: Mapping[str, Any],
) -> dict[str, Any]:
    release = _validate_release_shape(record)
    try:
        bound_attempt = _validate_attempt_record(attempt)
        bound_ready = validate_ready_record(
            ready,
            attempt=bound_attempt,
            child_pid=_positive_int(ready.get("child_pid"), "child_pid"),
        )
    except StudyHandshakeError as exc:
        raise StudyHandshakeError("release binding mismatch") from exc
    expected = build_release_record(
        bound_attempt,
        bound_ready,
        created_unix_ns=release["created_unix_ns"],
    )
    if release != expected:
        raise StudyHandshakeError("release binding mismatch")
    return release


def publish_record_once(path: Path | str, record: Mapping[str, Any]) -> None:
    resolved_path = _absolute_path(path, "publication path")
    validated, expected_path = _validated_record_and_path(record)
    if resolved_path != expected_path:
        raise StudyHandshakeError("publication path does not match record")
    payload = (_canonical_json(validated) + "\n").encode("utf-8")
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = None
    temporary_path: Path | None = None
    try:
        descriptor, raw_temporary_path = tempfile.mkstemp(
            prefix=f".{resolved_path.name}.",
            suffix=".tmp",
            dir=resolved_path.parent,
        )
        temporary_path = Path(raw_temporary_path)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_path, resolved_path)
    except FileExistsError as exc:
        raise StudyHandshakeError(
            f"handshake artifact already exists: {resolved_path}"
        ) from exc
    except OSError as exc:
        raise StudyHandshakeError(
            f"cannot publish handshake artifact {resolved_path}: {exc}"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def load_attempt_record(path: Path | str) -> dict[str, Any]:
    return _validate_attempt_record(_load_record(path, "attempt"))


def load_ready_record(path: Path | str) -> dict[str, Any]:
    return _validate_ready_shape(_load_record(path, "ready"))


def load_release_record(path: Path | str) -> dict[str, Any]:
    return _validate_release_shape(_load_record(path, "release"))


def perform_child_handshake_if_configured(
    coordinator: Any,
    *,
    environ: Mapping[str, str] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    child_pid: int | None = None,
    created_unix_ns: Callable[[], int] = time.time_ns,
) -> bool:
    environment = os.environ if environ is None else environ
    raw_attempt_path = environment.get(HANDSHAKE_ATTEMPT_ENV)
    if raw_attempt_path is None:
        return False
    if not isinstance(raw_attempt_path, str) or not raw_attempt_path.strip():
        raise StudyHandshakeError("handshake attempt environment is empty")
    attempt_path = _absolute_path(raw_attempt_path, "attempt environment path")
    attempt = load_attempt_record(attempt_path)
    if attempt["attempt_path"] != str(attempt_path):
        raise StudyHandshakeError("attempt environment binding mismatch")
    ready_path = Path(attempt["ready_path"])
    release_path = Path(attempt["release_path"])
    if ready_path.exists() or release_path.exists():
        raise StudyHandshakeError("stale handshake artifact exists before child ready")
    config_path = Path(attempt["config_path"])
    try:
        config_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise StudyHandshakeError(f"cannot read registered config: {exc}") from exc
    if config_sha256 != attempt["config_sha256"]:
        raise StudyHandshakeError("registered config hash mismatch")
    resolved_pid = os.getpid() if child_pid is None else child_pid
    resolved_pid = _positive_int(resolved_pid, "child_pid")
    try:
        coordinator.start_input_thread()
    except Exception as exc:
        raise StudyHandshakeError(f"cannot start CommunicationMod input: {exc}") from exc

    readiness_deadline = monotonic() + attempt["readiness_timeout_seconds"]
    while True:
        try:
            received = coordinator.receive_game_state_update(
                block=False,
                perform_callbacks=False,
            )
        except Exception as exc:
            raise StudyHandshakeError(
                f"CommunicationMod state receive failed: {exc}"
            ) from exc
        if received:
            if getattr(coordinator, "last_error", None) is not None:
                raise StudyHandshakeError(
                    "CommunicationMod error before child readiness: "
                    + str(coordinator.last_error)
                )
            if getattr(coordinator, "last_game_state", None) is None:
                raise StudyHandshakeError(
                    "CommunicationMod state was not retained before child readiness"
                )
            break
        if monotonic() >= readiness_deadline:
            raise StudyHandshakeError("child readiness deadline exceeded")
        sleep(POLL_INTERVAL_SECONDS)

    ready = build_ready_record(
        attempt,
        child_pid=resolved_pid,
        created_unix_ns=_nonnegative_int(
            created_unix_ns(),
            "ready created_unix_ns",
        ),
    )
    publish_record_once(ready_path, ready)
    release_deadline = monotonic() + attempt["release_timeout_seconds"]
    while True:
        if release_path.exists():
            release = load_release_record(release_path)
            validate_release_record(release, attempt=attempt, ready=ready)
            return True
        if monotonic() >= release_deadline:
            raise StudyHandshakeError("child release deadline exceeded")
        sleep(POLL_INTERVAL_SECONDS)


def _validate_attempt_record(record: Mapping[str, Any]) -> dict[str, Any]:
    value = _mapping(record, "attempt record")
    expected_fields = {
        "attempt_hash",
        "attempt_path",
        "config_path",
        "config_sha256",
        "created_unix_ns",
        "marker_start_count",
        "protocol_version",
        "readiness_timeout_seconds",
        "ready_path",
        "registration_hash",
        "release_path",
        "release_timeout_seconds",
        "run_lock_hash",
        "schema_version",
        "session_id",
        "slot_number",
        "slot_token",
        "study_id",
    }
    if set(value) != expected_fields:
        raise StudyHandshakeError("attempt fields mismatch")
    if value.get("schema_version") != ATTEMPT_SCHEMA_VERSION:
        raise StudyHandshakeError("attempt schema mismatch")
    if value.get("protocol_version") != HANDSHAKE_SCHEMA_VERSION:
        raise StudyHandshakeError("attempt protocol mismatch")
    attempt_path = _absolute_path(value.get("attempt_path"), "attempt path")
    ready_path = _absolute_path(value.get("ready_path"), "ready path")
    release_path = _absolute_path(value.get("release_path"), "release path")
    config_path = _absolute_path(value.get("config_path"), "config path")
    if (
        len({attempt_path, ready_path, release_path}) != 3
        or len({path.parent for path in (attempt_path, ready_path, release_path)})
        != 1
        or config_path.parent != attempt_path.parent
    ):
        raise StudyHandshakeError("attempt path binding mismatch")
    readiness_timeout = _exact_int(
        value.get("readiness_timeout_seconds"),
        "readiness timeout",
    )
    release_timeout = _exact_int(
        value.get("release_timeout_seconds"),
        "release timeout",
    )
    if readiness_timeout != READINESS_TIMEOUT_SECONDS:
        raise StudyHandshakeError("attempt readiness timeout mismatch")
    if release_timeout != RELEASE_TIMEOUT_SECONDS:
        raise StudyHandshakeError("attempt release timeout mismatch")
    registration_hash = _required_sha256(
        value.get("registration_hash"),
        "registration_hash",
    )
    run_lock_hash = _required_sha256(value.get("run_lock_hash"), "run_lock_hash")
    config_sha256 = _required_sha256(value.get("config_sha256"), "config_sha256")
    slot_number = _positive_int(value.get("slot_number"), "slot_number")
    session_id = _required_string(value.get("session_id"), "session_id")
    _required_string(value.get("study_id"), "study_id")
    _nonnegative_int(value.get("created_unix_ns"), "created_unix_ns")
    _nonnegative_int(value.get("marker_start_count"), "marker_start_count")
    expected_token = derive_slot_token(
        registration_hash=registration_hash,
        run_lock_hash=run_lock_hash,
        slot_number=slot_number,
        session_id=session_id,
        config_sha256=config_sha256,
    )
    if value.get("slot_token") != expected_token:
        raise StudyHandshakeError("attempt slot token mismatch")
    if value.get("attempt_hash") != _self_hash(value, "attempt_hash"):
        raise StudyHandshakeError("attempt hash mismatch")
    return dict(value)


def _validate_ready_shape(record: Mapping[str, Any]) -> dict[str, Any]:
    value = _mapping(record, "ready record")
    expected_fields = {
        "attempt_hash",
        "child_pid",
        "communication_state_received",
        "config_path",
        "config_sha256",
        "created_unix_ns",
        "protocol_version",
        "ready_hash",
        "ready_path",
        "registration_hash",
        "run_lock_hash",
        "schema_version",
        "session_id",
        "slot_number",
        "slot_token",
        "study_id",
    }
    if set(value) != expected_fields:
        raise StudyHandshakeError("ready fields mismatch")
    if value.get("schema_version") != READY_SCHEMA_VERSION:
        raise StudyHandshakeError("ready schema mismatch")
    if value.get("protocol_version") != HANDSHAKE_SCHEMA_VERSION:
        raise StudyHandshakeError("ready protocol mismatch")
    _required_sha256(value.get("attempt_hash"), "attempt_hash")
    _positive_int(value.get("child_pid"), "child_pid")
    if value.get("communication_state_received") is not True:
        raise StudyHandshakeError("ready state proof mismatch")
    _absolute_path(value.get("config_path"), "config path")
    _required_sha256(value.get("config_sha256"), "config_sha256")
    _nonnegative_int(value.get("created_unix_ns"), "created_unix_ns")
    _absolute_path(value.get("ready_path"), "ready path")
    _required_sha256(value.get("registration_hash"), "registration_hash")
    _required_sha256(value.get("run_lock_hash"), "run_lock_hash")
    _required_string(value.get("session_id"), "session_id")
    _positive_int(value.get("slot_number"), "slot_number")
    _required_sha256(value.get("slot_token"), "slot_token")
    _required_string(value.get("study_id"), "study_id")
    if value.get("ready_hash") != _self_hash(value, "ready_hash"):
        raise StudyHandshakeError("ready hash mismatch")
    return dict(value)


def _validate_release_shape(record: Mapping[str, Any]) -> dict[str, Any]:
    value = _mapping(record, "release record")
    expected_fields = {
        "attempt_hash",
        "child_pid",
        "created_unix_ns",
        "protocol_version",
        "ready_hash",
        "registration_hash",
        "release_hash",
        "release_path",
        "run_lock_hash",
        "schema_version",
        "session_id",
        "slot_number",
        "slot_token",
        "study_id",
    }
    if set(value) != expected_fields:
        raise StudyHandshakeError("release fields mismatch")
    if value.get("schema_version") != RELEASE_SCHEMA_VERSION:
        raise StudyHandshakeError("release schema mismatch")
    if value.get("protocol_version") != HANDSHAKE_SCHEMA_VERSION:
        raise StudyHandshakeError("release protocol mismatch")
    _required_sha256(value.get("attempt_hash"), "attempt_hash")
    _positive_int(value.get("child_pid"), "child_pid")
    _nonnegative_int(value.get("created_unix_ns"), "created_unix_ns")
    _required_sha256(value.get("ready_hash"), "ready_hash")
    _required_sha256(value.get("registration_hash"), "registration_hash")
    _absolute_path(value.get("release_path"), "release path")
    _required_sha256(value.get("run_lock_hash"), "run_lock_hash")
    _required_string(value.get("session_id"), "session_id")
    _positive_int(value.get("slot_number"), "slot_number")
    _required_sha256(value.get("slot_token"), "slot_token")
    _required_string(value.get("study_id"), "study_id")
    if value.get("release_hash") != _self_hash(value, "release_hash"):
        raise StudyHandshakeError("release hash mismatch")
    return dict(value)


def _validated_record_and_path(
    record: Mapping[str, Any],
) -> tuple[dict[str, Any], Path]:
    schema_version = record.get("schema_version") if isinstance(record, Mapping) else None
    if schema_version == ATTEMPT_SCHEMA_VERSION:
        validated = _validate_attempt_record(record)
        return validated, Path(validated["attempt_path"])
    if schema_version == READY_SCHEMA_VERSION:
        validated = _validate_ready_shape(record)
        return validated, Path(validated["ready_path"])
    if schema_version == RELEASE_SCHEMA_VERSION:
        validated = _validate_release_shape(record)
        return validated, Path(validated["release_path"])
    raise StudyHandshakeError("unsupported handshake record schema")


def _load_record(path: Path | str, label: str) -> Mapping[str, Any]:
    resolved_path = _absolute_path(path, f"{label} path")
    try:
        payload = resolved_path.read_bytes()
    except OSError as exc:
        raise StudyHandshakeError(f"cannot read {label} record: {exc}") from exc
    if not payload.endswith(b"\n") or payload.endswith(b"\n\n"):
        raise StudyHandshakeError(f"{label} record is not one canonical JSON line")
    try:
        record = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise StudyHandshakeError(f"invalid {label} record: {exc}") from exc
    value = _mapping(record, f"{label} record")
    expected = (_canonical_json(value) + "\n").encode("utf-8")
    if payload != expected:
        raise StudyHandshakeError(f"{label} record is not canonical JSON")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _self_hash(record: Mapping[str, Any], field: str) -> str:
    payload = dict(record)
    payload[field] = None
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StudyHandshakeError(f"{field} must be an object")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise StudyHandshakeError(f"{field} must be a canonical nonempty string")
    return value


def _required_sha256(value: Any, field: str) -> str:
    normalized = _required_string(value, field)
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise StudyHandshakeError(f"{field} must be lowercase SHA-256")
    return normalized


def _exact_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StudyHandshakeError(f"{field} must be an integer")
    return value


def _positive_int(value: Any, field: str) -> int:
    normalized = _exact_int(value, field)
    if normalized <= 0:
        raise StudyHandshakeError(f"{field} must be positive")
    return normalized


def _nonnegative_int(value: Any, field: str) -> int:
    normalized = _exact_int(value, field)
    if normalized < 0:
        raise StudyHandshakeError(f"{field} must be nonnegative")
    return normalized


def _absolute_path(value: Path | str | Any, field: str) -> Path:
    if isinstance(value, Path):
        raw = str(value)
    elif isinstance(value, str):
        raw = value
    else:
        raise StudyHandshakeError(f"{field} must be a path string")
    path = Path(raw)
    if not path.is_absolute() or str(path.resolve()) != raw:
        raise StudyHandshakeError(f"{field} must be resolved absolute")
    return path

#!/usr/bin/env python3
"""Operate the fixed, no-training non-combat outcome-evidence study."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _contains_project_package(search_root: str) -> bool:
    try:
        root = Path(search_root or os.getcwd()).resolve()
    except OSError:
        return False
    return any(
        (root / name).exists() for name in ("analysis_scripts", "spirecomm")
    )


sys.path[:] = [
    search_root
    for search_root in sys.path
    if not _contains_project_package(search_root)
]
sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.noncombat_outcome_evidence_expansion import (
    OutcomeEvidenceRegistration,
    OutcomeEvidenceRegistrationError,
    RegisteredSlot,
    build_registered_pool,
    collect_registered_session_evidence,
    conservative_marker_run_pairs,
    create_run_lock,
    finalize_registered_integrity_stop,
    finalize_registered_outcome_evidence,
    load_registration,
    manifest_isolation_matches_run_lock,
    registration_handshake_rules,
    require_launchable_registration,
    validate_run_lock,
)
from spirecomm.ai.noncombat_exploration import (
    CONFIG_ENV,
    CONFIG_SCHEMA_VERSION,
    load_exploration_config,
    parse_exploration_config,
)
from spirecomm.communication.study_handshake import (
    HANDSHAKE_ATTEMPT_ENV,
    POLL_INTERVAL_SECONDS,
    HandshakePaths,
    build_attempt_record,
    build_release_record,
    load_attempt_record,
    load_ready_record,
    publish_record_once,
    validate_ready_record,
)


LEDGER_SCHEMA_VERSION = "noncombat-outcome-evidence-ledger-v1"
MONITOR_SCHEMA_VERSION = "noncombat-outcome-evidence-blinded-monitor-v2"
_SHA256_LENGTH = 64
_GIT_COMMIT_LENGTH = 40
_PROCESS_TERMINATION_TIMEOUT_SECONDS = 5


class OutcomeEvidenceRunnerError(RuntimeError):
    """Raised when a registered launch or ledger transition is invalid."""


@dataclass(frozen=True)
class RegisteredSlotLaunch:
    slot_number: int
    session_id: str
    config_path: str
    command: tuple[str, ...]
    environment: Mapping[str, str]
    config_record: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "command", tuple(self.command))
        object.__setattr__(
            self,
            "environment",
            MappingProxyType(dict(self.environment)),
        )
        object.__setattr__(
            self,
            "config_record",
            MappingProxyType(json.loads(_canonical_json(self.config_record))),
        )


def build_slot_launch(
    registration: OutcomeEvidenceRegistration,
    run_lock: Mapping[str, Any],
    slot_number: int,
) -> RegisteredSlotLaunch:
    """Build one registered launch without touching the filesystem or a process."""

    slot = _registered_slot(registration, slot_number)
    binding = _validate_run_lock_binding(registration, run_lock)
    command = tuple(_registered_command(registration))
    validate_registered_command(registration, command)
    config_record = {
        "category_rates_bps": {"card_reward": 300, "shop": 1000},
        "enabled_categories": ["card_reward", "shop"],
        "manifest_path": slot.manifest_path,
        "per_run_alternative_budget": 2,
        "schema_version": CONFIG_SCHEMA_VERSION,
        "seed": slot.seed,
        "session_id": slot.session_id,
        "source_commit": binding["source_commit"],
        "study_id": registration.study_id,
        "study_registration_hash": registration.registration_hash,
        "study_run_lock_hash": binding["run_lock_hash"],
        "study_slot_number": slot.slot_number,
        "trace_path": slot.trace_path,
    }
    parse_exploration_config(config_record, config_path=Path(slot.config_path))
    return RegisteredSlotLaunch(
        slot_number=slot.slot_number,
        session_id=slot.session_id,
        config_path=slot.config_path,
        command=command,
        environment={CONFIG_ENV: slot.config_path},
        config_record=config_record,
    )


def validate_registered_command(
    registration: OutcomeEvidenceRegistration,
    command: Sequence[str],
) -> tuple[str, ...]:
    if isinstance(command, (str, bytes)) or not isinstance(command, Sequence):
        raise OutcomeEvidenceRunnerError("command must be a sequence of strings")
    normalized = tuple(command)
    if not normalized or any(
        not isinstance(part, str) or not part for part in normalized
    ):
        raise OutcomeEvidenceRunnerError("command contains an invalid argument")
    expected = tuple(_registered_command(registration))
    if normalized != expected:
        raise OutcomeEvidenceRunnerError("command differs from the registered command")
    forbidden = {
        "--train",
        "--model",
        "--epsilon",
        "--expert-mix",
        "--expert-mix-prob",
        "--expert-mix-warmup",
    }
    if forbidden.intersection(normalized) or "--eval" not in normalized:
        raise OutcomeEvidenceRunnerError(
            "command contains a training or policy-mutation flag"
        )
    return normalized


def render_slot_config(launch: RegisteredSlotLaunch) -> str:
    return _canonical_json(dict(launch.config_record)) + "\n"


def write_slot_config_once(launch: RegisteredSlotLaunch) -> str:
    rendered = render_slot_config(launch)
    _publish_text_once(Path(launch.config_path), rendered, "slot config")
    return rendered


def validate_run_lock_or_stop(
    ledger: "StudyLedger",
    *,
    validator: Callable[[], Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Convert any pre-launch lock failure into an irreversible global stop."""

    try:
        run_lock = validator()
        if not isinstance(run_lock, Mapping):
            raise OutcomeEvidenceRunnerError(
                "run lock validator did not return an object"
            )
        observed_hash = _required_sha256(
            run_lock.get("run_lock_hash"), "run lock hash"
        )
        if observed_hash != ledger.run_lock_hash:
            raise OutcomeEvidenceRunnerError(
                "validated run lock differs from the ledger binding"
            )
        return run_lock
    except Exception as exc:
        reason = f"run lock validation failed: {type(exc).__name__}: {exc}"
        if ledger.snapshot()["global_stop"] is None:
            ledger.global_stop(reason=reason)
        raise OutcomeEvidenceRunnerError(reason) from exc


def execute_registered_slot(
    *,
    ledger: "StudyLedger",
    launch: RegisteredSlotLaunch,
    marker_path: Path | str,
    process_runner: Callable[[RegisteredSlotLaunch], int],
    started_unix_ns: int | None = None,
    ended_unix_ns: int | None = None,
) -> dict[str, Any]:
    """Launch one slot and derive completion only from AI marker growth."""

    expected = ledger.next_slot()
    if (
        launch.slot_number != expected.slot_number
        or launch.session_id != expected.session_id
    ):
        raise OutcomeEvidenceRunnerError(
            "launch does not match the next registered ledger slot"
        )
    marker_file = Path(marker_path).resolve()
    before_count = _ai_marker_count(marker_file)
    ledger.start_slot(
        launch.slot_number,
        launch.session_id,
        started_unix_ns=started_unix_ns,
    )
    try:
        exit_code = process_runner(launch)
    except BaseException as exc:
        complete, after_count = _safe_marker_delta_or_stop(
            ledger=ledger,
            marker_path=marker_file,
            before_count=before_count,
            ended_unix_ns=ended_unix_ns,
        )
        if ledger.snapshot()["active_slot"] is not None:
            ledger.recover_active_slot(
                reason=f"child process raised: {type(exc).__name__}",
                complete_trajectories=complete,
                marker_start_count=before_count,
                marker_end_count=after_count,
                ended_unix_ns=ended_unix_ns,
            )
        raise
    complete, after_count = _safe_marker_delta_or_stop(
        ledger=ledger,
        marker_path=marker_file,
        before_count=before_count,
        ended_unix_ns=ended_unix_ns,
    )
    if type(exit_code) is not int:
        ledger.recover_active_slot(
            reason="child process returned a non-integer exit code",
            complete_trajectories=complete,
            marker_start_count=before_count,
            marker_end_count=after_count,
            ended_unix_ns=ended_unix_ns,
        )
        ledger.global_stop(reason="child process exit code was invalid")
        raise OutcomeEvidenceRunnerError("child process exit code is invalid")
    return ledger.finish_slot(
        launch.slot_number,
        process_exit_code=exit_code,
        complete_trajectories=complete,
        marker_start_count=before_count,
        marker_end_count=after_count,
        ended_unix_ns=ended_unix_ns,
    )


def execute_handshaken_registered_slot(
    *,
    ledger: "StudyLedger",
    launch: RegisteredSlotLaunch,
    marker_path: Path | str,
    process_starter: Callable[[RegisteredSlotLaunch, Mapping[str, str]], Any],
    preclaim_validator: Callable[[], Mapping[str, Any]] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    time_ns: Callable[[], int] = time.time_ns,
) -> dict[str, Any]:
    """Claim a registered slot only after its real child proves readiness."""

    expected = ledger.next_slot()
    if (
        launch.slot_number != expected.slot_number
        or launch.session_id != expected.session_id
    ):
        raise OutcomeEvidenceRunnerError(
            "launch does not match the next registered ledger slot"
        )
    if not callable(process_starter):
        raise OutcomeEvidenceRunnerError("process_starter must be callable")
    marker_file = Path(marker_path).resolve()
    rules = registration_handshake_rules(ledger.registration)
    if rules is None:
        raise OutcomeEvidenceRunnerError(
            "launchable registration has no handshake rules"
        )
    paths = _handshake_paths_from_rules(
        config_path=launch.config_path,
        session_id=launch.session_id,
        rules=rules,
    )
    slot = _registered_slot(ledger.registration, launch.slot_number)
    output_paths = (Path(slot.manifest_path), Path(slot.trace_path))
    process = None
    marker_start_count: int | None = None
    try:
        _require_paths_absent(
            (paths.attempt, paths.ready, paths.release),
            "handshake artifact exists before launch",
        )
        _require_paths_absent(
            output_paths,
            "gameplay output exists before launch",
        )
        marker_start_count = _ai_marker_count(marker_file)
        config_path = Path(launch.config_path).resolve()
        config_sha256 = _handshake_file_sha256(
            config_path,
            "registered slot config",
        )
        attempt = build_attempt_record(
            study_id=ledger.registration.study_id,
            registration_hash=ledger.registration.registration_hash,
            run_lock_hash=ledger.run_lock_hash,
            slot_number=launch.slot_number,
            session_id=launch.session_id,
            config_path=config_path,
            config_sha256=config_sha256,
            marker_start_count=marker_start_count,
            paths=paths,
            readiness_timeout_seconds=rules["readiness_timeout_seconds"],
            release_timeout_seconds=rules["release_timeout_seconds"],
            created_unix_ns=_positive_time_ns(time_ns),
        )
        publish_record_once(paths.attempt, attempt)
        child_environment = dict(launch.environment)
        child_environment[HANDSHAKE_ATTEMPT_ENV] = str(paths.attempt)
        process = process_starter(
            launch,
            MappingProxyType(child_environment),
        )
        child_pid = _child_process_pid(process)
        ready = _wait_for_child_readiness(
            process=process,
            child_pid=child_pid,
            attempt=attempt,
            ready_path=paths.ready,
            timeout_seconds=rules["readiness_timeout_seconds"],
            monotonic=monotonic,
            sleep=sleep,
        )
        _validate_preclaim_handshake_state(
            attempt=attempt,
            paths=paths,
            output_paths=output_paths,
            marker_path=marker_file,
            marker_start_count=marker_start_count,
            config_path=config_path,
            config_sha256=config_sha256,
        )
        _validate_preclaim_run_lock(
            preclaim_validator,
            expected_run_lock_hash=ledger.run_lock_hash,
        )
        _require_child_running(process, stage="slot claim")
        ledger.start_slot(
            launch.slot_number,
            launch.session_id,
            marker_start_count=marker_start_count,
            started_unix_ns=_positive_time_ns(time_ns),
        )
        _require_child_running(process, stage="postclaim validation")
        _validate_preclaim_handshake_state(
            attempt=attempt,
            paths=paths,
            output_paths=output_paths,
            marker_path=marker_file,
            marker_start_count=marker_start_count,
            config_path=config_path,
            config_sha256=config_sha256,
            boundary="child release",
        )
        _require_child_running(process, stage="child release")
        release = build_release_record(
            attempt,
            ready,
            created_unix_ns=_positive_time_ns(time_ns),
        )
        publish_record_once(paths.release, release)
    except BaseException as exc:
        active = _ledger_has_active_slot(ledger)
        stage = "postclaim release failed" if active else "preclaim handshake failed"
        reason = f"{stage}: {type(exc).__name__}: {exc}"
        cleanup_error = _terminate_child_process(process)
        if cleanup_error is not None:
            reason = f"{reason}; child cleanup failed: {cleanup_error}"
        if active:
            _recover_claimed_slot_for_stop(
                ledger=ledger,
                marker_path=marker_file,
                marker_start_count=marker_start_count,
                reason=reason,
                ended_unix_ns=_safe_time_ns(time_ns),
            )
        _record_global_stop_once(ledger, reason)
        raise OutcomeEvidenceRunnerError(reason) from exc

    try:
        exit_code = process.wait()
    except BaseException as exc:
        reason = f"released child wait failed: {type(exc).__name__}: {exc}"
        cleanup_error = _terminate_child_process(process)
        if cleanup_error is not None:
            reason = f"{reason}; child cleanup failed: {cleanup_error}"
        _recover_claimed_slot_for_stop(
            ledger=ledger,
            marker_path=marker_file,
            marker_start_count=marker_start_count,
            reason=reason,
            ended_unix_ns=_safe_time_ns(time_ns),
        )
        _record_global_stop_once(ledger, reason)
        raise OutcomeEvidenceRunnerError(reason) from exc
    complete, marker_end_count = _safe_marker_delta_or_stop(
        ledger=ledger,
        marker_path=marker_file,
        before_count=marker_start_count,
        ended_unix_ns=_safe_time_ns(time_ns),
    )
    if type(exit_code) is not int:
        reason = "released child process returned a non-integer exit code"
        ledger.recover_active_slot(
            reason=reason,
            complete_trajectories=complete,
            marker_start_count=marker_start_count,
            marker_end_count=marker_end_count,
            ended_unix_ns=_safe_time_ns(time_ns),
        )
        _record_global_stop_once(ledger, reason)
        raise OutcomeEvidenceRunnerError(reason)
    return ledger.finish_slot(
        launch.slot_number,
        process_exit_code=exit_code,
        complete_trajectories=complete,
        marker_start_count=marker_start_count,
        marker_end_count=marker_end_count,
        ended_unix_ns=_safe_time_ns(time_ns),
    )


def _handshake_paths_from_rules(
    *,
    config_path: Path | str,
    session_id: str,
    rules: Mapping[str, Any],
) -> HandshakePaths:
    parent = Path(config_path).resolve().parent
    return HandshakePaths(
        attempt=(parent / f"{session_id}{rules['attempt_suffix']}").resolve(),
        ready=(parent / f"{session_id}{rules['ready_suffix']}").resolve(),
        release=(parent / f"{session_id}{rules['release_suffix']}").resolve(),
    )


def _wait_for_child_readiness(
    *,
    process: Any,
    child_pid: int,
    attempt: Mapping[str, Any],
    ready_path: Path,
    timeout_seconds: int,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    deadline = monotonic() + timeout_seconds
    while True:
        if ready_path.exists():
            if process.poll() is not None:
                raise OutcomeEvidenceRunnerError(
                    "child exited before readiness verification"
                )
            ready = load_ready_record(ready_path)
            validated = validate_ready_record(
                ready,
                attempt=attempt,
                child_pid=child_pid,
            )
            if process.poll() is not None:
                raise OutcomeEvidenceRunnerError(
                    "child exited before readiness verification"
                )
            return validated
        exit_code = process.poll()
        if exit_code is not None:
            raise OutcomeEvidenceRunnerError(
                f"child exited before readiness with code {exit_code}"
            )
        if monotonic() >= deadline:
            raise OutcomeEvidenceRunnerError("child readiness deadline exceeded")
        sleep(POLL_INTERVAL_SECONDS)


def _validate_preclaim_handshake_state(
    *,
    attempt: Mapping[str, Any],
    paths: HandshakePaths,
    output_paths: Sequence[Path],
    marker_path: Path,
    marker_start_count: int,
    config_path: Path,
    config_sha256: str,
    boundary: str = "slot claim",
) -> None:
    if load_attempt_record(paths.attempt) != dict(attempt):
        raise OutcomeEvidenceRunnerError(
            f"handshake attempt changed before {boundary}"
        )
    if paths.release.exists():
        raise OutcomeEvidenceRunnerError(f"release exists before {boundary}")
    _require_paths_absent(
        output_paths,
        f"gameplay output was created before {boundary}",
    )
    if _ai_marker_count(marker_path) != marker_start_count:
        raise OutcomeEvidenceRunnerError(
            f"AI marker count changed before {boundary}"
        )
    if (
        _handshake_file_sha256(config_path, "registered slot config")
        != config_sha256
    ):
        raise OutcomeEvidenceRunnerError(
            f"registered slot config changed before {boundary}"
        )


def _validate_preclaim_run_lock(
    validator: Callable[[], Mapping[str, Any]] | None,
    *,
    expected_run_lock_hash: str,
) -> None:
    if validator is None:
        return
    if not callable(validator):
        raise OutcomeEvidenceRunnerError("preclaim_validator must be callable")
    observed = validator()
    if not isinstance(observed, Mapping):
        raise OutcomeEvidenceRunnerError(
            "preclaim run lock validator returned a non-object"
        )
    if observed.get("run_lock_hash") != expected_run_lock_hash:
        raise OutcomeEvidenceRunnerError(
            "preclaim run lock differs from the ledger binding"
        )


def _require_child_running(process: Any, *, stage: str) -> None:
    exit_code = process.poll()
    if exit_code is not None:
        raise OutcomeEvidenceRunnerError(
            f"child exited before {stage} with code {exit_code}"
        )


def _recover_active_slot_after_host_failure(
    *,
    ledger: "StudyLedger",
    marker_path: Path | str,
    ended_unix_ns: int | None = None,
) -> None:
    snapshot = ledger.snapshot()
    active = snapshot["active_slot"]
    if active is None:
        return
    reason = "active slot recovery after parent or host failure"
    _recover_claimed_slot_for_stop(
        ledger=ledger,
        marker_path=Path(marker_path).resolve(),
        marker_start_count=active.get("marker_start_count"),
        reason=reason,
        ended_unix_ns=ended_unix_ns,
    )
    _record_global_stop_once(ledger, reason)
    raise OutcomeEvidenceRunnerError(reason)


def _recover_claimed_slot_for_stop(
    *,
    ledger: "StudyLedger",
    marker_path: Path,
    marker_start_count: Any,
    reason: str,
    ended_unix_ns: int | None,
) -> None:
    marker_end_count = None
    complete = 0
    recovery_reason = reason
    if type(marker_start_count) is int and marker_start_count >= 0:
        try:
            observed_end = _ai_marker_count(marker_path)
            observed_complete = observed_end - marker_start_count
            if observed_complete < 0 or observed_complete > 25:
                raise OutcomeEvidenceRunnerError(
                    "AI marker delta is outside the registered slot"
                )
            marker_end_count = observed_end
            complete = observed_complete
        except OutcomeEvidenceRunnerError as exc:
            recovery_reason = f"{reason}; marker recovery failed: {exc}"
            marker_start_count = None
            marker_end_count = None
            complete = 0
    else:
        marker_start_count = None
        recovery_reason = f"{reason}; marker start boundary is unavailable"
    ledger.recover_active_slot(
        reason=recovery_reason,
        complete_trajectories=complete,
        marker_start_count=marker_start_count,
        marker_end_count=marker_end_count,
        ended_unix_ns=ended_unix_ns,
    )


def _terminate_child_process(process: Any) -> str | None:
    if process is None:
        return None
    failures = []
    try:
        if process.poll() is not None:
            return None
    except BaseException as exc:
        failures.append(f"poll failed: {type(exc).__name__}: {exc}")
    try:
        process.terminate()
        try:
            process.wait(timeout=_PROCESS_TERMINATION_TIMEOUT_SECONDS)
            return None
        except subprocess.TimeoutExpired:
            failures.append("terminate deadline exceeded")
        except BaseException as exc:
            failures.append(f"terminate wait failed: {type(exc).__name__}: {exc}")
    except BaseException as exc:
        failures.append(f"terminate failed: {type(exc).__name__}: {exc}")
    try:
        process.kill()
        process.wait(timeout=_PROCESS_TERMINATION_TIMEOUT_SECONDS)
        return None
    except BaseException as exc:
        failures.append(f"kill failed: {type(exc).__name__}: {exc}")
    try:
        if process.poll() is not None:
            return None
    except BaseException as exc:
        failures.append(f"final poll failed: {type(exc).__name__}: {exc}")
    return "; ".join(failures) or "child process remains live"


def _ledger_has_active_slot(ledger: "StudyLedger") -> bool:
    try:
        return ledger.snapshot()["active_slot"] is not None
    except OutcomeEvidenceRunnerError:
        return False


def _record_global_stop_once(ledger: "StudyLedger", reason: str) -> None:
    if ledger.snapshot()["global_stop"] is None:
        ledger.global_stop(reason=reason)


def _child_process_pid(process: Any) -> int:
    pid = getattr(process, "pid", None)
    if type(pid) is not int or pid <= 0:
        raise OutcomeEvidenceRunnerError("child process PID is invalid")
    return pid


def _require_paths_absent(paths: Sequence[Path], message: str) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise OutcomeEvidenceRunnerError(f"{message}: {existing[0]}")


def _handshake_file_sha256(path: Path, label: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(f"cannot read {label}: {exc}") from exc


def _positive_time_ns(clock: Callable[[], int]) -> int:
    value = clock()
    if type(value) is not int or value <= 0:
        raise OutcomeEvidenceRunnerError("clock returned an invalid timestamp")
    return value


def _safe_time_ns(clock: Callable[[], int]) -> int | None:
    try:
        return _positive_time_ns(clock)
    except BaseException:
        return None


def _safe_marker_delta_or_stop(
    *,
    ledger: "StudyLedger",
    marker_path: Path,
    before_count: int,
    ended_unix_ns: int | None,
) -> tuple[int, int]:
    try:
        after_count = _ai_marker_count(marker_path)
        complete = after_count - before_count
        if complete < 0:
            raise OutcomeEvidenceRunnerError("AI marker file was truncated")
        if complete > 25:
            raise OutcomeEvidenceRunnerError(
                "AI marker delta exceeds the registered 25-game slot"
            )
        return complete, after_count
    except OutcomeEvidenceRunnerError as exc:
        if ledger.snapshot()["active_slot"] is not None:
            ledger.recover_active_slot(
                reason=f"marker integrity failure: {exc}",
                complete_trajectories=0,
                ended_unix_ns=ended_unix_ns,
            )
        ledger.global_stop(reason=f"marker integrity failure: {exc}")
        raise


def _ai_marker_count(path: Path) -> int:
    return len(_load_ai_markers(path))


def _load_ai_markers(path: Path) -> list[int]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise OutcomeEvidenceRunnerError(f"cannot read AI marker file: {exc}") from exc
    raw_markers = [line.strip() for line in lines if line.strip()]
    if any(not marker.isdigit() for marker in raw_markers):
        raise OutcomeEvidenceRunnerError("AI marker file contains an invalid marker")
    return [int(marker) for marker in raw_markers]


def conservative_run_join_count(
    *,
    marker_timestamps: Sequence[int],
    run_timestamps: Sequence[int],
    tolerance_seconds: int = 10,
) -> int:
    """Count only markers with one unique, unused nearby run filename."""
    try:
        return len(
            conservative_marker_run_pairs(
                marker_timestamps=marker_timestamps,
                run_timestamps=run_timestamps,
                tolerance_seconds=tolerance_seconds,
            )
        )
    except ValueError as exc:
        raise OutcomeEvidenceRunnerError(str(exc)) from exc


def build_blinded_monitor(
    *,
    registration: OutcomeEvidenceRegistration,
    run_lock: Mapping[str, Any],
    ledger_snapshot: Mapping[str, Any],
    structural_observations: Sequence[Mapping[str, Any]],
    run_lock_valid: bool = True,
) -> dict[str, Any]:
    """Build an allowlisted collection monitor with no outcome surface."""

    binding = _validate_run_lock_binding(registration, run_lock)
    handshake_rules = registration_handshake_rules(registration)
    if isinstance(structural_observations, (str, bytes)) or not isinstance(
        structural_observations, Sequence
    ):
        raise OutcomeEvidenceRunnerError(
            "structural observations must be a sequence"
        )
    if not isinstance(ledger_snapshot, Mapping):
        raise OutcomeEvidenceRunnerError("ledger snapshot must be an object")
    if type(run_lock_valid) is not bool:
        raise OutcomeEvidenceRunnerError("run_lock_valid must be a boolean")

    blockers: set[str] = set()
    if not run_lock_valid:
        blockers.add("run_lock_invalid")
    observations_by_slot: dict[int, Mapping[str, Any]] = {}
    registered_sessions = {
        slot.slot_number: slot.session_id for slot in registration.slots
    }
    for observation in structural_observations:
        if not isinstance(observation, Mapping):
            blockers.add("invalid_structural_observation")
            continue
        slot_number = observation.get("slot_number")
        session_id = observation.get("session_id")
        if (
            type(slot_number) is not int
            or registered_sessions.get(slot_number) != session_id
        ):
            blockers.add("unregistered_structural_observation")
            continue
        if slot_number in observations_by_slot:
            blockers.add(f"duplicate_structural_observation_slot_{slot_number:02d}")
            continue
        observations_by_slot[slot_number] = observation

    active = ledger_snapshot.get("active_slot")
    active_number = active.get("slot_number") if isinstance(active, Mapping) else None
    terminal_records = ledger_snapshot.get("terminal_slots")
    if not isinstance(terminal_records, Sequence):
        raise OutcomeEvidenceRunnerError("ledger terminal_slots is invalid")
    terminal_by_slot = {
        record.get("slot_number"): record
        for record in terminal_records
        if isinstance(record, Mapping)
    }
    launched_numbers = set(terminal_by_slot)
    if type(active_number) is int:
        launched_numbers.add(active_number)

    slots = []
    for slot in registration.slots:
        if slot.slot_number in terminal_by_slot:
            lifecycle = str(
                terminal_by_slot[slot.slot_number].get("terminal_status")
            )
            process_exit_code = terminal_by_slot[slot.slot_number].get(
                "process_exit_code"
            )
        elif slot.slot_number == active_number:
            lifecycle = "active"
            process_exit_code = None
        else:
            lifecycle = "unlaunched"
            process_exit_code = None
        observation = observations_by_slot.get(slot.slot_number)
        if slot.slot_number in launched_numbers and observation is None:
            blockers.add(f"missing_launched_slot_{slot.slot_number:02d}")
        structural = _sanitize_structural_observation(
            observation,
            slot_number=slot.slot_number,
            blockers=blockers,
        )
        handshake_paths = (
            None
            if handshake_rules is None
            else _handshake_paths_from_rules(
                config_path=slot.config_path,
                session_id=slot.session_id,
                rules=handshake_rules,
            )
        )
        structural.update(
            {
                "handshake_attempt_path": (
                    str(handshake_paths.attempt)
                    if handshake_paths is not None
                    else None
                ),
                "handshake_ready_path": (
                    str(handshake_paths.ready)
                    if handshake_paths is not None
                    else None
                ),
                "handshake_release_path": (
                    str(handshake_paths.release)
                    if handshake_paths is not None
                    else None
                ),
            }
        )
        handshake_status = structural["handshake_status"]
        if handshake_rules is not None and handshake_status == "invalid":
            blockers.add(f"invalid_handshake_sequence_slot_{slot.slot_number:02d}")
        if handshake_rules is not None and lifecycle in {
            "active",
            "completed",
            "interrupted",
        } and (
            handshake_status != "released"
        ):
            blockers.add(f"launched_slot_handshake_missing_{slot.slot_number:02d}")
        if (
            handshake_rules is not None
            and lifecycle == "unlaunched"
            and handshake_status != "not_started"
        ):
            blockers.add(f"unlaunched_slot_handshake_{slot.slot_number:02d}")
        if lifecycle == "active" and not structural["config_exists"]:
            blockers.add(f"active_slot_config_missing_{slot.slot_number:02d}")
        if lifecycle in {"completed", "interrupted"} and (
            not structural["config_exists"]
            or not structural["manifest_exists"]
            or not structural["trace_exists"]
            or not structural["isolation_verified"]
        ):
            blockers.add(f"terminal_slot_structure_invalid_{slot.slot_number:02d}")
        slots.append(
            {
                **structural,
                "lifecycle": lifecycle,
                "process_exit_code": process_exit_code,
                "session_id": slot.session_id,
                "slot_number": slot.slot_number,
            }
        )

    global_stop = ledger_snapshot.get("global_stop") is not None
    if global_stop:
        blockers.add("global_integrity_stop_recorded")
    all_terminal = ledger_snapshot.get("all_slots_terminal") is True
    phase = "blocked" if global_stop else "terminal" if all_terminal else "collection"
    return {
        "blockers": sorted(blockers),
        "global_integrity_stop": global_stop,
        "integrity_valid": not blockers,
        "launched_slot_count": len(launched_numbers),
        "phase": phase,
        "registration_valid": True,
        "registration_hash": registration.registration_hash,
        "run_lock_valid": run_lock_valid,
        "run_lock_hash": binding["run_lock_hash"],
        "schema_version": MONITOR_SCHEMA_VERSION,
        "slot_count": len(registration.slots),
        "slots": slots,
        "study_id": registration.study_id,
        "terminal_slot_count": len(terminal_by_slot),
    }


def _sanitize_structural_observation(
    observation: Mapping[str, Any] | None,
    *,
    slot_number: int,
    blockers: set[str],
) -> dict[str, Any]:
    defaults = {
        "candidate_legal_records": 0,
        "config_exists": False,
        "config_sha256": None,
        "confirmed_records": 0,
        "handshake_attempt_exists": False,
        "handshake_attempt_sha256": None,
        "handshake_ready_exists": False,
        "handshake_ready_sha256": None,
        "handshake_release_exists": False,
        "handshake_release_sha256": None,
        "handshake_status": "not_started",
        "isolation_verified": False,
        "manifest_exists": False,
        "manifest_hash": None,
        "manifest_sha256": None,
        "proposed_records": 0,
        "replay_valid_records": 0,
        "run_join_complete_count": 0,
        "trace_exists": False,
        "trace_sha256": None,
    }
    if observation is None:
        return defaults
    valid = observation.get("structural_valid", True) is True
    boolean_fields = (
        "config_exists",
        "handshake_attempt_exists",
        "handshake_ready_exists",
        "handshake_release_exists",
        "isolation_verified",
        "manifest_exists",
        "trace_exists",
    )
    count_fields = (
        "candidate_legal_records",
        "confirmed_records",
        "proposed_records",
        "replay_valid_records",
        "run_join_complete_count",
    )
    hash_fields = (
        "config_sha256",
        "handshake_attempt_sha256",
        "handshake_ready_sha256",
        "handshake_release_sha256",
        "manifest_hash",
        "manifest_sha256",
        "trace_sha256",
    )
    result = dict(defaults)
    for field in boolean_fields:
        value = observation.get(field)
        if type(value) is not bool:
            valid = False
        else:
            result[field] = value
    for field in count_fields:
        value = observation.get(field)
        if type(value) is not int or value < 0:
            valid = False
        else:
            result[field] = value
    for field in hash_fields:
        value = observation.get(field)
        if value is not None and (
            not isinstance(value, str) or not _is_lower_hex(value, _SHA256_LENGTH)
        ):
            valid = False
        else:
            result[field] = value
    if (
        result["confirmed_records"] > result["proposed_records"]
        or result["replay_valid_records"] > result["confirmed_records"]
        or result["candidate_legal_records"] > result["replay_valid_records"]
        or (result["config_exists"] and result["config_sha256"] is None)
        or result["handshake_attempt_exists"]
        != (result["handshake_attempt_sha256"] is not None)
        or result["handshake_ready_exists"]
        != (result["handshake_ready_sha256"] is not None)
        or result["handshake_release_exists"]
        != (result["handshake_release_sha256"] is not None)
        or (
            result["manifest_exists"]
            and (
                result["manifest_sha256"] is None
                or result["manifest_hash"] is None
            )
        )
        or (result["trace_exists"] and result["trace_sha256"] is None)
    ):
        valid = False
    if not valid:
        blockers.add(f"invalid_structural_observation_slot_{slot_number:02d}")
        return defaults
    handshake_shape = (
        result["handshake_attempt_exists"],
        result["handshake_ready_exists"],
        result["handshake_release_exists"],
    )
    result["handshake_status"] = {
        (False, False, False): "not_started",
        (True, False, False): "attempted",
        (True, True, False): "ready",
        (True, True, True): "released",
    }.get(handshake_shape, "invalid")
    return result


def render_blinded_monitor_json(monitor: Mapping[str, Any]) -> str:
    return _canonical_json(monitor) + "\n"


def render_blinded_monitor_markdown(monitor: Mapping[str, Any]) -> str:
    integrity = "valid" if monitor.get("integrity_valid") is True else "blocked"
    lines = [
        "# Blinded Structural Monitor",
        "",
        f"- Study: `{monitor.get('study_id')}`",
        f"- Phase: `{monitor.get('phase')}`",
        f"- Integrity: `{integrity}`",
        (
            f"- Progress: {monitor.get('terminal_slot_count')}/"
            f"{monitor.get('slot_count')} terminal slots"
        ),
        "",
        "| Slot | Session | Lifecycle | Handshake | Exit | Config | Manifest | Trace | "
        "Proposed | Confirmed | Replay valid | Candidate legal | "
        "Complete joins | Isolation |",
        "|---:|---|---|---|---:|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    slots = monitor.get("slots", [])
    for slot in slots:
        lines.append(
            "| {slot_number:02d} | `{session_id}` | {lifecycle} | "
            "{handshake_status} | "
            "{process_exit_code} | {config} | "
            "{manifest} | {trace} | {proposed_records} | {confirmed_records} | "
            "{replay_valid_records} | {candidate_legal_records} | "
            "{run_join_complete_count} | {isolation} |".format(
                **slot,
                config="yes" if slot["config_exists"] else "no",
                manifest="yes" if slot["manifest_exists"] else "no",
                trace="yes" if slot["trace_exists"] else "no",
                isolation="valid" if slot["isolation_verified"] else "not-valid",
            )
        )
    blockers = monitor.get("blockers", [])
    if blockers:
        lines.extend(["", "## Structural Blockers", ""])
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    return "\n".join(lines) + "\n"


def collect_structural_observations(
    *,
    registration: OutcomeEvidenceRegistration,
    run_lock: Mapping[str, Any],
    ledger_snapshot: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Inspect launched artifacts while retaining only structural fields."""

    binding = _validate_run_lock_binding(registration, run_lock)
    handshake_rules = registration_handshake_rules(registration)
    active = ledger_snapshot.get("active_slot")
    active_number = active.get("slot_number") if isinstance(active, Mapping) else None
    terminal_records = ledger_snapshot.get("terminal_slots", [])
    terminal_by_slot = {
        record.get("slot_number"): record
        for record in terminal_records
        if isinstance(record, Mapping)
    }
    launched_numbers = set(terminal_by_slot)
    if type(active_number) is int:
        launched_numbers.add(active_number)
    handshake_paths_by_slot = {}
    observed_numbers = set(launched_numbers)
    for registered_slot in registration.slots:
        registered_paths = (
            None
            if handshake_rules is None
            else _handshake_paths_from_rules(
                config_path=registered_slot.config_path,
                session_id=registered_slot.session_id,
                rules=handshake_rules,
            )
        )
        handshake_paths_by_slot[registered_slot.slot_number] = registered_paths
        if registered_paths is not None and any(
            path.exists()
            for path in (
                registered_paths.attempt,
                registered_paths.ready,
                registered_paths.release,
            )
        ):
            observed_numbers.add(registered_slot.slot_number)

    game_root = Path(registration.checkpoint_root).resolve().parent
    join_inputs_valid = True
    try:
        marker_timestamps = _load_ai_markers(
            game_root / "runs" / "ai_games.txt"
        )
        run_timestamps = []
        for run_path in (game_root / "runs" / "IRONCLAD").glob("*.run"):
            if run_path.stem.isdigit():
                run_timestamps.append(int(run_path.stem))
    except (OSError, OutcomeEvidenceRunnerError):
        marker_timestamps = []
        run_timestamps = []
        join_inputs_valid = False

    observations = []
    for slot_number in sorted(observed_numbers):
        slot = _registered_slot(registration, slot_number)
        handshake_paths = handshake_paths_by_slot[slot_number]
        terminal = terminal_by_slot.get(slot_number, {})
        marker_start = terminal.get("marker_start_count")
        marker_end = terminal.get("marker_end_count")
        run_join_complete_count = 0
        slot_join_valid = join_inputs_valid
        if terminal:
            if (
                type(marker_start) is int
                and type(marker_end) is int
                and 0 <= marker_start <= marker_end <= len(marker_timestamps)
            ):
                run_join_complete_count = conservative_run_join_count(
                    marker_timestamps=marker_timestamps[marker_start:marker_end],
                    run_timestamps=run_timestamps,
                )
            else:
                slot_join_valid = False
        observation = {
            "candidate_legal_records": 0,
            "config_exists": False,
            "config_sha256": None,
            "confirmed_records": 0,
            "handshake_attempt_exists": False,
            "handshake_attempt_sha256": None,
            "handshake_ready_exists": False,
            "handshake_ready_sha256": None,
            "handshake_release_exists": False,
            "handshake_release_sha256": None,
            "isolation_verified": False,
            "manifest_exists": False,
            "manifest_hash": None,
            "manifest_sha256": None,
            "proposed_records": 0,
            "replay_valid_records": 0,
            "run_join_complete_count": run_join_complete_count,
            "session_id": slot.session_id,
            "slot_number": slot.slot_number,
            "structural_valid": slot_join_valid,
            "trace_exists": False,
            "trace_sha256": None,
        }
        config_path = Path(slot.config_path)
        manifest_path = Path(slot.manifest_path)
        trace_path = Path(slot.trace_path)
        try:
            if handshake_paths is not None:
                for name, handshake_path in (
                    ("attempt", handshake_paths.attempt),
                    ("ready", handshake_paths.ready),
                    ("release", handshake_paths.release),
                ):
                    if handshake_path.exists():
                        observation[f"handshake_{name}_exists"] = True
                        if not handshake_path.is_file():
                            raise OutcomeEvidenceRunnerError(
                                f"handshake {name} artifact is not a file"
                            )
                        observation[f"handshake_{name}_sha256"] = _sha256_file(
                            handshake_path
                        )
            if config_path.is_file():
                observation["config_exists"] = True
                observation["config_sha256"] = _sha256_file(config_path)
                config = load_exploration_config(config_path)
                if (
                    config.session_id != slot.session_id
                    or config.study_id != registration.study_id
                    or config.study_slot_number != slot.slot_number
                    or config.study_registration_hash
                    != registration.registration_hash
                    or config.study_run_lock_hash != binding["run_lock_hash"]
                    or config.source_commit != binding["source_commit"]
                ):
                    raise OutcomeEvidenceRunnerError(
                        "registered config binding mismatch"
                    )
            else:
                config = None

            manifest = None
            if manifest_path.is_file():
                observation["manifest_exists"] = True
                observation["manifest_sha256"] = _sha256_file(manifest_path)
                manifest = _load_json_object(manifest_path, "manifest")
                manifest_hash = manifest.get("manifest_hash")
                if not isinstance(manifest_hash, str) or not _is_lower_hex(
                    manifest_hash, _SHA256_LENGTH
                ):
                    raise OutcomeEvidenceRunnerError("manifest hash is invalid")
                observation["manifest_hash"] = manifest_hash
                effective = manifest.get("effective_config")
                if not isinstance(effective, Mapping) or (
                    effective.get("study_run_lock_hash")
                    != binding["run_lock_hash"]
                ):
                    raise OutcomeEvidenceRunnerError(
                        "manifest run lock binding mismatch"
                    )
                observation["isolation_verified"] = (
                    manifest_isolation_matches_run_lock(manifest, run_lock)
                )

            if trace_path.is_file():
                observation["trace_exists"] = True
                observation["trace_sha256"] = _sha256_file(trace_path)

            if config is not None and manifest is not None and trace_path.is_file():
                from analysis_scripts.noncombat_exploration_evidence import (
                    export_confirmed_exploration_samples,
                )

                export = export_confirmed_exploration_samples(
                    trace_path,
                    manifest_path,
                    expected_source_commit=binding["source_commit"],
                )
                summary = export.validation_summary
                observation["proposed_records"] = summary["proposed_records"]
                observation["confirmed_records"] = summary["confirmed"]
                observation["replay_valid_records"] = summary["replay_valid"]
                observation["candidate_legal_records"] = summary[
                    "candidate_legal"
                ]
        except Exception:
            observation["structural_valid"] = False
        observations.append(observation)
    return observations


def write_blinded_monitor_artifacts(
    monitor: Mapping[str, Any],
    *,
    json_path: Path | str,
    markdown_path: Path | str,
) -> dict[str, str]:
    rendered_json = render_blinded_monitor_json(monitor)
    rendered_markdown = render_blinded_monitor_markdown(monitor)
    resolved_json = Path(json_path).resolve()
    resolved_markdown = Path(markdown_path).resolve()
    if resolved_json == resolved_markdown:
        raise OutcomeEvidenceRunnerError("monitor output paths must be distinct")
    _replace_text_atomically(resolved_json, rendered_json)
    _replace_text_atomically(resolved_markdown, rendered_markdown)
    return {
        "json_path": str(resolved_json),
        "markdown_path": str(resolved_markdown),
    }


def _replace_text_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        descriptor, name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot update monitor artifact {path}: {exc}"
        ) from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(f"cannot hash artifact {path}: {exc}") from exc


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise OutcomeEvidenceRunnerError(f"{label} must be an object")
    return payload


class StudyLedger:
    """Hash-chained append-only lifecycle ledger for one registered schedule."""

    error_type = OutcomeEvidenceRunnerError

    def __init__(
        self,
        *,
        path: Path | str,
        registration: OutcomeEvidenceRegistration,
        run_lock_hash: str,
    ) -> None:
        self.path = Path(path).resolve()
        self.registration = registration
        self.run_lock_hash = _required_sha256(run_lock_hash, "run lock hash")
        self._slots = {slot.slot_number: slot for slot in registration.slots}

    @classmethod
    def open_existing(
        cls,
        *,
        path: Path | str,
        registration: OutcomeEvidenceRegistration,
    ) -> "StudyLedger":
        """Open a ledger using its validated first record as the lock binding."""

        resolved_path = Path(path).resolve()
        try:
            content = resolved_path.read_bytes()
        except OSError as exc:
            raise OutcomeEvidenceRunnerError(
                f"cannot read existing ledger: {exc}"
            ) from exc
        if not content or not content.endswith(b"\n"):
            raise OutcomeEvidenceRunnerError(
                "existing ledger is empty or has a partial final record"
            )
        try:
            first_record = json.loads(
                content.splitlines()[0].decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise OutcomeEvidenceRunnerError(
                f"invalid first ledger record: {exc}"
            ) from exc
        if not isinstance(first_record, Mapping):
            raise OutcomeEvidenceRunnerError(
                "first ledger record must be an object"
            )
        run_lock_hash = _required_sha256(
            first_record.get("run_lock_hash"), "ledger run lock hash"
        )
        _validate_ledger_record(
            first_record,
            sequence=1,
            previous_hash=None,
            registration=registration,
            run_lock_hash=run_lock_hash,
        )
        ledger = cls(
            path=resolved_path,
            registration=registration,
            run_lock_hash=run_lock_hash,
        )
        snapshot = ledger.snapshot()
        if not snapshot["initialized"]:
            raise OutcomeEvidenceRunnerError(
                "existing ledger is not initialized"
            )
        return ledger

    def initialize(self, *, created_unix_ns: int | None = None) -> dict[str, Any]:
        created = _timestamp(created_unix_ns)

        def validate(snapshot: Mapping[str, Any]) -> None:
            if snapshot["initialized"]:
                raise OutcomeEvidenceRunnerError("study ledger is already initialized")

        return self._append(
            event="study_started",
            created_unix_ns=created,
            slot=None,
            payload={"slot_count": len(self.registration.slots)},
            validate=validate,
        )

    def start_slot(
        self,
        slot_number: int,
        session_id: str,
        *,
        marker_start_count: int | None = None,
        started_unix_ns: int | None = None,
    ) -> dict[str, Any]:
        created = _timestamp(started_unix_ns)
        requested_slot = _exact_int(slot_number, "slot_number")
        if marker_start_count is not None and (
            type(marker_start_count) is not int or marker_start_count < 0
        ):
            raise OutcomeEvidenceRunnerError(
                "marker_start_count must be a nonnegative integer"
            )

        def validate(snapshot: Mapping[str, Any]) -> None:
            expected = self._next_slot_from_snapshot(snapshot)
            if requested_slot != expected.slot_number:
                raise OutcomeEvidenceRunnerError(
                    "out of order launch: next registered slot is "
                    f"{expected.slot_number}"
                )
            if session_id != expected.session_id:
                raise OutcomeEvidenceRunnerError(
                    "session_id does not match the next registered slot"
                )

        return self._append(
            event="slot_started",
            created_unix_ns=created,
            slot=self._slots.get(requested_slot),
            payload=(
                {}
                if marker_start_count is None
                else {"marker_start_count": marker_start_count}
            ),
            validate=validate,
        )

    def finish_slot(
        self,
        slot_number: int,
        *,
        process_exit_code: int,
        complete_trajectories: int,
        marker_start_count: int | None = None,
        marker_end_count: int | None = None,
        ended_unix_ns: int | None = None,
    ) -> dict[str, Any]:
        created = _timestamp(ended_unix_ns)
        requested_slot = _exact_int(slot_number, "slot_number")
        exit_code = _exact_int(process_exit_code, "process_exit_code")
        complete = _bounded_count(complete_trajectories)
        marker_start, marker_end = _marker_bounds(
            marker_start_count,
            marker_end_count,
            complete_trajectories=complete,
        )
        terminal_status = (
            "completed" if exit_code == 0 and complete == 25 else "interrupted"
        )

        def validate(snapshot: Mapping[str, Any]) -> None:
            active = snapshot["active_slot"]
            if active is None:
                raise OutcomeEvidenceRunnerError(
                    "no active slot; duplicate terminal transition refused"
                )
            if active["slot_number"] != requested_slot:
                raise OutcomeEvidenceRunnerError("terminal slot is not the active slot")

        slot = self._slots.get(requested_slot)
        record = self._append(
            event="slot_terminal",
            created_unix_ns=created,
            slot=slot,
            payload={
                "complete_trajectories": complete,
                "marker_end_count": marker_end,
                "marker_start_count": marker_start,
                "process_exit_code": exit_code,
                "terminal_status": terminal_status,
            },
            validate=validate,
        )
        return dict(record["payload"])

    def recover_active_slot(
        self,
        *,
        reason: str,
        complete_trajectories: int,
        marker_start_count: int | None = None,
        marker_end_count: int | None = None,
        ended_unix_ns: int | None = None,
    ) -> dict[str, Any]:
        if not isinstance(reason, str) or not reason.strip():
            raise OutcomeEvidenceRunnerError("recovery reason must be nonempty")
        complete = _bounded_count(complete_trajectories)
        marker_start, marker_end = _marker_bounds(
            marker_start_count,
            marker_end_count,
            complete_trajectories=complete,
        )
        created = _timestamp(ended_unix_ns)
        selected_slot: RegisteredSlot | None = None

        def validate(snapshot: Mapping[str, Any]) -> None:
            nonlocal selected_slot
            active = snapshot["active_slot"]
            if active is None:
                raise OutcomeEvidenceRunnerError("there is no active slot to recover")
            selected_slot = self._slots[active["slot_number"]]

        record = self._append(
            event="slot_terminal",
            created_unix_ns=created,
            slot_getter=lambda: selected_slot,
            payload={
                "complete_trajectories": complete,
                "marker_end_count": marker_end,
                "marker_start_count": marker_start,
                "process_exit_code": None,
                "reason": reason.strip(),
                "terminal_status": "interrupted",
            },
            validate=validate,
        )
        return dict(record["payload"])

    def global_stop(
        self, *, reason: str, created_unix_ns: int | None = None
    ) -> dict[str, Any]:
        if not isinstance(reason, str) or not reason.strip():
            raise OutcomeEvidenceRunnerError("global stop reason must be nonempty")
        created = _timestamp(created_unix_ns)

        def validate(snapshot: Mapping[str, Any]) -> None:
            if not snapshot["initialized"]:
                raise OutcomeEvidenceRunnerError("study ledger is not initialized")
            if snapshot["global_stop"] is not None:
                raise OutcomeEvidenceRunnerError("duplicate global stop refused")

        record = self._append(
            event="global_stop",
            created_unix_ns=created,
            slot=None,
            payload={"reason": reason.strip()},
            validate=validate,
        )
        return dict(record["payload"])

    def next_slot(self) -> RegisteredSlot:
        return self._next_slot_from_snapshot(self.snapshot())

    def snapshot(self) -> dict[str, Any]:
        return self._reduce(self._read_records())

    def _next_slot_from_snapshot(
        self, snapshot: Mapping[str, Any]
    ) -> RegisteredSlot:
        if not snapshot["initialized"]:
            raise OutcomeEvidenceRunnerError("study ledger is not initialized")
        if snapshot["global_stop"] is not None:
            raise OutcomeEvidenceRunnerError("global stop prevents later launches")
        if snapshot["active_slot"] is not None:
            raise OutcomeEvidenceRunnerError(
                "active slot must become terminal before the next launch"
            )
        next_number = snapshot["terminal_slot_count"] + 1
        if next_number > len(self.registration.slots):
            raise OutcomeEvidenceRunnerError(
                "registered schedule is complete; there is no later slot"
            )
        return self._slots[next_number]

    def _append(
        self,
        *,
        event: str,
        created_unix_ns: int,
        payload: Mapping[str, Any],
        validate: Callable[[Mapping[str, Any]], None],
        slot: RegisteredSlot | None = None,
        slot_getter: Callable[[], RegisteredSlot | None] | None = None,
    ) -> dict[str, Any]:
        lock_path = self.path.with_name(self.path.name + ".append.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock_descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as exc:
            raise OutcomeEvidenceRunnerError(
                f"ledger append lock already exists: {lock_path}"
            ) from exc
        try:
            records = self._read_records()
            snapshot = self._reduce(records)
            validate(snapshot)
            if slot_getter is not None:
                slot = slot_getter()
            if event.startswith("slot_") and slot is None:
                raise OutcomeEvidenceRunnerError("slot event has no registered slot")
            previous_hash = records[-1]["record_hash"] if records else None
            record = {
                "created_unix_ns": created_unix_ns,
                "event": event,
                "payload": dict(payload),
                "previous_record_hash": previous_hash,
                "record_hash": None,
                "registration_hash": self.registration.registration_hash,
                "run_lock_hash": self.run_lock_hash,
                "schema_version": LEDGER_SCHEMA_VERSION,
                "sequence": len(records) + 1,
                "session_id": slot.session_id if slot is not None else None,
                "slot_number": slot.slot_number if slot is not None else None,
                "study_id": self.registration.study_id,
            }
            record["record_hash"] = _record_hash(record)
            self._append_line(_canonical_json(record).encode("utf-8") + b"\n")
            return json.loads(_canonical_json(record))
        finally:
            os.close(lock_descriptor)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def _append_line(self, encoded: bytes) -> None:
        descriptor = os.open(
            self.path,
            os.O_APPEND | os.O_CREAT | os.O_WRONLY,
        )
        try:
            written = os.write(descriptor, encoded)
            if written != len(encoded):
                raise OutcomeEvidenceRunnerError("partial ledger append detected")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            content = self.path.read_bytes()
        except OSError as exc:
            raise OutcomeEvidenceRunnerError(f"cannot read ledger: {exc}") from exc
        if not content:
            return []
        if not content.endswith(b"\n"):
            raise OutcomeEvidenceRunnerError("ledger has a partial final record")
        records = []
        previous_hash = None
        for index, raw_line in enumerate(content.splitlines(), start=1):
            try:
                record = json.loads(
                    raw_line.decode("utf-8"),
                    object_pairs_hook=_reject_duplicate_keys,
                    parse_constant=_reject_json_constant,
                )
            except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
                raise OutcomeEvidenceRunnerError(
                    f"invalid ledger record {index}: {exc}"
                ) from exc
            _validate_ledger_record(
                record,
                sequence=index,
                previous_hash=previous_hash,
                registration=self.registration,
                run_lock_hash=self.run_lock_hash,
            )
            previous_hash = record["record_hash"]
            records.append(record)
        return records

    def _reduce(self, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        initialized = False
        active_slot = None
        terminal_slots = []
        global_stop = None
        for record in records:
            event = record["event"]
            if event == "study_started":
                if initialized or record["sequence"] != 1:
                    raise OutcomeEvidenceRunnerError(
                        "duplicate or misplaced study_started record"
                    )
                initialized = True
            elif event == "slot_started":
                if (
                    not initialized
                    or active_slot is not None
                    or global_stop is not None
                ):
                    raise OutcomeEvidenceRunnerError("invalid slot_started lifecycle")
                expected = len(terminal_slots) + 1
                if record["slot_number"] != expected:
                    raise OutcomeEvidenceRunnerError("ledger slot order mismatch")
                active_slot = {
                    "marker_start_count": record["payload"].get(
                        "marker_start_count"
                    ),
                    "session_id": record["session_id"],
                    "slot_number": record["slot_number"],
                }
            elif event == "slot_terminal":
                if active_slot is None:
                    raise OutcomeEvidenceRunnerError(
                        "terminal record has no active slot"
                    )
                if record["slot_number"] != active_slot["slot_number"]:
                    raise OutcomeEvidenceRunnerError("terminal record slot mismatch")
                if (
                    active_slot["marker_start_count"] is not None
                    and record["payload"].get("marker_start_count")
                    != active_slot["marker_start_count"]
                ):
                    raise OutcomeEvidenceRunnerError(
                        "terminal marker start differs from slot claim"
                    )
                terminal_slots.append(
                    {
                        "complete_trajectories": record["payload"].get(
                            "complete_trajectories"
                        ),
                        "marker_end_count": record["payload"].get(
                            "marker_end_count"
                        ),
                        "marker_start_count": record["payload"].get(
                            "marker_start_count"
                        ),
                        "process_exit_code": record["payload"].get(
                            "process_exit_code"
                        ),
                        "session_id": record["session_id"],
                        "slot_number": record["slot_number"],
                        "terminal_status": record["payload"].get("terminal_status"),
                    }
                )
                active_slot = None
            elif event == "global_stop":
                if not initialized or global_stop is not None:
                    raise OutcomeEvidenceRunnerError("invalid global_stop lifecycle")
                global_stop = {"reason": record["payload"].get("reason")}
            else:
                raise OutcomeEvidenceRunnerError(f"unsupported ledger event: {event}")
        return {
            "active_slot": active_slot,
            "all_slots_terminal": (
                initialized
                and active_slot is None
                and len(terminal_slots) == len(self.registration.slots)
            ),
            "global_stop": global_stop,
            "initialized": initialized,
            "terminal_slot_count": len(terminal_slots),
            "terminal_slots": terminal_slots,
        }


def _registered_slot(
    registration: OutcomeEvidenceRegistration, slot_number: int
) -> RegisteredSlot:
    number = _exact_int(slot_number, "slot_number")
    if number < 1 or number > len(registration.slots):
        raise OutcomeEvidenceRunnerError("slot_number is not registered")
    slot = registration.slots[number - 1]
    if slot.slot_number != number:
        raise OutcomeEvidenceRunnerError("registration slot order is invalid")
    return slot


def _validate_run_lock_binding(
    registration: OutcomeEvidenceRegistration,
    run_lock: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(run_lock, Mapping):
        raise OutcomeEvidenceRunnerError("run lock must be an object")
    run_lock_hash = _required_sha256(run_lock.get("run_lock_hash"), "run lock hash")
    if run_lock.get("study_id") != registration.study_id:
        raise OutcomeEvidenceRunnerError("run lock study_id mismatch")
    registration_binding = run_lock.get("registration")
    if not isinstance(registration_binding, Mapping) or registration_binding.get(
        "canonical_hash"
    ) != registration.registration_hash:
        raise OutcomeEvidenceRunnerError("run lock registration hash mismatch")
    source = run_lock.get("source")
    source_commit = source.get("commit") if isinstance(source, Mapping) else None
    if not isinstance(source_commit, str) or not _is_lower_hex(
        source_commit, _GIT_COMMIT_LENGTH
    ):
        raise OutcomeEvidenceRunnerError("run lock source commit is invalid")
    return {"run_lock_hash": run_lock_hash, "source_commit": source_commit}


def _registered_command(registration: OutcomeEvidenceRegistration) -> list[str]:
    command_record = registration.to_record()["command"]
    return [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]


def _validate_ledger_record(
    record: Any,
    *,
    sequence: int,
    previous_hash: str | None,
    registration: OutcomeEvidenceRegistration,
    run_lock_hash: str,
) -> None:
    if not isinstance(record, Mapping):
        raise OutcomeEvidenceRunnerError("ledger record must be an object")
    expected_fields = {
        "created_unix_ns",
        "event",
        "payload",
        "previous_record_hash",
        "record_hash",
        "registration_hash",
        "run_lock_hash",
        "schema_version",
        "sequence",
        "session_id",
        "slot_number",
        "study_id",
    }
    if set(record) != expected_fields:
        raise OutcomeEvidenceRunnerError("ledger record fields mismatch")
    if record["schema_version"] != LEDGER_SCHEMA_VERSION:
        raise OutcomeEvidenceRunnerError("ledger schema_version mismatch")
    if type(record["sequence"]) is not int or record["sequence"] != sequence:
        raise OutcomeEvidenceRunnerError("ledger sequence mismatch")
    if record["previous_record_hash"] != previous_hash:
        raise OutcomeEvidenceRunnerError("ledger hash chain mismatch")
    if record["study_id"] != registration.study_id:
        raise OutcomeEvidenceRunnerError("ledger study_id mismatch")
    if record["registration_hash"] != registration.registration_hash:
        raise OutcomeEvidenceRunnerError("ledger registration hash mismatch")
    if record["run_lock_hash"] != run_lock_hash:
        raise OutcomeEvidenceRunnerError("ledger run lock mismatch")
    if type(record["created_unix_ns"]) is not int or record["created_unix_ns"] <= 0:
        raise OutcomeEvidenceRunnerError("ledger timestamp is invalid")
    if not isinstance(record["event"], str) or not isinstance(
        record["payload"], Mapping
    ):
        raise OutcomeEvidenceRunnerError("ledger event or payload is invalid")
    if record["event"] in {"slot_started", "slot_terminal"}:
        slot_number = record["slot_number"]
        if type(slot_number) is not int or not (
            1 <= slot_number <= len(registration.slots)
        ):
            raise OutcomeEvidenceRunnerError("ledger slot identity is invalid")
        registered_slot = registration.slots[slot_number - 1]
        if record["session_id"] != registered_slot.session_id:
            raise OutcomeEvidenceRunnerError(
                "ledger session identity differs from registration"
            )
    elif record["event"] in {"study_started", "global_stop"}:
        if record["slot_number"] is not None or record["session_id"] is not None:
            raise OutcomeEvidenceRunnerError(
                "non-slot ledger event contains a session identity"
            )
    else:
        raise OutcomeEvidenceRunnerError(
            f"unsupported ledger event: {record['event']}"
        )
    payload = record["payload"]
    if record["event"] == "study_started":
        if payload != {"slot_count": len(registration.slots)}:
            raise OutcomeEvidenceRunnerError("study_started payload mismatch")
    elif record["event"] == "slot_started":
        if set(payload) not in (set(), {"marker_start_count"}):
            raise OutcomeEvidenceRunnerError("slot_started payload fields mismatch")
        if "marker_start_count" in payload and (
            type(payload["marker_start_count"]) is not int
            or payload["marker_start_count"] < 0
        ):
            raise OutcomeEvidenceRunnerError(
                "slot_started marker_start_count is invalid"
            )
    elif record["event"] == "slot_terminal":
        required_payload_fields = {
            "complete_trajectories",
            "marker_end_count",
            "marker_start_count",
            "process_exit_code",
            "terminal_status",
        }
        actual_payload_fields = set(payload)
        if not required_payload_fields.issubset(actual_payload_fields) or not (
            actual_payload_fields <= required_payload_fields | {"reason"}
        ):
            raise OutcomeEvidenceRunnerError("slot_terminal payload fields mismatch")
        complete = _bounded_count(payload["complete_trajectories"])
        _marker_bounds(
            payload["marker_start_count"],
            payload["marker_end_count"],
            complete_trajectories=complete,
        )
        exit_code = payload["process_exit_code"]
        if exit_code is not None and type(exit_code) is not int:
            raise OutcomeEvidenceRunnerError("process_exit_code is invalid")
        expected_status = (
            "completed" if exit_code == 0 and complete == 25 else "interrupted"
        )
        if payload["terminal_status"] != expected_status:
            raise OutcomeEvidenceRunnerError("terminal_status contradicts evidence")
        if "reason" in payload and (
            not isinstance(payload["reason"], str) or not payload["reason"].strip()
        ):
            raise OutcomeEvidenceRunnerError("terminal interruption reason is invalid")
        if exit_code is None and "reason" not in payload:
            raise OutcomeEvidenceRunnerError(
                "missing reason for terminal record without an exit code"
            )
    else:
        if set(payload) != {"reason"} or not isinstance(
            payload.get("reason"), str
        ) or not payload["reason"].strip():
            raise OutcomeEvidenceRunnerError("global_stop payload is invalid")
    supplied_hash = record["record_hash"]
    if not isinstance(supplied_hash, str) or not _is_lower_hex(
        supplied_hash, _SHA256_LENGTH
    ):
        raise OutcomeEvidenceRunnerError("ledger record hash is invalid")
    if supplied_hash != _record_hash(record):
        raise OutcomeEvidenceRunnerError("ledger record hash mismatch")


def _record_hash(record: Mapping[str, Any]) -> str:
    hash_input = dict(record)
    hash_input["record_hash"] = None
    return hashlib.sha256(_canonical_json(hash_input).encode("utf-8")).hexdigest()


def _publish_text_once(path: Path, text: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        descriptor, name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_path, path)
    except FileExistsError as exc:
        raise OutcomeEvidenceRunnerError(f"{label} already exists: {path}") from exc
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(f"cannot publish {label}: {exc}") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(f"value is not canonical JSON: {exc}") from exc


def _timestamp(value: int | None) -> int:
    timestamp = time.time_ns() if value is None else value
    if type(timestamp) is not int or timestamp <= 0:
        raise OutcomeEvidenceRunnerError("timestamp must be a positive integer")
    return timestamp


def _exact_int(value: Any, field: str) -> int:
    if type(value) is not int:
        raise OutcomeEvidenceRunnerError(f"{field} must be an exact integer")
    return value


def _bounded_count(value: Any) -> int:
    count = _exact_int(value, "complete_trajectories")
    if count < 0 or count > 25:
        raise OutcomeEvidenceRunnerError(
            "complete_trajectories must be between 0 and 25"
        )
    return count


def _marker_bounds(
    start: Any,
    end: Any,
    *,
    complete_trajectories: int,
) -> tuple[int | None, int | None]:
    if start is None and end is None:
        return None, None
    if type(start) is not int or type(end) is not int or start < 0 or end < start:
        raise OutcomeEvidenceRunnerError("AI marker bounds are invalid")
    if end - start != complete_trajectories:
        raise OutcomeEvidenceRunnerError(
            "AI marker bounds differ from complete_trajectories"
        )
    return start, end


def _required_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _is_lower_hex(value, _SHA256_LENGTH):
        raise OutcomeEvidenceRunnerError(f"{field} must be a SHA-256 hash")
    return value


def _is_lower_hex(value: str, length: int) -> bool:
    return len(value) == length and all(
        character in "0123456789abcdef" for character in value
    )


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise OutcomeEvidenceRunnerError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise OutcomeEvidenceRunnerError(f"invalid JSON constant: {value}")


def _load_run_lock_record(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(f"cannot load run lock: {exc}") from exc
    if not isinstance(payload, dict):
        raise OutcomeEvidenceRunnerError("run lock must be an object")
    return payload


def _ledger_path(registration: OutcomeEvidenceRegistration) -> Path:
    return Path(registration.artifact_root) / "study-ledger.jsonl"


def _run_lock_path(registration: OutcomeEvidenceRegistration) -> Path:
    return Path(registration.artifact_root) / "run-lock.json"


def _blocked_monitor_run_lock(
    registration: OutcomeEvidenceRegistration,
    ledger: StudyLedger,
) -> dict[str, Any]:
    return {
        "registration": {"canonical_hash": registration.registration_hash},
        "run_lock_hash": ledger.run_lock_hash,
        "source": {"commit": "0" * _GIT_COMMIT_LENGTH},
        "study_id": registration.study_id,
    }


def _load_runner_registration(
    registration_path: Path,
) -> OutcomeEvidenceRegistration:
    registration = load_registration(registration_path)
    registered_root = Path(registration.repo_root).resolve()
    if registered_root != REPO_ROOT:
        raise OutcomeEvidenceRunnerError(
            "registration repo_root does not match the runner checkout: "
            f"registered={registered_root}, runner={REPO_ROOT}"
        )
    return registration


def _require_launchable_runner_registration(
    registration: OutcomeEvidenceRegistration,
) -> OutcomeEvidenceRegistration:
    try:
        return require_launchable_registration(registration)
    except OutcomeEvidenceRegistrationError as exc:
        raise OutcomeEvidenceRunnerError(str(exc)) from exc


def _start_command(registration_path: Path) -> dict[str, Any]:
    registration = _load_runner_registration(registration_path)
    registration = _require_launchable_runner_registration(registration)
    command = _registered_command(registration)
    run_lock = create_run_lock(
        registration_path=registration_path,
        lock_path=_run_lock_path(registration),
        repo_root=registration.repo_root,
        child_command=command,
    )
    ledger = StudyLedger(
        path=_ledger_path(registration),
        registration=registration,
        run_lock_hash=run_lock["run_lock_hash"],
    )
    ledger.initialize()
    try:
        for slot in registration.slots:
            write_slot_config_once(
                build_slot_launch(registration, run_lock, slot.slot_number)
            )
    except Exception as exc:
        ledger.global_stop(
            reason=f"registered config publication failed: {type(exc).__name__}: {exc}"
        )
        raise
    return run_lock


def _dry_run_command(registration_path: Path) -> dict[str, Any]:
    registration = _load_runner_registration(registration_path)
    command = _registered_command(registration)
    run_lock_path = _run_lock_path(registration)
    ledger_path = _ledger_path(registration)
    if run_lock_path.exists() or ledger_path.exists():
        ledger = StudyLedger.open_existing(
            path=ledger_path,
            registration=registration,
        )
        run_lock = dict(
            validate_run_lock_or_stop(
                ledger,
                validator=lambda: validate_run_lock(
                    lock_path=run_lock_path,
                    registration_path=registration_path,
                    repo_root=registration.repo_root,
                    child_command=command,
                ),
            )
        )
    else:
        source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=registration.repo_root,
            text=True,
            encoding="utf-8",
        ).strip().lower()
        run_lock = {
            "registration": {"canonical_hash": registration.registration_hash},
            "run_lock_hash": "0" * 64,
            "source": {"commit": source_commit},
            "study_id": registration.study_id,
        }
    launches = [
        build_slot_launch(registration, run_lock, slot.slot_number)
        for slot in registration.slots
    ]
    handshake_rules = registration_handshake_rules(registration)
    return {
        "launch_count": len(launches),
        "launches": [
            {
                "command": list(launch.command),
                "config_path": launch.config_path,
                "config_record": dict(launch.config_record),
                "environment": dict(launch.environment),
                "handshake": _dry_run_handshake_record(
                    launch,
                    handshake_rules,
                ),
                "session_id": launch.session_id,
                "slot_number": launch.slot_number,
            }
            for launch in launches
        ],
        "study_id": registration.study_id,
    }


def _dry_run_handshake_record(
    launch: RegisteredSlotLaunch,
    rules: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if rules is None:
        return None
    paths = _handshake_paths_from_rules(
        config_path=launch.config_path,
        session_id=launch.session_id,
        rules=rules,
    )
    return {
        "attempt_path": str(paths.attempt),
        "protocol_version": rules["protocol_version"],
        "readiness_timeout_seconds": rules["readiness_timeout_seconds"],
        "ready_path": str(paths.ready),
        "release_path": str(paths.release),
        "release_timeout_seconds": rules["release_timeout_seconds"],
    }


def _run_next_command(registration_path: Path) -> dict[str, Any]:
    registration = _load_runner_registration(registration_path)
    registration = _require_launchable_runner_registration(registration)
    command = _registered_command(registration)
    run_lock_path = _run_lock_path(registration)
    ledger = StudyLedger.open_existing(
        path=_ledger_path(registration),
        registration=registration,
    )
    marker_path = (
        Path(registration.checkpoint_root).parent / "runs" / "ai_games.txt"
    )
    _recover_active_slot_after_host_failure(
        ledger=ledger,
        marker_path=marker_path,
    )
    run_lock = validate_run_lock_or_stop(
        ledger,
        validator=lambda: validate_run_lock(
            lock_path=run_lock_path,
            registration_path=registration_path,
            repo_root=registration.repo_root,
            child_command=command,
        ),
    )
    slot = ledger.next_slot()
    launch = build_slot_launch(registration, run_lock, slot.slot_number)
    config_path = Path(launch.config_path)
    if not config_path.exists():
        raise OutcomeEvidenceRunnerError(
            f"registered slot config is missing: {config_path}"
        )
    def process_starter(
        _launch: RegisteredSlotLaunch,
        child_environment: Mapping[str, str],
    ) -> subprocess.Popen:
        environment = os.environ.copy()
        environment.update(child_environment)
        return subprocess.Popen(
            list(launch.command),
            env=environment,
            cwd=str(Path(registration.checkpoint_root).parent),
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    return execute_handshaken_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_starter=process_starter,
        preclaim_validator=lambda: validate_run_lock(
            lock_path=run_lock_path,
            registration_path=registration_path,
            repo_root=registration.repo_root,
            child_command=command,
        ),
    )


def _monitor_command(registration_path: Path) -> dict[str, Any]:
    registration = _load_runner_registration(registration_path)
    command = _registered_command(registration)
    run_lock_path = _run_lock_path(registration)
    ledger = StudyLedger.open_existing(
        path=_ledger_path(registration),
        registration=registration,
    )
    snapshot = ledger.snapshot()
    stop_reason = (
        snapshot["global_stop"].get("reason")
        if isinstance(snapshot["global_stop"], Mapping)
        else None
    )
    run_lock_valid = not (
        isinstance(stop_reason, str)
        and stop_reason.startswith("run lock validation failed:")
    )
    run_lock: dict[str, Any] | None = None
    if snapshot["global_stop"] is None:
        try:
            run_lock = dict(
                validate_run_lock_or_stop(
                    ledger,
                    validator=lambda: validate_run_lock(
                        lock_path=run_lock_path,
                        registration_path=registration_path,
                        repo_root=registration.repo_root,
                        child_command=command,
                    ),
                )
            )
        except OutcomeEvidenceRunnerError:
            run_lock_valid = False
            snapshot = ledger.snapshot()
    if run_lock is None:
        try:
            candidate_run_lock = _load_run_lock_record(run_lock_path)
            candidate_binding = _validate_run_lock_binding(
                registration,
                candidate_run_lock,
            )
            if candidate_binding["run_lock_hash"] != ledger.run_lock_hash:
                raise OutcomeEvidenceRunnerError(
                    "monitor run lock differs from the ledger binding"
                )
            run_lock = candidate_run_lock
        except OutcomeEvidenceRunnerError:
            run_lock_valid = False
            run_lock = _blocked_monitor_run_lock(registration, ledger)
    observations = collect_structural_observations(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=snapshot,
    )
    monitor = build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=snapshot,
        structural_observations=observations,
        run_lock_valid=run_lock_valid,
    )
    artifact_root = Path(registration.artifact_root)
    write_blinded_monitor_artifacts(
        monitor,
        json_path=artifact_root / "blinded-monitor.json",
        markdown_path=artifact_root / "blinded-monitor.md",
    )
    return monitor


def _finalize_gate_command(registration_path: Path) -> dict[str, Any]:
    registration = _load_runner_registration(registration_path)
    ledger = StudyLedger.open_existing(
        path=_ledger_path(registration),
        registration=registration,
    )
    snapshot = ledger.snapshot()
    if not (
        snapshot["all_slots_terminal"] or snapshot["global_stop"] is not None
    ):
        raise OutcomeEvidenceRunnerError(
            "finalization requires all slots terminal or a global stop"
        )
    if snapshot["global_stop"] is not None:
        return finalize_registered_integrity_stop(
            registration,
            run_lock_hash=ledger.run_lock_hash,
            ledger_snapshot=snapshot,
        )

    command = _registered_command(registration)
    try:
        run_lock = validate_run_lock_or_stop(
            ledger,
            validator=lambda: validate_run_lock(
                lock_path=_run_lock_path(registration),
                registration_path=registration_path,
                repo_root=registration.repo_root,
                child_command=command,
            ),
        )
    except OutcomeEvidenceRunnerError:
        snapshot = ledger.snapshot()
        if snapshot["global_stop"] is None:
            raise
        return finalize_registered_integrity_stop(
            registration,
            run_lock_hash=ledger.run_lock_hash,
            ledger_snapshot=snapshot,
        )
    snapshot = ledger.snapshot()
    if snapshot["global_stop"] is not None:
        return finalize_registered_integrity_stop(
            registration,
            run_lock_hash=ledger.run_lock_hash,
            ledger_snapshot=snapshot,
        )
    sessions = collect_registered_session_evidence(
        registration,
        run_lock=run_lock,
        ledger_snapshot=snapshot,
    )
    run_lock_hash = str(run_lock["run_lock_hash"])
    pool = build_registered_pool(
        registration,
        run_lock_hash=run_lock_hash,
        ledger_snapshot=snapshot,
        sessions=sessions,
    )
    return finalize_registered_outcome_evidence(
        registration,
        run_lock_hash=run_lock_hash,
        ledger_snapshot=snapshot,
        pool=pool,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Operate the registered non-combat outcome-evidence study."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    for name in ("start", "dry-run", "run-next", "monitor", "finalize"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--registration", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.subcommand == "start":
            result = _start_command(args.registration)
        elif args.subcommand == "dry-run":
            result = _dry_run_command(args.registration)
        elif args.subcommand == "run-next":
            result = _run_next_command(args.registration)
        elif args.subcommand == "monitor":
            result = _monitor_command(args.registration)
        else:
            result = _finalize_gate_command(args.registration)
        output_stream = sys.stderr if args.subcommand == "run-next" else sys.stdout
        print(_canonical_json(result), file=output_stream)
        return 0
    except Exception as exc:
        print(f"[outcome-evidence] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

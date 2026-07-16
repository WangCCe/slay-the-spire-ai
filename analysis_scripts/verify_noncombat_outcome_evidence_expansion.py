"""Independently replay a registered non-combat outcome-evidence study."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from analysis_scripts.verify_noncombat_ope_artifacts import (
    ArtifactVerificationError,
    verify_artifact_pair,
)
from analysis_scripts.verify_noncombat_ope_estimates import (
    EstimateVerificationError,
    verify_estimate_artifact,
)


AUDIT_SCHEMA_VERSION = "noncombat-outcome-evidence-verification-audit-v1"
LEGACY_REGISTRATION_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-registration-v1"
)
REGISTRATION_SCHEMA_VERSION = "noncombat-outcome-evidence-registration-v2"
RUN_LOCK_SCHEMA_VERSION = "noncombat-outcome-evidence-run-lock-v1"
LEDGER_SCHEMA_VERSION = "noncombat-outcome-evidence-ledger-v1"
POOL_SCHEMA_VERSION = "noncombat-outcome-evidence-pool-v1"
CLOSEOUT_SCHEMA_VERSION = "noncombat-outcome-evidence-closeout-v1"
EVIDENCE_GATE_SCHEMA_VERSION = "noncombat-outcome-evidence-gate-v1"
CLAIM_SCHEMA_VERSION = "noncombat-outcome-evidence-finalization-claim-v1"
HANDSHAKE_SCHEMA_VERSION = "noncombat-outcome-evidence-handshake-v1"
HANDSHAKE_ATTEMPT_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-handshake-attempt-v1"
)
HANDSHAKE_READY_SCHEMA_VERSION = "noncombat-outcome-evidence-handshake-ready-v1"
HANDSHAKE_RELEASE_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-handshake-release-v1"
)
BLOCKED_ESTIMATE_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-estimate-blocked-v1"
)
ESTIMATE_SCHEMA_VERSION = "noncombat-ope-estimate-v1"
SLOT_COUNT = 24
GAMES_PER_SLOT = 25
SCHEDULED_ATTEMPTS = SLOT_COUNT * GAMES_PER_SLOT
DRAW_BUCKET_COUNT = 10_000
OUTCOME_JOIN_TOLERANCE_SECONDS = 30
WINDOWS_PYTHON = str(Path(r"D:\anaconda\envs\stsai\python.exe").resolve())
SELECTION_SCHEMA_VERSION = "noncombat-exploration-selection-v1"
COMMAND_ARGUMENTS = (
    "--agent",
    "combat_rl",
    "--elite-route",
    "conservative",
    "--max-games",
    "25",
    "--ascension",
    "0",
    "--rl-version",
    "v2",
    "--eval",
)
LEGACY_IMPLEMENTATION_PATHS = (
    "analysis_scripts/__init__.py",
    "analysis_scripts/noncombat_exploration_evidence.py",
    "analysis_scripts/noncombat_ope_estimate_artifacts.py",
    "analysis_scripts/noncombat_ope_estimation.py",
    "analysis_scripts/noncombat_ope_readiness.py",
    "analysis_scripts/noncombat_outcome_evidence_expansion.py",
    "analysis_scripts/verify_noncombat_ope_artifacts.py",
    "analysis_scripts/verify_noncombat_ope_estimates.py",
    "analysis_scripts/verify_noncombat_outcome_evidence_expansion.py",
    "main.py",
    "scripts/run_noncombat_outcome_evidence_expansion.py",
    "spirecomm/ai/noncombat_exploration.py",
    "spirecomm/ai/noncombat_exploration_runtime.py",
)
IMPLEMENTATION_PATHS = (
    *LEGACY_IMPLEMENTATION_PATHS,
    "spirecomm/communication/study_handshake.py",
)
CHECKPOINT_PATTERNS = ("rl_combat_model_*.pth", "rl_model_*.pth")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_STUDY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class OutcomeEvidenceVerificationError(ValueError):
    """Raised when independent study replay cannot close every check."""


class _DuplicateJsonKeyError(ValueError):
    pass


class _Checks:
    def __init__(self) -> None:
        self.count = 0

    def require(self, condition: bool, message: str) -> None:
        self.count += 1
        if condition is not True:
            raise OutcomeEvidenceVerificationError(message)


def verify_outcome_evidence_expansion(
    registration_path: Path | str,
) -> dict[str, Any]:
    """Replay registration-through-closeout evidence without study imports."""

    checks = _Checks()
    try:
        registration_path = Path(registration_path).resolve()
        registration_bytes = registration_path.read_bytes()
        registration = _load_mapping_bytes(registration_bytes, registration_path)
        _verify_registration(registration, checks)
        paths = _artifact_paths(registration)

        run_lock = _load_mapping(paths["run_lock"])
        locked_isolation = _verify_run_lock(
            run_lock,
            registration=registration,
            registration_path=registration_path,
            registration_bytes=registration_bytes,
            checks=checks,
        )
        ledger = _verify_ledger(
            paths["ledger"],
            registration=registration,
            run_lock=run_lock,
            checks=checks,
        )
        _verify_handshake_evidence(
            registration=registration,
            run_lock=run_lock,
            ledger=ledger,
            checks=checks,
        )
        claim = _verify_claim(
            paths["claim"],
            registration=registration,
            run_lock=run_lock,
            checks=checks,
        )
        blocked = ledger["global_stop"] is not None
        expected_claim_mode = "integrity_stop" if blocked else "complete"
        checks.require(
            claim["mode"] == expected_claim_mode,
            "ledger and finalization claim mode mismatch",
        )
        implementation_hashes = {
            str(row["relative_path"]): str(row["sha256"])
            for row in run_lock["implementation_files"]
        }
        if blocked:
            blocked_result = _verify_blocked_closeout(
                registration=registration,
                run_lock=run_lock,
                ledger=ledger,
                paths=paths,
                checks=checks,
            )
            return {
                "check_count": checks.count,
                "closeout_hash": blocked_result["closeout_hash"],
                "closeout_mode": "integrity_stop",
                "ledger_final_record_hash": ledger["final_record_hash"],
                "passed": True,
                "registration_hash": registration["registration_hash"],
                "run_lock_hash": run_lock["run_lock_hash"],
                "run_lock_isolation": locked_isolation,
                "schema_version": AUDIT_SCHEMA_VERSION,
                "source_implementation_sha256": implementation_hashes,
                "study_id": registration["study_id"],
                "verifier_implementation_sha256": _file_sha256(Path(__file__)),
            }

        checks.require(
            len(ledger["terminal_slots"]) == SLOT_COUNT,
            "not every registered slot is terminal",
        )
        live_isolation = _verify_live_run_lock_state(
            run_lock,
            registration=registration,
            registration_path=registration_path,
            registration_bytes=registration_bytes,
            checks=checks,
        )

        samples = _load_jsonl(paths["pool_samples"])
        pool = _load_mapping(paths["pool_manifest"])
        pool_result = _verify_pool(
            samples,
            pool,
            registration=registration,
            run_lock=run_lock,
            ledger=ledger,
            checks=checks,
        )
        target = _load_mapping(paths["target"])
        readiness = _load_mapping(paths["readiness"])
        try:
            readiness_audit = verify_artifact_pair(
                paths["pool_samples"],
                paths["target"],
                paths["readiness"],
            )
        except ArtifactVerificationError as exc:
            raise OutcomeEvidenceVerificationError(
                f"OPE readiness replay failed: {exc}"
            ) from exc
        metrics = _recompute_metrics(
            samples,
            target,
            registration=registration,
            pool_result=pool_result,
            checks=checks,
        )
        _verify_readiness_metrics(readiness, metrics, checks)

        estimate = _load_mapping(paths["estimate"])
        estimate_result = _verify_estimate(
            estimate,
            paths=paths,
            registration=registration,
            readiness=readiness,
            readiness_audit=readiness_audit,
            checks=checks,
        )
        expected_gate = _build_evidence_gate(registration, metrics)
        closeout = _load_mapping(paths["closeout"])
        _verify_closeout(
            closeout,
            registration=registration,
            run_lock=run_lock,
            ledger=ledger,
            pool=pool,
            target=target,
            readiness=readiness,
            estimate_result=estimate_result,
            expected_gate=expected_gate,
            paths=paths,
            checks=checks,
        )

        return {
            "ai_marker_file_sha256": pool_result[
                "ai_marker_file_sha256"
            ],
            "check_count": checks.count,
            "closeout_mode": "complete",
            "conservative_join_run_file_sha256": pool_result[
                "conservative_join_run_file_sha256"
            ],
            "conservative_run_inventory_sha256": pool_result[
                "conservative_run_inventory_sha256"
            ],
            "ledger_final_record_hash": ledger["final_record_hash"],
            "live_isolation": live_isolation,
            "passed": True,
            "pool_manifest_hash": pool["pool_manifest_hash"],
            "recomputed": {
                "category_arm_support": metrics["category_arm_support"],
                "complete_trajectory_count": metrics[
                    "complete_trajectory_count"
                ],
                "ess_fraction": _fraction_record(metrics["ess_fraction"]),
                "max_normalized_weight": _fraction_record(
                    metrics["max_normalized_weight"]
                ),
                "nonzero_weight_trajectory_count": metrics[
                    "nonzero_weight_trajectory_count"
                ],
                "outcome_evidence_expansion_ready": expected_gate[
                    "outcome_evidence_expansion_ready"
                ],
                "supported_victories": metrics["supported_victories"],
                "supported_victory_count": metrics[
                    "supported_victory_count"
                ],
            },
            "registration_hash": registration["registration_hash"],
            "run_lock_hash": run_lock["run_lock_hash"],
            "schema_version": AUDIT_SCHEMA_VERSION,
            "source_implementation_sha256": implementation_hashes,
            "study_id": registration["study_id"],
            "terminal_outcome_file_sha256": pool_result[
                "terminal_outcome_file_sha256"
            ],
            "verifier_implementation_sha256": _file_sha256(Path(__file__)),
        }
    except OutcomeEvidenceVerificationError:
        raise
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise OutcomeEvidenceVerificationError(
            f"outcome-evidence verification failed: {exc}"
        ) from exc


def render_verification_audit(audit: Mapping[str, Any]) -> str:
    if not isinstance(audit, Mapping) or audit.get("passed") is not True:
        raise OutcomeEvidenceVerificationError("verification audit is not passing")
    return _canonical_json(audit) + "\n"


def _verify_registration(record: Mapping[str, Any], checks: _Checks) -> None:
    supplied_hash = record.get("registration_hash")
    checks.require(_is_sha256(supplied_hash), "registration hash is invalid")
    checks.require(
        supplied_hash == _self_hash(record, "registration_hash"),
        "registration hash mismatch",
    )
    expected = _expected_registration(record)
    expected["registration_hash"] = supplied_hash
    checks.require(record == expected, "registered study contract mismatch")


def _expected_registration(record: Mapping[str, Any]) -> dict[str, Any]:
    schema_version = _required_string(
        record.get("schema_version"),
        "schema_version",
    )
    if schema_version == LEGACY_REGISTRATION_SCHEMA_VERSION:
        implementation_paths = LEGACY_IMPLEMENTATION_PATHS
    elif schema_version == REGISTRATION_SCHEMA_VERSION:
        implementation_paths = IMPLEMENTATION_PATHS
    else:
        raise OutcomeEvidenceVerificationError(
            "registration schema_version is unsupported"
        )
    study_id = _required_string(record.get("study_id"), "study_id")
    if _STUDY_PATTERN.fullmatch(study_id) is None:
        raise OutcomeEvidenceVerificationError("study_id is invalid")
    artifact_root = _absolute_path(record.get("artifact_root"), "artifact_root")
    repo_root = _absolute_path(record.get("repo_root"), "repo_root")
    seed_base = _exact_int(record.get("seed_base"), "seed_base")
    command = _mapping(record.get("command"), "command")
    python_executable = _required_string(
        command.get("python_executable"),
        "python_executable",
    )
    if str(Path(python_executable).resolve()) != WINDOWS_PYTHON:
        raise OutcomeEvidenceVerificationError("registered Python path mismatch")
    integrity = _mapping(record.get("integrity_rules"), "integrity_rules")
    communication_path = _absolute_path(
        integrity.get("communication_config_path"),
        "communication_config_path",
    )
    checkpoint_inventory = _mapping(
        integrity.get("checkpoint_inventory"),
        "checkpoint_inventory",
    )
    checkpoint_root = _absolute_path(
        checkpoint_inventory.get("root"),
        "checkpoint_root",
    )
    slots = []
    for number in range(1, SLOT_COUNT + 1):
        session_id = f"{study_id}-s{number:02d}"
        slots.append(
            {
                "config_path": str(
                    (artifact_root / f"{session_id}-config.json").resolve()
                ),
                "manifest_path": str(
                    (artifact_root / f"{session_id}-manifest.json").resolve()
                ),
                "seed": seed_base + number,
                "session_id": session_id,
                "slot_number": number,
                "trace_path": str(
                    (artifact_root / f"{session_id}-trace.jsonl").resolve()
                ),
            }
        )
    integrity_rules = {
        "checkpoint_inventory": {
            "patterns": list(CHECKPOINT_PATTERNS),
            "root": str(checkpoint_root),
        },
        "communication_config_path": str(communication_path),
        "implementation_paths": list(implementation_paths),
        "launches_per_slot": 1,
        "replacement_slots_forbidden": True,
        "tracked_source_frozen_during_run_lock": True,
    }
    if schema_version == REGISTRATION_SCHEMA_VERSION:
        integrity_rules["communication_handshake"] = {
            "attempt_suffix": "-communication-attempt.json",
            "orphaned_attempt_global_stop": True,
            "protocol_version": "noncombat-outcome-evidence-handshake-v1",
            "readiness_timeout_seconds": 30,
            "ready_suffix": "-communication-ready.json",
            "release_suffix": "-communication-release.json",
            "release_timeout_seconds": 10,
            "required_before_slot_claim": True,
        }
    return {
        "analysis_rules": {
            "bootstrap_confidence_level": {
                "denominator": 100,
                "numerator": 95,
            },
            "bootstrap_replicates": 10_000,
            "bootstrap_seed": (
                f"{study_id}:current-deterministic-bootstrap-v1"
            ),
            "calibration_artifact_relative_path": (
                "reports/noncombat_ope_estimator_calibration_20260714.json"
            ),
            "target_policy_mode": "current_deterministic",
        },
        "artifact_root": str(artifact_root),
        "behavior": {
            "category_rates_bps": {"card_reward": 300, "shop": 1000},
            "enabled_categories": ["card_reward", "shop"],
            "executable_alternatives": {
                "card_reward": "card_reward:skip",
                "shop": "shop:leave",
            },
            "per_run_alternative_budget": 2,
            "shadow_only_categories": ["event", "route"],
        },
        "blinding_rules": {
            "finalization_requires_all_slots_terminal": True,
            "outcome_adaptive_decisions_forbidden": True,
            "outcome_fields_forbidden_during_collection": True,
        },
        "command": {
            "arguments": list(COMMAND_ARGUMENTS),
            "main_path": str((repo_root / "main.py").resolve()),
            "python_executable": python_executable,
        },
        "games_per_slot": GAMES_PER_SLOT,
        "integrity_rules": integrity_rules,
        "output_rules": {
            "canonical_json_line_ending": "LF",
            "closeout_json_filename": "outcome-evidence-closeout.json",
            "closeout_markdown_filename": "outcome-evidence-closeout.md",
            "config_suffix": "-config.json",
            "estimate_json_filename": "ope-estimate.json",
            "estimate_markdown_filename": "ope-estimate.md",
            "finalization_claim_filename": "finalization-claim.json",
            "manifest_suffix": "-manifest.json",
            "monitor_json_filename": "blinded-monitor.json",
            "monitor_markdown_filename": "blinded-monitor.md",
            "pool_manifest_filename": "registered-pool-manifest.json",
            "pool_samples_filename": "registered-pool-samples.jsonl",
            "readiness_json_filename": "ope-readiness.json",
            "readiness_markdown_filename": "ope-readiness.md",
            "run_lock_filename": "run-lock.json",
            "study_ledger_filename": "study-ledger.jsonl",
            "target_manifest_filename": "current-target.json",
            "trace_suffix": "-trace.jsonl",
        },
        "registration_hash": None,
        "repo_root": str(repo_root),
        "scheduled_attempts": SCHEDULED_ATTEMPTS,
        "schema_version": schema_version,
        "seed_base": seed_base,
        "slot_count": SLOT_COUNT,
        "slots": slots,
        "study_id": study_id,
        "thresholds": {
            "maximum_normalized_weight": {"denominator": 20, "numerator": 1},
            "minimum_arm_decisions_per_category": 50,
            "minimum_complete_trajectories": 575,
            "minimum_ess_fraction": {"denominator": 2, "numerator": 1},
            "minimum_nonzero_weight_fraction": {
                "denominator": 2,
                "numerator": 1,
            },
            "minimum_supported_victories": 3,
        },
    }


def _artifact_paths(registration: Mapping[str, Any]) -> dict[str, Path]:
    root = Path(str(registration["artifact_root"]))
    rules = _mapping(registration.get("output_rules"), "output_rules")
    repo_root = Path(str(registration["repo_root"]))
    analysis = _mapping(registration.get("analysis_rules"), "analysis_rules")
    return {
        "calibration": repo_root
        / str(analysis["calibration_artifact_relative_path"]),
        "claim": root / str(rules["finalization_claim_filename"]),
        "closeout": root / str(rules["closeout_json_filename"]),
        "closeout_markdown": root
        / str(rules["closeout_markdown_filename"]),
        "estimate": root / str(rules["estimate_json_filename"]),
        "estimate_markdown": root
        / str(rules["estimate_markdown_filename"]),
        "ledger": root / str(rules["study_ledger_filename"]),
        "pool_manifest": root / str(rules["pool_manifest_filename"]),
        "pool_samples": root / str(rules["pool_samples_filename"]),
        "readiness": root / str(rules["readiness_json_filename"]),
        "readiness_markdown": root
        / str(rules["readiness_markdown_filename"]),
        "run_lock": root / str(rules["run_lock_filename"]),
        "target": root / str(rules["target_manifest_filename"]),
    }


def _verify_handshake_evidence(
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    checks: _Checks,
) -> None:
    if registration["schema_version"] == LEGACY_REGISTRATION_SCHEMA_VERSION:
        return

    rules = _mapping(
        registration["integrity_rules"].get("communication_handshake"),
        "communication_handshake",
    )
    terminals = list(ledger["terminal_slots"])
    terminal_count = len(terminals)
    blocked = ledger["global_stop"] is not None
    for raw_slot in registration["slots"]:
        slot = _mapping(raw_slot, "registered slot")
        slot_number = _exact_int(slot.get("slot_number"), "slot_number")
        paths = _handshake_paths(slot, rules)
        if slot_number <= terminal_count:
            terminal = terminals[slot_number - 1]
            checks.require(
                paths["attempt"].is_file(),
                f"slot {slot_number} handshake attempt is missing",
            )
            attempt = _verify_handshake_attempt(
                _load_canonical_handshake_record(
                    paths["attempt"],
                    f"slot {slot_number} handshake attempt",
                ),
                registration=registration,
                run_lock=run_lock,
                slot=slot,
                paths=paths,
                rules=rules,
                expected_marker_start=terminal["marker_start_count"],
                checks=checks,
            )
            checks.require(
                paths["ready"].is_file(),
                f"slot {slot_number} handshake ready record is missing",
            )
            ready = _verify_handshake_ready(
                _load_canonical_handshake_record(
                    paths["ready"],
                    f"slot {slot_number} handshake ready",
                ),
                attempt=attempt,
                checks=checks,
            )
            release_exists = paths["release"].exists()
            if terminal["terminal_status"] == "completed":
                checks.require(
                    paths["release"].is_file(),
                    f"slot {slot_number} handshake release is missing",
                )
            if release_exists:
                _verify_handshake_release(
                    _load_canonical_handshake_record(
                        paths["release"],
                        f"slot {slot_number} handshake release",
                    ),
                    attempt=attempt,
                    ready=ready,
                    checks=checks,
                )
            continue

        is_next_blocked_slot = blocked and slot_number == terminal_count + 1
        if is_next_blocked_slot:
            checks.require(
                not paths["release"].exists(),
                f"unlaunched slot {slot_number} has a handshake release",
            )
            checks.require(
                not paths["ready"].exists() or paths["attempt"].exists(),
                f"unlaunched slot {slot_number} ready has no attempt",
            )
            attempt = None
            if paths["attempt"].exists():
                attempt = _verify_handshake_attempt(
                    _load_canonical_handshake_record(
                        paths["attempt"],
                        f"slot {slot_number} handshake attempt",
                    ),
                    registration=registration,
                    run_lock=run_lock,
                    slot=slot,
                    paths=paths,
                    rules=rules,
                    expected_marker_start=None,
                    checks=checks,
                )
            if paths["ready"].exists():
                _verify_handshake_ready(
                    _load_canonical_handshake_record(
                        paths["ready"],
                        f"slot {slot_number} handshake ready",
                    ),
                    attempt=attempt,
                    checks=checks,
                )
            continue

        checks.require(
            not any(path.exists() for path in paths.values()),
            f"later unlaunched slot {slot_number} has handshake artifacts",
        )


def _handshake_paths(
    slot: Mapping[str, Any],
    rules: Mapping[str, Any],
) -> dict[str, Path]:
    config_path = Path(str(slot["config_path"])).resolve()
    session_id = str(slot["session_id"])
    return {
        "attempt": (
            config_path.parent / f"{session_id}{rules['attempt_suffix']}"
        ).resolve(),
        "ready": (
            config_path.parent / f"{session_id}{rules['ready_suffix']}"
        ).resolve(),
        "release": (
            config_path.parent / f"{session_id}{rules['release_suffix']}"
        ).resolve(),
    }


def _verify_handshake_attempt(
    record: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    slot: Mapping[str, Any],
    paths: Mapping[str, Path],
    rules: Mapping[str, Any],
    expected_marker_start: int | None,
    checks: _Checks,
) -> dict[str, Any]:
    slot_number = _exact_int(slot.get("slot_number"), "slot_number")
    created_unix_ns = _exact_int(
        record.get("created_unix_ns"),
        "handshake attempt created_unix_ns",
    )
    marker_start = _exact_int(
        record.get("marker_start_count"),
        "handshake attempt marker_start_count",
    )
    checks.require(
        created_unix_ns >= 0 and marker_start >= 0,
        f"slot {slot_number} handshake attempt counters are invalid",
    )
    if expected_marker_start is not None:
        checks.require(
            marker_start == expected_marker_start,
            f"slot {slot_number} handshake marker boundary mismatch",
        )
    config_path = Path(str(slot["config_path"])).resolve()
    try:
        config_sha256 = _file_sha256(config_path)
    except OSError as exc:
        raise OutcomeEvidenceVerificationError(
            f"slot {slot_number} handshake config is unreadable: {exc}"
        ) from exc
    token = _derive_handshake_slot_token(
        registration_hash=str(registration["registration_hash"]),
        run_lock_hash=str(run_lock["run_lock_hash"]),
        slot_number=slot_number,
        session_id=str(slot["session_id"]),
        config_sha256=config_sha256,
    )
    expected = {
        "attempt_hash": None,
        "attempt_path": str(paths["attempt"]),
        "config_path": str(config_path),
        "config_sha256": config_sha256,
        "created_unix_ns": created_unix_ns,
        "marker_start_count": marker_start,
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "readiness_timeout_seconds": rules["readiness_timeout_seconds"],
        "ready_path": str(paths["ready"]),
        "registration_hash": registration["registration_hash"],
        "release_path": str(paths["release"]),
        "release_timeout_seconds": rules["release_timeout_seconds"],
        "run_lock_hash": run_lock["run_lock_hash"],
        "schema_version": HANDSHAKE_ATTEMPT_SCHEMA_VERSION,
        "session_id": slot["session_id"],
        "slot_number": slot_number,
        "slot_token": token,
        "study_id": registration["study_id"],
    }
    expected["attempt_hash"] = _self_hash(expected, "attempt_hash")
    checks.require(
        record == expected,
        f"slot {slot_number} handshake attempt mismatch",
    )
    return expected


def _verify_handshake_ready(
    record: Mapping[str, Any],
    *,
    attempt: Mapping[str, Any] | None,
    checks: _Checks,
) -> dict[str, Any]:
    if attempt is None:
        raise OutcomeEvidenceVerificationError(
            "handshake ready cannot be verified without an attempt"
        )
    slot_number = int(attempt["slot_number"])
    child_pid = _exact_int(record.get("child_pid"), "handshake ready child_pid")
    created_unix_ns = _exact_int(
        record.get("created_unix_ns"),
        "handshake ready created_unix_ns",
    )
    checks.require(
        child_pid > 0 and created_unix_ns >= 0,
        f"slot {slot_number} handshake ready counters are invalid",
    )
    expected = {
        "attempt_hash": attempt["attempt_hash"],
        "child_pid": child_pid,
        "communication_state_received": True,
        "config_path": attempt["config_path"],
        "config_sha256": attempt["config_sha256"],
        "created_unix_ns": created_unix_ns,
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "ready_hash": None,
        "ready_path": attempt["ready_path"],
        "registration_hash": attempt["registration_hash"],
        "run_lock_hash": attempt["run_lock_hash"],
        "schema_version": HANDSHAKE_READY_SCHEMA_VERSION,
        "session_id": attempt["session_id"],
        "slot_number": slot_number,
        "slot_token": attempt["slot_token"],
        "study_id": attempt["study_id"],
    }
    expected["ready_hash"] = _self_hash(expected, "ready_hash")
    checks.require(
        record == expected,
        f"slot {slot_number} handshake ready mismatch",
    )
    return expected


def _verify_handshake_release(
    record: Mapping[str, Any],
    *,
    attempt: Mapping[str, Any],
    ready: Mapping[str, Any],
    checks: _Checks,
) -> None:
    slot_number = int(attempt["slot_number"])
    created_unix_ns = _exact_int(
        record.get("created_unix_ns"),
        "handshake release created_unix_ns",
    )
    checks.require(
        created_unix_ns >= 0,
        f"slot {slot_number} handshake release time is invalid",
    )
    expected = {
        "attempt_hash": attempt["attempt_hash"],
        "child_pid": ready["child_pid"],
        "created_unix_ns": created_unix_ns,
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "ready_hash": ready["ready_hash"],
        "registration_hash": attempt["registration_hash"],
        "release_hash": None,
        "release_path": attempt["release_path"],
        "run_lock_hash": attempt["run_lock_hash"],
        "schema_version": HANDSHAKE_RELEASE_SCHEMA_VERSION,
        "session_id": attempt["session_id"],
        "slot_number": slot_number,
        "slot_token": attempt["slot_token"],
        "study_id": attempt["study_id"],
    }
    expected["release_hash"] = _self_hash(expected, "release_hash")
    checks.require(
        record == expected,
        f"slot {slot_number} handshake release mismatch",
    )


def _derive_handshake_slot_token(
    *,
    registration_hash: str,
    run_lock_hash: str,
    slot_number: int,
    session_id: str,
    config_sha256: str,
) -> str:
    payload = {
        "config_sha256": config_sha256,
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "registration_hash": registration_hash,
        "run_lock_hash": run_lock_hash,
        "session_id": session_id,
        "slot_number": slot_number,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _load_canonical_handshake_record(
    path: Path,
    label: str,
) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidenceVerificationError(
            f"{label} is missing or unreadable: {exc}"
        ) from exc
    value = _load_mapping_bytes(data, path)
    if data != (_canonical_json(value) + "\n").encode("utf-8"):
        raise OutcomeEvidenceVerificationError(f"{label} is not canonical JSON")
    return value


def _registered_implementation_paths(
    registration: Mapping[str, Any],
) -> tuple[str, ...]:
    integrity = _mapping(registration.get("integrity_rules"), "integrity_rules")
    raw_paths = _sequence(
        integrity.get("implementation_paths"),
        "implementation_paths",
    )
    if any(not isinstance(path, str) or not path for path in raw_paths):
        raise OutcomeEvidenceVerificationError(
            "registration implementation paths are invalid"
        )
    return tuple(raw_paths)


def _verify_run_lock(
    record: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    registration_path: Path,
    registration_bytes: bytes,
    checks: _Checks,
) -> dict[str, Any]:
    checks.require(
        record.get("schema_version") == RUN_LOCK_SCHEMA_VERSION,
        "run lock schema mismatch",
    )
    checks.require(_is_sha256(record.get("run_lock_hash")), "run lock hash invalid")
    checks.require(
        record.get("run_lock_hash") == _self_hash(record, "run_lock_hash"),
        "run lock hash mismatch",
    )
    checks.require(
        record.get("study_id") == registration["study_id"],
        "run lock study mismatch",
    )
    checks.require(
        record.get("repo_root") == registration["repo_root"],
        "run lock repo mismatch",
    )
    checks.require(
        record.get("python_executable")
        == registration["command"]["python_executable"],
        "run lock Python mismatch",
    )
    expected_command = [
        registration["command"]["python_executable"],
        registration["command"]["main_path"],
        *registration["command"]["arguments"],
    ]
    checks.require(record.get("command") == expected_command, "run lock command drift")
    source = _mapping(record.get("source"), "run lock source")
    checks.require(
        _COMMIT_PATTERN.fullmatch(str(source.get("commit"))) is not None,
        "run lock source commit invalid",
    )
    checks.require(
        source.get("tracked_clean") is True
        and source.get("tracked_status") == "",
        "run lock source was not tracked-clean",
    )
    registration_binding = _mapping(
        record.get("registration"),
        "run lock registration",
    )
    checks.require(
        registration_binding
        == {
            "canonical_hash": registration["registration_hash"],
            "file_sha256": hashlib.sha256(registration_bytes).hexdigest(),
            "path": str(registration_path),
        },
        "run lock registration binding mismatch",
    )
    _verify_implementation_files(
        record,
        registration,
        source_commit=str(source["commit"]),
        checks=checks,
    )
    _verify_git_anchor(
        source,
        registration=registration,
        registration_path=registration_path,
        registration_bytes=registration_bytes,
        checks=checks,
    )
    locked_checkpoints = _verify_locked_checkpoint_inventory(
        record,
        registration,
        checks,
    )
    locked_communication = _verify_locked_communication(
        record,
        registration,
        checks,
    )
    return {
        "checkpoints": locked_checkpoints,
        "communication_mod": locked_communication,
    }


def _verify_implementation_files(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    *,
    source_commit: str,
    checks: _Checks,
) -> None:
    rows = _sequence(run_lock.get("implementation_files"), "implementation_files")
    implementation_paths = _registered_implementation_paths(registration)
    checks.require(
        len(rows) == len(implementation_paths),
        "source file count mismatch",
    )
    repo_root = Path(str(registration["repo_root"])).resolve()
    for relative_path, raw_row in zip(implementation_paths, rows, strict=True):
        row = _mapping(raw_row, "implementation file")
        path = (repo_root / relative_path).resolve()
        content = _git_blob(repo_root, source_commit, relative_path)
        checks.require(
            row
            == {
                "path": str(path),
                "relative_path": relative_path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            },
            f"implementation source drift: {relative_path}",
        )


def _verify_git_anchor(
    source: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    registration_path: Path,
    registration_bytes: bytes,
    checks: _Checks,
) -> None:
    repo_root = Path(str(registration["repo_root"])).resolve()
    observed_root = Path(
        _git_text(repo_root, "rev-parse", "--show-toplevel")
    ).resolve()
    checks.require(observed_root == repo_root, "Git repository root mismatch")
    commit = str(source["commit"])
    checks.require(
        _git_text(repo_root, "rev-parse", f"{commit}^{{commit}}") == commit,
        "run lock source commit is unavailable",
    )
    try:
        registration_relative = registration_path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceVerificationError(
            "registration file is outside the locked repository"
        ) from exc
    checks.require(
        _git_blob(repo_root, commit, registration_relative) == registration_bytes,
        "committed registration bytes differ from the verified file",
    )


def _verify_locked_checkpoint_inventory(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    checkpoints = _mapping(run_lock.get("checkpoints"), "checkpoints")
    inventory = registration["integrity_rules"]["checkpoint_inventory"]
    root = Path(str(inventory["root"])).resolve()
    patterns = list(inventory["patterns"])
    checks.require(
        set(checkpoints) == {"files", "patterns", "root"}
        and checkpoints.get("patterns") == patterns
        and checkpoints.get("root") == str(root),
        "run lock checkpoint contract mismatch",
    )
    rows = _sequence(checkpoints.get("files"), "checkpoint files")
    normalized_rows = []
    observed_paths = []
    for raw_row in rows:
        row = _mapping(raw_row, "checkpoint file")
        path = _absolute_path(row.get("path"), "checkpoint path")
        size = _exact_int(row.get("size"), "checkpoint size")
        checks.require(
            set(row) == {"path", "sha256", "size"}
            and path.parent == root
            and any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns)
            and _is_sha256(row.get("sha256"))
            and size >= 0,
            "run lock checkpoint row mismatch",
        )
        observed_paths.append(str(path))
        normalized_rows.append(dict(row))
    checks.require(
        len(observed_paths) == len(set(observed_paths))
        and observed_paths == sorted(observed_paths, key=str.casefold),
        "run lock checkpoint order mismatch",
    )
    return {
        "files": normalized_rows,
        "patterns": patterns,
        "root": str(root),
    }


def _verify_locked_communication(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    communication = _mapping(run_lock.get("communication_mod"), "communication_mod")
    expected_path = registration["integrity_rules"]["communication_config_path"]
    checks.require(
        set(communication) == {"path", "semantic_sha256"}
        and communication.get("path") == expected_path
        and _is_sha256(communication.get("semantic_sha256")),
        "run lock CommunicationMod contract mismatch",
    )
    return dict(communication)


def _verify_live_run_lock_state(
    run_lock: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    registration_path: Path,
    registration_bytes: bytes,
    checks: _Checks,
) -> dict[str, Any]:
    source = _mapping(run_lock.get("source"), "run lock source")
    _verify_live_implementation_files(run_lock, registration, checks)
    _verify_live_git_anchor(
        source,
        registration=registration,
        registration_path=registration_path,
        registration_bytes=registration_bytes,
        checks=checks,
    )
    observed_checkpoints = _verify_checkpoint_files(
        run_lock,
        registration,
        checks,
    )
    expected_communication_path = registration["integrity_rules"][
        "communication_config_path"
    ]
    observed_communication = {
        "path": expected_communication_path,
        "semantic_sha256": _properties_semantic_sha256(
            Path(expected_communication_path)
        ),
    }
    checks.require(
        run_lock.get("communication_mod") == observed_communication,
        "CommunicationMod semantic configuration drift",
    )
    return {
        "checkpoints": observed_checkpoints,
        "communication_mod": observed_communication,
    }


def _verify_live_implementation_files(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> None:
    rows = _sequence(run_lock.get("implementation_files"), "implementation_files")
    implementation_paths = _registered_implementation_paths(registration)
    repo_root = Path(str(registration["repo_root"])).resolve()
    for relative_path, raw_row in zip(implementation_paths, rows, strict=True):
        row = _mapping(raw_row, "implementation file")
        path = (repo_root / relative_path).resolve()
        content = path.read_bytes()
        checks.require(
            row
            == {
                "path": str(path),
                "relative_path": relative_path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            },
            f"implementation source drift: {relative_path}",
        )


def _verify_live_git_anchor(
    source: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    registration_path: Path,
    registration_bytes: bytes,
    checks: _Checks,
) -> None:
    repo_root = Path(str(registration["repo_root"])).resolve()
    commit = str(source["commit"])
    checks.require(
        _git_text(repo_root, "rev-parse", "HEAD") == commit,
        "Git HEAD differs from the run lock",
    )
    checks.require(
        _git_text(
            repo_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
        )
        == "",
        "Git tracked worktree differs from the run lock",
    )
    try:
        registration_relative = registration_path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceVerificationError(
            "registration file is outside the locked repository"
        ) from exc
    implementation_paths = _registered_implementation_paths(registration)
    relative_paths = [registration_relative, *implementation_paths]
    _git_text(
        repo_root,
        "ls-files",
        "--error-unmatch",
        "--",
        *relative_paths,
    )
    checks.require(
        _git_blob(repo_root, commit, registration_relative) == registration_bytes,
        "committed registration bytes differ from the verified file",
    )
    for relative_path in implementation_paths:
        checks.require(
            _git_blob(repo_root, commit, relative_path)
            == (repo_root / relative_path).read_bytes(),
            f"committed implementation bytes differ: {relative_path}",
        )


def _git_text(repo_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise OutcomeEvidenceVerificationError(
            f"Git {' '.join(arguments)} failed: {detail}"
        )
    return completed.stdout.strip()


def _git_blob(repo_root: Path, commit: str, relative_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{commit}:{relative_path}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise OutcomeEvidenceVerificationError(
            f"cannot read committed Git blob {relative_path}: {detail}"
        )
    return completed.stdout


def _verify_checkpoint_files(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    checkpoints = _mapping(run_lock.get("checkpoints"), "checkpoints")
    inventory = registration["integrity_rules"]["checkpoint_inventory"]
    root = Path(str(inventory["root"])).resolve()
    patterns = list(inventory["patterns"])
    paths = {
        path.resolve()
        for pattern in patterns
        for path in root.glob(pattern)
        if path.is_file()
    }
    observed = {
        "files": [
            {
                "path": str(path),
                "sha256": _file_sha256(path),
                "size": len(path.read_bytes()),
            }
            for path in sorted(paths, key=lambda path: str(path).casefold())
        ],
        "patterns": patterns,
        "root": str(root),
    }
    checks.require(
        checkpoints == observed,
        "checkpoint inventory drift",
    )
    return observed


def _verify_ledger(
    path: Path,
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    records = _load_jsonl(path)
    checks.require(bool(records), "study ledger is empty")
    previous_hash = None
    active = None
    terminals = []
    next_slot = 1
    initialized = False
    global_stop = None
    marker_end_cursor = None
    for sequence, raw_record in enumerate(records, start=1):
        record = _mapping(raw_record, f"ledger record {sequence}")
        checks.require(
            record.get("schema_version") == LEDGER_SCHEMA_VERSION,
            "ledger schema mismatch",
        )
        checks.require(record.get("sequence") == sequence, "ledger sequence mismatch")
        checks.require(
            record.get("previous_record_hash") == previous_hash,
            "ledger hash chain mismatch",
        )
        checks.require(
            record.get("record_hash") == _self_hash(record, "record_hash"),
            "ledger record hash mismatch",
        )
        checks.require(
            record.get("registration_hash") == registration["registration_hash"]
            and record.get("run_lock_hash") == run_lock["run_lock_hash"]
            and record.get("study_id") == registration["study_id"],
            "ledger study binding mismatch",
        )
        event = record.get("event")
        payload = _mapping(record.get("payload"), "ledger payload")
        checks.require(
            global_stop is None,
            "ledger event follows the global stop",
        )
        if event == "study_started":
            checks.require(
                not initialized
                and sequence == 1
                and payload == {"slot_count": SLOT_COUNT},
                "ledger initialization mismatch",
            )
            initialized = True
        elif event == "slot_started":
            checks.require(
                initialized and active is None and global_stop is None,
                "invalid ledger slot start state",
            )
            marker_start_count = None
            if registration["schema_version"] == REGISTRATION_SCHEMA_VERSION:
                marker_start_count = _exact_int(
                    payload.get("marker_start_count"),
                    "slot_started marker_start_count",
                )
                expected_start_payload = {
                    "marker_start_count": marker_start_count
                }
            else:
                expected_start_payload = {}
            checks.require(
                record.get("slot_number") == next_slot
                and record.get("session_id")
                == registration["slots"][next_slot - 1]["session_id"]
                and payload == expected_start_payload
                and (marker_start_count is None or marker_start_count >= 0),
                "ledger slot start order mismatch",
            )
            active = {
                "marker_start_count": marker_start_count,
                "session_id": record["session_id"],
                "slot_number": next_slot,
            }
        elif event == "slot_terminal":
            checks.require(active is not None, "terminal ledger row has no active slot")
            checks.require(
                record.get("slot_number") == active["slot_number"]
                and record.get("session_id") == active["session_id"],
                "terminal ledger slot mismatch",
            )
            complete = _exact_int(
                payload.get("complete_trajectories"),
                "complete_trajectories",
            )
            marker_start = _exact_int(
                payload.get("marker_start_count"),
                "marker_start_count",
            )
            marker_end = _exact_int(
                payload.get("marker_end_count"),
                "marker_end_count",
            )
            status = payload.get("terminal_status")
            exit_code = payload.get("process_exit_code")
            expected_status = (
                "completed"
                if exit_code == 0 and complete == GAMES_PER_SLOT
                else "interrupted"
            )
            checks.require(status == expected_status, "ledger terminal status mismatch")
            checks.require(
                0 <= complete <= GAMES_PER_SLOT
                and marker_start >= 0
                and marker_end >= marker_start
                and marker_end - marker_start == complete
                and (
                    active["marker_start_count"] is None
                    or marker_start == active["marker_start_count"]
                ),
                "ledger marker accounting mismatch",
            )
            checks.require(
                marker_end_cursor is None or marker_start == marker_end_cursor,
                "ledger marker intervals are not contiguous",
            )
            terminals.append(
                {
                    "complete_trajectories": complete,
                    "marker_end_count": marker_end,
                    "marker_start_count": marker_start,
                    "process_exit_code": exit_code,
                    "session_id": active["session_id"],
                    "slot_number": active["slot_number"],
                    "terminal_status": status,
                }
            )
            active = None
            marker_end_cursor = marker_end
            next_slot += 1
        elif event == "global_stop":
            reason = _required_string(payload.get("reason"), "global stop reason")
            checks.require(
                initialized
                and active is None
                and record.get("slot_number") is None
                and record.get("session_id") is None
                and payload == {"reason": reason},
                "ledger global stop structure mismatch",
            )
            global_stop = {"reason": reason}
        else:
            raise OutcomeEvidenceVerificationError(
                f"unsupported ledger event: {event}"
            )
        previous_hash = record["record_hash"]
    checks.require(initialized, "ledger was not initialized")
    checks.require(active is None, "ledger has an active final slot")
    return {
        "final_record_hash": previous_hash,
        "global_stop": global_stop,
        "terminal_slots": terminals,
    }


def _verify_claim(
    path: Path,
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    checks: _Checks,
) -> Mapping[str, Any]:
    claim = _load_mapping(path)
    checks.require(
        set(claim)
        == {
            "claim_hash",
            "mode",
            "registration_hash",
            "run_lock_hash",
            "schema_version",
            "study_id",
        },
        "finalization claim fields mismatch",
    )
    checks.require(
        claim.get("schema_version") == CLAIM_SCHEMA_VERSION,
        "finalization claim schema mismatch",
    )
    checks.require(
        claim.get("claim_hash") == _self_hash(claim, "claim_hash"),
        "finalization claim hash mismatch",
    )
    checks.require(
        claim.get("mode") in {"complete", "integrity_stop"}
        and claim.get("study_id") == registration["study_id"]
        and claim.get("registration_hash") == registration["registration_hash"]
        and claim.get("run_lock_hash") == run_lock["run_lock_hash"],
        "finalization claim binding mismatch",
    )
    return claim


def _verify_blocked_closeout(
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    paths: Mapping[str, Path],
    checks: _Checks,
) -> dict[str, Any]:
    stop = _mapping(ledger.get("global_stop"), "ledger global stop")
    stop_reason = _required_string(stop.get("reason"), "global stop reason")
    terminal_slots = _sequence(
        ledger.get("terminal_slots"),
        "ledger terminal slots",
    )
    expected_slots = [
        {
            "session_id": str(row["session_id"]),
            "slot_number": int(row["slot_number"]),
            "terminal_status": str(row["terminal_status"]),
        }
        for row in terminal_slots
    ]
    for raw_slot in registration["slots"][len(expected_slots) :]:
        slot = _mapping(raw_slot, "registered slot")
        expected_slots.append(
            {
                "session_id": str(slot["session_id"]),
                "slot_number": int(slot["slot_number"]),
                "terminal_status": "unlaunched",
            }
        )
    checks.require(
        len(expected_slots) == SLOT_COUNT
        and [row["slot_number"] for row in expected_slots]
        == list(range(1, SLOT_COUNT + 1)),
        "blocked closeout slot accounting mismatch",
    )

    metrics = {
        "all_registered_slots_accounted": False,
        "category_arm_support": {
            "card_reward": {"alternative": 0, "baseline": 0},
            "shop": {"alternative": 0, "baseline": 0},
        },
        "complete_trajectory_count": 0,
        "ess_fraction": Fraction(0, 1),
        "global_integrity_stop": True,
        "max_normalized_weight": Fraction(0, 1),
        "nonzero_weight_trajectory_count": 0,
        "supported_victory_count": 0,
    }
    gate = _build_evidence_gate(registration, metrics)
    expected = {
        "blockers": list(gate["blockers"]),
        "closeout_hash": None,
        "evidence_gate": gate,
        "gates": {
            "causal_uplift_ready": False,
            "dataset_ope_readiness_ready": False,
            "formal_noncombat_rl_training_ready": False,
            "live_policy_promotion_ready": False,
            "ope_estimate_ready": False,
            "outcome_evidence_expansion_ready": False,
            "policy_comparison_ready": False,
            "reward_design_ready": False,
        },
        "integrity_stop": {"reason": stop_reason},
        "limitations": [
            "Evidence readiness is separate from policy comparison.",
            (
                "No closeout gate authorizes causal claims, training, reward "
                "design, or live promotion."
            ),
        ],
        "registration_hash": registration["registration_hash"],
        "run_lock_hash": run_lock["run_lock_hash"],
        "schema_version": CLOSEOUT_SCHEMA_VERSION,
        "slots": expected_slots,
        "source": {
            "calibration_file_sha256": None,
            "estimate_file_sha256": None,
            "pool_manifest_hash": None,
            "readiness_file_sha256": None,
            "target_manifest_hash": None,
        },
        "status": "blocked",
        "study_id": registration["study_id"],
    }
    expected["closeout_hash"] = _self_hash(expected, "closeout_hash")
    observed = _load_mapping(paths["closeout"])
    checks.require(
        observed == expected,
        "blocked closeout differs from independent reconstruction",
    )
    checks.require(
        paths["closeout"].read_bytes()
        == (_canonical_json(expected) + "\n").encode("utf-8"),
        "blocked closeout JSON rendering mismatch",
    )
    checks.require(
        paths["closeout_markdown"].read_bytes()
        == _render_blocked_closeout_markdown(expected).encode("utf-8"),
        "blocked closeout Markdown rendering mismatch",
    )
    forbidden = (
        "pool_manifest",
        "pool_samples",
        "target",
        "readiness",
        "readiness_markdown",
        "estimate",
        "estimate_markdown",
    )
    existing = sorted(paths[name].name for name in forbidden if paths[name].exists())
    checks.require(
        not existing,
        "blocked closeout has forbidden normal artifacts: " + ", ".join(existing),
    )
    return expected


def _render_blocked_closeout_markdown(closeout: Mapping[str, Any]) -> str:
    lines = [
        "# Non-combat outcome-evidence closeout",
        "",
        f"- Study: `{closeout.get('study_id')}`",
        f"- Status: `{closeout.get('status')}`",
        "",
        "## Integrity stop",
        "",
        (
            "- Reason: "
            + _canonical_json(
                _mapping(closeout.get("integrity_stop"), "integrity stop").get(
                    "reason"
                )
            )
        ),
        "",
        "## Evidence gate",
        "",
        "| Condition | Observed | Required | Passed |",
        "|---|---|---|---|",
    ]
    conditions = closeout["evidence_gate"]["conditions"]
    for code in sorted(conditions):
        condition = conditions[code]
        lines.append(
            f"| `{code}` | `{_canonical_json(condition['observed'])}` | "
            f"`{_canonical_json(condition['required'])}` | "
            f"{'yes' if condition['passed'] else 'no'} |"
        )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- `{blocker}`" for blocker in closeout["blockers"])
    if not closeout["blockers"]:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Slot status",
            "",
            "| Slot | Session | Status |",
            "|---:|---|---|",
        ]
    )
    for slot in closeout["slots"]:
        lines.append(
            f"| {slot['slot_number']:02d} | `{slot['session_id']}` | "
            f"{slot['terminal_status']} |"
        )
    lines.extend(["", "## Authority gates", ""])
    for gate_name, ready in sorted(closeout["gates"].items()):
        lines.append(f"- `{gate_name}`: `{'true' if ready else 'false'}`")
    return "\n".join(lines) + "\n"


def _verify_pool(
    samples: Sequence[Mapping[str, Any]],
    pool: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    checks.require(pool.get("schema_version") == POOL_SCHEMA_VERSION, "pool schema")
    checks.require(
        pool.get("pool_manifest_hash")
        == _self_hash(pool, "pool_manifest_hash"),
        "pool manifest hash mismatch",
    )
    rendered_samples = "".join(_canonical_json(row) + "\n" for row in samples)
    checks.require(
        pool.get("sample_jsonl_sha256")
        == hashlib.sha256(rendered_samples.encode("utf-8")).hexdigest(),
        "pool sample hash mismatch",
    )
    checks.require(
        pool.get("study_id") == registration["study_id"]
        and pool.get("registration_hash") == registration["registration_hash"]
        and pool.get("run_lock_hash") == run_lock["run_lock_hash"],
        "pool study binding mismatch",
    )
    ordered = sorted(samples, key=_sample_sort_key)
    checks.require(list(samples) == ordered, "pool sample order is not canonical")
    sample_ids = set()
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_session: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    support = Counter()
    registered_session_ids = {
        slot["session_id"] for slot in registration["slots"]
    }
    for raw_sample in samples:
        sample = _mapping(raw_sample, "pool sample")
        sample_id = _required_string(sample.get("sample_id"), "sample_id")
        checks.require(sample_id not in sample_ids, f"duplicate sample_id: {sample_id}")
        sample_ids.add(sample_id)
        exploration = _mapping(sample.get("exploration"), "sample exploration")
        session_id = _required_string(exploration.get("session_id"), "session_id")
        checks.require(
            session_id in registered_session_ids,
            f"sample belongs to an unregistered session: {sample_id}",
        )
        checks.require(
            sample.get("behavior_policy_commit") == run_lock["source"]["commit"]
            and exploration.get("source_commit")
            == run_lock["source"]["commit"],
            f"sample source lock mismatch: {sample_id}",
        )
        category = sample.get("category")
        arm = exploration.get("selected_arm")
        checks.require(
            category in {"card_reward", "shop"}
            and arm in {"baseline", "alternative"},
            f"unsupported sample arm: {sample_id}",
        )
        _verify_sample_probability(sample, checks)
        group_id = _required_string(
            sample.get("trajectory_group_id"),
            "trajectory_group_id",
        )
        groups[group_id].append(sample)
        by_session[session_id].append(sample)
        support[(category, arm)] += 1
    included = _included_trajectory_rows(groups)
    checks.require(
        pool.get("included_trajectories") == included,
        "pool membership does not match canonical samples",
    )
    aggregate_support = {
        category: {
            arm: support[(category, arm)]
            for arm in ("alternative", "baseline")
        }
        for category in ("card_reward", "shop")
    }
    checks.require(
        pool.get("aggregate_arm_support") == aggregate_support,
        "pool arm support mismatch",
    )
    conservative_joins = _reconstruct_conservative_run_joins(
        registration,
        ledger,
        checks=checks,
    )
    exclusion_accounting = _verify_pool_exclusions(
        pool,
        included,
        registration=registration,
        checks=checks,
    )
    slot_rows = _sequence(pool.get("slots"), "pool slots")
    checks.require(len(slot_rows) == SLOT_COUNT, "pool slot count mismatch")
    terminal_by_slot = {
        row["slot_number"]: row for row in ledger["terminal_slots"]
    }
    included_groups_by_session = Counter(
        row["session_id"] for row in included
    )
    included_run_files_by_session: dict[str, list[str]] = defaultdict(list)
    for row in included:
        included_run_files_by_session[str(row["session_id"])].append(
            str(row["run_file"])
        )
    runs_root = conservative_joins["runs_root"]
    for slot, raw_pool_slot in zip(
        registration["slots"],
        slot_rows,
        strict=True,
    ):
        pool_slot = _mapping(raw_pool_slot, "pool slot")
        number = slot["slot_number"]
        terminal = terminal_by_slot[number]
        session_samples = by_session.get(slot["session_id"], [])
        checks.require(
            pool_slot.get("slot_number") == number
            and pool_slot.get("session_id") == slot["session_id"],
            f"pool slot identity mismatch: {number}",
        )
        checks.require(
            pool_slot.get("terminal_status") == terminal["terminal_status"]
            and pool_slot.get("process_exit_code")
            == terminal["process_exit_code"]
            and pool_slot.get("marker_trajectory_count")
            == terminal["complete_trajectories"],
            f"pool slot lifecycle mismatch: {number}",
        )
        checks.require(
            pool_slot.get("included_decision_count") == len(session_samples)
            and pool_slot.get("included_trajectory_count")
            == included_groups_by_session[slot["session_id"]],
            f"pool slot inclusion accounting mismatch: {number}",
        )
        included_count = included_groups_by_session[slot["session_id"]]
        exclusion = exclusion_accounting[number]
        declared_joined_run_files = sorted(
            [
                *included_run_files_by_session[slot["session_id"]],
                *exclusion["joined_excluded_run_files"],
            ],
            key=lambda value: int(Path(value).stem),
        )
        expected_joined_run_files = sorted(
            conservative_joins["by_slot"][number],
            key=lambda value: int(Path(value).stem),
        )
        checks.require(
            declared_joined_run_files == expected_joined_run_files,
            f"conservative run join mismatch: slot {number}",
        )
        checks.require(
            pool_slot.get("excluded_trajectory_count")
            == terminal["complete_trajectories"] - included_count
            and pool_slot.get("joined_run_count")
            == included_count + exclusion["joined_excluded_count"]
            and pool_slot.get("unresolved_join_count")
            == exclusion["unresolved_join_count"]
            and exclusion["excluded_trajectory_count"]
            == terminal["complete_trajectories"] - included_count,
            f"pool slot exclusion accounting mismatch: {number}",
        )
        _verify_session_artifacts(
            slot,
            pool_slot,
            session_samples,
            joined_run_files=declared_joined_run_files,
            runs_root=runs_root,
            registration=registration,
            run_lock=run_lock,
            checks=checks,
        )
    accounting = _mapping(pool.get("accounting"), "pool accounting")
    marker_count = sum(row["complete_trajectories"] for row in ledger["terminal_slots"])
    excluded_count = marker_count - len(groups)
    checks.require(
        accounting
        == {
            "conservative_joined_run_count": sum(
                included_groups_by_session[slot["session_id"]]
                + exclusion_accounting[slot["slot_number"]][
                    "joined_excluded_count"
                ]
                for slot in registration["slots"]
            ),
            "excluded_trajectory_count": excluded_count,
            "included_decision_count": len(samples),
            "included_trajectory_count": len(groups),
            "marker_trajectory_count": marker_count,
            "registered_slot_count": SLOT_COUNT,
        },
        "pool aggregate accounting mismatch",
    )
    checks.require(
        sum(
            row["excluded_trajectory_count"]
            for row in exclusion_accounting.values()
        )
        == excluded_count,
        "pool exclusion accounting mismatch",
    )
    terminal_outcome_hashes = _verify_terminal_outcomes(
        groups,
        registration,
        checks,
    )
    return {
        "ai_marker_file_sha256": conservative_joins[
            "ai_marker_file_sha256"
        ],
        "category_arm_support": aggregate_support,
        "conservative_join_run_file_sha256": conservative_joins[
            "run_file_sha256"
        ],
        "conservative_run_inventory_sha256": conservative_joins[
            "run_inventory_sha256"
        ],
        "groups": groups,
        "terminal_outcome_file_sha256": terminal_outcome_hashes,
    }


def _reconstruct_conservative_run_joins(
    registration: Mapping[str, Any],
    ledger: Mapping[str, Any],
    *,
    checks: _Checks,
) -> dict[str, Any]:
    checkpoint_root = Path(
        str(registration["integrity_rules"]["checkpoint_inventory"]["root"])
    ).resolve()
    runs_parent = checkpoint_root.parent / "runs"
    runs_root = runs_parent / "IRONCLAD"
    marker_path = runs_parent / "ai_games.txt"
    marker_bytes = marker_path.read_bytes()
    try:
        marker_lines = marker_bytes.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot decode AI marker file: {exc}"
        ) from exc
    markers = []
    for line in marker_lines:
        value = line.strip()
        if not value:
            continue
        checks.require(
            value.isdigit(),
            "AI marker file contains an invalid marker",
        )
        markers.append(int(value))

    numeric_run_paths = sorted(
        (path for path in runs_root.glob("*.run") if path.stem.isdigit()),
        key=lambda path: (int(path.stem), path.name),
    )
    run_inventory = [path.name for path in numeric_run_paths]
    run_timestamps = [int(path.stem) for path in numeric_run_paths]
    marker_candidates = [
        tuple(
            run_index
            for run_index, run_timestamp in enumerate(run_timestamps)
            if 0 <= marker_timestamp - run_timestamp <= 10
        )
        for marker_timestamp in markers
    ]
    run_candidate_counts = Counter(
        run_index
        for candidates in marker_candidates
        for run_index in candidates
    )
    joined_by_marker = {
        marker_index: run_timestamps[candidates[0]]
        for marker_index, candidates in enumerate(marker_candidates)
        if len(candidates) == 1
        and run_candidate_counts[candidates[0]] == 1
    }

    by_slot = {}
    joined_run_files = set()
    for terminal in ledger["terminal_slots"]:
        marker_start = int(terminal["marker_start_count"])
        marker_end = int(terminal["marker_end_count"])
        checks.require(
            marker_end <= len(markers),
            (
                "slot marker slice exceeds AI marker file: "
                f"{terminal['slot_number']}"
            ),
        )
        slot_run_files = [
            f"{joined_by_marker[index]}.run"
            for index in range(marker_start, marker_end)
            if index in joined_by_marker
        ]
        by_slot[int(terminal["slot_number"])] = slot_run_files
        joined_run_files.update(slot_run_files)

    return {
        "ai_marker_file_sha256": hashlib.sha256(marker_bytes).hexdigest(),
        "by_slot": by_slot,
        "run_file_sha256": {
            run_file: _file_sha256(runs_root / run_file)
            for run_file in sorted(
                joined_run_files,
                key=lambda value: int(Path(value).stem),
            )
        },
        "run_inventory_sha256": hashlib.sha256(
            _canonical_json(run_inventory).encode("utf-8")
        ).hexdigest(),
        "runs_root": runs_root,
    }


def _verify_pool_exclusions(
    pool: Mapping[str, Any],
    included: Sequence[Mapping[str, Any]],
    *,
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[int, dict[str, Any]]:
    rows = _sequence(pool.get("excluded_trajectories"), "excluded trajectories")
    registered_sessions = {
        slot["slot_number"]: slot["session_id"] for slot in registration["slots"]
    }
    accounting = {
        number: {
            "excluded_trajectory_count": 0,
            "joined_excluded_count": 0,
            "joined_excluded_run_files": [],
            "unresolved_join_count": 0,
        }
        for number in registered_sessions
    }
    included_run_files = [str(row["run_file"]) for row in included]
    checks.require(
        len(included_run_files) == len(set(included_run_files)),
        "included pool run files are not unique",
    )
    seen_run_files = set(included_run_files)
    unresolved_slots = set()
    normalized = []
    for raw_row in rows:
        row = dict(_mapping(raw_row, "excluded trajectory"))
        slot_number = _exact_int(row.get("slot_number"), "exclusion slot_number")
        checks.require(
            slot_number in registered_sessions
            and row.get("session_id") == registered_sessions[slot_number],
            "excluded trajectory slot binding mismatch",
        )
        checks.require(
            row.get("trajectory_session_id") is None,
            "excluded trajectory session attribution mismatch",
        )
        reason = row.get("reason")
        if reason == "no_complete_confirmed_decision":
            checks.require(
                set(row)
                == {
                    "reason",
                    "run_file",
                    "session_id",
                    "slot_number",
                    "trajectory_session_id",
                },
                "joined exclusion fields mismatch",
            )
            run_file = _required_string(row.get("run_file"), "excluded run_file")
            checks.require(
                re.fullmatch(r"[0-9]+\.run", run_file) is not None
                and run_file not in seen_run_files,
                "excluded run file is invalid or duplicated",
            )
            seen_run_files.add(run_file)
            accounting[slot_number]["excluded_trajectory_count"] += 1
            accounting[slot_number]["joined_excluded_count"] += 1
            accounting[slot_number]["joined_excluded_run_files"].append(
                run_file
            )
        elif reason == "run_join_missing_or_ambiguous":
            checks.require(
                set(row)
                == {
                    "count",
                    "reason",
                    "run_file",
                    "session_id",
                    "slot_number",
                    "trajectory_session_id",
                }
                and row.get("run_file") is None
                and slot_number not in unresolved_slots,
                "unresolved exclusion fields mismatch",
            )
            count = _exact_int(row.get("count"), "unresolved exclusion count")
            checks.require(count > 0, "unresolved exclusion count is not positive")
            unresolved_slots.add(slot_number)
            accounting[slot_number]["excluded_trajectory_count"] += count
            accounting[slot_number]["unresolved_join_count"] += count
        else:
            raise OutcomeEvidenceVerificationError(
                f"unsupported trajectory exclusion reason: {reason}"
            )
        normalized.append(row)
    checks.require(
        normalized
        == sorted(
            normalized,
            key=lambda row: (
                int(row["slot_number"]),
                str(row.get("run_file") or ""),
                str(row.get("trajectory_session_id") or ""),
                str(row["reason"]),
            ),
        ),
        "excluded trajectories are not canonically ordered",
    )
    return accounting


def _verify_session_artifacts(
    slot: Mapping[str, Any],
    pool_slot: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    *,
    joined_run_files: Sequence[str],
    runs_root: Path,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    checks: _Checks,
) -> None:
    config_path = Path(str(slot["config_path"]))
    manifest_path = Path(str(slot["manifest_path"]))
    trace_path = Path(str(slot["trace_path"]))
    hashes = _mapping(pool_slot.get("artifact_hashes"), "artifact hashes")
    checks.require(
        hashes.get("config_sha256") == _file_sha256(config_path)
        and hashes.get("manifest_sha256") == _file_sha256(manifest_path)
        and hashes.get("trace_sha256") == _file_sha256(trace_path),
        f"session artifact hash mismatch: {slot['slot_number']}",
    )
    config = _load_mapping(config_path)
    expected_config = {
        "category_rates_bps": {"card_reward": 300, "shop": 1000},
        "enabled_categories": ["card_reward", "shop"],
        "manifest_path": str(manifest_path),
        "per_run_alternative_budget": 2,
        "schema_version": "noncombat-exploration-config-v1",
        "seed": slot["seed"],
        "session_id": slot["session_id"],
        "source_commit": run_lock["source"]["commit"],
        "study_id": registration["study_id"],
        "study_registration_hash": registration["registration_hash"],
        "study_run_lock_hash": run_lock["run_lock_hash"],
        "study_slot_number": slot["slot_number"],
        "trace_path": str(trace_path),
    }
    checks.require(config == expected_config, "session config contract mismatch")
    manifest = _load_mapping(manifest_path)
    manifest_hash_input = dict(manifest)
    supplied_manifest_hash = manifest_hash_input.pop("manifest_hash", None)
    checks.require(
        supplied_manifest_hash
        == hashlib.sha256(
            _canonical_json(manifest_hash_input).encode("utf-8")
        ).hexdigest()
        and hashes.get("manifest_hash") == supplied_manifest_hash,
        "session manifest hash mismatch",
    )
    effective = _mapping(manifest.get("effective_config"), "effective config")
    effective_without_source = dict(effective)
    source_path = effective_without_source.pop("source_path", None)
    checks.require(
        effective_without_source == config and source_path == str(config_path),
        "session manifest effective config mismatch",
    )
    checks.require(
        manifest.get("effective_config_hash")
        == hashlib.sha256(_canonical_json(effective).encode("utf-8")).hexdigest()
        and manifest.get("config_file_sha256") == _file_sha256(config_path),
        "session manifest config hash mismatch",
    )
    checks.require(
        manifest.get("session_id") == slot["session_id"]
        and manifest.get("trace_path") == str(trace_path)
        and manifest.get("manifest_path") == str(manifest_path)
        and manifest.get("python_executable")
        == registration["command"]["python_executable"]
        and manifest.get("command") == run_lock["command"]
        and manifest.get("source")
        == {"commit": run_lock["source"]["commit"], "tracked_clean": True},
        "session manifest provenance mismatch",
    )
    _verify_manifest_isolation(
        manifest,
        run_lock,
        slot_number=slot["slot_number"],
        checks=checks,
    )
    _verify_trace(
        trace_path,
        samples,
        pool_slot,
        joined_run_files=joined_run_files,
        runs_root=runs_root,
        manifest=manifest,
        checks=checks,
    )


def _verify_manifest_isolation(
    manifest: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    *,
    slot_number: int,
    checks: _Checks,
) -> None:
    pre_session = _mapping(
        manifest.get("pre_session_isolation_hashes"),
        "pre-session isolation hashes",
    )
    pre_by_path = {}
    for raw_path, raw_fingerprint in pre_session.items():
        checks.require(
            isinstance(raw_path, str) and isinstance(raw_fingerprint, Mapping),
            f"session isolation entry is invalid: {slot_number}",
        )
        normalized_path = str(Path(raw_path).resolve()).casefold()
        checks.require(
            normalized_path not in pre_by_path,
            f"session isolation path is duplicated: {slot_number}",
        )
        pre_by_path[normalized_path] = raw_fingerprint

    communication = _mapping(
        run_lock.get("communication_mod"),
        "run-lock CommunicationMod",
    )
    communication_path = str(Path(str(communication["path"])).resolve()).casefold()
    observed_communication = pre_by_path.get(communication_path)
    checks.require(
        isinstance(observed_communication, Mapping)
        and observed_communication.get("semantic_sha256")
        == communication.get("semantic_sha256"),
        f"session CommunicationMod isolation mismatch: {slot_number}",
    )

    checkpoints = _mapping(run_lock.get("checkpoints"), "run-lock checkpoints")
    checkpoint_root = Path(str(checkpoints["root"])).resolve()
    patterns = _sequence(checkpoints.get("patterns"), "checkpoint patterns")
    checks.require(
        all(isinstance(pattern, str) and pattern for pattern in patterns),
        "checkpoint patterns are invalid",
    )
    expected_files = {
        str(Path(str(row["path"])).resolve()).casefold(): row
        for row in _sequence(checkpoints.get("files"), "checkpoint files")
    }
    observed_checkpoint_paths = set()
    for raw_path in pre_session:
        path = Path(str(raw_path)).resolve()
        try:
            path.relative_to(checkpoint_root)
        except ValueError:
            continue
        if any(fnmatch.fnmatchcase(path.name, pattern) for pattern in patterns):
            observed_checkpoint_paths.add(str(path).casefold())
    checks.require(
        observed_checkpoint_paths == set(expected_files),
        f"session checkpoint isolation membership mismatch: {slot_number}",
    )
    for normalized_path, expected in expected_files.items():
        observed = pre_by_path.get(normalized_path)
        checks.require(
            isinstance(observed, Mapping)
            and observed.get("sha256") == expected.get("sha256")
            and observed.get("size") == expected.get("size"),
            f"session checkpoint isolation mismatch: {slot_number}",
        )


def _verify_trace(
    path: Path,
    samples: Sequence[Mapping[str, Any]],
    pool_slot: Mapping[str, Any],
    *,
    joined_run_files: Sequence[str],
    runs_root: Path,
    manifest: Mapping[str, Any],
    checks: _Checks,
) -> None:
    rows = _load_jsonl(path)
    proposed = {}
    resolutions = {}
    for row in rows:
        record = _mapping(row, "trace record")
        decision_id = _required_string(record.get("decision_id"), "decision_id")
        record_type = record.get("record_type")
        target = proposed if record_type == "proposed" else resolutions
        checks.require(
            record_type in {"proposed", "resolution"},
            "unsupported trace record type",
        )
        checks.require(decision_id not in target, "duplicate trace decision record")
        target[decision_id] = record
    checks.require(
        set(resolutions).issubset(proposed),
        "trace resolution references an unknown proposal",
    )
    history_errors = _proposal_history_errors(proposed, manifest)
    expected_exclusion_reasons = {
        decision_id: _expected_export_exclusion_reason(
            proposal,
            resolutions.get(decision_id),
            history_errors.get(decision_id),
            manifest,
        )
        for decision_id, proposal in proposed.items()
    }
    sample_ids = set()
    sample_group_ids = {}
    for sample in samples:
        sample_id = str(sample["sample_id"])
        sample_ids.add(sample_id)
        sample_group_ids[sample_id] = str(sample["trajectory_group_id"])
        checks.require(
            sample_id in proposed and sample_id in resolutions,
            f"pool sample is absent from trace: {sample_id}",
        )
        checks.require(
            expected_exclusion_reasons[sample_id] is None,
            f"included proposal should have been excluded: {sample_id}",
        )
        proposal = proposed[sample_id]
        resolution = resolutions[sample_id]
        exploration = sample["exploration"]
        proposal_body = _mapping(proposal.get("proposal"), "trace proposal")
        selection = _mapping(proposal.get("selection"), "trace selection")
        candidate_actions = _sequence(
            sample.get("candidate_actions"),
            "sample candidate actions",
        )
        selected_candidates = [
            candidate
            for candidate in candidate_actions
            if isinstance(candidate, Mapping)
            and candidate.get("action_id") == sample["selected_action_id"]
        ]
        checks.require(
            proposal.get("session_id") == exploration["session_id"]
            and proposal.get("trajectory_session_id")
            == sample["trajectory_session_id"]
            and proposal.get("category") == sample["category"]
            and proposal.get("decision_index") == exploration["decision_index"],
            f"trace proposal identity mismatch: {sample_id}",
        )
        checks.require(
            exploration.get("proposal_record_hash")
            == hashlib.sha256(
                _canonical_json(proposal).encode("utf-8")
            ).hexdigest()
            and exploration.get("resolution_record_hash")
            == hashlib.sha256(
                _canonical_json(resolution).encode("utf-8")
            ).hexdigest()
            and exploration.get("manifest_hash") == manifest.get("manifest_hash")
            and exploration.get("effective_config_hash")
            == manifest.get("effective_config_hash")
            and exploration.get("config_file_sha256")
            == manifest.get("config_file_sha256"),
            f"trace record or manifest binding mismatch: {sample_id}",
        )
        timestamps = (
            proposal.get("trajectory_started_unix"),
            proposal.get("proposed_unix"),
            resolution.get("resolved_unix"),
        )
        checks.require(
            all(
                not isinstance(value, bool)
                and isinstance(value, (int, float))
                and math.isfinite(float(value))
                and float(value) >= 0
                for value in timestamps
            )
            and float(timestamps[0])
            <= float(timestamps[1])
            <= float(timestamps[2])
            and exploration.get("trajectory_started_unix") == timestamps[0]
            and exploration.get("proposed_unix") == timestamps[1]
            and exploration.get("resolved_unix") == timestamps[2],
            f"trace timestamps are invalid or unbound: {sample_id}",
        )
        checks.require(
            proposal.get("behavior_policy_id") == sample["behavior_policy_id"]
            and proposal_body.get("category") == sample["category"]
            and proposal_body.get("baseline_action_id")
            == exploration["baseline_action_id"]
            and proposal_body.get("alternative_action_id")
            == exploration["alternative_action_id"]
            and proposal_body.get("candidates") == candidate_actions
            and proposal_body.get("state_hash") == exploration["state_hash"]
            and proposal_body.get("execution_eligible") is True
            and proposal_body.get("rollout_mode") == "executable",
            f"trace proposal payload mismatch: {sample_id}",
        )
        checks.require(
            _selection_replays(proposal, selection, manifest),
            f"trace deterministic selection replay mismatch: {sample_id}",
        )
        selected_candidate = _mapping(
            proposal.get("selected_candidate"),
            "trace selected candidate",
        )
        checks.require(
            len(selected_candidates) == 1
            and selected_candidate == selected_candidates[0]
            and selected_candidate.get("available") is True
            and selected_candidate.get("executable") is True,
            f"trace selected candidate is not legal: {sample_id}",
        )
        checks.require(
            selection.get("selected_action_id") == sample["selected_action_id"]
            and selection.get("distribution")
            == exploration["candidate_distribution"]
            and selection.get("distribution_hash")
            == exploration["distribution_hash"]
            and selection.get("state_hash") == exploration["state_hash"]
            and selection.get("session_id") == exploration["session_id"]
            and selection.get("trajectory_session_id")
            == sample["trajectory_session_id"]
            and selection.get("category") == sample["category"]
            and selection.get("decision_index")
            == exploration["decision_index"]
            and selection.get("selected_probability_numerator")
            == exploration["selected_probability"]["numerator"]
            and selection.get("selected_probability_denominator")
            == exploration["selected_probability"]["denominator"]
            and selection.get("selected_action_probability")
            == sample["behavior_action_probability"]
            and exploration.get("candidate_legality") == "valid"
            and exploration.get("replay_status") == "valid"
            and exploration.get("confirmation_status") == "confirmed",
            f"trace propensity mismatch: {sample_id}",
        )
        checks.require(
            resolution.get("decision_id") == sample_id
            and resolution.get("session_id") == exploration["session_id"]
            and resolution.get("category") == sample["category"]
            and resolution.get("status") == "confirmed"
            and resolution.get("executed_known_propensity") is True
            and resolution.get("reason") == "confirmed"
            and exploration.get("confirmation_reason")
            == resolution.get("reason")
            and resolution.get("selected_action_id")
            == sample["selected_action_id"]
            and resolution.get("trajectory_session_id")
            == sample["trajectory_session_id"],
            f"trace confirmation mismatch: {sample_id}",
        )
    exclusions = _sequence(pool_slot.get("export_exclusions"), "export exclusions")
    normalized_exclusions = []
    excluded_ids = set()
    for raw_exclusion in exclusions:
        exclusion = dict(_mapping(raw_exclusion, "export exclusion"))
        decision_id = _required_string(
            exclusion.get("decision_id"),
            "excluded decision_id",
        )
        checks.require(
            decision_id in proposed
            and decision_id not in sample_ids
            and decision_id not in excluded_ids,
            f"export exclusion is not a unique excluded proposal: {decision_id}",
        )
        expected_reason = expected_exclusion_reasons[decision_id]
        checks.require(
            expected_reason is not None,
            (
                "confirmed eligible proposal was exported as an exclusion: "
                f"{decision_id}"
            ),
        )
        reason = _required_string(exclusion.get("reason"), "exclusion reason")
        checks.require(
            set(exclusion).issubset({"category", "decision_id", "detail", "reason"})
            and (
                "category" not in exclusion
                or exclusion["category"] == proposed[decision_id].get("category")
            )
            and (
                "detail" not in exclusion
                or isinstance(exclusion["detail"], str)
                and bool(exclusion["detail"])
            )
            and bool(reason),
            f"export exclusion fields mismatch: {decision_id}",
        )
        checks.require(
            reason == expected_reason,
            (
                "export exclusion reason mismatch: "
                f"{decision_id}: expected {expected_reason}, observed {reason}"
            ),
        )
        excluded_ids.add(decision_id)
        normalized_exclusions.append(exclusion)
    checks.require(
        normalized_exclusions
        == sorted(normalized_exclusions, key=_canonical_json),
        "export exclusions are not canonically ordered",
    )
    checks.require(
        excluded_ids
        == {
            decision_id
            for decision_id, reason in expected_exclusion_reasons.items()
            if reason is not None
        },
        "export exclusion membership mismatch",
    )
    checks.require(
        not excluded_ids,
        "normal closeout contains trace export exclusions",
    )

    unattributed = _sequence(
        pool_slot.get("unattributed_sample_groups"),
        "unattributed groups",
    )
    checks.require(
        len(joined_run_files) == len(set(joined_run_files))
        and len(joined_run_files) == pool_slot.get("joined_run_count"),
        "joined run file membership mismatch",
    )
    joined_outcomes = _load_joined_run_outcomes(
        joined_run_files,
        runs_root=runs_root,
    )
    eligible_by_session: dict[str, list[str]] = defaultdict(list)
    matched_group_by_decision = {}
    for decision_id, proposal in proposed.items():
        if expected_exclusion_reasons[decision_id] is not None:
            continue
        trajectory_session_id = _required_string(
            proposal.get("trajectory_session_id"),
            "eligible trajectory_session_id",
        )
        eligible_by_session[trajectory_session_id].append(decision_id)
        matched_group_by_decision[decision_id] = _replay_outcome_join(
            proposal,
            joined_outcomes,
        )

    expected_unattributed = []
    for trajectory_session_id in sorted(eligible_by_session):
        decision_ids = eligible_by_session[trajectory_session_id]
        matched_groups = [
            matched_group_by_decision[decision_id]
            for decision_id in decision_ids
        ]
        all_matched = all(group_id is not None for group_id in matched_groups)
        unique_groups = {group_id for group_id in matched_groups if group_id}
        if all_matched and len(unique_groups) == 1:
            expected_group = next(iter(unique_groups))
            for decision_id in decision_ids:
                checks.require(
                    decision_id in sample_ids,
                    (
                        "eligible proposal was laundered as unattributed: "
                        f"{decision_id}"
                    ),
                )
                checks.require(
                    sample_group_ids[decision_id] == expected_group,
                    f"independent outcome join mismatch: {decision_id}",
                )
            continue
        checks.require(
            not any(decision_id in sample_ids for decision_id in decision_ids),
            (
                "outcome-incomplete trajectory was included in the pool: "
                f"{trajectory_session_id}"
            ),
        )
        expected_unattributed.append(
            {
                "decision_count": len(decision_ids),
                "reason": (
                    "outcome_join_incomplete"
                    if not all_matched
                    else "trajectory_group_conflict"
                ),
                "trajectory_session_id": trajectory_session_id,
            }
        )

    normalized_unattributed = []
    for raw_group in unattributed:
        group = dict(_mapping(raw_group, "unattributed group"))
        checks.require(
            set(group)
            == {"decision_count", "reason", "trajectory_session_id"}
            and _exact_int(
                group.get("decision_count"),
                "unattributed decision_count",
            )
            > 0
            and group.get("reason")
            in {"outcome_join_incomplete", "trajectory_group_conflict"}
            and isinstance(group.get("trajectory_session_id"), str)
            and bool(group["trajectory_session_id"]),
            "unattributed group fields mismatch",
        )
        normalized_unattributed.append(group)
    checks.require(
        normalized_unattributed == expected_unattributed,
        "unattributed groups do not match independent outcome joins",
    )


def _load_joined_run_outcomes(
    run_files: Sequence[str],
    *,
    runs_root: Path,
) -> list[dict[str, Any]]:
    outcomes = []
    for run_file in run_files:
        if (
            not isinstance(run_file, str)
            or re.fullmatch(r"[0-9]+\.run", run_file) is None
        ):
            raise OutcomeEvidenceVerificationError(
                f"joined run file is invalid: {run_file}"
            )
        completed_unix = int(Path(run_file).stem)
        run_path = runs_root / run_file
        record = _load_mapping(run_path)
        playtime = _coerce_outcome_int(record.get("playtime"), default=0) or 0
        floor_reached = (
            _coerce_outcome_int(record.get("floor_reached"), default=0) or 0
        )
        outcomes.append(
            {
                "end_unix": completed_unix,
                "floor_reached": floor_reached,
                "group_id": f"run:{completed_unix}",
                "start_unix": max(0, completed_unix - playtime),
            }
        )
    return outcomes


def _replay_outcome_join(
    proposal: Mapping[str, Any],
    outcomes: Sequence[Mapping[str, Any]],
) -> str | None:
    proposal_body = _mapping(proposal.get("proposal"), "trace proposal")
    state = _mapping(proposal_body.get("state"), "proposal state")
    try:
        sample_time = float(proposal.get("trajectory_started_unix"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(sample_time):
        return None
    sample_floor = _coerce_outcome_int(state.get("floor"), default=None)
    time_matches = [
        outcome
        for outcome in outcomes
        if float(outcome["start_unix"]) - OUTCOME_JOIN_TOLERANCE_SECONDS
        <= sample_time
        <= float(outcome["end_unix"])
    ]
    matches = [
        outcome
        for outcome in time_matches
        if sample_floor is not None
        and sample_floor >= 0
        and int(outcome["floor_reached"]) > 0
        and sample_floor <= int(outcome["floor_reached"])
    ]
    if len(matches) != 1:
        return None
    return str(matches[0]["group_id"])


def _coerce_outcome_int(value: Any, *, default: int | None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _proposal_history_errors(
    proposed: Mapping[str, Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> dict[str, str]:
    config = _mapping(manifest.get("effective_config"), "effective config")
    session_id = _required_string(config.get("session_id"), "config session_id")
    alternative_limit = _exact_int(
        config.get("per_run_alternative_budget"),
        "alternative budget",
    )
    expected_policy_id = f"known-propensity-epsilon-v1:{session_id}"
    errors: dict[str, str] = {}
    trajectories = {}
    for decision_id, record in proposed.items():
        trajectory_id = str(record.get("trajectory_session_id") or "")
        state = trajectories.setdefault(
            trajectory_id,
            {
                "alternative_attempts": 0,
                "history_invalid": False,
                "next_index": 0,
                "seen_indices": set(),
                "started_unix": record.get("trajectory_started_unix"),
            },
        )
        if state["history_invalid"]:
            errors[decision_id] = "trajectory_history_invalid"
            continue
        raw_index = record.get("decision_index")
        if (
            isinstance(raw_index, bool)
            or not isinstance(raw_index, int)
            or raw_index < 0
        ):
            errors[decision_id] = "trajectory_decision_index_mismatch"
            state["history_invalid"] = True
            continue
        if raw_index in state["seen_indices"]:
            errors[decision_id] = "duplicate_trajectory_decision_index"
            state["history_invalid"] = True
            continue
        if raw_index != state["next_index"]:
            errors[decision_id] = "trajectory_decision_index_mismatch"
            state["history_invalid"] = True
            continue
        state["seen_indices"].add(raw_index)
        state["next_index"] = raw_index + 1
        if record.get("trajectory_started_unix") != state["started_unix"]:
            errors[decision_id] = "trajectory_start_mismatch"
            state["history_invalid"] = True
            continue
        proposal = _mapping(record.get("proposal"), "trace proposal")
        state_hash = str(proposal.get("state_hash") or "")
        if not trajectory_id or not state_hash:
            errors.setdefault(decision_id, "trajectory_identity_invalid")
        else:
            identity = {
                "decision_index": raw_index,
                "namespace": "noncombat-exploration-decision-v1",
                "session_id": session_id,
                "state_hash": state_hash,
                "trajectory_session_id": trajectory_id,
            }
            expected_decision_id = "decision-" + hashlib.sha256(
                _canonical_json(identity).encode("utf-8")
            ).hexdigest()[:32]
            if decision_id != expected_decision_id:
                errors.setdefault(decision_id, "decision_id_mismatch")
        if record.get("behavior_policy_id") != expected_policy_id:
            errors.setdefault(decision_id, "behavior_policy_id_mismatch")
        selection = _mapping(record.get("selection"), "trace selection")
        selected_alternative = selection.get(
            "selected_action_id"
        ) == proposal.get("alternative_action_id")
        budget = _mapping(
            record.get("alternative_attempt_budget"),
            "alternative attempt budget",
        )
        if not (
            type(budget.get("limit")) is int
            and budget.get("limit") == alternative_limit
            and type(budget.get("used_before")) is int
            and budget.get("used_before") == state["alternative_attempts"]
            and budget.get("selected_alternative") is selected_alternative
            and state["alternative_attempts"] < alternative_limit
        ):
            errors.setdefault(
                decision_id,
                "alternative_budget_history_mismatch",
            )
        if decision_id in errors:
            state["history_invalid"] = True
        elif selected_alternative:
            state["alternative_attempts"] += 1
    return errors


def _selection_replays(
    proposal_record: Mapping[str, Any],
    selection: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> bool:
    proposal = _mapping(proposal_record.get("proposal"), "trace proposal")
    config = _mapping(manifest.get("effective_config"), "effective config")
    category = str(proposal.get("category") or "")
    enabled_categories = _sequence(
        config.get("enabled_categories"),
        "enabled categories",
    )
    rates = _mapping(config.get("category_rates_bps"), "category rates")
    epsilon_bps = rates.get(category)
    if (
        category not in enabled_categories
        or isinstance(epsilon_bps, bool)
        or not isinstance(epsilon_bps, int)
        or not 0 <= epsilon_bps <= DRAW_BUCKET_COUNT
    ):
        return False
    candidates = _sequence(proposal.get("candidates"), "proposal candidates")
    candidate_ids = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            return False
        action_id = candidate.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            return False
        candidate_ids.append(action_id)
    baseline_action_id = proposal.get("baseline_action_id")
    alternative_action_id = proposal.get("alternative_action_id")
    if (
        not isinstance(baseline_action_id, str)
        or not isinstance(alternative_action_id, str)
        or baseline_action_id == alternative_action_id
        or len(candidate_ids) != len(set(candidate_ids))
        or baseline_action_id not in candidate_ids
        or alternative_action_id not in candidate_ids
    ):
        return False
    state = proposal.get("state")
    if not isinstance(state, Mapping):
        return False
    expected_state_hash = hashlib.sha256(
        _canonical_json(
            {
                "candidates": list(candidates),
                "category": category,
                "state": state,
            }
        ).encode("utf-8")
    ).hexdigest()
    if proposal.get("state_hash") != expected_state_hash:
        return False
    if proposal.get("execution_eligible") is True:
        by_id = {
            str(candidate["action_id"]): candidate for candidate in candidates
        }
        if any(
            by_id[action_id].get("available") is not True
            or by_id[action_id].get("executable") is not True
            for action_id in (baseline_action_id, alternative_action_id)
        ):
            return False
    seed = config.get("seed")
    decision_index = proposal_record.get("decision_index")
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index < 0
    ):
        return False
    distribution = [
        {
            "action_id": baseline_action_id,
            "denominator": DRAW_BUCKET_COUNT,
            "numerator": DRAW_BUCKET_COUNT - epsilon_bps,
            "value": (DRAW_BUCKET_COUNT - epsilon_bps) / DRAW_BUCKET_COUNT,
        },
        {
            "action_id": alternative_action_id,
            "denominator": DRAW_BUCKET_COUNT,
            "numerator": epsilon_bps,
            "value": epsilon_bps / DRAW_BUCKET_COUNT,
        },
    ]
    draw_input = {
        "alternative_action_id": alternative_action_id,
        "baseline_action_id": baseline_action_id,
        "candidate_action_ids": candidate_ids,
        "category": category,
        "decision_index": decision_index,
        "epsilon_bps": epsilon_bps,
        "schema_version": SELECTION_SCHEMA_VERSION,
        "seed": seed,
        "session_id": config.get("session_id"),
        "state_hash": proposal.get("state_hash"),
        "trajectory_session_id": proposal_record.get("trajectory_session_id"),
    }
    encoded = _canonical_json(draw_input).encode("utf-8")
    acceptance_limit = (1 << 64) - ((1 << 64) % DRAW_BUCKET_COUNT)
    for draw_counter in range(1_000_000):
        digest = hashlib.sha256(
            encoded + b"\x00" + str(draw_counter).encode("ascii")
        ).digest()
        draw_u64 = int.from_bytes(digest[:8], byteorder="big", signed=False)
        if draw_u64 < acceptance_limit:
            break
    else:
        raise OutcomeEvidenceVerificationError(
            "cannot derive deterministic exploration draw"
        )
    draw_bucket = draw_u64 % DRAW_BUCKET_COUNT
    selected_action_id = (
        alternative_action_id
        if draw_bucket < epsilon_bps
        else baseline_action_id
    )
    selected_probability = next(
        row for row in distribution if row["action_id"] == selected_action_id
    )
    expected = {
        "category": category,
        "decision_index": decision_index,
        "distribution": distribution,
        "distribution_hash": hashlib.sha256(
            _canonical_json(distribution).encode("utf-8")
        ).hexdigest(),
        "draw_bucket": draw_bucket,
        "draw_counter": draw_counter,
        "draw_input_hash": hashlib.sha256(encoded).hexdigest(),
        "draw_u64": draw_u64,
        "schema_version": SELECTION_SCHEMA_VERSION,
        "selected_action_id": selected_action_id,
        "selected_action_probability": selected_probability["value"],
        "selected_probability_denominator": selected_probability["denominator"],
        "selected_probability_numerator": selected_probability["numerator"],
        "session_id": config.get("session_id"),
        "state_hash": proposal.get("state_hash"),
        "trajectory_session_id": proposal_record.get("trajectory_session_id"),
    }
    return dict(selection) == expected


def _expected_export_exclusion_reason(
    proposal: Mapping[str, Any],
    resolution: Mapping[str, Any] | None,
    history_error: str | None,
    manifest: Mapping[str, Any],
) -> str | None:
    proposal_body = _mapping(proposal.get("proposal"), "trace proposal")
    if not bool(proposal_body.get("execution_eligible")):
        return "shadow_only"
    if history_error is not None:
        return history_error
    if not isinstance(resolution, Mapping):
        return "confirmation_missing"
    status = str(resolution.get("status") or "missing")
    if status != "confirmed" or not bool(
        resolution.get("executed_known_propensity")
    ):
        return f"confirmation_{status}"
    if not _resolution_matches_proposal(proposal, resolution):
        return "confirmation_link_mismatch"
    if not _trace_timestamps_are_monotonic(proposal, resolution):
        return "timestamp_order_invalid"
    selection = proposal.get("selection")
    if not isinstance(selection, Mapping):
        return "replay_mismatch"
    try:
        replay_valid = _selection_replays(proposal, selection, manifest)
    except (OutcomeEvidenceVerificationError, KeyError, TypeError, ValueError):
        replay_valid = False
    if not replay_valid:
        return "replay_mismatch"
    try:
        candidate_legal = _selected_candidate_is_legal(proposal, selection)
    except (OutcomeEvidenceVerificationError, KeyError, TypeError, ValueError):
        candidate_legal = False
    if not candidate_legal:
        return "selected_candidate_illegal"
    return None


def _resolution_matches_proposal(
    proposal: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> bool:
    selection = proposal.get("selection")
    return isinstance(selection, Mapping) and all(
        resolution.get(field) == proposal.get(field)
        for field in (
            "decision_id",
            "session_id",
            "trajectory_session_id",
            "category",
        )
    ) and resolution.get("selected_action_id") == selection.get(
        "selected_action_id"
    )


def _selected_candidate_is_legal(
    proposal: Mapping[str, Any],
    selection: Mapping[str, Any],
) -> bool:
    selected_candidate = proposal.get("selected_candidate")
    if not isinstance(selected_candidate, Mapping):
        return False
    if selected_candidate.get("action_id") != selection.get("selected_action_id"):
        return False
    proposal_body = _mapping(proposal.get("proposal"), "trace proposal")
    matching_candidates = [
        candidate
        for candidate in _sequence(
            proposal_body.get("candidates"),
            "proposal candidates",
        )
        if isinstance(candidate, Mapping)
        and candidate.get("action_id") == selection.get("selected_action_id")
    ]
    if len(matching_candidates) != 1:
        return False
    candidate = matching_candidates[0]
    return all(
        (
            candidate.get("available") is True,
            candidate.get("executable") is True,
            selected_candidate.get("available") is True,
            selected_candidate.get("executable") is True,
            selected_candidate.get("kind") == candidate.get("kind"),
            selected_candidate.get("label") == candidate.get("label"),
            selected_candidate.get("raw", {}) == candidate.get("raw", {}),
        )
    )


def _trace_timestamps_are_monotonic(
    proposal: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> bool:
    values = (
        proposal.get("trajectory_started_unix"),
        proposal.get("proposed_unix"),
        resolution.get("resolved_unix"),
    )
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
        for value in values
    ):
        return False
    started, proposed_unix, resolved_unix = (float(value) for value in values)
    return started <= proposed_unix <= resolved_unix


def _verify_sample_probability(
    sample: Mapping[str, Any],
    checks: _Checks,
) -> None:
    exploration = _mapping(sample.get("exploration"), "sample exploration")
    selected = _fraction(
        exploration.get("selected_probability"),
        "selected probability",
    )
    distribution = _sequence(
        exploration.get("candidate_distribution"),
        "candidate distribution",
    )
    probabilities = {}
    for raw_row in distribution:
        row = _mapping(raw_row, "candidate probability")
        action_id = _required_string(row.get("action_id"), "probability action_id")
        probability = _fraction(row, "candidate probability")
        checks.require(action_id not in probabilities, "duplicate behavior action")
        probabilities[action_id] = probability
    checks.require(
        sum(probabilities.values(), Fraction(0, 1)) == 1,
        "behavior distribution does not sum to one",
    )
    checks.require(
        probabilities.get(sample.get("selected_action_id")) == selected
        and sample.get("behavior_probability_status")
        == "verified_known_propensity"
        and sample.get("behavior_action_probability") == float(selected),
        "selected behavior probability mismatch",
    )


def _included_trajectory_rows(
    groups: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    rows = []
    for group_id in sorted(groups, key=_group_sort_key):
        decisions = groups[group_id]
        outcome = _mapping(decisions[0].get("outcome"), "trajectory outcome")
        session_id = decisions[0]["exploration"]["session_id"]
        trajectory_session_id = decisions[0]["trajectory_session_id"]
        for decision in decisions[1:]:
            if (
                decision.get("outcome") != outcome
                or decision["exploration"]["session_id"] != session_id
                or decision.get("trajectory_session_id")
                != trajectory_session_id
            ):
                raise OutcomeEvidenceVerificationError(
                    f"trajectory content conflicts: {group_id}"
                )
        rows.append(
            {
                "decision_count": len(decisions),
                "group_id": group_id,
                "run_file": outcome["run_file"],
                "session_id": session_id,
                "trajectory_session_id": trajectory_session_id,
            }
        )
    return rows


def _verify_terminal_outcomes(
    groups: Mapping[str, Sequence[Mapping[str, Any]]],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, str]:
    checkpoint_root = Path(
        registration["integrity_rules"]["checkpoint_inventory"]["root"]
    )
    runs_root = checkpoint_root.resolve().parent / "runs" / "IRONCLAD"
    hashes = {}
    for group_id in sorted(groups, key=_group_sort_key):
        decisions = groups[group_id]
        outcome = _mapping(decisions[0].get("outcome"), "sample outcome")
        run_file = _required_string(outcome.get("run_file"), "run_file")
        run_path = runs_root / run_file
        run_bytes = run_path.read_bytes()
        raw = _load_mapping_bytes(run_bytes, run_path)
        checks.require(
            raw.get("victory") is outcome.get("victory")
            and raw.get("floor_reached") == outcome.get("floor_reached")
            and raw.get("killed_by") == outcome.get("killed_by")
            and raw.get("playtime") == outcome.get("playtime"),
            f"terminal outcome mismatch: {group_id}",
        )
        hashes[run_file] = hashlib.sha256(run_bytes).hexdigest()
    return hashes


def _recompute_metrics(
    samples: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    pool_result: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    checks.require(
        target.get("construction_mode") == "current_deterministic"
        and target.get("diagnostic_only") is False,
        "target is not deterministic Current",
    )
    entries = _sequence(target.get("entries"), "target entries")
    by_sample = {}
    for raw_entry in entries:
        entry = _mapping(raw_entry, "target entry")
        sample_id = _required_string(entry.get("sample_id"), "target sample_id")
        checks.require(sample_id not in by_sample, "duplicate target sample_id")
        probabilities = {}
        for raw_probability in _sequence(
            entry.get("probabilities"),
            "target probabilities",
        ):
            row = _mapping(raw_probability, "target probability")
            action_id = _required_string(row.get("action_id"), "target action")
            probabilities[action_id] = _fraction(row, "target probability")
        checks.require(
            sum(probabilities.values(), Fraction(0, 1)) == 1,
            f"target probabilities do not sum to one: {sample_id}",
        )
        by_sample[sample_id] = probabilities
    checks.require(len(by_sample) == len(samples), "target sample coverage mismatch")
    weights = {}
    outcomes = {}
    arm_decisions = Counter()
    arm_trajectories: dict[tuple[str, str], set[str]] = defaultdict(set)
    for sample in samples:
        sample_id = str(sample["sample_id"])
        checks.require(sample_id in by_sample, f"missing target sample: {sample_id}")
        selected = str(sample["selected_action_id"])
        behavior = _fraction(
            sample["exploration"]["selected_probability"],
            "behavior probability",
        )
        target_probability = by_sample[sample_id].get(selected, Fraction(0, 1))
        group_id = str(sample["trajectory_group_id"])
        category = str(sample["category"])
        selected_arm = str(sample["exploration"]["selected_arm"])
        arm_key = (category, selected_arm)
        arm_decisions[arm_key] += 1
        arm_trajectories[arm_key].add(group_id)
        weights[group_id] = weights.get(group_id, Fraction(1, 1)) * (
            target_probability / behavior
        )
        outcome = sample["outcome"]
        if group_id in outcomes and outcomes[group_id] != outcome:
            raise OutcomeEvidenceVerificationError(
                f"trajectory outcome conflict: {group_id}"
            )
        outcomes[group_id] = outcome
    weight_sum = sum(weights.values(), Fraction(0, 1))
    squared_sum = sum((weight * weight for weight in weights.values()), Fraction(0, 1))
    ess = (
        weight_sum * weight_sum / squared_sum
        if squared_sum > 0
        else Fraction(0, 1)
    )
    trajectory_count = len(weights)
    ess_fraction = ess / (trajectory_count or 1)
    max_normalized = (
        max(weights.values(), default=Fraction(0, 1)) / weight_sum
        if weight_sum > 0
        else Fraction(0, 1)
    )
    supported = [
        {
            "group_id": group_id,
            "weight": _fraction_record(weights[group_id]),
        }
        for group_id in sorted(weights, key=_group_sort_key)
        if outcomes[group_id].get("victory") is True and weights[group_id] > 0
    ]
    readiness_support = {
        category: {
            arm: {
                "decision_count": arm_decisions[(category, arm)],
                "trajectory_count": len(arm_trajectories[(category, arm)]),
            }
            for arm in ("alternative", "baseline")
        }
        for category in ("card_reward", "shop")
    }
    return {
        "all_registered_slots_accounted": True,
        "category_arm_support": pool_result["category_arm_support"],
        "complete_trajectory_count": trajectory_count,
        "ess_fraction": ess_fraction,
        "global_integrity_stop": False,
        "max_normalized_weight": max_normalized,
        "nonzero_weight_trajectory_count": sum(
            weight > 0 for weight in weights.values()
        ),
        "readiness_category_arm_support": readiness_support,
        "supported_victories": supported,
        "supported_victory_count": len(supported),
    }


def _verify_readiness_metrics(
    readiness: Mapping[str, Any],
    metrics: Mapping[str, Any],
    checks: _Checks,
) -> None:
    diagnostics = _mapping(readiness.get("diagnostics"), "readiness diagnostics")
    checks.require(
        diagnostics.get("trajectory_count")
        == metrics["complete_trajectory_count"]
        and diagnostics.get("nonzero_weight_count")
        == metrics["nonzero_weight_trajectory_count"]
        and _fraction(diagnostics.get("ess_fraction"), "readiness ESS fraction")
        == metrics["ess_fraction"]
        and _fraction(
            diagnostics.get("max_normalized_weight"),
            "readiness maximum normalized weight",
        )
        == metrics["max_normalized_weight"]
        and diagnostics.get("category_arm_support")
        == metrics["readiness_category_arm_support"],
        "readiness diagnostics differ from independent metrics",
    )


def _verify_estimate(
    estimate: Mapping[str, Any],
    *,
    paths: Mapping[str, Path],
    registration: Mapping[str, Any],
    readiness: Mapping[str, Any],
    readiness_audit: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, bool]:
    schema = estimate.get("schema_version")
    if schema == ESTIMATE_SCHEMA_VERSION:
        try:
            verify_estimate_artifact(
                sample_path=paths["pool_samples"],
                target_manifest_path=paths["target"],
                readiness_path=paths["readiness"],
                estimate_path=paths["estimate"],
                calibration_path=paths["calibration"],
            )
        except EstimateVerificationError as exc:
            raise OutcomeEvidenceVerificationError(
                f"OPE estimate replay failed: {exc}"
            ) from exc
    elif schema == BLOCKED_ESTIMATE_SCHEMA_VERSION:
        checks.require(
            bool(readiness_audit.get("overlap_blockers")),
            "blocked estimate has no independently replayed overlap blocker",
        )
        source = _mapping(estimate.get("source"), "blocked estimate source")
        expected_source = {
            "calibration_file_sha256": _file_sha256(paths["calibration"]),
            "estimate_artifact_implementation_sha256": _file_sha256(
                Path(registration["repo_root"])
                / "analysis_scripts/noncombat_ope_estimate_artifacts.py"
            ),
            "estimator_implementation_sha256": _file_sha256(
                Path(registration["repo_root"])
                / "analysis_scripts/noncombat_ope_estimation.py"
            ),
            "readiness_file_sha256": _file_sha256(paths["readiness"]),
            "sample_file_sha256": _file_sha256(paths["pool_samples"]),
            "target_file_sha256": _file_sha256(paths["target"]),
        }
        checks.require(source == expected_source, "blocked estimate source mismatch")
        analysis = registration["analysis_rules"]
        checks.require(
            estimate.get("contracts")
            == {
                "bootstrap_confidence_level": {
                    "denominator": 20,
                    "numerator": 19,
                    "value": 0.95,
                },
                "bootstrap_seed": analysis["bootstrap_seed"],
                "primary_outcome": "victory",
                "production_bootstrap_replicates": 10_000,
                "terminal_horizon": "complete_run",
            },
            "blocked estimate production contract mismatch",
        )
        expected_gates = {
            "causal_uplift_ready": False,
            "dataset_estimation_ready": False,
            "formal_noncombat_rl_training_ready": False,
            "live_policy_promotion_ready": False,
            "ope_estimate_ready": False,
            "policy_comparison_ready": False,
            "reward_design_ready": False,
        }
        checks.require(
            estimate.get("estimates") is None
            and estimate.get("bootstrap") is None
            and estimate.get("influence") is None
            and estimate.get("gates") == expected_gates
            and estimate.get("blockers") == ["dataset_estimation_not_ready"]
            and estimate.get("readiness_blockers")
            == sorted(str(value) for value in readiness.get("blockers", [])),
            "blocked estimate widened authority or changed blockers",
        )
    else:
        raise OutcomeEvidenceVerificationError("estimate schema mismatch")
    gates = _mapping(estimate.get("gates"), "estimate gates")
    return {
        "ope_estimate_ready": gates.get("ope_estimate_ready") is True,
        "policy_comparison_ready": gates.get("policy_comparison_ready") is True,
    }


def _build_evidence_gate(
    registration: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    thresholds = registration["thresholds"]
    minimum_nonzero = _fraction(
        thresholds["minimum_nonzero_weight_fraction"],
        "minimum nonzero fraction",
    )
    minimum_ess = _fraction(
        thresholds["minimum_ess_fraction"],
        "minimum ESS fraction",
    )
    maximum_weight = _fraction(
        thresholds["maximum_normalized_weight"],
        "maximum normalized weight",
    )
    conditions = {}

    def add(code: str, observed: Any, required: Any, passed: bool) -> None:
        conditions[code] = {
            "observed": _gate_value(observed),
            "passed": passed is True,
            "required": _gate_value(required),
        }

    add(
        "all_registered_slots_accounted",
        metrics["all_registered_slots_accounted"],
        True,
        metrics["all_registered_slots_accounted"],
    )
    add(
        "no_global_integrity_stop",
        metrics["global_integrity_stop"],
        False,
        not metrics["global_integrity_stop"],
    )
    complete = metrics["complete_trajectory_count"]
    minimum_complete = thresholds["minimum_complete_trajectories"]
    add(
        "minimum_complete_trajectories",
        complete,
        minimum_complete,
        complete >= minimum_complete,
    )
    minimum_arm = thresholds["minimum_arm_decisions_per_category"]
    for category in ("card_reward", "shop"):
        for arm in ("baseline", "alternative"):
            observed = metrics["category_arm_support"][category][arm]
            add(
                f"minimum_{category}_{arm}_decisions",
                observed,
                minimum_arm,
                observed >= minimum_arm,
            )
    minimum_count = (
        complete * minimum_nonzero.numerator
        + minimum_nonzero.denominator
        - 1
    ) // minimum_nonzero.denominator
    nonzero_count = metrics["nonzero_weight_trajectory_count"]
    add(
        "minimum_nonzero_weight_fraction",
        {
            "count": nonzero_count,
            "fraction": _fraction_record(Fraction(nonzero_count, complete or 1)),
        },
        {
            "fraction": _fraction_record(minimum_nonzero),
            "minimum_count": minimum_count,
        },
        nonzero_count >= minimum_count,
    )
    add(
        "minimum_ess_fraction",
        metrics["ess_fraction"],
        minimum_ess,
        metrics["ess_fraction"] >= minimum_ess,
    )
    add(
        "maximum_normalized_weight",
        metrics["max_normalized_weight"],
        maximum_weight,
        metrics["max_normalized_weight"] <= maximum_weight,
    )
    supported = metrics["supported_victory_count"]
    minimum_supported = thresholds["minimum_supported_victories"]
    add(
        "minimum_supported_victories",
        supported,
        minimum_supported,
        supported >= minimum_supported,
    )
    blockers = sorted(
        code for code, condition in conditions.items() if not condition["passed"]
    )
    return {
        "blockers": blockers,
        "conditions": conditions,
        "outcome_evidence_expansion_ready": not blockers,
        "schema_version": EVIDENCE_GATE_SCHEMA_VERSION,
        "study_id": registration["study_id"],
    }


def _verify_closeout(
    closeout: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    pool: Mapping[str, Any],
    target: Mapping[str, Any],
    readiness: Mapping[str, Any],
    estimate_result: Mapping[str, bool],
    expected_gate: Mapping[str, Any],
    paths: Mapping[str, Path],
    checks: _Checks,
) -> None:
    checks.require(
        set(closeout)
        == {
            "blockers",
            "closeout_hash",
            "evidence_gate",
            "gates",
            "integrity_stop",
            "limitations",
            "registration_hash",
            "run_lock_hash",
            "schema_version",
            "slots",
            "source",
            "status",
            "study_id",
        },
        "closeout fields mismatch",
    )
    checks.require(
        closeout.get("schema_version") == CLOSEOUT_SCHEMA_VERSION,
        "closeout schema mismatch",
    )
    checks.require(
        closeout.get("closeout_hash") == _self_hash(closeout, "closeout_hash"),
        "closeout hash mismatch",
    )
    checks.require(
        closeout.get("study_id") == registration["study_id"]
        and closeout.get("registration_hash") == registration["registration_hash"]
        and closeout.get("run_lock_hash") == run_lock["run_lock_hash"],
        "closeout study binding mismatch",
    )
    checks.require(
        closeout.get("source")
        == {
            "calibration_file_sha256": _file_sha256(paths["calibration"]),
            "estimate_file_sha256": _file_sha256(paths["estimate"]),
            "pool_manifest_hash": pool["pool_manifest_hash"],
            "readiness_file_sha256": _file_sha256(paths["readiness"]),
            "target_manifest_hash": target["manifest_hash"],
        },
        "closeout source binding mismatch",
    )
    expected_slots = [
        {
            "session_id": row["session_id"],
            "slot_number": row["slot_number"],
            "terminal_status": row["terminal_status"],
        }
        for row in ledger["terminal_slots"]
    ]
    checks.require(closeout.get("slots") == expected_slots, "closeout slots mismatch")
    checks.require(
        closeout.get("evidence_gate") == expected_gate,
        "closeout evidence gate differs from independent replay",
    )
    readiness_gates = _mapping(readiness.get("readiness"), "readiness gates")
    dataset_ready = (
        readiness_gates.get("outcome_contract_ready") is True
        and readiness_gates.get("overlap_ready") is True
        and readiness_gates.get("target_policy_ready") is True
    )
    evidence_ready = expected_gate["outcome_evidence_expansion_ready"] is True
    expected_gates = {
        "causal_uplift_ready": False,
        "dataset_ope_readiness_ready": dataset_ready,
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
        "ope_estimate_ready": estimate_result["ope_estimate_ready"],
        "outcome_evidence_expansion_ready": evidence_ready,
        "policy_comparison_ready": estimate_result["policy_comparison_ready"],
        "reward_design_ready": False,
    }
    checks.require(
        closeout.get("gates") == expected_gates,
        "closeout authority or readiness gates mismatch",
    )
    checks.require(
        closeout.get("limitations")
        == [
            "Evidence readiness is separate from policy comparison.",
            (
                "No closeout gate authorizes causal claims, training, "
                "reward design, or live promotion."
            ),
        ],
        "closeout authority limitations mismatch",
    )
    expected_status = "ready" if evidence_ready else "inconclusive"
    checks.require(
        closeout.get("status") == expected_status
        and closeout.get("blockers") == expected_gate["blockers"]
        and closeout.get("integrity_stop") is None,
        "closeout status mismatch",
    )


def _properties_semantic_sha256(path: Path) -> str:
    content = path.read_text(encoding="iso-8859-1")
    natural_lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    properties = {}
    for logical_line in _java_properties_logical_lines(natural_lines):
        parsed = _parse_java_property(logical_line)
        if parsed is not None:
            key, value = parsed
            properties[key] = value
    payload = (_canonical_json(properties) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _java_properties_logical_lines(lines: Sequence[str]):
    pending = ""
    continuing = False
    for natural_line in lines:
        if not continuing and natural_line.lstrip(" \t\f").startswith(("#", "!")):
            yield natural_line
            continue
        piece = natural_line.lstrip(" \t\f") if continuing else natural_line
        pending += piece
        trailing_backslashes = len(pending) - len(pending.rstrip("\\"))
        if trailing_backslashes % 2 == 1:
            pending = pending[:-1]
            continuing = True
            continue
        yield pending
        pending = ""
        continuing = False
    if pending or continuing:
        yield pending


def _parse_java_property(line: str) -> tuple[str, str] | None:
    content = line.lstrip(" \t\f")
    if not content or content.startswith(("#", "!")):
        return None
    key_end = len(content)
    value_start = len(content)
    escaped = False
    for index, character in enumerate(content):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character in "=: \t\f":
            key_end = index
            value_start = index
            break
    while value_start < len(content) and content[value_start] in " \t\f":
        value_start += 1
    if value_start < len(content) and content[value_start] in "=:":
        value_start += 1
    while value_start < len(content) and content[value_start] in " \t\f":
        value_start += 1
    return (
        _decode_java_property_escapes(content[:key_end]),
        _decode_java_property_escapes(content[value_start:]),
    )


def _decode_java_property_escapes(value: str) -> str:
    decoded = []
    index = 0
    escapes = {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}
    while index < len(value):
        character = value[index]
        if character != "\\":
            decoded.append(character)
            index += 1
            continue
        index += 1
        if index >= len(value):
            raise OutcomeEvidenceVerificationError(
                "invalid trailing escape in CommunicationMod config"
            )
        escaped = value[index]
        if escaped == "u":
            digits = value[index + 1 : index + 5]
            if len(digits) != 4 or any(
                digit not in "0123456789abcdefABCDEF" for digit in digits
            ):
                raise OutcomeEvidenceVerificationError(
                    "invalid Unicode escape in CommunicationMod config"
                )
            decoded.append(chr(int(digits, 16)))
            index += 5
            continue
        decoded.append(escapes.get(escaped, escaped))
        index += 1
    return "".join(decoded)


def _load_mapping(path: Path) -> dict[str, Any]:
    return _load_mapping_bytes(path.read_bytes(), path)


def _load_mapping_bytes(data: bytes, path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceVerificationError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OutcomeEvidenceVerificationError(
            f"JSON artifact is not an object: {path}"
        )
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise OutcomeEvidenceVerificationError(f"partial JSONL artifact: {path}")
    rows = []
    for line_number, raw_line in enumerate(data.splitlines(), start=1):
        try:
            value = json.loads(
                raw_line.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_constant,
            )
        except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise OutcomeEvidenceVerificationError(
                f"invalid JSONL row {path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise OutcomeEvidenceVerificationError(
                f"JSONL row is not an object: {path}:{line_number}"
            )
        rows.append(value)
    return rows


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _self_hash(value: Mapping[str, Any], field: str) -> str:
    payload = deepcopy(dict(value))
    payload[field] = None
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OutcomeEvidenceVerificationError(f"{field} must be an object")
    return value


def _sequence(value: Any, field: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise OutcomeEvidenceVerificationError(f"{field} must be a list")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise OutcomeEvidenceVerificationError(f"{field} must be nonempty")
    return value


def _absolute_path(value: Any, field: str) -> Path:
    raw = _required_string(value, field)
    path = Path(raw)
    if not path.is_absolute() or str(path.resolve()) != raw:
        raise OutcomeEvidenceVerificationError(f"{field} must be resolved absolute")
    return path


def _exact_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OutcomeEvidenceVerificationError(f"{field} must be an integer")
    return value


def _fraction(value: Any, field: str) -> Fraction:
    record = _mapping(value, field)
    numerator = _exact_int(record.get("numerator"), f"{field}.numerator")
    denominator = _exact_int(record.get("denominator"), f"{field}.denominator")
    if denominator <= 0 or numerator < 0:
        raise OutcomeEvidenceVerificationError(f"{field} is invalid")
    result = Fraction(numerator, denominator)
    if "value" in record and record.get("value") != float(result):
        raise OutcomeEvidenceVerificationError(f"{field}.value is not exact")
    return result


def _fraction_record(value: Fraction) -> dict[str, int | float]:
    return {
        "denominator": value.denominator,
        "numerator": value.numerator,
        "value": float(value),
    }


def _gate_value(value: Any) -> Any:
    if isinstance(value, Fraction):
        return _fraction_record(value)
    if isinstance(value, Mapping):
        return {
            str(key): _gate_value(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_gate_value(item) for item in value]
    return value


def _group_sort_key(group_id: str) -> int:
    if not group_id.startswith("run:") or not group_id[4:].isdigit():
        raise OutcomeEvidenceVerificationError(f"invalid trajectory group: {group_id}")
    return int(group_id[4:])


def _sample_sort_key(sample: Mapping[str, Any]) -> tuple[int, int, str]:
    return (
        _group_sort_key(str(sample.get("trajectory_group_id"))),
        _exact_int(sample["exploration"].get("decision_index"), "decision_index"),
        str(sample.get("sample_id")),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify a non-combat outcome-evidence study."
    )
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        audit = verify_outcome_evidence_expansion(args.registration)
        rendered = render_verification_audit(audit)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8", newline="")
        print(rendered, end="")
        return 0
    except Exception as exc:
        print(f"[outcome-evidence-verifier] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

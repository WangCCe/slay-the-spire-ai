"""Pre-registered, fixed-schedule non-combat outcome evidence study helpers."""

from __future__ import annotations

import hashlib
import fnmatch
import json
import os
import re
import subprocess
import tempfile
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path
from typing import Any


REGISTRATION_SCHEMA_VERSION = "noncombat-outcome-evidence-registration-v1"
RUN_LOCK_SCHEMA_VERSION = "noncombat-outcome-evidence-run-lock-v1"
POOL_SCHEMA_VERSION = "noncombat-outcome-evidence-pool-v1"
EVIDENCE_GATE_SCHEMA_VERSION = "noncombat-outcome-evidence-gate-v1"
CLOSEOUT_SCHEMA_VERSION = "noncombat-outcome-evidence-closeout-v1"
BLOCKED_ESTIMATE_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-estimate-blocked-v1"
)
FINALIZATION_CLAIM_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-finalization-claim-v1"
)
CALIBRATION_ARTIFACT_RELATIVE_PATH = (
    "reports/noncombat_ope_estimator_calibration_20260714.json"
)
TARGET_POLICY_MODE = "current_deterministic"
PRODUCTION_BOOTSTRAP_REPLICATES = 10_000
PRODUCTION_BOOTSTRAP_CONFIDENCE_LEVEL = Fraction(95, 100)
SLOT_COUNT = 24
GAMES_PER_SLOT = 25
SCHEDULED_ATTEMPTS = SLOT_COUNT * GAMES_PER_SLOT
COMMAND_ARGUMENTS = (
    "--agent",
    "combat_rl",
    "--elite-route",
    "conservative",
    "--max-games",
    str(GAMES_PER_SLOT),
    "--ascension",
    "0",
    "--rl-version",
    "v2",
    "--eval",
)
_STUDY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SUPPORTED_WINDOWS_PYTHON = str(Path(r"D:\anaconda\envs\stsai\python.exe").resolve())
DEFAULT_COMMUNICATION_CONFIG_PATH = str(
    Path(
        r"C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties"
    ).resolve()
)
DEFAULT_CHECKPOINT_ROOT = str(
    Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints").resolve()
)
CHECKPOINT_PATTERNS = ("rl_combat_model_*.pth", "rl_model_*.pth")
RUN_LOCK_IMPLEMENTATION_PATHS = (
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


class OutcomeEvidenceRegistrationError(ValueError):
    """Raised when a study registration is malformed or has been changed."""


class OutcomeEvidenceRunLockError(RuntimeError):
    """Raised when the immutable study run lock cannot be proven valid."""


class OutcomeEvidencePoolError(ValueError):
    """Raised when registered evidence cannot form one canonical pool."""


@dataclass(frozen=True)
class GitSourceSnapshot:
    commit: str
    tracked_clean: bool
    tracked_status: str


@dataclass(frozen=True)
class RegisteredSlot:
    slot_number: int
    session_id: str
    seed: int
    config_path: str
    manifest_path: str
    trace_path: str

    def to_record(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "manifest_path": self.manifest_path,
            "seed": self.seed,
            "session_id": self.session_id,
            "slot_number": self.slot_number,
            "trace_path": self.trace_path,
        }


@dataclass(frozen=True)
class OutcomeEvidenceRegistration:
    study_id: str
    artifact_root: str
    repo_root: str
    seed_base: int
    python_executable: str
    communication_config_path: str
    checkpoint_root: str
    slots: tuple[RegisteredSlot, ...]
    registration_hash: str

    def to_record(self) -> dict[str, Any]:
        record = _registration_body(self)
        record["registration_hash"] = self.registration_hash
        return record


@dataclass(frozen=True)
class RegisteredSessionEvidence:
    slot_number: int
    session_id: str
    run_lock_hash: str
    config_sha256: str
    manifest_sha256: str
    manifest_hash: str
    trace_sha256: str
    marker_trajectory_count: int
    joined_run_files: tuple[str, ...]
    samples: tuple[Mapping[str, Any], ...]
    exclusions: tuple[Mapping[str, Any], ...]
    validation_summary: Mapping[str, Any]
    provenance_verified: bool
    isolation_verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "joined_run_files", tuple(self.joined_run_files))
        object.__setattr__(
            self,
            "samples",
            tuple(_pool_json_copy(sample, "session sample") for sample in self.samples),
        )
        object.__setattr__(
            self,
            "exclusions",
            tuple(
                _pool_json_copy(exclusion, "session exclusion")
                for exclusion in self.exclusions
            ),
        )
        object.__setattr__(
            self,
            "validation_summary",
            _pool_json_copy(self.validation_summary, "validation summary"),
        )


@dataclass(frozen=True)
class RegisteredPool:
    samples: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "samples",
            tuple(_pool_json_copy(sample, "pool sample") for sample in self.samples),
        )
        object.__setattr__(
            self,
            "manifest",
            _pool_json_copy(self.manifest, "pool manifest"),
        )


@dataclass(frozen=True)
class OutcomeEvidenceGateMetrics:
    all_registered_slots_accounted: bool
    global_integrity_stop: bool
    complete_trajectory_count: int
    category_arm_support: Mapping[str, Mapping[str, int]]
    nonzero_weight_trajectory_count: int
    ess_fraction: Fraction
    max_normalized_weight: Fraction
    supported_victory_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "category_arm_support",
            _pool_json_copy(self.category_arm_support, "category arm support"),
        )


def evaluate_outcome_evidence_expansion_gate(
    registration: OutcomeEvidenceRegistration,
    metrics: OutcomeEvidenceGateMetrics,
) -> dict[str, Any]:
    """Apply the pre-registered evidence thresholds with exact arithmetic."""

    validated_registration = validate_registration(registration.to_record())
    normalized = _validate_gate_metrics(metrics)
    thresholds = validated_registration.to_record()["thresholds"]
    minimum_trajectories = int(thresholds["minimum_complete_trajectories"])
    minimum_arm_decisions = int(
        thresholds["minimum_arm_decisions_per_category"]
    )
    minimum_nonzero_fraction = _registered_fraction(
        thresholds["minimum_nonzero_weight_fraction"],
        "minimum_nonzero_weight_fraction",
    )
    minimum_ess_fraction = _registered_fraction(
        thresholds["minimum_ess_fraction"],
        "minimum_ess_fraction",
    )
    maximum_normalized_weight = _registered_fraction(
        thresholds["maximum_normalized_weight"],
        "maximum_normalized_weight",
    )
    minimum_supported_victories = int(
        thresholds["minimum_supported_victories"]
    )

    conditions: dict[str, dict[str, Any]] = {}

    def add_condition(code: str, observed: Any, required: Any, passed: bool) -> None:
        conditions[code] = {
            "observed": _gate_json_value(observed),
            "passed": passed is True,
            "required": _gate_json_value(required),
        }

    add_condition(
        "all_registered_slots_accounted",
        normalized.all_registered_slots_accounted,
        True,
        normalized.all_registered_slots_accounted,
    )
    add_condition(
        "no_global_integrity_stop",
        normalized.global_integrity_stop,
        False,
        not normalized.global_integrity_stop,
    )
    add_condition(
        "minimum_complete_trajectories",
        normalized.complete_trajectory_count,
        minimum_trajectories,
        normalized.complete_trajectory_count >= minimum_trajectories,
    )
    for category in ("card_reward", "shop"):
        for arm in ("baseline", "alternative"):
            code = f"minimum_{category}_{arm}_decisions"
            observed = normalized.category_arm_support[category][arm]
            add_condition(
                code,
                observed,
                minimum_arm_decisions,
                observed >= minimum_arm_decisions,
            )
    required_nonzero_count = _minimum_fraction_count(
        normalized.complete_trajectory_count,
        minimum_nonzero_fraction,
    )
    observed_nonzero_fraction = Fraction(
        normalized.nonzero_weight_trajectory_count,
        normalized.complete_trajectory_count or 1,
    )
    add_condition(
        "minimum_nonzero_weight_fraction",
        {
            "count": normalized.nonzero_weight_trajectory_count,
            "fraction": _pool_fraction_record(observed_nonzero_fraction),
        },
        {
            "minimum_count": required_nonzero_count,
            "fraction": _pool_fraction_record(minimum_nonzero_fraction),
        },
        normalized.nonzero_weight_trajectory_count >= required_nonzero_count,
    )
    add_condition(
        "minimum_ess_fraction",
        normalized.ess_fraction,
        minimum_ess_fraction,
        normalized.ess_fraction >= minimum_ess_fraction,
    )
    add_condition(
        "maximum_normalized_weight",
        normalized.max_normalized_weight,
        maximum_normalized_weight,
        normalized.max_normalized_weight <= maximum_normalized_weight,
    )
    add_condition(
        "minimum_supported_victories",
        normalized.supported_victory_count,
        minimum_supported_victories,
        normalized.supported_victory_count >= minimum_supported_victories,
    )
    blockers = sorted(
        code for code, condition in conditions.items() if not condition["passed"]
    )
    return {
        "blockers": blockers,
        "conditions": conditions,
        "outcome_evidence_expansion_ready": not blockers,
        "schema_version": EVIDENCE_GATE_SCHEMA_VERSION,
        "study_id": validated_registration.study_id,
    }


def build_outcome_evidence_closeout(
    registration: OutcomeEvidenceRegistration,
    *,
    run_lock_hash: str,
    pool_manifest_hash: str | None,
    target_manifest_hash: str | None,
    slot_statuses: Sequence[Mapping[str, Any]],
    metrics: OutcomeEvidenceGateMetrics,
    readiness_artifact: Mapping[str, Any] | None = None,
    estimate_artifact: Mapping[str, Any] | None = None,
    readiness_file_hash: str | None = None,
    estimate_file_hash: str | None = None,
    calibration_file_hash: str | None = None,
    integrity_stop_reason: str | None = None,
) -> dict[str, Any]:
    """Compose one deterministic closeout without widening authority."""

    validated_registration = validate_registration(registration.to_record())
    resolved_run_lock_hash = _pool_sha256(run_lock_hash, "run_lock_hash")
    if metrics.global_integrity_stop:
        blocked_bindings = {
            "calibration_file_hash": calibration_file_hash,
            "estimate_artifact": estimate_artifact,
            "estimate_file_hash": estimate_file_hash,
            "pool_manifest_hash": pool_manifest_hash,
            "readiness_artifact": readiness_artifact,
            "readiness_file_hash": readiness_file_hash,
            "target_manifest_hash": target_manifest_hash,
        }
        bound_names = sorted(
            name for name, value in blocked_bindings.items() if value is not None
        )
        if bound_names:
            raise OutcomeEvidencePoolError(
                "global-stop closeout must not bind pool or OPE artifacts: "
                + ", ".join(bound_names)
            )
        resolved_pool_hash = None
        resolved_target_hash = None
        resolved_readiness_hash = None
        resolved_estimate_hash = None
        resolved_calibration_hash = None
        if not isinstance(integrity_stop_reason, str) or not (
            integrity_stop_reason.strip()
        ):
            raise OutcomeEvidencePoolError(
                "blocked closeout requires an integrity stop reason"
            )
        normalized_stop_reason = integrity_stop_reason.strip()
    else:
        resolved_pool_hash = _pool_sha256(
            pool_manifest_hash,
            "pool_manifest_hash",
        )
        resolved_target_hash = _pool_sha256(
            target_manifest_hash,
            "target_manifest_hash",
        )
        resolved_readiness_hash = _optional_pool_sha256(
            readiness_file_hash,
            "readiness_file_hash",
        )
        resolved_estimate_hash = _optional_pool_sha256(
            estimate_file_hash,
            "estimate_file_hash",
        )
        resolved_calibration_hash = _optional_pool_sha256(
            calibration_file_hash,
            "calibration_file_hash",
        )
        if integrity_stop_reason is not None:
            raise OutcomeEvidencePoolError(
                "non-blocked closeout cannot contain an integrity stop reason"
            )
        normalized_stop_reason = None
    slots = _validate_closeout_slots(validated_registration, slot_statuses)
    lifecycles = {str(slot["terminal_status"]) for slot in slots}
    if metrics.all_registered_slots_accounted and not lifecycles <= {
        "completed",
        "interrupted",
    }:
        raise OutcomeEvidencePoolError(
            "all-slots-accounted metrics contradict closeout lifecycles"
        )
    if not metrics.global_integrity_stop and lifecycles & {
        "blocked",
        "unlaunched",
    }:
        raise OutcomeEvidencePoolError(
            "non-stopped metrics contradict blocked closeout lifecycles"
        )
    gate = evaluate_outcome_evidence_expansion_gate(
        validated_registration,
        metrics,
    )
    readiness = (
        readiness_artifact.get("readiness", {})
        if isinstance(readiness_artifact, Mapping)
        else {}
    )
    dataset_ope_readiness_ready = (
        isinstance(readiness, Mapping)
        and readiness.get("outcome_contract_ready") is True
        and readiness.get("overlap_ready") is True
        and readiness.get("target_policy_ready") is True
    )
    estimate_gates = (
        estimate_artifact.get("gates", {})
        if isinstance(estimate_artifact, Mapping)
        else {}
    )
    ope_estimate_ready = (
        isinstance(estimate_gates, Mapping)
        and estimate_gates.get("ope_estimate_ready") is True
    )
    policy_comparison_ready = (
        isinstance(estimate_gates, Mapping)
        and estimate_gates.get("policy_comparison_ready") is True
    )
    evidence_ready = gate["outcome_evidence_expansion_ready"] is True
    status = (
        "blocked"
        if metrics.global_integrity_stop
        else "ready"
        if evidence_ready
        else "inconclusive"
    )
    closeout = {
        "blockers": list(gate["blockers"]),
        "closeout_hash": None,
        "evidence_gate": gate,
        "gates": {
            "causal_uplift_ready": False,
            "dataset_ope_readiness_ready": dataset_ope_readiness_ready,
            "formal_noncombat_rl_training_ready": False,
            "live_policy_promotion_ready": False,
            "ope_estimate_ready": ope_estimate_ready,
            "outcome_evidence_expansion_ready": evidence_ready,
            "policy_comparison_ready": policy_comparison_ready,
            "reward_design_ready": False,
        },
        "integrity_stop": (
            {"reason": normalized_stop_reason}
            if normalized_stop_reason is not None
            else None
        ),
        "limitations": [
            "Evidence readiness is separate from policy comparison.",
            (
                "No closeout gate authorizes causal claims, training, reward design, "
                "or live promotion."
            ),
        ],
        "registration_hash": validated_registration.registration_hash,
        "run_lock_hash": resolved_run_lock_hash,
        "schema_version": CLOSEOUT_SCHEMA_VERSION,
        "slots": slots,
        "source": {
            "calibration_file_sha256": resolved_calibration_hash,
            "estimate_file_sha256": resolved_estimate_hash,
            "pool_manifest_hash": resolved_pool_hash,
            "readiness_file_sha256": resolved_readiness_hash,
            "target_manifest_hash": resolved_target_hash,
        },
        "status": status,
        "study_id": validated_registration.study_id,
    }
    closeout["closeout_hash"] = _closeout_hash(closeout)
    return closeout


def render_outcome_evidence_closeout_json(closeout: Mapping[str, Any]) -> str:
    _validate_closeout_hash(closeout)
    return _canonical_json(closeout) + "\n"


def render_outcome_evidence_closeout_markdown(
    closeout: Mapping[str, Any],
) -> str:
    _validate_closeout_hash(closeout)
    lines = [
        "# Non-combat outcome-evidence closeout",
        "",
        f"- Study: `{closeout.get('study_id')}`",
        f"- Status: `{closeout.get('status')}`",
    ]
    integrity_stop = closeout.get("integrity_stop")
    if isinstance(integrity_stop, Mapping):
        lines.extend(
            [
                "",
                "## Integrity stop",
                "",
                f"- Reason: {_canonical_json(integrity_stop.get('reason'))}",
            ]
        )
    lines.extend(
        [
            "",
            "## Evidence gate",
            "",
            "| Condition | Observed | Required | Passed |",
            "|---|---|---|---|",
        ]
    )
    conditions = closeout["evidence_gate"]["conditions"]
    for code in sorted(conditions):
        condition = conditions[code]
        lines.append(
            f"| `{code}` | `{_canonical_json(condition['observed'])}` | "
            f"`{_canonical_json(condition['required'])}` | "
            f"{'yes' if condition['passed'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Blockers",
            "",
            *(f"- `{blocker}`" for blocker in closeout["blockers"]),
        ]
    )
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
    for gate, ready in sorted(closeout["gates"].items()):
        lines.append(f"- `{gate}`: `{'true' if ready else 'false'}`")
    return "\n".join(lines) + "\n"


def derive_outcome_evidence_gate_metrics(
    registration: OutcomeEvidenceRegistration,
    *,
    pool: RegisteredPool,
    target_manifest: Mapping[str, Any],
    ledger_snapshot: Mapping[str, Any],
) -> OutcomeEvidenceGateMetrics:
    """Recompute study metrics from the canonical pool and Current target."""

    validated_registration = validate_registration(registration.to_record())
    if not isinstance(pool, RegisteredPool):
        raise OutcomeEvidencePoolError("pool must be a RegisteredPool")
    render_registered_pool_samples(pool)
    render_registered_pool_manifest(pool)
    if pool.manifest.get("registration_hash") != (
        validated_registration.registration_hash
    ):
        raise OutcomeEvidencePoolError("pool registration hash mismatch")
    terminal_by_slot = _pool_terminal_slots(
        validated_registration,
        ledger_snapshot,
    )

    from analysis_scripts.noncombat_ope_readiness import (
        audit_trajectories,
        compute_weight_diagnostics,
        validate_target_policy_manifest,
    )

    source_sample_sha256 = pool.manifest.get("sample_jsonl_sha256")
    _pool_sha256(source_sample_sha256, "sample_jsonl_sha256")
    try:
        validated_target = validate_target_policy_manifest(
            target_manifest,
            pool.samples,
            source_sample_sha256=source_sample_sha256,
        )
        if (
            validated_target.get("construction_mode") != "current_deterministic"
            or validated_target.get("diagnostic_only") is not False
        ):
            raise OutcomeEvidencePoolError(
                "outcome evidence gate requires deterministic Current target"
            )
        audit = audit_trajectories(pool.samples)
        diagnostics = compute_weight_diagnostics(audit, validated_target)
    except OutcomeEvidencePoolError:
        raise
    except Exception as exc:
        raise OutcomeEvidencePoolError(
            f"cannot derive deterministic Current metrics: {exc}"
        ) from exc
    if audit.blocked_trajectories or audit.complete_decision_count != len(
        pool.samples
    ):
        raise OutcomeEvidencePoolError(
            "canonical pool contains an incomplete trajectory"
        )
    if pool.manifest.get("accounting", {}).get(
        "included_trajectory_count"
    ) != audit.complete_trajectory_count:
        raise OutcomeEvidencePoolError("pool trajectory accounting mismatch")

    category_arm_support = {
        category: {
            arm: int(
                diagnostics.category_arm_support.get(category, {})
                .get(arm, {})
                .get("decision_count", 0)
            )
            for arm in ("alternative", "baseline")
        }
        for category in ("card_reward", "shop")
    }
    if pool.manifest.get("aggregate_arm_support") != category_arm_support:
        raise OutcomeEvidencePoolError("pool arm support accounting mismatch")
    weights_by_group = {
        row.group_id: row.weight for row in diagnostics.trajectory_weights
    }
    supported_victories = sum(
        trajectory.outcome.victory
        and weights_by_group.get(trajectory.group_id, Fraction(0, 1)) > 0
        for trajectory in audit.trajectories
    )
    pool_slots = pool.manifest.get("slots")
    all_slots_accounted = (
        isinstance(pool_slots, Sequence)
        and len(pool_slots) == len(validated_registration.slots)
        and len(terminal_by_slot) == len(validated_registration.slots)
    )
    return OutcomeEvidenceGateMetrics(
        all_registered_slots_accounted=all_slots_accounted,
        global_integrity_stop=False,
        complete_trajectory_count=audit.complete_trajectory_count,
        category_arm_support=category_arm_support,
        nonzero_weight_trajectory_count=diagnostics.nonzero_weight_count,
        ess_fraction=diagnostics.ess_fraction,
        max_normalized_weight=diagnostics.max_normalized_weight,
        supported_victory_count=int(supported_victories),
    )


def finalize_registered_integrity_stop(
    registration: OutcomeEvidenceRegistration,
    *,
    run_lock_hash: str,
    ledger_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Publish a blocked closeout without pooling or reading outcomes."""

    validated_registration = validate_registration(registration.to_record())
    resolved_run_lock_hash = _pool_sha256(run_lock_hash, "run_lock_hash")
    slot_statuses, stop_reason = _blocked_closeout_slots(
        validated_registration,
        ledger_snapshot,
    )
    metrics = OutcomeEvidenceGateMetrics(
        all_registered_slots_accounted=False,
        global_integrity_stop=True,
        complete_trajectory_count=0,
        category_arm_support={
            "card_reward": {"alternative": 0, "baseline": 0},
            "shop": {"alternative": 0, "baseline": 0},
        },
        nonzero_weight_trajectory_count=0,
        ess_fraction=Fraction(0, 1),
        max_normalized_weight=Fraction(0, 1),
        supported_victory_count=0,
    )
    closeout = build_outcome_evidence_closeout(
        validated_registration,
        run_lock_hash=resolved_run_lock_hash,
        pool_manifest_hash=None,
        target_manifest_hash=None,
        slot_statuses=slot_statuses,
        metrics=metrics,
        integrity_stop_reason=stop_reason,
    )
    output_rules = validated_registration.to_record()["output_rules"]
    all_output_paths = _finalization_output_paths(
        validated_registration,
        output_rules,
    )
    existing_outputs = [
        path for path in all_output_paths.values() if path.exists()
    ]
    if existing_outputs:
        raise OutcomeEvidencePoolError(
            "study is already finalized or has final artifacts: "
            + ", ".join(sorted(path.name for path in existing_outputs))
        )
    output_paths = {
        name: all_output_paths[name]
        for name in ("closeout_json", "closeout_markdown")
    }
    payloads = {
        "closeout_json": render_outcome_evidence_closeout_json(closeout),
        "closeout_markdown": render_outcome_evidence_closeout_markdown(closeout),
    }

    from analysis_scripts.noncombat_ope_readiness import (
        _replace_files_transactionally,
    )

    _publish_finalization_claim_once(
        all_output_paths["finalization_claim"],
        _finalization_claim_text(
            validated_registration,
            run_lock_hash=resolved_run_lock_hash,
            mode="integrity_stop",
        ),
    )
    _replace_files_transactionally(
        tuple(
            (output_paths[name], payloads[name].encode("utf-8"))
            for name in sorted(payloads)
        )
    )
    return {
        "closeout": closeout,
        "paths": {
            name: str(path)
            for name, path in sorted(output_paths.items())
        },
        "study_id": validated_registration.study_id,
    }


def finalize_registered_outcome_evidence(
    registration: OutcomeEvidenceRegistration,
    *,
    run_lock_hash: str,
    ledger_snapshot: Mapping[str, Any],
    pool: RegisteredPool,
) -> dict[str, Any]:
    """Run the frozen production OPE pipeline and publish one closeout."""

    validated_registration = validate_registration(registration.to_record())
    resolved_run_lock_hash = _pool_sha256(run_lock_hash, "run_lock_hash")
    _pool_terminal_slots(validated_registration, ledger_snapshot)
    registration_record = validated_registration.to_record()
    analysis_rules = registration_record["analysis_rules"]
    output_rules = registration_record["output_rules"]
    output_paths = _finalization_output_paths(
        validated_registration,
        output_rules,
    )
    existing_outputs = [path for path in output_paths.values() if path.exists()]
    if existing_outputs:
        raise OutcomeEvidencePoolError(
            "study is already finalized or has final artifacts: "
            + ", ".join(sorted(path.name for path in existing_outputs))
        )
    sample_text = render_registered_pool_samples(pool)
    pool_manifest_text = render_registered_pool_manifest(pool)
    if pool.manifest.get("run_lock_hash") != resolved_run_lock_hash:
        raise OutcomeEvidencePoolError("pool run lock hash mismatch")
    if (
        pool.manifest.get("registration_hash")
        != validated_registration.registration_hash
    ):
        raise OutcomeEvidencePoolError("pool registration hash mismatch")

    from analysis_scripts import noncombat_ope_estimate_artifacts as estimate_artifacts
    from analysis_scripts import noncombat_ope_estimation as estimation
    from analysis_scripts import noncombat_ope_readiness as readiness

    confidence_level = _registered_fraction(
        analysis_rules["bootstrap_confidence_level"],
        "bootstrap_confidence_level",
    )
    replicate_count = int(analysis_rules["bootstrap_replicates"])
    if (
        analysis_rules["target_policy_mode"] != TARGET_POLICY_MODE
        or replicate_count != PRODUCTION_BOOTSTRAP_REPLICATES
        or confidence_level != PRODUCTION_BOOTSTRAP_CONFIDENCE_LEVEL
        or replicate_count != estimate_artifacts.PRODUCTION_BOOTSTRAP_REPLICATES
        or confidence_level != estimate_artifacts.PRODUCTION_CONFIDENCE_LEVEL
    ):
        raise OutcomeEvidencePoolError("registered production OPE contract drifted")

    repo_root = Path(validated_registration.repo_root).resolve()
    calibration_path = (
        repo_root / analysis_rules["calibration_artifact_relative_path"]
    ).resolve()
    try:
        calibration_path.relative_to(repo_root)
    except ValueError as exc:
        raise OutcomeEvidencePoolError(
            "calibration artifact escapes registered repository"
        ) from exc
    try:
        calibration_bytes = calibration_path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidencePoolError(
            f"cannot read registered calibration artifact: {exc}"
        ) from exc

    source_sample_sha256 = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()
    try:
        target_manifest = readiness.build_current_deterministic_manifest(
            pool.samples,
            source_sample_sha256=source_sample_sha256,
        )
        target_text = readiness.render_target_manifest_json(target_manifest)
        with tempfile.TemporaryDirectory(
            prefix="noncombat-outcome-evidence-finalize-"
        ) as temporary_root:
            stage_root = Path(temporary_root)
            sample_path = stage_root / output_rules["pool_samples_filename"]
            target_path = stage_root / output_rules["target_manifest_filename"]
            readiness_path = stage_root / output_rules["readiness_json_filename"]
            sample_path.write_bytes(sample_text.encode("utf-8"))
            target_path.write_bytes(target_text.encode("utf-8"))

            readiness_artifact = readiness.build_readiness_artifact(
                sample_path,
                target_manifest,
            )
            readiness_json = readiness.render_readiness_json(readiness_artifact)
            readiness_markdown = readiness.render_readiness_markdown(
                readiness_artifact
            )
            readiness_path.write_bytes(readiness_json.encode("utf-8"))

            try:
                bundle = estimation.load_estimator_bundle(
                    sample_path=sample_path,
                    target_manifest_path=target_path,
                    readiness_path=readiness_path,
                    calibration_path=calibration_path,
                )
            except estimation.EstimatorInputError as exc:
                readiness_gates = readiness_artifact.get("readiness")
                recognized_overlap_blocker = (
                    isinstance(readiness_gates, Mapping)
                    and readiness_gates.get("overlap_ready") is False
                    and str(exc)
                    == "independent readiness replay found overlap blockers"
                )
                if not recognized_overlap_blocker:
                    raise
                estimate_artifact = _build_blocked_estimate_artifact(
                    readiness_artifact=readiness_artifact,
                    sample_bytes=sample_text.encode("utf-8"),
                    target_bytes=target_text.encode("utf-8"),
                    readiness_bytes=readiness_json.encode("utf-8"),
                    calibration_bytes=calibration_bytes,
                    bootstrap_seed=analysis_rules["bootstrap_seed"],
                    replicate_count=replicate_count,
                    confidence_level=confidence_level,
                    estimator_implementation_hash=(
                        estimation.estimator_implementation_sha256()
                    ),
                    estimate_implementation_hash=(
                        estimate_artifacts.estimate_artifact_implementation_sha256()
                    ),
                )
                estimate_json = _canonical_json(estimate_artifact) + "\n"
                estimate_markdown = _render_blocked_estimate_markdown(
                    estimate_artifact
                )
            else:
                estimate_artifact = estimate_artifacts.build_estimate_artifact(
                    bundle,
                    seed=analysis_rules["bootstrap_seed"],
                    replicate_count=replicate_count,
                    confidence_level=confidence_level,
                )
                estimate_json = estimate_artifacts.render_estimate_json(
                    estimate_artifact
                )
                estimate_markdown = estimate_artifacts.render_estimate_markdown(
                    estimate_artifact
                )
            _reject_downstream_authority(
                readiness_artifact,
                estimate_artifact,
            )
    except OutcomeEvidencePoolError:
        raise
    except Exception as exc:
        raise OutcomeEvidencePoolError(
            f"registered production OPE finalization failed: {exc}"
        ) from exc

    metrics = derive_outcome_evidence_gate_metrics(
        validated_registration,
        pool=pool,
        target_manifest=target_manifest,
        ledger_snapshot=ledger_snapshot,
    )
    slot_statuses = [
        {
            "session_id": terminal["session_id"],
            "slot_number": terminal["slot_number"],
            "terminal_status": terminal["terminal_status"],
        }
        for terminal in ledger_snapshot["terminal_slots"]
    ]
    closeout = build_outcome_evidence_closeout(
        validated_registration,
        run_lock_hash=resolved_run_lock_hash,
        pool_manifest_hash=str(pool.manifest["pool_manifest_hash"]),
        target_manifest_hash=str(target_manifest["manifest_hash"]),
        slot_statuses=slot_statuses,
        metrics=metrics,
        readiness_artifact=readiness_artifact,
        estimate_artifact=estimate_artifact,
        readiness_file_hash=hashlib.sha256(
            readiness_json.encode("utf-8")
        ).hexdigest(),
        estimate_file_hash=hashlib.sha256(
            estimate_json.encode("utf-8")
        ).hexdigest(),
        calibration_file_hash=hashlib.sha256(calibration_bytes).hexdigest(),
    )
    closeout_json = render_outcome_evidence_closeout_json(closeout)
    closeout_markdown = render_outcome_evidence_closeout_markdown(closeout)
    payloads = {
        "closeout_json": closeout_json,
        "closeout_markdown": closeout_markdown,
        "estimate_json": estimate_json,
        "estimate_markdown": estimate_markdown,
        "pool_manifest": pool_manifest_text,
        "pool_samples": sample_text,
        "readiness_json": readiness_json,
        "readiness_markdown": readiness_markdown,
        "target_manifest": target_text,
    }
    _publish_finalization_claim_once(
        output_paths["finalization_claim"],
        _finalization_claim_text(
            validated_registration,
            run_lock_hash=resolved_run_lock_hash,
            mode="complete",
        ),
    )
    readiness._replace_files_transactionally(
        tuple(
            (output_paths[name], payloads[name].encode("utf-8"))
            for name in sorted(payloads)
        )
    )
    return {
        "closeout": closeout,
        "paths": {
            name: str(path)
            for name, path in sorted(output_paths.items())
        },
        "study_id": validated_registration.study_id,
    }


def build_registered_pool(
    registration: OutcomeEvidenceRegistration,
    *,
    run_lock_hash: str,
    ledger_snapshot: Mapping[str, Any],
    sessions: Sequence[RegisteredSessionEvidence],
) -> RegisteredPool:
    """Build one deterministic pool from every terminal registered slot."""

    validated_registration = validate_registration(registration.to_record())
    expected_run_lock_hash = _pool_sha256(run_lock_hash, "run_lock_hash")
    terminal_by_slot = _pool_terminal_slots(
        validated_registration,
        ledger_snapshot,
    )
    evidence_by_slot = _pool_session_set(validated_registration, sessions)

    from analysis_scripts.noncombat_exploration_evidence import (
        behavior_evidence_status,
    )
    from analysis_scripts.noncombat_ope_readiness import audit_trajectories

    sample_ids: set[str] = set()
    run_owners: dict[str, int] = {}
    included_samples: list[dict[str, Any]] = []
    excluded_trajectories: list[dict[str, Any]] = []
    slot_records: list[dict[str, Any]] = []

    for slot in validated_registration.slots:
        evidence = evidence_by_slot[slot.slot_number]
        terminal = terminal_by_slot[slot.slot_number]
        _validate_registered_session_evidence(
            evidence,
            slot=slot,
            terminal=terminal,
            run_lock_hash=expected_run_lock_hash,
        )
        joined_run_files = tuple(
            sorted(evidence.joined_run_files, key=_run_file_sort_key)
        )
        for run_file in joined_run_files:
            previous_slot = run_owners.setdefault(run_file, slot.slot_number)
            if previous_slot != slot.slot_number:
                raise OutcomeEvidencePoolError(
                    "duplicate trajectory run across registered sessions: "
                    f"{run_file}"
                )

        by_trajectory_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for raw_sample in evidence.samples:
            sample = _pool_json_copy(raw_sample, "session sample")
            sample_id = sample.get("sample_id")
            if not isinstance(sample_id, str) or not sample_id:
                raise OutcomeEvidencePoolError("session sample_id is invalid")
            if sample_id in sample_ids:
                raise OutcomeEvidencePoolError(f"duplicate sample_id: {sample_id}")
            sample_ids.add(sample_id)
            exploration = sample.get("exploration")
            if not isinstance(exploration, Mapping) or exploration.get(
                "session_id"
            ) != slot.session_id:
                raise OutcomeEvidencePoolError(
                    f"slot {slot.slot_number}: sample session identity mismatch"
                )
            status = behavior_evidence_status(sample)
            if status.get("verified") is not True:
                raise OutcomeEvidencePoolError(
                    f"{sample_id}: behavior evidence is not verified: "
                    f"{status.get('reason')}"
                )
            trajectory_session_id = sample.get("trajectory_session_id")
            if not isinstance(trajectory_session_id, str) or not trajectory_session_id:
                raise OutcomeEvidencePoolError(
                    f"{sample_id}: trajectory_session_id is invalid"
                )
            by_trajectory_session[trajectory_session_id].append(sample)

        slot_included: list[dict[str, Any]] = []
        unattributed_sample_groups: list[dict[str, Any]] = []
        for trajectory_session_id in sorted(by_trajectory_session):
            rows = by_trajectory_session[trajectory_session_id]
            matched = all(_sample_has_registered_outcome(row) for row in rows)
            group_ids = {str(row.get("trajectory_group_id")) for row in rows}
            if not matched or len(group_ids) != 1:
                unattributed_sample_groups.append(
                    {
                        "decision_count": len(rows),
                        "reason": (
                            "outcome_join_incomplete"
                            if not matched
                            else "trajectory_group_conflict"
                        ),
                        "trajectory_session_id": trajectory_session_id,
                    }
                )
                continue
            group_id = next(iter(group_ids))
            run_file = f"{group_id.removeprefix('run:')}.run"
            if run_file not in joined_run_files:
                raise OutcomeEvidencePoolError(
                    f"{trajectory_session_id}: matched outcome is outside the "
                    "registered conservative run join"
                )
            slot_included.extend(rows)

        included_run_files = {
            str(sample["outcome"]["run_file"]) for sample in slot_included
        }
        for run_file in joined_run_files:
            if run_file not in included_run_files:
                excluded_trajectories.append(
                    {
                        "reason": "no_complete_confirmed_decision",
                        "run_file": run_file,
                        "session_id": slot.session_id,
                        "slot_number": slot.slot_number,
                        "trajectory_session_id": None,
                    }
                )
        unresolved_join_count = evidence.marker_trajectory_count - len(
            joined_run_files
        )
        if unresolved_join_count:
            excluded_trajectories.append(
                {
                    "count": unresolved_join_count,
                    "reason": "run_join_missing_or_ambiguous",
                    "run_file": None,
                    "session_id": slot.session_id,
                    "slot_number": slot.slot_number,
                    "trajectory_session_id": None,
                }
            )

        included_samples.extend(slot_included)
        slot_records.append(
            {
                "artifact_hashes": {
                    "config_sha256": evidence.config_sha256,
                    "manifest_hash": evidence.manifest_hash,
                    "manifest_sha256": evidence.manifest_sha256,
                    "trace_sha256": evidence.trace_sha256,
                },
                "export_exclusions": [
                    _pool_json_copy(row, "export exclusion")
                    for row in sorted(
                        evidence.exclusions,
                        key=lambda row: _canonical_json(row),
                    )
                ],
                "included_decision_count": len(slot_included),
                "included_trajectory_count": len(included_run_files),
                "excluded_trajectory_count": (
                    evidence.marker_trajectory_count - len(included_run_files)
                ),
                "joined_run_count": len(joined_run_files),
                "marker_trajectory_count": evidence.marker_trajectory_count,
                "process_exit_code": terminal.get("process_exit_code"),
                "session_id": slot.session_id,
                "slot_number": slot.slot_number,
                "terminal_status": terminal.get("terminal_status"),
                "unattributed_sample_groups": unattributed_sample_groups,
                "unresolved_join_count": unresolved_join_count,
            }
        )

    ordered_samples = tuple(sorted(included_samples, key=_pool_sample_sort_key))
    try:
        audit = audit_trajectories(ordered_samples)
    except Exception as exc:
        raise OutcomeEvidencePoolError(f"trajectory audit failed: {exc}") from exc
    if audit.blocked_trajectories:
        reasons = sorted(
            {
                reason
                for blocked in audit.blocked_trajectories
                for reason in blocked.reasons
            }
        )
        raise OutcomeEvidencePoolError(
            "terminal outcome conflict or incomplete trajectory: "
            + ",".join(reasons)
        )
    if audit.complete_decision_count != len(ordered_samples):
        raise OutcomeEvidencePoolError("selective pool omission detected")

    support = Counter(
        (
            str(sample.get("category")),
            str(sample["exploration"].get("selected_arm")),
        )
        for sample in ordered_samples
    )
    aggregate_support = {
        category: {
            arm: support[(category, arm)]
            for arm in ("alternative", "baseline")
        }
        for category in ("card_reward", "shop")
    }
    sample_text = _render_pool_sample_rows(ordered_samples)
    marker_trajectory_count = sum(
        record["marker_trajectory_count"] for record in slot_records
    )
    excluded_trajectory_count = (
        marker_trajectory_count - audit.complete_trajectory_count
    )
    if sum(int(row.get("count", 1)) for row in excluded_trajectories) != (
        excluded_trajectory_count
    ):
        raise OutcomeEvidencePoolError(
            "pool trajectory exclusion accounting does not close"
        )
    manifest = {
        "accounting": {
            "conservative_joined_run_count": sum(
                record["joined_run_count"] for record in slot_records
            ),
            "excluded_trajectory_count": excluded_trajectory_count,
            "included_decision_count": len(ordered_samples),
            "included_trajectory_count": audit.complete_trajectory_count,
            "marker_trajectory_count": marker_trajectory_count,
            "registered_slot_count": len(slot_records),
        },
        "aggregate_arm_support": aggregate_support,
        "excluded_trajectories": sorted(
            excluded_trajectories,
            key=lambda row: (
                int(row["slot_number"]),
                str(row.get("run_file") or ""),
                str(row.get("trajectory_session_id") or ""),
                str(row["reason"]),
            ),
        ),
        "included_trajectories": [
            {
                "decision_count": len(trajectory.decisions),
                "group_id": trajectory.group_id,
                "run_file": trajectory.outcome.run_file,
                "session_id": str(
                    trajectory.decisions[0]["exploration"]["session_id"]
                ),
                "trajectory_session_id": trajectory.trajectory_session_id,
            }
            for trajectory in audit.trajectories
        ],
        "pool_manifest_hash": None,
        "registration_hash": validated_registration.registration_hash,
        "run_lock_hash": expected_run_lock_hash,
        "sample_jsonl_sha256": hashlib.sha256(
            sample_text.encode("utf-8")
        ).hexdigest(),
        "schema_version": POOL_SCHEMA_VERSION,
        "slots": slot_records,
        "study_id": validated_registration.study_id,
    }
    manifest["pool_manifest_hash"] = _pool_manifest_hash(manifest)
    return RegisteredPool(samples=ordered_samples, manifest=manifest)


def render_registered_pool_samples(pool: RegisteredPool) -> str:
    if not isinstance(pool, RegisteredPool):
        raise OutcomeEvidencePoolError("pool must be a RegisteredPool")
    rendered = _render_pool_sample_rows(pool.samples)
    expected = pool.manifest.get("sample_jsonl_sha256")
    if hashlib.sha256(rendered.encode("utf-8")).hexdigest() != expected:
        raise OutcomeEvidencePoolError("pool sample hash mismatch")
    return rendered


def render_registered_pool_manifest(pool: RegisteredPool) -> str:
    if not isinstance(pool, RegisteredPool):
        raise OutcomeEvidencePoolError("pool must be a RegisteredPool")
    supplied_hash = pool.manifest.get("pool_manifest_hash")
    if supplied_hash != _pool_manifest_hash(pool.manifest):
        raise OutcomeEvidencePoolError("pool manifest hash mismatch")
    return _canonical_json(pool.manifest) + "\n"


def conservative_marker_run_pairs(
    *,
    marker_timestamps: Sequence[int],
    run_timestamps: Sequence[int],
    tolerance_seconds: int = 10,
) -> tuple[tuple[int, int], ...]:
    """Return only mutually unique marker-index/run-timestamp pairs."""

    if type(tolerance_seconds) is not int or tolerance_seconds < 0:
        raise OutcomeEvidencePoolError(
            "tolerance_seconds must be a nonnegative integer"
        )
    markers = tuple(
        _pool_timestamp(value, "marker timestamp") for value in marker_timestamps
    )
    runs = tuple(_pool_timestamp(value, "run timestamp") for value in run_timestamps)
    marker_candidates = [
        tuple(
            run_index
            for run_index, run_timestamp in enumerate(runs)
            if 0 <= marker_timestamp - run_timestamp <= tolerance_seconds
        )
        for marker_timestamp in markers
    ]
    run_candidate_counts = Counter(
        run_index
        for candidates in marker_candidates
        for run_index in candidates
    )
    pairs = []
    for marker_index, candidates in enumerate(marker_candidates):
        if len(candidates) != 1:
            continue
        run_index = candidates[0]
        if run_candidate_counts[run_index] != 1:
            continue
        pairs.append((marker_index, runs[run_index]))
    return tuple(pairs)


def manifest_isolation_matches_run_lock(
    manifest: Mapping[str, Any],
    run_lock: Mapping[str, Any],
) -> bool:
    """Compare one runtime pre-session snapshot to the registered live lock."""

    pre_session = manifest.get("pre_session_isolation_hashes")
    communication = run_lock.get("communication_mod")
    checkpoints = run_lock.get("checkpoints")
    if not all(
        isinstance(value, Mapping)
        for value in (pre_session, communication, checkpoints)
    ):
        return False

    communication_path = communication.get("path")
    communication_semantic_hash = communication.get("semantic_sha256")
    if not isinstance(communication_path, str) or not isinstance(
        communication_semantic_hash, str
    ):
        return False
    pre_by_path = {
        str(path).casefold(): value
        for path, value in pre_session.items()
        if isinstance(path, str) and isinstance(value, Mapping)
    }
    observed_communication = pre_by_path.get(communication_path.casefold())
    if (
        not isinstance(observed_communication, Mapping)
        or observed_communication.get("semantic_sha256")
        != communication_semantic_hash
    ):
        return False

    root_value = checkpoints.get("root")
    patterns = checkpoints.get("patterns")
    files = checkpoints.get("files")
    if (
        not isinstance(root_value, str)
        or isinstance(patterns, (str, bytes))
        or not isinstance(patterns, Sequence)
        or not all(isinstance(pattern, str) and pattern for pattern in patterns)
        or isinstance(files, (str, bytes))
        or not isinstance(files, Sequence)
    ):
        return False
    checkpoint_root = Path(root_value).resolve()
    expected_files: dict[str, Mapping[str, Any]] = {}
    for record in files:
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            return False
        expected_files[str(Path(record["path"]).resolve()).casefold()] = record
    if not expected_files:
        return False

    observed_checkpoint_paths = set()
    for raw_path in pre_session:
        if not isinstance(raw_path, str):
            continue
        path = Path(raw_path).resolve()
        try:
            path.relative_to(checkpoint_root)
        except ValueError:
            continue
        if any(fnmatch.fnmatchcase(path.name, pattern) for pattern in patterns):
            observed_checkpoint_paths.add(str(path).casefold())
    if observed_checkpoint_paths != set(expected_files):
        return False
    for normalized_path, expected in expected_files.items():
        observed = pre_by_path.get(normalized_path)
        if not isinstance(observed, Mapping):
            return False
        if (
            observed.get("sha256") != expected.get("sha256")
            or observed.get("size") != expected.get("size")
        ):
            return False
    return True


def collect_registered_session_evidence(
    registration: OutcomeEvidenceRegistration,
    *,
    run_lock: Mapping[str, Any],
    ledger_snapshot: Mapping[str, Any],
    marker_path: Path | str | None = None,
    runs_root: Path | str | None = None,
) -> tuple[RegisteredSessionEvidence, ...]:
    """Replay every registered session against one global conservative run join."""

    validated_registration = validate_registration(registration.to_record())
    binding = _pool_run_lock_binding(validated_registration, run_lock)
    terminal_by_slot = _pool_terminal_slots(
        validated_registration,
        ledger_snapshot,
    )
    game_root = Path(validated_registration.checkpoint_root).resolve().parent
    resolved_runs_root = (
        Path(runs_root).resolve() if runs_root is not None else game_root / "runs"
    )
    resolved_marker_path = (
        Path(marker_path).resolve()
        if marker_path is not None
        else resolved_runs_root / "ai_games.txt"
    )
    markers = _load_pool_markers(resolved_marker_path)
    run_timestamps = sorted(
        int(path.stem)
        for path in (resolved_runs_root / "IRONCLAD").glob("*.run")
        if path.stem.isdigit()
    )
    joined_by_marker = dict(
        conservative_marker_run_pairs(
            marker_timestamps=markers,
            run_timestamps=run_timestamps,
        )
    )

    from analysis_scripts.noncombat_exploration_evidence import (
        export_confirmed_exploration_samples,
    )
    from analysis_scripts.noncombat_rl_decision_loop import load_run_outcomes

    sessions = []
    for slot in validated_registration.slots:
        terminal = terminal_by_slot[slot.slot_number]
        marker_start = int(terminal["marker_start_count"])
        marker_end = int(terminal["marker_end_count"])
        if marker_end > len(markers):
            raise OutcomeEvidencePoolError(
                f"slot {slot.slot_number}: marker slice exceeds marker file"
            )
        joined_run_files = tuple(
            f"{joined_by_marker[index]}.run"
            for index in range(marker_start, marker_end)
            if index in joined_by_marker
        )
        manifest_path = Path(slot.manifest_path)
        manifest = _load_pool_json_object(manifest_path, "session manifest")
        _validate_pool_manifest_binding(
            validated_registration,
            slot=slot,
            manifest=manifest,
            run_lock=run_lock,
            binding=binding,
        )
        pre_isolation = manifest.get("pre_session_isolation_hashes")
        if not isinstance(pre_isolation, Mapping):
            raise OutcomeEvidencePoolError(
                f"slot {slot.slot_number}: pre-session isolation snapshot is invalid"
            )
        outcomes = load_run_outcomes(
            resolved_runs_root,
            character="IRONCLAD",
            limit=0,
            ai_markers_path=resolved_marker_path,
            run_files=joined_run_files,
        )
        export = export_confirmed_exploration_samples(
            Path(slot.trace_path),
            manifest_path,
            outcomes=outcomes,
            expected_pre_isolation_hashes=pre_isolation,
            expected_source_commit=binding["source_commit"],
        )
        if _pool_json_copy(export.manifest, "export manifest") != manifest:
            raise OutcomeEvidencePoolError(
                f"slot {slot.slot_number}: exporter manifest changed during replay"
            )
        sessions.append(
            RegisteredSessionEvidence(
                slot_number=slot.slot_number,
                session_id=slot.session_id,
                run_lock_hash=binding["run_lock_hash"],
                config_sha256=_pool_file_sha256(
                    Path(slot.config_path), "slot config"
                ),
                manifest_sha256=_pool_file_sha256(
                    manifest_path, "session manifest"
                ),
                manifest_hash=_pool_sha256(
                    manifest.get("manifest_hash"), "manifest_hash"
                ),
                trace_sha256=_pool_file_sha256(
                    Path(slot.trace_path), "session trace"
                ),
                marker_trajectory_count=int(terminal["complete_trajectories"]),
                joined_run_files=joined_run_files,
                samples=tuple(export.samples),
                exclusions=tuple(export.exclusions),
                validation_summary=export.validation_summary,
                provenance_verified=export.provenance_verified is True,
                isolation_verified=manifest_isolation_matches_run_lock(
                    manifest,
                    run_lock,
                ),
            )
        )
    return tuple(sessions)


def build_registration(
    *,
    study_id: str,
    artifact_root: Path | str,
    repo_root: Path | str,
    seed_base: int,
    python_executable: Path | str,
    communication_config_path: Path | str = DEFAULT_COMMUNICATION_CONFIG_PATH,
    checkpoint_root: Path | str = DEFAULT_CHECKPOINT_ROOT,
) -> OutcomeEvidenceRegistration:
    """Build the one fixed 24-by-25 registration used by this study."""

    if not isinstance(study_id, str) or not _STUDY_ID_PATTERN.fullmatch(study_id):
        raise OutcomeEvidenceRegistrationError(
            "study_id must contain only lowercase letters, digits, and hyphens"
        )
    _require_exact_int(seed_base, "seed_base")

    normalized_artifact_root = str(Path(artifact_root).resolve())
    normalized_repo_root = str(Path(repo_root).resolve())
    normalized_python = str(Path(python_executable).resolve())
    normalized_communication_config = str(Path(communication_config_path).resolve())
    normalized_checkpoint_root = str(Path(checkpoint_root).resolve())

    slots = tuple(
        _build_slot(
            study_id=study_id,
            artifact_root=Path(normalized_artifact_root),
            seed_base=seed_base,
            slot_number=slot_number,
        )
        for slot_number in range(1, SLOT_COUNT + 1)
    )
    registration = OutcomeEvidenceRegistration(
        study_id=study_id,
        artifact_root=normalized_artifact_root,
        repo_root=normalized_repo_root,
        seed_base=seed_base,
        python_executable=normalized_python,
        communication_config_path=normalized_communication_config,
        checkpoint_root=normalized_checkpoint_root,
        slots=slots,
        registration_hash="",
    )
    digest = _hash_registration_record(_record_with_null_hash(registration))
    return replace(registration, registration_hash=digest)


def canonical_registration_hash(record: Mapping[str, Any]) -> str:
    """Return the canonical hash after replacing the self-hash with null."""

    if not isinstance(record, Mapping):
        raise OutcomeEvidenceRegistrationError("registration must be a JSON object")
    hash_input = dict(record)
    hash_input["registration_hash"] = None
    return _hash_registration_record(hash_input)


def validate_registration(
    payload: Mapping[str, Any],
) -> OutcomeEvidenceRegistration:
    """Validate all registered values before checking the canonical hash."""

    record = _require_mapping(payload, "registration")
    expected_top_level = {
        "analysis_rules",
        "artifact_root",
        "behavior",
        "blinding_rules",
        "command",
        "games_per_slot",
        "integrity_rules",
        "output_rules",
        "registration_hash",
        "repo_root",
        "scheduled_attempts",
        "schema_version",
        "seed_base",
        "slot_count",
        "slots",
        "study_id",
        "thresholds",
    }
    _require_exact_fields(record, expected_top_level, "registration")

    study_id = _require_string(record["study_id"], "study_id")
    artifact_root = _require_string(record["artifact_root"], "artifact_root")
    repo_root = _require_string(record["repo_root"], "repo_root")
    seed_base = _require_exact_int(record["seed_base"], "seed_base")
    command = _require_mapping(record["command"], "command")
    _require_exact_fields(
        command, {"arguments", "main_path", "python_executable"}, "command"
    )
    python_executable = _require_string(
        command["python_executable"], "command.python_executable"
    )
    integrity_rules = _require_mapping(record["integrity_rules"], "integrity_rules")
    communication_config_path = _require_string(
        integrity_rules.get("communication_config_path"),
        "integrity_rules.communication_config_path",
    )
    checkpoint_inventory = _require_mapping(
        integrity_rules.get("checkpoint_inventory"),
        "integrity_rules.checkpoint_inventory",
    )
    checkpoint_root = _require_string(
        checkpoint_inventory.get("root"),
        "integrity_rules.checkpoint_inventory.root",
    )

    expected = build_registration(
        study_id=study_id,
        artifact_root=artifact_root,
        repo_root=repo_root,
        seed_base=seed_base,
        python_executable=python_executable,
        communication_config_path=communication_config_path,
        checkpoint_root=checkpoint_root,
    )
    expected_record = expected.to_record()

    for key in sorted(expected_top_level - {"registration_hash"}):
        _assert_exact_value(record[key], expected_record[key], key)

    supplied_hash = _require_string(record["registration_hash"], "registration_hash")
    if not _SHA256_PATTERN.fullmatch(supplied_hash):
        raise OutcomeEvidenceRegistrationError(
            "registration_hash must be a lowercase SHA-256 hash"
        )
    canonical_hash = canonical_registration_hash(record)
    if supplied_hash != canonical_hash:
        raise OutcomeEvidenceRegistrationError("registration hash mismatch")
    return expected


def render_registration_json(
    registration: OutcomeEvidenceRegistration | Mapping[str, Any],
) -> str:
    """Render canonical UTF-8 JSON with a single LF terminator."""

    if isinstance(registration, OutcomeEvidenceRegistration):
        validated = validate_registration(registration.to_record())
    else:
        validated = validate_registration(registration)
    return _canonical_json(validated.to_record()) + "\n"


def load_registration(path: Path | str) -> OutcomeEvidenceRegistration:
    """Load strict JSON, rejecting duplicate keys and non-standard constants."""

    registration_path = Path(path)
    try:
        text = registration_path.read_text(encoding="utf-8")
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except OutcomeEvidenceRegistrationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OutcomeEvidenceRegistrationError(
            f"cannot load registration {registration_path}: {exc}"
        ) from exc
    return validate_registration(payload)


def create_run_lock(
    *,
    registration_path: Path | str,
    lock_path: Path | str,
    repo_root: Path | str,
    child_command: Sequence[str],
    created_unix_ns: int | None = None,
) -> dict[str, Any]:
    """Atomically bind a committed registration to one clean source snapshot."""

    resolved_lock_path = Path(lock_path).resolve()
    if resolved_lock_path.exists():
        raise OutcomeEvidenceRunLockError(
            f"run lock already exists for this study: {resolved_lock_path}"
        )
    registration, registration_file_sha256, source = _validate_run_lock_inputs(
        registration_path=registration_path,
        repo_root=repo_root,
        child_command=child_command,
    )
    expected_lock_path = Path(registration.artifact_root) / "run-lock.json"
    if resolved_lock_path != expected_lock_path.resolve():
        raise OutcomeEvidenceRunLockError(
            f"lock path differs from registered output: {resolved_lock_path}"
        )
    if created_unix_ns is None:
        created_unix_ns = time.time_ns()
    if type(created_unix_ns) is not int or created_unix_ns <= 0:
        raise OutcomeEvidenceRunLockError("created_unix_ns must be a positive integer")

    command = _normalize_child_command(child_command)
    record = {
        "checkpoints": _checkpoint_inventory_snapshot(
            Path(registration.checkpoint_root)
        ),
        "command": command,
        "communication_mod": _communication_mod_snapshot(
            Path(registration.communication_config_path)
        ),
        "created_unix_ns": created_unix_ns,
        "implementation_files": _implementation_snapshot(Path(repo_root)),
        "python_executable": registration.python_executable,
        "registration": {
            "canonical_hash": registration.registration_hash,
            "file_sha256": registration_file_sha256,
            "path": str(Path(registration_path).resolve()),
        },
        "repo_root": registration.repo_root,
        "run_lock_hash": None,
        "schema_version": RUN_LOCK_SCHEMA_VERSION,
        "source": {
            "commit": source.commit,
            "tracked_clean": True,
            "tracked_status": "",
        },
        "study_id": registration.study_id,
    }
    record["run_lock_hash"] = _hash_run_lock_record(record)
    _publish_json_once(resolved_lock_path, _canonical_json(record) + "\n")
    return json.loads(_canonical_json(record))


def validate_run_lock(
    *,
    lock_path: Path | str,
    registration_path: Path | str,
    repo_root: Path | str,
    child_command: Sequence[str],
) -> dict[str, Any]:
    """Recompute every source and live-isolation binding in a run lock."""

    record = _load_run_lock(Path(lock_path))
    expected_fields = {
        "checkpoints",
        "command",
        "communication_mod",
        "created_unix_ns",
        "implementation_files",
        "python_executable",
        "registration",
        "repo_root",
        "run_lock_hash",
        "schema_version",
        "source",
        "study_id",
    }
    _require_run_lock_fields(record, expected_fields, "run lock")
    if record["schema_version"] != RUN_LOCK_SCHEMA_VERSION:
        raise OutcomeEvidenceRunLockError("run lock schema_version mismatch")
    supplied_hash = record["run_lock_hash"]
    if not isinstance(supplied_hash, str) or not _SHA256_PATTERN.fullmatch(
        supplied_hash
    ):
        raise OutcomeEvidenceRunLockError("run_lock_hash is not a SHA-256 hash")
    if supplied_hash != canonical_run_lock_hash(record):
        raise OutcomeEvidenceRunLockError("run lock hash mismatch")

    registration, registration_file_sha256, source = _validate_run_lock_inputs(
        registration_path=registration_path,
        repo_root=repo_root,
        child_command=child_command,
    )
    expected_registration = {
        "canonical_hash": registration.registration_hash,
        "file_sha256": registration_file_sha256,
        "path": str(Path(registration_path).resolve()),
    }
    actual_registration = record["registration"]
    if not isinstance(actual_registration, Mapping):
        raise OutcomeEvidenceRunLockError("run lock registration must be an object")
    if actual_registration.get("file_sha256") != registration_file_sha256:
        raise OutcomeEvidenceRunLockError("registration bytes changed after run lock")
    _assert_run_lock_value(
        actual_registration, expected_registration, "registration"
    )
    _assert_run_lock_value(record["study_id"], registration.study_id, "study_id")
    _assert_run_lock_value(record["repo_root"], registration.repo_root, "repo_root")
    _assert_run_lock_value(
        record["python_executable"],
        registration.python_executable,
        "python_executable",
    )
    _assert_run_lock_value(
        record["command"], _normalize_child_command(child_command), "command"
    )
    _assert_run_lock_value(
        record["source"],
        {
            "commit": source.commit,
            "tracked_clean": True,
            "tracked_status": "",
        },
        "source",
    )

    expected_implementation = _implementation_snapshot(Path(repo_root))
    if record["implementation_files"] != expected_implementation:
        raise OutcomeEvidenceRunLockError("source file hash drift detected")
    expected_communication = _communication_mod_snapshot(
        Path(registration.communication_config_path)
    )
    if record["communication_mod"] != expected_communication:
        raise OutcomeEvidenceRunLockError(
            "CommunicationMod semantic configuration drift detected"
        )
    expected_checkpoints = _checkpoint_inventory_snapshot(
        Path(registration.checkpoint_root)
    )
    if record["checkpoints"] != expected_checkpoints:
        raise OutcomeEvidenceRunLockError("checkpoint drift detected")
    if type(record["created_unix_ns"]) is not int or record["created_unix_ns"] <= 0:
        raise OutcomeEvidenceRunLockError(
            "created_unix_ns must be a positive integer"
        )
    return json.loads(_canonical_json(record))


def canonical_run_lock_hash(record: Mapping[str, Any]) -> str:
    if not isinstance(record, Mapping):
        raise OutcomeEvidenceRunLockError("run lock must be a JSON object")
    hash_input = dict(record)
    hash_input["run_lock_hash"] = None
    return _hash_run_lock_record(hash_input)


def _validate_run_lock_inputs(
    *,
    registration_path: Path | str,
    repo_root: Path | str,
    child_command: Sequence[str],
) -> tuple[OutcomeEvidenceRegistration, str, GitSourceSnapshot]:
    resolved_registration_path = Path(registration_path).resolve()
    resolved_repo_root = Path(repo_root).resolve()
    if _git_repository_root(resolved_repo_root) != resolved_repo_root:
        raise OutcomeEvidenceRunLockError(
            "repo_root must be the Git repository top level"
        )
    try:
        registration_bytes = resolved_registration_path.read_bytes()
        registration = load_registration(resolved_registration_path)
    except (OSError, OutcomeEvidenceRegistrationError) as exc:
        raise OutcomeEvidenceRunLockError(f"invalid registration: {exc}") from exc
    if registration.repo_root != str(resolved_repo_root):
        raise OutcomeEvidenceRunLockError("registration repo_root mismatch")
    try:
        registration_relative_path = resolved_registration_path.relative_to(
            resolved_repo_root
        )
    except ValueError as exc:
        raise OutcomeEvidenceRunLockError(
            "registration must be inside the registered repository"
        ) from exc
    if registration.python_executable.casefold() != SUPPORTED_WINDOWS_PYTHON.casefold():
        raise OutcomeEvidenceRunLockError(
            "study requires the supported Windows Python executable: "
            + SUPPORTED_WINDOWS_PYTHON
        )

    command = _normalize_child_command(child_command)
    command_record = registration.to_record()["command"]
    expected_command = [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]
    if command != expected_command:
        raise OutcomeEvidenceRunLockError("child command differs from registration")
    if "--train" in command or "--eval" not in command:
        raise OutcomeEvidenceRunLockError(
            "child command must be eval-only and must not train"
        )

    source = _inspect_git_source(resolved_repo_root)
    if not source.tracked_clean:
        raise OutcomeEvidenceRunLockError(
            "tracked source is dirty; refusing run lock: " + source.tracked_status
        )
    if not re.fullmatch(r"[0-9a-f]{40}", source.commit):
        raise OutcomeEvidenceRunLockError("source commit is not a Git SHA-1")
    _verify_head_file(
        repo_root=resolved_repo_root,
        relative_path=registration_relative_path,
        working_bytes=registration_bytes,
        label="registration file",
    )
    for relative_path in RUN_LOCK_IMPLEMENTATION_PATHS:
        resolved_path = (resolved_repo_root / relative_path).resolve()
        try:
            working_bytes = resolved_path.read_bytes()
        except OSError as exc:
            raise OutcomeEvidenceRunLockError(
                f"cannot read implementation file {relative_path}: {exc}"
            ) from exc
        _verify_head_file(
            repo_root=resolved_repo_root,
            relative_path=Path(relative_path),
            working_bytes=working_bytes,
            label=f"implementation file {relative_path}",
        )
    return (
        registration,
        hashlib.sha256(registration_bytes).hexdigest(),
        source,
    )


def _normalize_child_command(child_command: Sequence[str]) -> list[str]:
    if isinstance(child_command, (str, bytes)) or not isinstance(
        child_command, Sequence
    ):
        raise OutcomeEvidenceRunLockError("child command must be a sequence")
    command = list(child_command)
    if not command or any(not isinstance(value, str) for value in command):
        raise OutcomeEvidenceRunLockError(
            "child command must contain only nonempty string arguments"
        )
    if any(not value for value in command):
        raise OutcomeEvidenceRunLockError(
            "child command must contain only nonempty string arguments"
        )
    return command


def _inspect_git_source(repo_root: Path) -> GitSourceSnapshot:
    commit = _run_git(repo_root, "rev-parse", "HEAD").strip().lower()
    tracked_status = _run_git(
        repo_root, "status", "--porcelain", "--untracked-files=no"
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise OutcomeEvidenceRunLockError(
            f"git returned an invalid source commit: {commit!r}"
        )
    return GitSourceSnapshot(
        commit=commit,
        tracked_clean=not tracked_status,
        tracked_status=tracked_status,
    )


def _run_git(repo_root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(f"unable to run git: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise OutcomeEvidenceRunLockError(
            f"git {' '.join(arguments)} failed: {detail}"
        )
    return result.stdout


def _git_repository_root(repo_root: Path) -> Path:
    return Path(_run_git(repo_root, "rev-parse", "--show-toplevel").strip()).resolve()


def _head_blob_bytes(repo_root: Path, relative_path: Path) -> bytes | None:
    git_path = relative_path.as_posix()
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{git_path}"],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(f"unable to run git: {exc}") from exc
    if result.returncode != 0:
        return None
    return result.stdout


def _verify_head_file(
    *,
    repo_root: Path,
    relative_path: Path,
    working_bytes: bytes,
    label: str,
) -> None:
    head_bytes = _head_blob_bytes(repo_root, relative_path)
    if head_bytes is None:
        raise OutcomeEvidenceRunLockError(f"{label} must be committed at HEAD")
    if working_bytes != head_bytes and _filtered_working_blob_oid(
        repo_root, relative_path, working_bytes
    ) != _git_blob_oid(head_bytes):
        raise OutcomeEvidenceRunLockError(f"{label} bytes differ from HEAD")


def _filtered_working_blob_oid(
    repo_root: Path, relative_path: Path, working_bytes: bytes
) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "hash-object",
                f"--path={relative_path.as_posix()}",
                "--stdin",
            ],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            input=working_bytes,
        )
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(f"unable to run git: {exc}") from exc
    oid = result.stdout.decode("ascii", errors="strict").strip().lower()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", oid):
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise OutcomeEvidenceRunLockError(
            f"git hash-object failed for {relative_path}: {detail}"
        )
    return oid


def _git_blob_oid(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def _implementation_snapshot(repo_root: Path) -> list[dict[str, Any]]:
    snapshot = []
    for relative_path in RUN_LOCK_IMPLEMENTATION_PATHS:
        path = (repo_root / relative_path).resolve()
        try:
            path.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise OutcomeEvidenceRunLockError(
                f"source file escapes repository: {relative_path}"
            ) from exc
        fingerprint = _required_file_snapshot(path, "source file")
        snapshot.append(
            {
                "path": str(path),
                "relative_path": relative_path,
                **fingerprint,
            }
        )
    return snapshot


def _communication_mod_snapshot(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise OutcomeEvidenceRunLockError(
            f"CommunicationMod config is not a file: {resolved}"
        )
    try:
        semantic_sha256 = _properties_semantic_sha256(resolved)
    except (OSError, UnicodeError, OutcomeEvidenceRunLockError):
        raise
    return {"path": str(resolved), "semantic_sha256": semantic_sha256}


def _checkpoint_inventory_snapshot(checkpoint_root: Path) -> dict[str, Any]:
    resolved_root = checkpoint_root.resolve()
    if not resolved_root.is_dir():
        raise OutcomeEvidenceRunLockError(
            f"registered checkpoint root is not a directory: {resolved_root}"
        )
    checkpoint_paths = {
        path.resolve()
        for pattern in CHECKPOINT_PATTERNS
        for path in resolved_root.glob(pattern)
        if path.is_file()
    }
    ordered_paths = sorted(checkpoint_paths, key=lambda path: str(path).casefold())
    if not ordered_paths:
        raise OutcomeEvidenceRunLockError(
            "registered checkpoint inventory contains no matching checkpoints"
        )
    return {
        "files": [
            {"path": str(path), **_required_file_snapshot(path, "checkpoint")}
            for path in ordered_paths
        ],
        "patterns": list(CHECKPOINT_PATTERNS),
        "root": str(resolved_root),
    }


def _required_file_snapshot(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise OutcomeEvidenceRunLockError(f"required {label} is missing: {path}")
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(
            f"cannot read {label} {path}: {exc}"
        ) from exc
    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def _properties_semantic_sha256(path: Path) -> str:
    try:
        content = path.read_text(encoding="iso-8859-1")
        natural_lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        properties: dict[str, str] = {}
        for logical_line in _java_properties_logical_lines(natural_lines):
            parsed = _parse_java_property(logical_line)
            if parsed is not None:
                key, value = parsed
                properties[key] = value
    except (OSError, UnicodeError) as exc:
        raise OutcomeEvidenceRunLockError(
            f"cannot read CommunicationMod config {path}: {exc}"
        ) from exc
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
    decoded: list[str] = []
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
            raise OutcomeEvidenceRunLockError(
                "invalid trailing escape in CommunicationMod config"
            )
        escaped = value[index]
        if escaped == "u":
            digits = value[index + 1 : index + 5]
            if len(digits) != 4 or any(
                digit not in "0123456789abcdefABCDEF" for digit in digits
            ):
                raise OutcomeEvidenceRunLockError(
                    "invalid Unicode escape in CommunicationMod config"
                )
            decoded.append(chr(int(digits, 16)))
            index += 5
            continue
        decoded.append(escapes.get(escaped, escaped))
        index += 1
    return "".join(decoded)


def _load_run_lock(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except OutcomeEvidenceRegistrationError as exc:
        raise OutcomeEvidenceRunLockError(str(exc)) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OutcomeEvidenceRunLockError(
            f"cannot load run lock {path}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise OutcomeEvidenceRunLockError("run lock must be a JSON object")
    return payload


def _publish_json_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
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
        raise OutcomeEvidenceRunLockError(
            f"run lock already exists for this study: {path}"
        ) from exc
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(
            f"cannot publish run lock {path}: {exc}"
        ) from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _require_run_lock_fields(
    value: Mapping[str, Any], expected: set[str], field: str
) -> None:
    actual = set(value)
    if actual != expected:
        raise OutcomeEvidenceRunLockError(
            f"{field} fields mismatch: missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )


def _assert_run_lock_value(actual: Any, expected: Any, path: str) -> None:
    try:
        _assert_exact_value(actual, expected, path)
    except OutcomeEvidenceRegistrationError as exc:
        raise OutcomeEvidenceRunLockError(str(exc)) from exc


def _hash_run_lock_record(record: Mapping[str, Any]) -> str:
    try:
        payload = _canonical_json(record).encode("utf-8")
    except OutcomeEvidenceRegistrationError as exc:
        raise OutcomeEvidenceRunLockError(str(exc)) from exc
    return hashlib.sha256(payload).hexdigest()


def _pool_json_copy(value: Any, field: str) -> Any:
    try:
        return json.loads(_canonical_json(value))
    except (OutcomeEvidenceRegistrationError, json.JSONDecodeError) as exc:
        raise OutcomeEvidencePoolError(f"{field} is not canonical JSON: {exc}") from exc


def _pool_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise OutcomeEvidencePoolError(f"{field} must be a lowercase SHA-256 hash")
    return value


def _optional_pool_sha256(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _pool_sha256(value, field)


def _finalization_output_paths(
    registration: OutcomeEvidenceRegistration,
    output_rules: Mapping[str, Any],
) -> dict[str, Path]:
    root = Path(registration.artifact_root)
    paths = {
        "closeout_json": root / output_rules["closeout_json_filename"],
        "closeout_markdown": root / output_rules["closeout_markdown_filename"],
        "estimate_json": root / output_rules["estimate_json_filename"],
        "estimate_markdown": root / output_rules["estimate_markdown_filename"],
        "finalization_claim": root / output_rules["finalization_claim_filename"],
        "pool_manifest": root / output_rules["pool_manifest_filename"],
        "pool_samples": root / output_rules["pool_samples_filename"],
        "readiness_json": root / output_rules["readiness_json_filename"],
        "readiness_markdown": root / output_rules["readiness_markdown_filename"],
        "target_manifest": root / output_rules["target_manifest_filename"],
    }
    if len(set(paths.values())) != len(paths):
        raise OutcomeEvidencePoolError("finalization output paths are not unique")
    return paths


def _finalization_claim_text(
    registration: OutcomeEvidenceRegistration,
    *,
    run_lock_hash: str,
    mode: str,
) -> str:
    if mode not in {"complete", "integrity_stop"}:
        raise OutcomeEvidencePoolError("finalization claim mode is invalid")
    record = {
        "claim_hash": None,
        "mode": mode,
        "registration_hash": registration.registration_hash,
        "run_lock_hash": _pool_sha256(run_lock_hash, "run_lock_hash"),
        "schema_version": FINALIZATION_CLAIM_SCHEMA_VERSION,
        "study_id": registration.study_id,
    }
    record["claim_hash"] = hashlib.sha256(
        _canonical_json(record).encode("utf-8")
    ).hexdigest()
    return _canonical_json(record) + "\n"


def _publish_finalization_claim_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_path, path)
    except FileExistsError as exc:
        raise OutcomeEvidencePoolError(
            f"study is already finalized or claimed: {path}"
        ) from exc
    except OSError as exc:
        raise OutcomeEvidencePoolError(
            f"cannot publish finalization claim {path}: {exc}"
        ) from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _blocked_closeout_slots(
    registration: OutcomeEvidenceRegistration,
    ledger_snapshot: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    if not isinstance(ledger_snapshot, Mapping):
        raise OutcomeEvidencePoolError("ledger snapshot must be an object")
    if ledger_snapshot.get("initialized") is not True:
        raise OutcomeEvidencePoolError(
            "blocked closeout requires an initialized ledger"
        )
    global_stop = ledger_snapshot.get("global_stop")
    if not isinstance(global_stop, Mapping):
        raise OutcomeEvidencePoolError("blocked closeout requires a global stop")
    reason = global_stop.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise OutcomeEvidencePoolError("global stop reason must be nonempty")
    terminal_records = ledger_snapshot.get("terminal_slots")
    if isinstance(terminal_records, (str, bytes)) or not isinstance(
        terminal_records,
        Sequence,
    ):
        raise OutcomeEvidencePoolError("ledger terminal_slots must be a sequence")
    if ledger_snapshot.get("terminal_slot_count") != len(terminal_records):
        raise OutcomeEvidencePoolError("ledger terminal slot count mismatch")

    terminals: dict[int, dict[str, Any]] = {}
    for raw_terminal in terminal_records:
        if not isinstance(raw_terminal, Mapping):
            raise OutcomeEvidencePoolError("ledger terminal slot is invalid")
        slot_number = raw_terminal.get("slot_number")
        if type(slot_number) is not int or not 1 <= slot_number <= len(
            registration.slots
        ):
            raise OutcomeEvidencePoolError("ledger terminal slot identity is invalid")
        if slot_number in terminals:
            raise OutcomeEvidencePoolError("duplicate ledger terminal slot")
        slot = registration.slots[slot_number - 1]
        status = raw_terminal.get("terminal_status")
        if (
            raw_terminal.get("session_id") != slot.session_id
            or status not in {"completed", "interrupted"}
        ):
            raise OutcomeEvidencePoolError("ledger terminal slot is inconsistent")
        terminals[slot_number] = {
            "session_id": slot.session_id,
            "slot_number": slot_number,
            "terminal_status": status,
        }

    active_record = ledger_snapshot.get("active_slot")
    active_slot_number = None
    if active_record is not None:
        if not isinstance(active_record, Mapping):
            raise OutcomeEvidencePoolError("ledger active slot is invalid")
        active_slot_number = active_record.get("slot_number")
        if type(active_slot_number) is not int or not 1 <= active_slot_number <= len(
            registration.slots
        ):
            raise OutcomeEvidencePoolError("ledger active slot identity is invalid")
        active_slot = registration.slots[active_slot_number - 1]
        if (
            active_slot_number in terminals
            or active_record.get("session_id") != active_slot.session_id
        ):
            raise OutcomeEvidencePoolError("ledger active slot is inconsistent")

    statuses = []
    for slot in registration.slots:
        if slot.slot_number in terminals:
            statuses.append(terminals[slot.slot_number])
        else:
            statuses.append(
                {
                    "session_id": slot.session_id,
                    "slot_number": slot.slot_number,
                    "terminal_status": (
                        "blocked"
                        if slot.slot_number == active_slot_number
                        else "unlaunched"
                    ),
                }
            )
    return statuses, reason.strip()


def _reject_downstream_authority(
    readiness_artifact: Mapping[str, Any],
    estimate_artifact: Mapping[str, Any],
) -> None:
    authority_fields = {
        "causal_uplift_ready",
        "formal_noncombat_rl_training_ready",
        "live_policy_promotion_ready",
        "reward_design_ready",
    }
    for artifact_name, artifact, gate_field in (
        ("readiness", readiness_artifact, "readiness"),
        ("estimate", estimate_artifact, "gates"),
    ):
        gates = artifact.get(gate_field)
        if not isinstance(gates, Mapping):
            raise OutcomeEvidencePoolError(
                f"{artifact_name} artifact authority gates are missing"
            )
        authorized = sorted(
            field for field in authority_fields if gates.get(field) is True
        )
        if authorized:
            raise OutcomeEvidencePoolError(
                f"{artifact_name} artifact exceeds offline authority: "
                + ", ".join(authorized)
            )


def _build_blocked_estimate_artifact(
    *,
    readiness_artifact: Mapping[str, Any],
    sample_bytes: bytes,
    target_bytes: bytes,
    readiness_bytes: bytes,
    calibration_bytes: bytes,
    bootstrap_seed: str,
    replicate_count: int,
    confidence_level: Fraction,
    estimator_implementation_hash: str,
    estimate_implementation_hash: str,
) -> dict[str, Any]:
    blockers = readiness_artifact.get("blockers")
    if isinstance(blockers, (str, bytes)) or not isinstance(blockers, Sequence):
        readiness_blockers: list[str] = []
    else:
        readiness_blockers = sorted(
            str(blocker) for blocker in blockers if isinstance(blocker, str)
        )
    return {
        "blockers": ["dataset_estimation_not_ready"],
        "bootstrap": None,
        "comparison": {
            "blockers": ["ope_estimate_not_ready"],
            "conditions": {"ope_estimate_ready": False},
            "ready": False,
        },
        "contracts": {
            "bootstrap_confidence_level": _pool_fraction_record(
                confidence_level
            ),
            "bootstrap_seed": bootstrap_seed,
            "primary_outcome": "victory",
            "production_bootstrap_replicates": replicate_count,
            "terminal_horizon": "complete_run",
        },
        "estimates": None,
        "gates": {
            "causal_uplift_ready": False,
            "dataset_estimation_ready": False,
            "formal_noncombat_rl_training_ready": False,
            "live_policy_promotion_ready": False,
            "ope_estimate_ready": False,
            "policy_comparison_ready": False,
            "reward_design_ready": False,
        },
        "influence": None,
        "limitations": [
            "The validated estimator rejected a dataset that was not OPE-ready.",
            "No estimate, bootstrap, influence, training, or promotion result exists.",
        ],
        "readiness_blockers": readiness_blockers,
        "schema_version": BLOCKED_ESTIMATE_SCHEMA_VERSION,
        "source": {
            "calibration_file_sha256": hashlib.sha256(
                calibration_bytes
            ).hexdigest(),
            "estimate_artifact_implementation_sha256": (
                _pool_sha256(
                    estimate_implementation_hash,
                    "estimate_implementation_hash",
                )
            ),
            "estimator_implementation_sha256": _pool_sha256(
                estimator_implementation_hash,
                "estimator_implementation_hash",
            ),
            "readiness_file_sha256": hashlib.sha256(readiness_bytes).hexdigest(),
            "sample_file_sha256": hashlib.sha256(sample_bytes).hexdigest(),
            "target_file_sha256": hashlib.sha256(target_bytes).hexdigest(),
        },
    }


def _render_blocked_estimate_markdown(artifact: Mapping[str, Any]) -> str:
    blockers = artifact["readiness_blockers"]
    lines = [
        "# Non-combat OPE estimate",
        "",
        "Status: BLOCKED",
        "",
        "## Blockers",
        "",
        "- `dataset_estimation_not_ready`",
        "",
        "## Readiness blockers",
        "",
    ]
    lines.extend(f"- `{blocker}`" for blocker in blockers)
    if not blockers:
        lines.append("- none reported")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in artifact["limitations"])
    return "\n".join(lines) + "\n"


def _pool_timestamp(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise OutcomeEvidencePoolError(f"{field} must be a nonnegative integer")
    return value


def _validate_gate_metrics(
    metrics: OutcomeEvidenceGateMetrics,
) -> OutcomeEvidenceGateMetrics:
    if not isinstance(metrics, OutcomeEvidenceGateMetrics):
        raise OutcomeEvidencePoolError(
            "metrics must be OutcomeEvidenceGateMetrics"
        )
    if type(metrics.all_registered_slots_accounted) is not bool or type(
        metrics.global_integrity_stop
    ) is not bool:
        raise OutcomeEvidencePoolError("gate integrity metrics must be booleans")
    for field in (
        "complete_trajectory_count",
        "nonzero_weight_trajectory_count",
        "supported_victory_count",
    ):
        value = getattr(metrics, field)
        if type(value) is not int or value < 0:
            raise OutcomeEvidencePoolError(f"{field} must be nonnegative")
    if metrics.complete_trajectory_count > SCHEDULED_ATTEMPTS:
        raise OutcomeEvidencePoolError(
            "complete_trajectory_count exceeds the registered schedule"
        )
    if metrics.nonzero_weight_trajectory_count > metrics.complete_trajectory_count:
        raise OutcomeEvidencePoolError(
            "nonzero weight trajectories exceed complete trajectories"
        )
    if metrics.supported_victory_count > metrics.nonzero_weight_trajectory_count:
        raise OutcomeEvidencePoolError(
            "supported victories exceed nonzero-weight trajectories"
        )
    support = metrics.category_arm_support
    if not isinstance(support, Mapping) or set(support) != {
        "card_reward",
        "shop",
    }:
        raise OutcomeEvidencePoolError("category arm support categories mismatch")
    for category in ("card_reward", "shop"):
        arms = support[category]
        if not isinstance(arms, Mapping) or set(arms) != {
            "alternative",
            "baseline",
        }:
            raise OutcomeEvidencePoolError(
                f"{category} arm support fields mismatch"
            )
        if any(type(value) is not int or value < 0 for value in arms.values()):
            raise OutcomeEvidencePoolError(
                f"{category} arm support counts must be nonnegative integers"
            )
    for field in ("ess_fraction", "max_normalized_weight"):
        value = getattr(metrics, field)
        if not isinstance(value, Fraction) or not Fraction(0, 1) <= value <= 1:
            raise OutcomeEvidencePoolError(
                f"{field} must be an exact fraction in [0, 1]"
            )
    return metrics


def _registered_fraction(value: Any, field: str) -> Fraction:
    if not isinstance(value, Mapping) or set(value) != {
        "denominator",
        "numerator",
    }:
        raise OutcomeEvidencePoolError(f"registered {field} is invalid")
    numerator = value.get("numerator")
    denominator = value.get("denominator")
    if (
        type(numerator) is not int
        or type(denominator) is not int
        or numerator < 0
        or denominator <= 0
    ):
        raise OutcomeEvidencePoolError(f"registered {field} is invalid")
    return Fraction(numerator, denominator)


def _pool_fraction_record(value: Fraction) -> dict[str, int | float]:
    return {
        "denominator": value.denominator,
        "numerator": value.numerator,
        "value": float(value),
    }


def _gate_json_value(value: Any) -> Any:
    if isinstance(value, Fraction):
        return _pool_fraction_record(value)
    if isinstance(value, Mapping):
        return {
            str(key): _gate_json_value(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, tuple | list):
        return [_gate_json_value(item) for item in value]
    if value is None or type(value) in {bool, int, float, str}:
        return value
    raise OutcomeEvidencePoolError("gate value is not canonical JSON")


def _minimum_fraction_count(total: int, fraction: Fraction) -> int:
    numerator = total * fraction.numerator
    return (numerator + fraction.denominator - 1) // fraction.denominator


def _validate_closeout_slots(
    registration: OutcomeEvidenceRegistration,
    slot_statuses: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(slot_statuses, (str, bytes)) or not isinstance(
        slot_statuses, Sequence
    ):
        raise OutcomeEvidencePoolError("slot_statuses must be a sequence")
    by_slot: dict[int, dict[str, Any]] = {}
    for raw_status in slot_statuses:
        if not isinstance(raw_status, Mapping):
            raise OutcomeEvidencePoolError("closeout slot status is invalid")
        status = _pool_json_copy(raw_status, "closeout slot status")
        slot_number = status.get("slot_number")
        if type(slot_number) is not int or not 1 <= slot_number <= len(
            registration.slots
        ):
            raise OutcomeEvidencePoolError("closeout slot number is invalid")
        if slot_number in by_slot:
            raise OutcomeEvidencePoolError("duplicate closeout slot status")
        slot = registration.slots[slot_number - 1]
        if status.get("session_id") != slot.session_id:
            raise OutcomeEvidencePoolError("closeout slot session mismatch")
        if status.get("terminal_status") not in {
            "blocked",
            "completed",
            "interrupted",
            "unlaunched",
        }:
            raise OutcomeEvidencePoolError("closeout slot lifecycle is invalid")
        by_slot[slot_number] = status
    expected = set(range(1, len(registration.slots) + 1))
    if set(by_slot) != expected:
        raise OutcomeEvidencePoolError("closeout slot set mismatch")
    return [by_slot[number] for number in sorted(by_slot)]


def _closeout_hash(closeout: Mapping[str, Any]) -> str:
    record = dict(closeout)
    record["closeout_hash"] = None
    return hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()


def _validate_closeout_hash(closeout: Mapping[str, Any]) -> None:
    if not isinstance(closeout, Mapping):
        raise OutcomeEvidencePoolError("closeout must be an object")
    supplied_hash = closeout.get("closeout_hash")
    _pool_sha256(supplied_hash, "closeout_hash")
    if supplied_hash != _closeout_hash(closeout):
        raise OutcomeEvidencePoolError("closeout hash mismatch")


def _pool_run_lock_binding(
    registration: OutcomeEvidenceRegistration,
    run_lock: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(run_lock, Mapping):
        raise OutcomeEvidencePoolError("run lock must be an object")
    run_lock_hash = _pool_sha256(run_lock.get("run_lock_hash"), "run_lock_hash")
    if run_lock.get("study_id") != registration.study_id:
        raise OutcomeEvidencePoolError("run lock study_id mismatch")
    registration_binding = run_lock.get("registration")
    if not isinstance(registration_binding, Mapping) or registration_binding.get(
        "canonical_hash"
    ) != registration.registration_hash:
        raise OutcomeEvidencePoolError("run lock registration hash mismatch")
    source = run_lock.get("source")
    source_commit = source.get("commit") if isinstance(source, Mapping) else None
    if not isinstance(source_commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}", source_commit
    ):
        raise OutcomeEvidencePoolError("run lock source commit is invalid")
    return {"run_lock_hash": run_lock_hash, "source_commit": source_commit}


def _load_pool_markers(path: Path) -> tuple[int, ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise OutcomeEvidencePoolError(f"cannot read AI marker file: {exc}") from exc
    markers = []
    for line in lines:
        value = line.strip()
        if not value:
            continue
        if not value.isdigit():
            raise OutcomeEvidencePoolError("AI marker file contains an invalid marker")
        markers.append(int(value))
    return tuple(markers)


def _load_pool_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidencePoolError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise OutcomeEvidencePoolError(f"{label} must be an object")
    return payload


def _validate_pool_manifest_binding(
    registration: OutcomeEvidenceRegistration,
    *,
    slot: RegisteredSlot,
    manifest: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    binding: Mapping[str, str],
) -> None:
    effective = manifest.get("effective_config")
    source = manifest.get("source")
    if (
        manifest.get("session_id") != slot.session_id
        or manifest.get("manifest_path") != slot.manifest_path
        or manifest.get("trace_path") != slot.trace_path
        or not isinstance(effective, Mapping)
        or effective.get("study_id") != registration.study_id
        or effective.get("study_slot_number") != slot.slot_number
        or effective.get("study_registration_hash")
        != registration.registration_hash
        or effective.get("study_run_lock_hash") != binding["run_lock_hash"]
        or not isinstance(source, Mapping)
        or source.get("commit") != binding["source_commit"]
    ):
        raise OutcomeEvidencePoolError(
            f"slot {slot.slot_number}: manifest study binding mismatch"
        )
    _pool_sha256(manifest.get("manifest_hash"), "manifest_hash")
    if not manifest_isolation_matches_run_lock(manifest, run_lock):
        raise OutcomeEvidencePoolError(
            f"slot {slot.slot_number}: manifest isolation differs from run lock"
        )


def _pool_file_sha256(path: Path, label: str) -> str:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidencePoolError(f"cannot read {label} {path}: {exc}") from exc
    return hashlib.sha256(content).hexdigest()


def _pool_terminal_slots(
    registration: OutcomeEvidenceRegistration,
    ledger_snapshot: Mapping[str, Any],
) -> dict[int, Mapping[str, Any]]:
    if not isinstance(ledger_snapshot, Mapping):
        raise OutcomeEvidencePoolError("ledger snapshot must be an object")
    if (
        ledger_snapshot.get("initialized") is not True
        or ledger_snapshot.get("all_slots_terminal") is not True
        or ledger_snapshot.get("active_slot") is not None
        or ledger_snapshot.get("global_stop") is not None
    ):
        raise OutcomeEvidencePoolError(
            "registered pooling requires every slot terminal without a global stop"
        )
    records = ledger_snapshot.get("terminal_slots")
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        raise OutcomeEvidencePoolError("ledger terminal_slots must be a sequence")
    if ledger_snapshot.get("terminal_slot_count") != len(registration.slots):
        raise OutcomeEvidencePoolError("ledger terminal slot count mismatch")
    terminal_by_slot: dict[int, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise OutcomeEvidencePoolError("ledger terminal slot is invalid")
        slot_number = record.get("slot_number")
        if type(slot_number) is not int or not 1 <= slot_number <= len(
            registration.slots
        ):
            raise OutcomeEvidencePoolError("ledger terminal slot identity is invalid")
        if slot_number in terminal_by_slot:
            raise OutcomeEvidencePoolError("duplicate ledger terminal slot")
        slot = registration.slots[slot_number - 1]
        if record.get("session_id") != slot.session_id:
            raise OutcomeEvidencePoolError("ledger terminal session mismatch")
        complete = record.get("complete_trajectories")
        marker_start = record.get("marker_start_count")
        marker_end = record.get("marker_end_count")
        if (
            type(complete) is not int
            or not 0 <= complete <= GAMES_PER_SLOT
            or type(marker_start) is not int
            or type(marker_end) is not int
            or marker_start < 0
            or marker_end - marker_start != complete
        ):
            raise OutcomeEvidencePoolError("ledger terminal marker accounting mismatch")
        status = record.get("terminal_status")
        exit_code = record.get("process_exit_code")
        if status not in {"completed", "interrupted"} or (
            exit_code is not None and type(exit_code) is not int
        ):
            raise OutcomeEvidencePoolError("ledger terminal status is invalid")
        if (status == "completed") != (
            exit_code == 0 and complete == GAMES_PER_SLOT
        ):
            raise OutcomeEvidencePoolError(
                "ledger terminal status contradicts evidence"
            )
        terminal_by_slot[slot_number] = record
    if set(terminal_by_slot) != set(range(1, len(registration.slots) + 1)):
        raise OutcomeEvidencePoolError("ledger omits a registered terminal slot")
    return terminal_by_slot


def _pool_session_set(
    registration: OutcomeEvidenceRegistration,
    sessions: Sequence[RegisteredSessionEvidence],
) -> dict[int, RegisteredSessionEvidence]:
    if isinstance(sessions, (str, bytes)) or not isinstance(sessions, Sequence):
        raise OutcomeEvidencePoolError("sessions must be a sequence")
    by_slot: dict[int, RegisteredSessionEvidence] = {}
    for evidence in sessions:
        if not isinstance(evidence, RegisteredSessionEvidence):
            raise OutcomeEvidencePoolError(
                "every session must be RegisteredSessionEvidence"
            )
        if evidence.slot_number in by_slot:
            raise OutcomeEvidencePoolError("duplicate registered session slot")
        by_slot[evidence.slot_number] = evidence
    expected = set(range(1, len(registration.slots) + 1))
    actual = set(by_slot)
    if actual != expected:
        raise OutcomeEvidencePoolError(
            "registered session set mismatch: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    return by_slot


def _validate_registered_session_evidence(
    evidence: RegisteredSessionEvidence,
    *,
    slot: RegisteredSlot,
    terminal: Mapping[str, Any],
    run_lock_hash: str,
) -> None:
    if (
        evidence.slot_number != slot.slot_number
        or evidence.session_id != slot.session_id
    ):
        raise OutcomeEvidencePoolError("registered session identity mismatch")
    if evidence.run_lock_hash != run_lock_hash:
        raise OutcomeEvidencePoolError("registered session run lock mismatch")
    for field in (
        "config_sha256",
        "manifest_sha256",
        "manifest_hash",
        "trace_sha256",
    ):
        _pool_sha256(getattr(evidence, field), field)
    if type(evidence.marker_trajectory_count) is not int or (
        evidence.marker_trajectory_count != terminal.get("complete_trajectories")
    ):
        raise OutcomeEvidencePoolError("session marker trajectory count mismatch")
    if len(evidence.joined_run_files) > evidence.marker_trajectory_count:
        raise OutcomeEvidencePoolError("session run joins exceed marker trajectories")
    if len(set(evidence.joined_run_files)) != len(evidence.joined_run_files):
        raise OutcomeEvidencePoolError("duplicate joined run file within session")
    for run_file in evidence.joined_run_files:
        _run_file_sort_key(run_file)
    summary = evidence.validation_summary
    if not isinstance(summary, Mapping):
        raise OutcomeEvidencePoolError("session validation summary is invalid")
    counts: dict[str, int] = {}
    for field in ("candidate_legal", "confirmed", "exported", "replay_valid"):
        value = summary.get(field)
        if type(value) is not int or value < 0:
            raise OutcomeEvidencePoolError(
                f"session validation summary {field} is invalid"
            )
        counts[field] = value
    if not (
        counts["confirmed"]
        >= counts["replay_valid"]
        >= counts["candidate_legal"]
        == counts["exported"]
        == len(evidence.samples)
    ):
        raise OutcomeEvidencePoolError(
            "session exported sample accounting indicates selective omission"
        )
    if evidence.provenance_verified is not True:
        raise OutcomeEvidencePoolError("session provenance is not verified")
    if evidence.isolation_verified is not True:
        raise OutcomeEvidencePoolError("session isolation is not verified")


def _run_file_sort_key(value: Any) -> int:
    if not isinstance(value, str):
        raise OutcomeEvidencePoolError("joined run file must be a string")
    path = Path(value)
    if path.name != value or path.suffix != ".run" or not path.stem.isdigit():
        raise OutcomeEvidencePoolError(f"joined run file is invalid: {value}")
    return int(path.stem)


def _sample_has_registered_outcome(sample: Mapping[str, Any]) -> bool:
    group_id = sample.get("trajectory_group_id")
    outcome = sample.get("outcome")
    if (
        not isinstance(group_id, str)
        or not group_id.startswith("run:")
        or not group_id.removeprefix("run:").isdigit()
        or not isinstance(outcome, Mapping)
    ):
        return False
    return (
        outcome.get("included_in_gate") is True
        and outcome.get("join_status") == "matched"
        and outcome.get("run_file")
        == f"{group_id.removeprefix('run:')}.run"
    )


def _pool_sample_sort_key(sample: Mapping[str, Any]) -> tuple[int, int, str]:
    group_id = str(sample["trajectory_group_id"])
    exploration = sample["exploration"]
    return (
        int(group_id.removeprefix("run:")),
        int(exploration["decision_index"]),
        str(sample["sample_id"]),
    )


def _render_pool_sample_rows(samples: Sequence[Mapping[str, Any]]) -> str:
    return "".join(_canonical_json(sample) + "\n" for sample in samples)


def _pool_manifest_hash(manifest: Mapping[str, Any]) -> str:
    record = dict(manifest)
    record["pool_manifest_hash"] = None
    return hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()


def _build_slot(
    *, study_id: str, artifact_root: Path, seed_base: int, slot_number: int
) -> RegisteredSlot:
    suffix = f"s{slot_number:02d}"
    session_id = f"{study_id}-{suffix}"
    return RegisteredSlot(
        slot_number=slot_number,
        session_id=session_id,
        seed=seed_base + slot_number,
        config_path=str((artifact_root / f"{session_id}-config.json").resolve()),
        manifest_path=str((artifact_root / f"{session_id}-manifest.json").resolve()),
        trace_path=str((artifact_root / f"{session_id}-trace.jsonl").resolve()),
    )


def _registration_body(registration: OutcomeEvidenceRegistration) -> dict[str, Any]:
    return {
        "analysis_rules": {
            "bootstrap_confidence_level": {
                "denominator": 100,
                "numerator": 95,
            },
            "bootstrap_replicates": PRODUCTION_BOOTSTRAP_REPLICATES,
            "bootstrap_seed": (
                f"{registration.study_id}:current-deterministic-bootstrap-v1"
            ),
            "calibration_artifact_relative_path": (
                CALIBRATION_ARTIFACT_RELATIVE_PATH
            ),
            "target_policy_mode": TARGET_POLICY_MODE,
        },
        "artifact_root": registration.artifact_root,
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
            "outcome_fields_forbidden_during_collection": True,
            "outcome_adaptive_decisions_forbidden": True,
        },
        "command": {
            "arguments": list(COMMAND_ARGUMENTS),
            "main_path": str((Path(registration.repo_root) / "main.py").resolve()),
            "python_executable": registration.python_executable,
        },
        "games_per_slot": GAMES_PER_SLOT,
        "integrity_rules": {
            "checkpoint_inventory": {
                "patterns": list(CHECKPOINT_PATTERNS),
                "root": registration.checkpoint_root,
            },
            "communication_config_path": registration.communication_config_path,
            "implementation_paths": list(RUN_LOCK_IMPLEMENTATION_PATHS),
            "launches_per_slot": 1,
            "replacement_slots_forbidden": True,
            "tracked_source_frozen_during_run_lock": True,
        },
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
        "repo_root": registration.repo_root,
        "scheduled_attempts": SCHEDULED_ATTEMPTS,
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "seed_base": registration.seed_base,
        "slot_count": SLOT_COUNT,
        "slots": [slot.to_record() for slot in registration.slots],
        "study_id": registration.study_id,
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


def _record_with_null_hash(
    registration: OutcomeEvidenceRegistration,
) -> dict[str, Any]:
    record = _registration_body(registration)
    record["registration_hash"] = None
    return record


def _hash_registration_record(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()


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
        raise OutcomeEvidenceRegistrationError(
            f"registration is not canonical JSON: {exc}"
        ) from exc


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OutcomeEvidenceRegistrationError(f"{field} must be an object")
    return value


def _require_exact_fields(
    value: Mapping[str, Any], expected: set[str], field: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise OutcomeEvidenceRegistrationError(
            f"{field} fields mismatch: missing={missing}, unknown={unknown}"
        )


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise OutcomeEvidenceRegistrationError(f"{field} must be a string")
    return value


def _require_exact_int(value: Any, field: str) -> int:
    if type(value) is not int:
        raise OutcomeEvidenceRegistrationError(f"{field} must be an exact integer")
    return value


def _assert_exact_value(actual: Any, expected: Any, path: str) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            raise OutcomeEvidenceRegistrationError(
                f"{_field_label(path)} must be an object"
            )
        _require_exact_fields(actual, set(expected), path)
        for key in sorted(expected):
            _assert_exact_value(actual[key], expected[key], f"{path}.{key}")
        return

    if isinstance(expected, list):
        if not isinstance(actual, list):
            raise OutcomeEvidenceRegistrationError(
                f"{_field_label(path)} must be a list"
            )
        if len(actual) != len(expected):
            raise OutcomeEvidenceRegistrationError(
                f"{_field_label(path)} must contain exactly {len(expected)} entries"
            )
        for index, expected_item in enumerate(expected):
            _assert_exact_value(actual[index], expected_item, f"{path}[{index}]")
        return

    if type(actual) is not type(expected) or actual != expected:
        raise OutcomeEvidenceRegistrationError(
            f"{_field_label(path)} differs from the registered value"
        )


def _field_label(path: str) -> str:
    if path.startswith("analysis_rules."):
        return path
    leaf = path.rsplit(".", 1)[-1]
    if leaf == "per_run_alternative_budget":
        return "alternative budget"
    return leaf


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OutcomeEvidenceRegistrationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise OutcomeEvidenceRegistrationError(f"invalid JSON constant: {value}")

"""Audit trajectory-level readiness for offline non-combat policy evaluation."""

from __future__ import annotations

import argparse
import json
import hashlib
import math
import os
import re
import sys
import tempfile
from collections import defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_exploration_evidence import (
    CANONICAL_EXPLORATION_SCHEMA_VERSION,
    behavior_evidence_status,
)


OUTCOME_CONTRACT_VERSION = "noncombat-ope-outcome-contract-v1"
TARGET_POLICY_SCHEMA_VERSION = "noncombat-ope-target-policy-v1"
READINESS_ARTIFACT_SCHEMA_VERSION = "noncombat-ope-readiness-v1"
OVERLAP_SCREEN_POLICY_VERSION = "noncombat-ope-overlap-screen-v1"
MIN_COMPLETE_TRAJECTORIES = 100
MIN_NONZERO_WEIGHT_TRAJECTORIES = 50
MIN_EFFECTIVE_SAMPLE_SIZE = Fraction(50, 1)
MIN_ESS_FRACTION = Fraction(1, 2)
MAX_NORMALIZED_WEIGHT = Fraction(1, 10)
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class OpeReadinessError(ValueError):
    """Raised when input cannot be interpreted without inventing evidence."""


@dataclass(frozen=True)
class TerminalOutcome:
    run_file: str
    victory: bool
    floor_reached: int
    killed_by: str
    playtime: int


@dataclass(frozen=True)
class TrajectoryRecord:
    group_id: str
    trajectory_session_id: str
    behavior_policy_id: str
    behavior_policy_commit: str
    decisions: tuple[Mapping[str, Any], ...]
    outcome: TerminalOutcome


@dataclass(frozen=True)
class BlockedTrajectory:
    group_id: str
    decision_count: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class TrajectoryAudit:
    outcome_contract_version: str
    input_decision_count: int
    complete_decision_count: int
    complete_trajectory_count: int
    trajectories: tuple[TrajectoryRecord, ...]
    blocked_trajectories: tuple[BlockedTrajectory, ...]


@dataclass(frozen=True)
class DecisionWeight:
    sample_id: str
    category: str
    selected_arm: str
    selected_action_id: str
    behavior_probability: Fraction
    target_probability: Fraction
    ratio: Fraction
    ratio_display: float


@dataclass(frozen=True)
class TrajectoryWeight:
    group_id: str
    decision_weights: tuple[DecisionWeight, ...]
    weight: Fraction
    weight_display: float


@dataclass(frozen=True)
class WeightDiagnostics:
    trajectory_count: int
    decision_count: int
    nonzero_weight_count: int
    zero_weight_count: int
    weight_sum: Fraction
    effective_sample_size: Fraction
    ess_fraction: Fraction
    max_normalized_weight: Fraction
    trajectory_weights: tuple[TrajectoryWeight, ...]
    category_arm_support: Mapping[str, Any]
    outcome_variation: Mapping[str, Any]


@dataclass(frozen=True)
class IdentitySelfCheck:
    passed: bool
    mismatches: tuple[str, ...]
    unweighted_outcomes: Mapping[str, Fraction]
    weighted_outcomes: Mapping[str, Fraction]


@dataclass(frozen=True)
class ReadinessBlocker:
    code: str
    observed: Any
    required: Any


@dataclass(frozen=True)
class OverlapScreen:
    ready: bool
    blockers: tuple[ReadinessBlocker, ...]
    estimator_validation_ready: bool = False


def load_canonical_samples(path: Path | str) -> tuple[dict[str, Any], ...]:
    """Load canonical known-propensity JSONL without dropping malformed rows."""

    source = Path(path)
    samples: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise OpeReadinessError(
                    f"{source}:{line_number}: malformed JSON ({exc.msg})"
                ) from exc
            if not isinstance(value, dict):
                raise OpeReadinessError(
                    f"{source}:{line_number}: sample must be a JSON object"
                )
            _validate_sample_identity(value, source=f"{source}:{line_number}")
            samples.append(value)
    return tuple(samples)


def audit_trajectories(samples: Sequence[Mapping[str, Any]]) -> TrajectoryAudit:
    """Group canonical rows into complete terminal-run audit units."""

    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    sample_ids: set[str] = set()
    for row_number, sample in enumerate(samples, start=1):
        _validate_sample_identity(sample, source=f"sample {row_number}")
        sample_id = str(sample["sample_id"])
        if sample_id in sample_ids:
            raise OpeReadinessError(f"duplicate sample_id: {sample_id}")
        sample_ids.add(sample_id)
        groups[str(sample["trajectory_group_id"])].append(sample)

    trajectories: list[TrajectoryRecord] = []
    blocked: list[BlockedTrajectory] = []
    for group_id in sorted(groups):
        decisions = sorted(
            groups[group_id],
            key=lambda sample: (
                int(sample["exploration"]["decision_index"]),
                str(sample["sample_id"]),
            ),
        )
        decision_indexes: set[int] = set()
        for sample in decisions:
            decision_index = int(sample["exploration"]["decision_index"])
            if decision_index in decision_indexes:
                raise OpeReadinessError(
                    f"{group_id}: duplicate decision_index: {decision_index}"
                )
            decision_indexes.add(decision_index)

        reasons, outcome = _trajectory_outcome(group_id, decisions)
        if reasons:
            blocked.append(
                BlockedTrajectory(
                    group_id=group_id,
                    decision_count=len(decisions),
                    reasons=tuple(sorted(reasons)),
                )
            )
            continue

        first = decisions[0]
        trajectories.append(
            TrajectoryRecord(
                group_id=group_id,
                trajectory_session_id=str(first["trajectory_session_id"]),
                behavior_policy_id=str(first["behavior_policy_id"]),
                behavior_policy_commit=str(first["behavior_policy_commit"]),
                decisions=tuple(deepcopy(decision) for decision in decisions),
                outcome=outcome,
            )
        )

    return TrajectoryAudit(
        outcome_contract_version=OUTCOME_CONTRACT_VERSION,
        input_decision_count=len(samples),
        complete_decision_count=sum(
            len(trajectory.decisions) for trajectory in trajectories
        ),
        complete_trajectory_count=len(trajectories),
        trajectories=tuple(trajectories),
        blocked_trajectories=tuple(blocked),
    )


def build_behavior_identity_manifest(
    samples: Sequence[Mapping[str, Any]],
    *,
    source_sample_sha256: str,
) -> dict[str, Any]:
    """Materialize the logged behavior policy as an explicit diagnostic target."""

    _validate_sha256(source_sample_sha256, field="source_sample_sha256")
    entries = []
    for row_number, sample in enumerate(samples, start=1):
        _validate_sample_identity(sample, source=f"sample {row_number}")
        probabilities = [
            {
                "action_id": str(probability["action_id"]),
                "numerator": int(probability["numerator"]),
                "denominator": int(probability["denominator"]),
            }
            for probability in sample["exploration"]["candidate_distribution"]
        ]
        entries.append(
            {
                "sample_id": str(sample["sample_id"]),
                "state_hash": str(sample["exploration"]["state_hash"]),
                "behavior_distribution_hash": str(
                    sample["exploration"]["distribution_hash"]
                ),
                "probabilities": sorted(
                    probabilities,
                    key=lambda probability: probability["action_id"],
                ),
            }
        )

    manifest = {
        "schema_version": TARGET_POLICY_SCHEMA_VERSION,
        "target_policy_id": "behavior_identity",
        "target_policy_commit": None,
        "source_sample_sha256": source_sample_sha256,
        "construction_mode": "behavior_identity",
        "diagnostic_only": True,
        "entries": sorted(entries, key=lambda entry: entry["sample_id"]),
        "manifest_hash": None,
    }
    manifest["manifest_hash"] = _canonical_hash(manifest)
    return validate_target_policy_manifest(
        manifest,
        samples,
        source_sample_sha256=source_sample_sha256,
    )


def build_current_deterministic_manifest(
    samples: Sequence[Mapping[str, Any]],
    *,
    source_sample_sha256: str,
) -> dict[str, Any]:
    """Materialize Current labels as an explicit deterministic target policy."""

    _validate_sha256(source_sample_sha256, field="source_sample_sha256")
    entries = []
    source_commits: set[str] = set()
    for row_number, sample in enumerate(samples, start=1):
        _validate_sample_identity(sample, source=f"sample {row_number}")
        sample_id = str(sample["sample_id"])
        source_commits.add(str(sample["behavior_policy_commit"]))
        support = {
            str(probability["action_id"])
            for probability in sample["exploration"]["candidate_distribution"]
        }
        label = sample.get("current_policy_label")
        if not isinstance(label, Mapping):
            raise OpeReadinessError(
                f"{sample_id}: current policy label is unmapped"
            )
        action_id = label.get("action_id")
        label_text = label.get("label")
        if (
            not isinstance(action_id, str)
            or action_id not in support
            or not isinstance(label_text, str)
            or not label_text
        ):
            raise OpeReadinessError(
                f"{sample_id}: current policy label is unmapped"
            )
        entries.append(
            {
                "sample_id": sample_id,
                "state_hash": str(sample["exploration"]["state_hash"]),
                "behavior_distribution_hash": str(
                    sample["exploration"]["distribution_hash"]
                ),
                "label_provenance": {
                    "action_id": action_id,
                    "label": label_text,
                    "source_field": "current_policy_label",
                },
                "probabilities": [
                    {
                        "action_id": candidate_action_id,
                        "numerator": int(candidate_action_id == action_id),
                        "denominator": 1,
                    }
                    for candidate_action_id in sorted(support)
                ],
            }
        )
    if len(source_commits) > 1:
        raise OpeReadinessError("current target policy commit is ambiguous")

    manifest = {
        "schema_version": TARGET_POLICY_SCHEMA_VERSION,
        "target_policy_id": "current_deterministic",
        "target_policy_commit": next(iter(source_commits), None),
        "source_sample_sha256": source_sample_sha256,
        "construction_mode": "current_deterministic",
        "diagnostic_only": False,
        "label_provenance": {
            "source_field": "current_policy_label",
            "mapping": "deterministic_action_id",
        },
        "entries": sorted(entries, key=lambda entry: entry["sample_id"]),
        "manifest_hash": None,
    }
    manifest["manifest_hash"] = _canonical_hash(manifest)
    return validate_target_policy_manifest(
        manifest,
        samples,
        source_sample_sha256=source_sample_sha256,
    )


def validate_target_policy_manifest(
    manifest: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    *,
    source_sample_sha256: str,
) -> dict[str, Any]:
    """Validate exact target probabilities against canonical logged support."""

    _validate_sha256(source_sample_sha256, field="source_sample_sha256")
    if not isinstance(manifest, Mapping):
        raise OpeReadinessError("target manifest must be a mapping")
    if manifest.get("schema_version") != TARGET_POLICY_SCHEMA_VERSION:
        raise OpeReadinessError("unsupported target policy schema")
    if manifest.get("source_sample_sha256") != source_sample_sha256:
        raise OpeReadinessError("source sample hash mismatch")
    target_policy_id = manifest.get("target_policy_id")
    if not isinstance(target_policy_id, str) or not target_policy_id:
        raise OpeReadinessError("target policy id is invalid")
    target_policy_commit = manifest.get("target_policy_commit")
    if target_policy_commit is not None and (
        not isinstance(target_policy_commit, str)
        or _COMMIT_PATTERN.fullmatch(target_policy_commit) is None
    ):
        raise OpeReadinessError("target policy commit is invalid")
    construction_mode = manifest.get("construction_mode")
    if construction_mode not in {
        "behavior_identity",
        "current_deterministic",
        "imported",
    }:
        raise OpeReadinessError("target construction mode is invalid")
    if not isinstance(manifest.get("diagnostic_only"), bool):
        raise OpeReadinessError("target diagnostic_only flag is invalid")
    if construction_mode == "current_deterministic" and manifest.get(
        "label_provenance"
    ) != {
        "source_field": "current_policy_label",
        "mapping": "deterministic_action_id",
    }:
        raise OpeReadinessError("current label provenance is invalid")

    samples_by_id: dict[str, Mapping[str, Any]] = {}
    for row_number, sample in enumerate(samples, start=1):
        _validate_sample_identity(sample, source=f"sample {row_number}")
        sample_id = str(sample["sample_id"])
        if sample_id in samples_by_id:
            raise OpeReadinessError(f"duplicate sample_id: {sample_id}")
        samples_by_id[sample_id] = sample

    entries = manifest.get("entries")
    if (
        isinstance(entries, (str, bytes))
        or not isinstance(entries, Sequence)
    ):
        raise OpeReadinessError("target entries are invalid")
    target_sample_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise OpeReadinessError("target entry must be a mapping")
        sample_id = entry.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise OpeReadinessError("target sample_id is invalid")
        if sample_id in target_sample_ids:
            raise OpeReadinessError(f"duplicate target sample_id: {sample_id}")
        target_sample_ids.add(sample_id)
        sample = samples_by_id.get(sample_id)
        if sample is None:
            continue
        exploration = sample["exploration"]
        if (
            entry.get("state_hash") != exploration.get("state_hash")
            or entry.get("behavior_distribution_hash")
            != exploration.get("distribution_hash")
        ):
            raise OpeReadinessError(f"{sample_id}: target row binding mismatch")

        probabilities = entry.get("probabilities")
        if (
            isinstance(probabilities, (str, bytes))
            or not isinstance(probabilities, Sequence)
            or not probabilities
        ):
            raise OpeReadinessError(f"{sample_id}: target probabilities are invalid")
        exact_probabilities: dict[str, Fraction] = {}
        for probability in probabilities:
            if not isinstance(probability, Mapping):
                raise OpeReadinessError(
                    f"{sample_id}: target probability is invalid"
                )
            action_id = probability.get("action_id")
            if not isinstance(action_id, str) or not action_id:
                raise OpeReadinessError(
                    f"{sample_id}: target action id is invalid"
                )
            if action_id in exact_probabilities:
                raise OpeReadinessError(
                    f"{sample_id}: duplicate target action: {action_id}"
                )
            exact_probabilities[action_id] = _target_probability_fraction(
                probability,
                sample_id=sample_id,
            )

        logged_support = {
            str(probability["action_id"])
            for probability in exploration["candidate_distribution"]
        }
        if set(exact_probabilities) != logged_support:
            raise OpeReadinessError(f"{sample_id}: target support mismatch")
        if sum(exact_probabilities.values(), Fraction(0, 1)) != Fraction(1, 1):
            raise OpeReadinessError(
                f"{sample_id}: target probabilities do not sum to one"
            )
        if construction_mode == "current_deterministic":
            provenance = entry.get("label_provenance")
            current_label = sample.get("current_policy_label")
            if (
                not isinstance(provenance, Mapping)
                or not isinstance(current_label, Mapping)
                or provenance.get("source_field") != "current_policy_label"
                or provenance.get("action_id") != current_label.get("action_id")
                or provenance.get("label") != current_label.get("label")
                or exact_probabilities.get(str(provenance.get("action_id")))
                != Fraction(1, 1)
            ):
                raise OpeReadinessError(
                    f"{sample_id}: current label provenance is invalid"
                )

    if target_sample_ids != set(samples_by_id):
        raise OpeReadinessError("target entries do not match samples")
    if manifest.get("manifest_hash") != _canonical_hash(manifest):
        raise OpeReadinessError("target manifest hash mismatch")
    return deepcopy(dict(manifest))


def compute_weight_diagnostics(
    audit: TrajectoryAudit,
    target_manifest: Mapping[str, Any],
) -> WeightDiagnostics:
    """Compute exact decision ratios and complete-run trajectory weights."""

    target_entries: dict[str, Mapping[str, Any]] = {}
    entries = target_manifest.get("entries")
    if isinstance(entries, (str, bytes)) or not isinstance(entries, Sequence):
        raise OpeReadinessError("target entries are invalid")
    for entry in entries:
        if not isinstance(entry, Mapping) or not isinstance(
            entry.get("sample_id"), str
        ):
            raise OpeReadinessError("target entry is invalid")
        sample_id = str(entry["sample_id"])
        if sample_id in target_entries:
            raise OpeReadinessError(f"duplicate target sample_id: {sample_id}")
        target_entries[sample_id] = entry

    trajectory_weights: list[TrajectoryWeight] = []
    arm_decisions: dict[tuple[str, str], int] = defaultdict(int)
    arm_trajectories: dict[tuple[str, str], set[str]] = defaultdict(set)
    for trajectory in audit.trajectories:
        decision_weights: list[DecisionWeight] = []
        trajectory_weight = Fraction(1, 1)
        for decision in trajectory.decisions:
            sample_id = str(decision["sample_id"])
            selected_action_id = str(decision["selected_action_id"])
            behavior_probability = _logged_selected_probability(decision)
            entry = target_entries.get(sample_id)
            if entry is None:
                raise OpeReadinessError(f"{sample_id}: target entry is missing")
            target_probabilities = {
                str(probability["action_id"]): _target_probability_fraction(
                    probability,
                    sample_id=sample_id,
                )
                for probability in entry["probabilities"]
            }
            if selected_action_id not in target_probabilities:
                raise OpeReadinessError(
                    f"{sample_id}: selected action is outside target support"
                )
            target_probability = target_probabilities[selected_action_id]
            ratio = target_probability / behavior_probability
            category = str(decision.get("category") or "unknown")
            selected_arm = str(
                decision["exploration"].get("selected_arm") or "unknown"
            )
            decision_weights.append(
                DecisionWeight(
                    sample_id=sample_id,
                    category=category,
                    selected_arm=selected_arm,
                    selected_action_id=selected_action_id,
                    behavior_probability=behavior_probability,
                    target_probability=target_probability,
                    ratio=ratio,
                    ratio_display=finite_fraction_value(ratio),
                )
            )
            trajectory_weight *= ratio
            arm_key = (category, selected_arm)
            arm_decisions[arm_key] += 1
            arm_trajectories[arm_key].add(trajectory.group_id)
        trajectory_weights.append(
            TrajectoryWeight(
                group_id=trajectory.group_id,
                decision_weights=tuple(decision_weights),
                weight=trajectory_weight,
                weight_display=finite_fraction_value(trajectory_weight),
            )
        )

    exact_weights = [row.weight for row in trajectory_weights]
    weight_sum = sum(exact_weights, Fraction(0, 1))
    squared_weight_sum = sum(
        (weight * weight for weight in exact_weights),
        Fraction(0, 1),
    )
    effective_sample_size = (
        weight_sum * weight_sum / squared_weight_sum
        if squared_weight_sum
        else Fraction(0, 1)
    )
    trajectory_count = len(trajectory_weights)
    ess_fraction = (
        effective_sample_size / trajectory_count
        if trajectory_count
        else Fraction(0, 1)
    )
    max_normalized_weight = (
        max(exact_weights) / weight_sum
        if exact_weights and weight_sum
        else Fraction(0, 1)
    )
    category_arm_support: dict[str, dict[str, dict[str, int]]] = {}
    for category, arm in sorted(arm_decisions):
        category_arm_support.setdefault(category, {})[arm] = {
            "decision_count": arm_decisions[(category, arm)],
            "trajectory_count": len(arm_trajectories[(category, arm)]),
        }

    victory_true = sum(
        int(trajectory.outcome.victory) for trajectory in audit.trajectories
    )
    floors = [
        trajectory.outcome.floor_reached for trajectory in audit.trajectories
    ]
    outcome_variation = {
        "floor_reached": {
            "maximum": max(floors) if floors else None,
            "minimum": min(floors) if floors else None,
            "unique_count": len(set(floors)),
        },
        "victory": {
            "false": trajectory_count - victory_true,
            "true": victory_true,
            "unique_count": len(
                {trajectory.outcome.victory for trajectory in audit.trajectories}
            ),
        },
    }
    nonzero_weight_count = sum(weight != 0 for weight in exact_weights)
    return WeightDiagnostics(
        trajectory_count=trajectory_count,
        decision_count=sum(
            len(trajectory.decisions) for trajectory in audit.trajectories
        ),
        nonzero_weight_count=nonzero_weight_count,
        zero_weight_count=trajectory_count - nonzero_weight_count,
        weight_sum=weight_sum,
        effective_sample_size=effective_sample_size,
        ess_fraction=ess_fraction,
        max_normalized_weight=max_normalized_weight,
        trajectory_weights=tuple(trajectory_weights),
        category_arm_support=category_arm_support,
        outcome_variation=outcome_variation,
    )


def finite_fraction_value(value: Fraction) -> float:
    """Render an exact fraction as a finite float without changing exact math."""

    try:
        rendered = float(value)
    except OverflowError:
        rendered = -sys.float_info.max if value < 0 else sys.float_info.max
    if math.isfinite(rendered):
        return rendered
    return math.copysign(sys.float_info.max, rendered)


def evaluate_identity_self_check(
    audit: TrajectoryAudit,
    target_manifest: Mapping[str, Any],
    diagnostics: WeightDiagnostics,
) -> IdentitySelfCheck:
    """Verify the exact invariants of the logged behavior identity target."""

    mismatches: list[str] = []
    if target_manifest.get("construction_mode") != "behavior_identity":
        mismatches.append("target_not_behavior_identity")
    if any(
        decision.ratio != Fraction(1, 1)
        for trajectory in diagnostics.trajectory_weights
        for decision in trajectory.decision_weights
    ):
        mismatches.append("decision_ratio_not_identity")
    if any(
        trajectory.weight != Fraction(1, 1)
        for trajectory in diagnostics.trajectory_weights
    ):
        mismatches.append("trajectory_weight_not_identity")
    if diagnostics.effective_sample_size != Fraction(
        audit.complete_trajectory_count,
        1,
    ):
        mismatches.append("effective_sample_size_not_identity")

    trajectory_count = audit.complete_trajectory_count
    if trajectory_count:
        unweighted_outcomes = {
            "floor_reached_mean": Fraction(
                sum(row.outcome.floor_reached for row in audit.trajectories),
                trajectory_count,
            ),
            "victory_mean": Fraction(
                sum(int(row.outcome.victory) for row in audit.trajectories),
                trajectory_count,
            ),
        }
    else:
        unweighted_outcomes = {
            "floor_reached_mean": Fraction(0, 1),
            "victory_mean": Fraction(0, 1),
        }

    weights_by_group = {
        row.group_id: row.weight for row in diagnostics.trajectory_weights
    }
    weight_sum = sum(weights_by_group.values(), Fraction(0, 1))
    if weight_sum:
        weighted_outcomes = {
            "floor_reached_mean": sum(
                weights_by_group.get(row.group_id, Fraction(0, 1))
                * row.outcome.floor_reached
                for row in audit.trajectories
            )
            / weight_sum,
            "victory_mean": sum(
                weights_by_group.get(row.group_id, Fraction(0, 1))
                * int(row.outcome.victory)
                for row in audit.trajectories
            )
            / weight_sum,
        }
    else:
        weighted_outcomes = {
            "floor_reached_mean": Fraction(0, 1),
            "victory_mean": Fraction(0, 1),
        }
    if weighted_outcomes != unweighted_outcomes:
        mismatches.append("weighted_outcome_not_identity")
    return IdentitySelfCheck(
        passed=not mismatches,
        mismatches=tuple(mismatches),
        unweighted_outcomes=unweighted_outcomes,
        weighted_outcomes=weighted_outcomes,
    )


def evaluate_overlap_screens(diagnostics: WeightDiagnostics) -> OverlapScreen:
    """Apply minimum overlap screens without validating an OPE estimator."""

    blockers: list[ReadinessBlocker] = []
    if diagnostics.trajectory_count < MIN_COMPLETE_TRAJECTORIES:
        blockers.append(
            ReadinessBlocker(
                code="complete_trajectory_count_below_minimum",
                observed=diagnostics.trajectory_count,
                required=MIN_COMPLETE_TRAJECTORIES,
            )
        )
    if diagnostics.nonzero_weight_count < MIN_NONZERO_WEIGHT_TRAJECTORIES:
        blockers.append(
            ReadinessBlocker(
                code="nonzero_weight_trajectory_count_below_minimum",
                observed=diagnostics.nonzero_weight_count,
                required=MIN_NONZERO_WEIGHT_TRAJECTORIES,
            )
        )
    if diagnostics.effective_sample_size < MIN_EFFECTIVE_SAMPLE_SIZE:
        blockers.append(
            ReadinessBlocker(
                code="effective_sample_size_below_minimum",
                observed=diagnostics.effective_sample_size,
                required=MIN_EFFECTIVE_SAMPLE_SIZE,
            )
        )
    if diagnostics.ess_fraction < MIN_ESS_FRACTION:
        blockers.append(
            ReadinessBlocker(
                code="ess_fraction_below_minimum",
                observed=diagnostics.ess_fraction,
                required=MIN_ESS_FRACTION,
            )
        )
    if diagnostics.max_normalized_weight > MAX_NORMALIZED_WEIGHT:
        blockers.append(
            ReadinessBlocker(
                code="max_normalized_weight_above_maximum",
                observed=diagnostics.max_normalized_weight,
                required=MAX_NORMALIZED_WEIGHT,
            )
        )
    victory_variation = diagnostics.outcome_variation.get("victory", {})
    if victory_variation.get("unique_count") != 2:
        blockers.append(
            ReadinessBlocker(
                code="primary_outcome_degenerate",
                observed=victory_variation.get("unique_count", 0),
                required=2,
            )
        )
    return OverlapScreen(
        ready=not blockers,
        blockers=tuple(blockers),
        estimator_validation_ready=False,
    )


def build_readiness_artifact(
    sample_path: Path | str,
    target_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a deterministic, estimate-free readiness artifact."""

    source = Path(sample_path)
    source_bytes = source.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    samples = load_canonical_samples(source)
    validated_manifest = validate_target_policy_manifest(
        target_manifest,
        samples,
        source_sample_sha256=source_sha256,
    )
    audit = audit_trajectories(samples)
    diagnostics = compute_weight_diagnostics(audit, validated_manifest)
    identity_check = evaluate_identity_self_check(
        audit,
        validated_manifest,
        diagnostics,
    )
    overlap = evaluate_overlap_screens(diagnostics)
    identity_applicable = (
        validated_manifest["construction_mode"] == "behavior_identity"
    )
    identity_passed = identity_applicable and identity_check.passed
    outcome_contract_ready = (
        audit.input_decision_count > 0
        and audit.complete_decision_count == audit.input_decision_count
        and not audit.blocked_trajectories
    )

    readiness = {
        "causal_uplift_ready": False,
        "estimator_validation_ready": False,
        "formal_noncombat_rl_training_ready": False,
        "identity_self_check_passed": identity_passed,
        "input_valid": True,
        "live_policy_promotion_ready": False,
        "ope_ready": False,
        "outcome_contract_ready": outcome_contract_ready,
        "overlap_ready": overlap.ready,
        "target_policy_ready": True,
    }
    blocker_codes = [blocker.code for blocker in overlap.blockers]
    if not outcome_contract_ready:
        blocker_codes.append("outcome_contract_incomplete")
    for blocked in audit.blocked_trajectories:
        blocker_codes.extend(
            f"trajectory:{blocked.group_id}:{reason}"
            for reason in blocked.reasons
        )
    if identity_applicable:
        blocker_codes.extend(
            f"identity:{mismatch}" for mismatch in identity_check.mismatches
        )
    else:
        blocker_codes.append("identity_self_check_not_applicable")
    blocker_codes.append("estimator_validation_not_implemented")

    target_text = render_target_manifest_json(validated_manifest)
    artifact = {
        "schema_version": READINESS_ARTIFACT_SCHEMA_VERSION,
        "source": {
            "sample_file": source.name,
            "sample_sha256": source_sha256,
            "sample_size_bytes": len(source_bytes),
            "target_manifest_content_sha256": hashlib.sha256(
                target_text.encode("utf-8")
            ).hexdigest(),
            "target_manifest_hash": validated_manifest["manifest_hash"],
        },
        "contracts": {
            "canonical_sample_schema_version": CANONICAL_EXPLORATION_SCHEMA_VERSION,
            "outcome_contract_version": OUTCOME_CONTRACT_VERSION,
            "overlap_screen_policy_version": OVERLAP_SCREEN_POLICY_VERSION,
            "primary_outcome": "victory",
            "secondary_outcome": "floor_reached",
            "target_policy_schema_version": TARGET_POLICY_SCHEMA_VERSION,
            "terminal_horizon": "complete_run",
        },
        "target_policy": {
            "construction_mode": validated_manifest["construction_mode"],
            "diagnostic_only": validated_manifest["diagnostic_only"],
            "target_policy_commit": validated_manifest["target_policy_commit"],
            "target_policy_id": validated_manifest["target_policy_id"],
        },
        "trajectory_audit": {
            "input_decision_count": audit.input_decision_count,
            "complete_decision_count": audit.complete_decision_count,
            "complete_trajectory_count": audit.complete_trajectory_count,
            "complete_trajectories": [
                {
                    "decision_count": len(trajectory.decisions),
                    "group_id": trajectory.group_id,
                    "outcome": {
                        "floor_reached": trajectory.outcome.floor_reached,
                        "killed_by": trajectory.outcome.killed_by,
                        "playtime": trajectory.outcome.playtime,
                        "run_file": trajectory.outcome.run_file,
                        "victory": trajectory.outcome.victory,
                    },
                    "trajectory_session_id": trajectory.trajectory_session_id,
                }
                for trajectory in audit.trajectories
            ],
            "blocked_trajectories": [
                {
                    "decision_count": blocked.decision_count,
                    "group_id": blocked.group_id,
                    "reasons": list(blocked.reasons),
                }
                for blocked in audit.blocked_trajectories
            ],
        },
        "diagnostics": {
            "trajectory_count": diagnostics.trajectory_count,
            "decision_count": diagnostics.decision_count,
            "nonzero_weight_count": diagnostics.nonzero_weight_count,
            "zero_weight_count": diagnostics.zero_weight_count,
            "zero_weight_fraction": _fraction_record(
                Fraction(
                    diagnostics.zero_weight_count,
                    diagnostics.trajectory_count or 1,
                )
            ),
            "weight_sum": _fraction_record(diagnostics.weight_sum),
            "effective_sample_size": _fraction_record(
                diagnostics.effective_sample_size
            ),
            "ess_fraction": _fraction_record(diagnostics.ess_fraction),
            "max_normalized_weight": _fraction_record(
                diagnostics.max_normalized_weight
            ),
            "category_arm_support": deepcopy(
                dict(diagnostics.category_arm_support)
            ),
            "outcome_variation": deepcopy(dict(diagnostics.outcome_variation)),
            "trajectory_weights": [
                {
                    "group_id": trajectory.group_id,
                    "weight": _fraction_record(trajectory.weight),
                    "decisions": [
                        {
                            "behavior_probability": _fraction_record(
                                decision.behavior_probability
                            ),
                            "category": decision.category,
                            "ratio": _fraction_record(decision.ratio),
                            "sample_id": decision.sample_id,
                            "selected_action_id": decision.selected_action_id,
                            "selected_arm": decision.selected_arm,
                            "target_probability": _fraction_record(
                                decision.target_probability
                            ),
                        }
                        for decision in trajectory.decision_weights
                    ],
                }
                for trajectory in diagnostics.trajectory_weights
            ],
        },
        "identity_self_check": {
            "applicable": identity_applicable,
            "passed": identity_passed,
            "mismatches": list(identity_check.mismatches),
            "unweighted_outcomes": {
                key: _fraction_record(value)
                for key, value in sorted(
                    identity_check.unweighted_outcomes.items()
                )
            },
            "weighted_outcomes": {
                key: _fraction_record(value)
                for key, value in sorted(identity_check.weighted_outcomes.items())
            },
        },
        "overlap_screens": {
            "policy": {
                "maximum_normalized_weight": _fraction_record(
                    MAX_NORMALIZED_WEIGHT
                ),
                "minimum_complete_trajectories": MIN_COMPLETE_TRAJECTORIES,
                "minimum_effective_sample_size": _fraction_record(
                    MIN_EFFECTIVE_SAMPLE_SIZE
                ),
                "minimum_ess_fraction": _fraction_record(MIN_ESS_FRACTION),
                "minimum_nonzero_weight_trajectories": (
                    MIN_NONZERO_WEIGHT_TRAJECTORIES
                ),
                "required_primary_outcome_unique_count": 2,
            },
            "ready": overlap.ready,
            "blockers": [
                {
                    "code": blocker.code,
                    "observed": _json_exact_value(blocker.observed),
                    "required": _json_exact_value(blocker.required),
                }
                for blocker in overlap.blockers
            ],
        },
        "readiness": readiness,
        "blockers": sorted(set(blocker_codes)),
        "limitations": [
            "No OPE estimator, policy value, uplift, or confidence interval is computed.",
            "Overlap screens reject weak support but do not validate an estimator.",
            "Terminal outcomes remain separate diagnostics, not a formal RL reward.",
        ],
    }
    return artifact


def render_target_manifest_json(manifest: Mapping[str, Any]) -> str:
    """Render a target manifest as stable LF-terminated JSON."""

    return json.dumps(
        manifest,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ) + "\n"


def render_readiness_json(artifact: Mapping[str, Any]) -> str:
    """Render a readiness artifact as stable LF-terminated JSON."""

    return json.dumps(
        artifact,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ) + "\n"


def render_readiness_markdown(artifact: Mapping[str, Any]) -> str:
    """Render the estimate-free readiness result for human review."""

    source = artifact["source"]
    audit = artifact["trajectory_audit"]
    diagnostics = artifact["diagnostics"]
    lines = [
        "# Non-combat OPE readiness",
        "",
        "Status: BLOCKED",
        "",
        "## Source",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| sample_file | {source['sample_file']} |",
        f"| sample_sha256 | `{source['sample_sha256']}` |",
        f"| target_manifest_hash | `{source['target_manifest_hash']}` |",
        "",
        "## Readiness gates",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| {gate} | {'PASS' if ready else 'BLOCKED'} |"
        for gate, ready in sorted(artifact["readiness"].items())
    )
    lines.extend(
        [
            "",
            "## Accounting",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| input decisions | {audit['input_decision_count']} |",
            f"| complete decisions | {audit['complete_decision_count']} |",
            f"| complete trajectories | {audit['complete_trajectory_count']} |",
            f"| blocked trajectories | {len(audit['blocked_trajectories'])} |",
            f"| nonzero-weight trajectories | {diagnostics['nonzero_weight_count']} |",
            f"| zero-weight trajectories | {diagnostics['zero_weight_count']} |",
            f"| exact ESS | {_exact_text(diagnostics['effective_sample_size'])} |",
            f"| exact ESS fraction | {_exact_text(diagnostics['ess_fraction'])} |",
            f"| exact max normalized weight | {_exact_text(diagnostics['max_normalized_weight'])} |",
            "",
            "## Blockers",
            "",
        ]
    )
    lines.extend(f"- `{blocker}`" for blocker in artifact["blockers"])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in artifact["limitations"])
    return "\n".join(lines) + "\n"


def write_target_manifest(
    sample_path: Path | str,
    *,
    mode: str,
    output_path: Path | str,
) -> dict[str, Any]:
    """Generate and atomically replace one built-in target manifest."""

    source = Path(sample_path)
    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    samples = load_canonical_samples(source)
    if mode == "behavior_identity":
        manifest = build_behavior_identity_manifest(
            samples,
            source_sample_sha256=source_sha256,
        )
    elif mode == "current_deterministic":
        manifest = build_current_deterministic_manifest(
            samples,
            source_sample_sha256=source_sha256,
        )
    else:
        raise OpeReadinessError(f"unsupported target mode: {mode}")
    destination = Path(output_path)
    _replace_files_transactionally(
        ((destination, render_target_manifest_json(manifest).encode("utf-8")),)
    )
    return manifest


def write_readiness_artifacts(
    sample_path: Path | str,
    *,
    output_prefix: Path | str,
    target_manifest_path: Path | str | None = None,
    target_mode: str | None = None,
) -> tuple[Path, Path]:
    """Build and transactionally replace a complete JSON/Markdown pair."""

    if (target_manifest_path is None) == (target_mode is None):
        raise OpeReadinessError(
            "provide exactly one of target_manifest_path or target_mode"
        )
    source = Path(sample_path)
    if target_manifest_path is not None:
        manifest = _load_json_mapping(
            Path(target_manifest_path),
            description="target manifest",
        )
    else:
        source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        samples = load_canonical_samples(source)
        if target_mode == "behavior_identity":
            manifest = build_behavior_identity_manifest(
                samples,
                source_sample_sha256=source_sha256,
            )
        elif target_mode == "current_deterministic":
            manifest = build_current_deterministic_manifest(
                samples,
                source_sample_sha256=source_sha256,
            )
        else:
            raise OpeReadinessError(f"unsupported target mode: {target_mode}")

    artifact = build_readiness_artifact(source, manifest)
    prefix = Path(output_prefix)
    json_path = Path(f"{prefix}.json")
    markdown_path = Path(f"{prefix}.md")
    _replace_files_transactionally(
        (
            (json_path, render_readiness_json(artifact).encode("utf-8")),
            (markdown_path, render_readiness_markdown(artifact).encode("utf-8")),
        )
    )
    return json_path, markdown_path


def main(argv: Sequence[str] | None = None) -> int:
    """Run target generation or readiness auditing without gameplay imports."""

    parser = argparse.ArgumentParser(
        description="Audit trajectory-level non-combat OPE readiness."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    target_parser = subparsers.add_parser(
        "build-target",
        help="materialize a built-in target-policy manifest",
    )
    target_parser.add_argument("--samples", required=True, type=Path)
    target_parser.add_argument(
        "--mode",
        required=True,
        choices=("behavior_identity", "current_deterministic"),
    )
    target_parser.add_argument("--output", required=True, type=Path)

    audit_parser = subparsers.add_parser(
        "audit",
        help="write estimate-free readiness JSON and Markdown",
    )
    audit_parser.add_argument("--samples", required=True, type=Path)
    target_group = audit_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--target-manifest", type=Path)
    target_group.add_argument(
        "--target-mode",
        choices=("behavior_identity", "current_deterministic"),
    )
    audit_parser.add_argument("--output-prefix", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "build-target":
            write_target_manifest(
                args.samples,
                mode=args.mode,
                output_path=args.output,
            )
            print(args.output)
        else:
            json_path, markdown_path = write_readiness_artifacts(
                args.samples,
                target_manifest_path=args.target_manifest,
                target_mode=args.target_mode,
                output_prefix=args.output_prefix,
            )
            print(json_path)
            print(markdown_path)
    except (OpeReadinessError, OSError, UnicodeError, ValueError) as exc:
        print(f"noncombat OPE readiness error: {exc}", file=sys.stderr)
        return 2
    return 0


def _fraction_record(value: Fraction) -> dict[str, Any]:
    return {
        "denominator": value.denominator,
        "numerator": value.numerator,
        "value": finite_fraction_value(value),
    }


def _json_exact_value(value: Any) -> Any:
    if isinstance(value, Fraction):
        return _fraction_record(value)
    return value


def _exact_text(record: Mapping[str, Any]) -> str:
    numerator = record["numerator"]
    denominator = record["denominator"]
    return str(numerator) if denominator == 1 else f"{numerator}/{denominator}"


def _load_json_mapping(path: Path, *, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise OpeReadinessError(f"{path}: malformed {description}") from exc
    if not isinstance(value, dict):
        raise OpeReadinessError(f"{path}: {description} must be a JSON object")
    return value


def _replace_files_transactionally(
    payloads: Sequence[tuple[Path, bytes]],
) -> None:
    destinations = [Path(destination) for destination, _data in payloads]
    if len(set(destinations)) != len(destinations):
        raise OpeReadinessError("transaction destinations must be unique")
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_files: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    installed: list[Path] = []
    try:
        for destination, data in payloads:
            temporary_files[destination] = _write_temporary_file(destination, data)
        for destination in destinations:
            if destination.exists():
                backup = _reserve_backup_path(destination)
                os.replace(destination, backup)
                backups[destination] = backup
        for destination in destinations:
            os.replace(temporary_files[destination], destination)
            installed.append(destination)
    except Exception:
        for destination in reversed(installed):
            if destination.exists():
                destination.unlink()
        for destination, backup in backups.items():
            if backup.exists():
                os.replace(backup, destination)
        raise
    finally:
        for temporary in temporary_files.values():
            if temporary.exists():
                temporary.unlink()
        for backup in backups.values():
            if backup.exists():
                backup.unlink()


def _write_temporary_file(destination: Path, data: bytes) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    ) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        return Path(handle.name)


def _reserve_backup_path(destination: Path) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".bak",
        dir=destination.parent,
    )
    os.close(descriptor)
    backup = Path(raw_path)
    backup.unlink()
    return backup


def _validate_sample_identity(sample: Mapping[str, Any], *, source: str) -> None:
    if not isinstance(sample, Mapping):
        raise OpeReadinessError(f"{source}: sample must be a mapping")
    if sample.get("schema_version") != CANONICAL_EXPLORATION_SCHEMA_VERSION:
        raise OpeReadinessError(f"{source}: unsupported canonical sample schema")

    sample_id = sample.get("sample_id")
    group_id = sample.get("trajectory_group_id")
    trajectory_session_id = sample.get("trajectory_session_id")
    if not isinstance(sample_id, str) or not sample_id:
        raise OpeReadinessError(f"{source}: sample_id is required")
    if (
        not isinstance(group_id, str)
        or not group_id.startswith("run:")
        or not group_id.removeprefix("run:")
    ):
        raise OpeReadinessError(f"{source}: trajectory_group_id is invalid")
    if not isinstance(trajectory_session_id, str) or not trajectory_session_id:
        raise OpeReadinessError(f"{source}: trajectory_session_id is required")

    exploration = sample.get("exploration")
    if not isinstance(exploration, Mapping):
        raise OpeReadinessError(f"{source}: exploration block is required")
    if exploration.get("decision_id") != sample_id:
        raise OpeReadinessError(f"{source}: decision identity mismatch")
    decision_index = exploration.get("decision_index")
    if (
        isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index < 0
    ):
        raise OpeReadinessError(f"{source}: decision_index is invalid")
    if exploration.get("trajectory_session_id") != trajectory_session_id:
        raise OpeReadinessError(f"{source}: trajectory provenance mismatch")

    policy_id = sample.get("behavior_policy_id")
    policy_commit = sample.get("behavior_policy_commit")
    session_id = exploration.get("session_id")
    if (
        not isinstance(policy_id, str)
        or not isinstance(session_id, str)
        or policy_id != f"known-propensity-epsilon-v1:{session_id}"
    ):
        raise OpeReadinessError(f"{source}: behavior session provenance mismatch")
    if (
        not isinstance(policy_commit, str)
        or _COMMIT_PATTERN.fullmatch(policy_commit) is None
        or exploration.get("source_commit") != policy_commit
    ):
        raise OpeReadinessError(f"{source}: source commit provenance mismatch")

    evidence = behavior_evidence_status(sample)
    if evidence["verified"] is not True:
        raise OpeReadinessError(
            f"{source}: behavior evidence invalid: {evidence['reason']}"
        )


def _target_probability_fraction(
    record: Mapping[str, Any],
    *,
    sample_id: str,
) -> Fraction:
    numerator = record.get("numerator")
    denominator = record.get("denominator")
    if (
        isinstance(numerator, bool)
        or not isinstance(numerator, int)
        or isinstance(denominator, bool)
        or not isinstance(denominator, int)
        or numerator < 0
        or denominator <= 0
        or numerator > denominator
    ):
        raise OpeReadinessError(f"{sample_id}: target probability is invalid")
    return Fraction(numerator, denominator)


def _logged_selected_probability(sample: Mapping[str, Any]) -> Fraction:
    sample_id = str(sample.get("sample_id") or "<unknown>")
    selected = sample["exploration"].get("selected_probability")
    if not isinstance(selected, Mapping):
        raise OpeReadinessError(
            f"{sample_id}: logged selected probability is invalid"
        )
    probability = _target_probability_fraction(selected, sample_id=sample_id)
    if probability <= 0:
        raise OpeReadinessError(
            f"{sample_id}: logged selected probability must be positive"
        )
    return probability


def _validate_sha256(value: Any, *, field: str) -> None:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise OpeReadinessError(f"{field} is invalid")


def _canonical_hash(record: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(record))
    if "manifest_hash" in payload:
        payload["manifest_hash"] = None
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _trajectory_outcome(
    group_id: str,
    decisions: Sequence[Mapping[str, Any]],
) -> tuple[set[str], TerminalOutcome | None]:
    reasons: set[str] = set()
    expected_run_file = f"{group_id.removeprefix('run:')}.run"

    if len({str(row["trajectory_session_id"]) for row in decisions}) != 1:
        reasons.add("trajectory_session_conflict")
    if len({str(row["behavior_policy_id"]) for row in decisions}) != 1:
        reasons.add("behavior_policy_conflict")
    if len({str(row["behavior_policy_commit"]) for row in decisions}) != 1:
        reasons.add("source_commit_conflict")
    if len({str(row["exploration"]["session_id"]) for row in decisions}) != 1:
        reasons.add("behavior_session_conflict")

    valid_outcomes: list[TerminalOutcome] = []
    for sample in decisions:
        outcome = sample.get("outcome")
        if not isinstance(outcome, Mapping):
            reasons.add("outcome_missing")
            continue
        if outcome.get("included_in_gate") is not True:
            reasons.add("outcome_not_included")
        if outcome.get("join_status") != "matched":
            reasons.add("outcome_not_matched")

        run_file = outcome.get("run_file")
        victory = outcome.get("victory")
        floor_reached = outcome.get("floor_reached")
        killed_by = outcome.get("killed_by")
        playtime = outcome.get("playtime")
        fields_valid = True
        if run_file != expected_run_file:
            reasons.add("outcome_run_file_mismatch")
            fields_valid = False
        if not isinstance(victory, bool):
            reasons.add("outcome_victory_invalid")
            fields_valid = False
        if (
            isinstance(floor_reached, bool)
            or not isinstance(floor_reached, int)
            or floor_reached <= 0
        ):
            reasons.add("outcome_floor_reached_invalid")
            fields_valid = False
        if not isinstance(killed_by, str):
            reasons.add("outcome_killed_by_invalid")
            fields_valid = False
        if (
            isinstance(playtime, bool)
            or not isinstance(playtime, int)
            or playtime < 0
        ):
            reasons.add("outcome_playtime_invalid")
            fields_valid = False

        decision_floor = sample.get("floor")
        if (
            fields_valid
            and (
                isinstance(decision_floor, bool)
                or not isinstance(decision_floor, int)
                or decision_floor < 0
                or decision_floor > floor_reached
            )
        ):
            reasons.add("outcome_floor_precedes_decision")
        if fields_valid:
            valid_outcomes.append(
                TerminalOutcome(
                    run_file=run_file,
                    victory=victory,
                    floor_reached=floor_reached,
                    killed_by=killed_by,
                    playtime=playtime,
                )
            )

    if len(set(valid_outcomes)) > 1:
        reasons.add("outcome_conflict")
    if reasons or not valid_outcomes:
        return reasons or {"outcome_missing"}, None
    return reasons, valid_outcomes[0]


if __name__ == "__main__":
    raise SystemExit(main())

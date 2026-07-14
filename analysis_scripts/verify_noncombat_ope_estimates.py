"""Independently replay persisted non-combat OPE estimate artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Any

from analysis_scripts.verify_noncombat_ope_artifacts import (
    ArtifactVerificationError,
    verify_artifact_pair,
)


_ESTIMATE_SCHEMA = "noncombat-ope-estimate-v1"
_CALIBRATION_SCHEMA = "noncombat-ope-estimator-calibration-v1"
_BOOTSTRAP_SCHEMA = "noncombat-ope-bootstrap-draw-v1"
_PRODUCTION_REPLICATES = 10_000
_PRODUCTION_CONFIDENCE = Fraction(95, 100)


class EstimateVerificationError(ValueError):
    """Raised when a persisted estimate cannot be replayed exactly."""


class _DuplicateJsonKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


class _Checks:
    def __init__(self) -> None:
        self.count = 0

    def require(self, condition: bool, message: str) -> None:
        self.count += 1
        if not condition:
            raise EstimateVerificationError(message)


@dataclass(frozen=True)
class _Trajectory:
    group_id: str
    weight: Fraction
    victory: bool
    floor_reached: int
    sample_ids: tuple[str, ...]


def verify_calibration_artifact(
    calibration_path: Path | str,
    *,
    dataset_limit: int | None = None,
) -> dict[str, Any]:
    """Independently replay exact fixtures and deterministic coverage data."""

    checks = _Checks()
    calibration_path = Path(calibration_path)
    calibration = _load_mapping(calibration_path)
    _verify_calibration_structure(calibration, checks)
    configuration = calibration["configuration"]
    _verify_calibration_configuration(configuration, checks)
    _replay_exact_calibration(calibration["exact_calibration"], checks)
    dataset_count = configuration["dataset_count"]
    if dataset_limit is not None:
        checks.require(
            type(dataset_limit) is int and 0 < dataset_limit <= dataset_count,
            "calibration dataset limit is invalid",
        )
        replay_count = dataset_limit
    else:
        replay_count = dataset_count
    _replay_coverage_prefix(
        calibration["coverage_calibration"],
        configuration,
        replay_count,
        checks,
        verify_aggregate=dataset_limit is None,
    )
    return {
        "calibration_file_sha256": _file_sha256(calibration_path),
        "check_count": checks.count,
        "coverage_datasets_replayed": replay_count,
        "exact_calibration_replayed": True,
        "full_replay": dataset_limit is None,
        "passed": True,
        "verifier_implementation_sha256": _file_sha256(Path(__file__)),
    }


def verify_estimate_artifact(
    *,
    sample_path: Path | str,
    target_manifest_path: Path | str,
    readiness_path: Path | str,
    calibration_path: Path | str,
    estimate_path: Path | str,
    full_calibration_replay: bool = True,
) -> dict[str, Any]:
    """Replay one estimate without importing its implementation modules."""

    checks = _Checks()
    sample_path = Path(sample_path)
    target_manifest_path = Path(target_manifest_path)
    readiness_path = Path(readiness_path)
    calibration_path = Path(calibration_path)
    estimate_path = Path(estimate_path)
    try:
        readiness_audit = verify_artifact_pair(
            sample_path,
            target_manifest_path,
            readiness_path,
        )
    except ArtifactVerificationError as exc:
        raise EstimateVerificationError(
            f"independent readiness replay failed: {exc}"
        ) from exc
    checks.require(readiness_audit.get("passed") is True, "readiness replay failed")
    checks.require(
        not readiness_audit.get("overlap_blockers"),
        "readiness overlap blockers present",
    )

    readiness = _load_mapping(readiness_path)
    calibration = _load_mapping(calibration_path)
    estimate = _load_mapping(estimate_path)
    checks.require(
        estimate.get("schema_version") == _ESTIMATE_SCHEMA,
        "estimate schema mismatch",
    )
    _verify_calibration_structure(calibration, checks)

    source = estimate.get("source")
    checks.require(isinstance(source, Mapping), "estimate source block missing")
    expected_source = {
        "calibration_file_sha256": _file_sha256(calibration_path),
        "estimate_artifact_implementation_sha256": _file_sha256(
            Path(__file__).with_name("noncombat_ope_estimate_artifacts.py")
        ),
        "estimator_implementation_sha256": _file_sha256(
            Path(__file__).with_name("noncombat_ope_estimation.py")
        ),
        "readiness_file_sha256": _file_sha256(readiness_path),
        "sample_file_sha256": _file_sha256(sample_path),
        "target_file_sha256": _file_sha256(target_manifest_path),
    }
    checks.require(dict(source) == expected_source, "estimate source hashes mismatch")

    trajectories = _reconstruct_trajectories(readiness, checks)
    estimates = _estimate_channels(trajectories)
    _verify_estimates(estimate.get("estimates"), estimates, checks, "point")
    accounting = estimate.get("accounting")
    checks.require(isinstance(accounting, Mapping), "estimate accounting missing")
    decision_count = sum(len(row.sample_ids) for row in trajectories)
    checks.require(
        accounting.get("trajectory_count") == len(trajectories),
        "estimate trajectory count mismatch",
    )
    checks.require(
        accounting.get("decision_count") == decision_count,
        "estimate decision count mismatch",
    )
    checks.require(
        accounting.get("nonzero_weight_count")
        == sum(row.weight > 0 for row in trajectories),
        "estimate nonzero weight count mismatch",
    )
    checks.require(
        accounting.get("zero_weight_count")
        == sum(row.weight == 0 for row in trajectories),
        "estimate zero weight count mismatch",
    )
    checks.require(
        accounting.get("victory_count") == sum(int(row.victory) for row in trajectories),
        "estimate victory count mismatch",
    )
    for key in (
        "effective_sample_size",
        "ess_fraction",
        "max_normalized_weight",
    ):
        checks.require(
            accounting.get(key) == readiness_audit.get(key),
            f"estimate overlap metric mismatch: {key}",
        )

    bootstrap = _replay_bootstrap(
        trajectories,
        estimate.get("bootstrap"),
        checks,
    )
    influence = _replay_influence(
        trajectories,
        estimates,
        estimate.get("influence"),
        checks,
    )
    _verify_diagnostics(
        trajectories,
        estimates,
        estimate.get("diagnostics"),
        checks,
    )
    gate_result = _verify_gates(
        calibration,
        readiness_audit,
        estimates,
        bootstrap,
        influence,
        estimate,
        checks,
    )
    if full_calibration_replay:
        calibration_audit = verify_calibration_artifact(calibration_path)
        checks.require(
            calibration_audit.get("passed") is True
            and calibration_audit.get("full_replay") is True,
            "full calibration replay failed",
        )

    return {
        "bootstrap_replicate_count": bootstrap["replicate_count"],
        "calibration_full_replay": full_calibration_replay,
        "check_count": checks.count,
        "decision_count": decision_count,
        "estimate_file_sha256": _file_sha256(estimate_path),
        "passed": True,
        "policy_comparison_ready": gate_result["policy_comparison_ready"],
        "trajectory_count": len(trajectories),
        "verifier_implementation_sha256": _file_sha256(Path(__file__)),
    }


def _verify_calibration_structure(
    calibration: Mapping[str, Any],
    checks: _Checks,
) -> None:
    checks.require(
        calibration.get("schema_version") == _CALIBRATION_SCHEMA,
        "calibration schema mismatch",
    )
    source = calibration.get("source")
    checks.require(isinstance(source, Mapping), "calibration source missing")
    checks.require(
        source.get("estimator_implementation_sha256")
        == _file_sha256(Path(__file__).with_name("noncombat_ope_estimation.py")),
        "calibration estimator implementation hash mismatch",
    )
    checks.require(
        source.get("calibration_implementation_sha256")
        == _file_sha256(Path(__file__).with_name("noncombat_ope_calibration.py")),
        "calibration implementation hash mismatch",
    )
    configuration = calibration.get("configuration")
    exact = calibration.get("exact_calibration")
    checks.require(isinstance(configuration, Mapping), "calibration config missing")
    checks.require(isinstance(exact, Mapping), "calibration exact checks missing")
    checks.require(
        source.get("configuration_sha256") == _canonical_sha256(configuration),
        "calibration configuration hash mismatch",
    )
    checks.require(
        source.get("fixtures_sha256") == _canonical_sha256(exact),
        "calibration fixture hash mismatch",
    )
    checks.require(calibration.get("blockers") == [], "calibration blockers present")
    gates = calibration.get("gates")
    checks.require(
        isinstance(gates, Mapping)
        and gates.get("estimator_validation_ready") is True,
        "calibration gate is not ready",
    )
    checks.require(
        calibration.get("downstream_gates")
        == {
            "causal_uplift_ready": False,
            "formal_noncombat_rl_training_ready": False,
            "live_policy_promotion_ready": False,
        },
        "calibration downstream gate mismatch",
    )
    checks.require(exact.get("passed") is True, "exact calibration did not pass")
    exact_checks = exact.get("checks")
    checks.require(isinstance(exact_checks, Mapping), "exact checks missing")
    for name in (
        "balanced_one_step_known_truth",
        "behavior_identity",
        "bootstrap_exact_enumeration",
        "multi_decision_known_truth",
        "ordering_invariance",
    ):
        checks.require(
            isinstance(exact_checks.get(name), Mapping)
            and exact_checks[name].get("passed") is True,
            f"exact calibration check failed: {name}",
        )


def _reconstruct_trajectories(
    readiness: Mapping[str, Any],
    checks: _Checks,
) -> tuple[_Trajectory, ...]:
    audit = readiness.get("trajectory_audit")
    diagnostics = readiness.get("diagnostics")
    checks.require(isinstance(audit, Mapping), "trajectory audit missing")
    checks.require(isinstance(diagnostics, Mapping), "weight diagnostics missing")
    outcome_rows = audit.get("complete_trajectories")
    weight_rows = diagnostics.get("trajectory_weights")
    checks.require(isinstance(outcome_rows, list), "trajectory outcomes missing")
    checks.require(isinstance(weight_rows, list), "trajectory weights missing")
    outcomes: dict[str, tuple[bool, int]] = {}
    for row in outcome_rows:
        checks.require(isinstance(row, Mapping), "invalid trajectory outcome row")
        group_id = row.get("group_id")
        checks.require(
            isinstance(group_id, str) and group_id not in outcomes,
            "duplicate trajectory outcome",
        )
        outcome = row.get("outcome")
        checks.require(isinstance(outcome, Mapping), "terminal outcome missing")
        victory = outcome.get("victory")
        floor_reached = outcome.get("floor_reached")
        checks.require(type(victory) is bool, "invalid victory outcome")
        checks.require(
            type(floor_reached) is int and floor_reached >= 0,
            "invalid floor outcome",
        )
        outcomes[group_id] = (victory, floor_reached)
    weights: dict[str, tuple[Fraction, tuple[str, ...]]] = {}
    all_sample_ids: set[str] = set()
    for row in weight_rows:
        checks.require(isinstance(row, Mapping), "invalid trajectory weight row")
        group_id = row.get("group_id")
        checks.require(
            isinstance(group_id, str) and group_id not in weights,
            "duplicate trajectory weight",
        )
        weight = _reported_fraction(row.get("weight"), checks, "trajectory weight")
        checks.require(weight >= 0, "negative trajectory weight")
        decisions = row.get("decisions")
        checks.require(isinstance(decisions, list) and decisions, "decisions missing")
        sample_ids: list[str] = []
        for decision in decisions:
            checks.require(isinstance(decision, Mapping), "invalid decision row")
            sample_id = decision.get("sample_id")
            checks.require(
                isinstance(sample_id, str)
                and sample_id
                and sample_id not in all_sample_ids,
                "duplicate estimator sample",
            )
            all_sample_ids.add(sample_id)
            sample_ids.append(sample_id)
        weights[group_id] = (weight, tuple(sample_ids))
    checks.require(set(outcomes) == set(weights), "trajectory key mismatch")
    trajectories = tuple(
        _Trajectory(
            group_id=group_id,
            weight=weights[group_id][0],
            victory=outcomes[group_id][0],
            floor_reached=outcomes[group_id][1],
            sample_ids=weights[group_id][1],
        )
        for group_id in sorted(outcomes)
    )
    checks.require(
        sum((row.weight for row in trajectories), Fraction(0, 1)) > 0,
        "trajectory denominator is zero",
    )
    return trajectories


def _estimate_channels(
    trajectories: tuple[_Trajectory, ...],
) -> dict[str, dict[str, Fraction]]:
    return {
        "floor_reached": _estimate_channel(
            trajectories,
            tuple(Fraction(row.floor_reached, 1) for row in trajectories),
        ),
        "victory": _estimate_channel(
            trajectories,
            tuple(Fraction(int(row.victory), 1) for row in trajectories),
        ),
    }


def _estimate_channel(
    trajectories: tuple[_Trajectory, ...],
    outcomes: tuple[Fraction, ...],
) -> dict[str, Fraction]:
    count = len(trajectories)
    weight_sum = sum((row.weight for row in trajectories), Fraction(0, 1))
    if weight_sum <= 0:
        raise EstimateVerificationError("self-normalized denominator is zero")
    behavior = sum(outcomes, Fraction(0, 1)) / count
    weighted = sum(
        (row.weight * outcome for row, outcome in zip(trajectories, outcomes)),
        Fraction(0, 1),
    )
    ordinary = weighted / count
    self_normalized = weighted / weight_sum
    return {
        "behavior": behavior,
        "ordinary_is": ordinary,
        "ordinary_uplift": ordinary - behavior,
        "self_normalized_is": self_normalized,
        "self_normalized_uplift": self_normalized - behavior,
    }


def _verify_estimates(
    reported: Any,
    expected: Mapping[str, Mapping[str, Fraction]],
    checks: _Checks,
    label: str,
) -> None:
    checks.require(isinstance(reported, Mapping), f"{label} estimates missing")
    checks.require(set(reported) == set(expected), f"{label} channels mismatch")
    for channel, fields in expected.items():
        reported_fields = reported.get(channel)
        checks.require(
            isinstance(reported_fields, Mapping),
            f"{label} channel missing: {channel}",
        )
        checks.require(
            set(reported_fields) == set(fields),
            f"{label} estimate fields mismatch: {channel}",
        )
        for field, value in fields.items():
            _require_fraction_record(
                reported_fields.get(field),
                value,
                checks,
                f"{label}:{channel}:{field}",
            )


def _replay_bootstrap(
    trajectories: tuple[_Trajectory, ...],
    reported: Any,
    checks: _Checks,
) -> dict[str, Any]:
    checks.require(isinstance(reported, Mapping), "bootstrap block missing")
    checks.require(
        reported.get("schema_version") == _BOOTSTRAP_SCHEMA,
        "bootstrap schema mismatch",
    )
    seed = reported.get("seed")
    replicate_count = reported.get("effective_replicate_count")
    checks.require(isinstance(seed, str) and seed, "bootstrap seed missing")
    checks.require(
        type(replicate_count) is int and replicate_count > 0,
        "bootstrap replicate count invalid",
    )
    checks.require(
        reported.get("production_replicate_count") == _PRODUCTION_REPLICATES,
        "production bootstrap count mismatch",
    )
    confidence = _reported_fraction(
        reported.get("confidence_level"),
        checks,
        "bootstrap confidence",
    )
    checks.require(0 < confidence < 1, "bootstrap confidence invalid")
    draw_digest = hashlib.sha256()
    estimate_digest = hashlib.sha256()
    values = {
        channel: {field: [] for field in _ESTIMATE_FIELDS}
        for channel in ("floor_reached", "victory")
    }
    undefined: list[dict[str, Any]] = []
    zero_victory_count = 0
    for replicate_index in range(replicate_count):
        draw_indices: list[int] = []
        selected: list[_Trajectory] = []
        for draw_index in range(len(trajectories)):
            selected_index = _hash_draw_index(
                len(trajectories),
                seed,
                replicate_index,
                draw_index,
            )
            checks.require(
                0 <= selected_index < len(trajectories),
                "bootstrap draw index out of range",
            )
            draw_indices.append(selected_index)
            selected.append(trajectories[selected_index])
        _update_jsonl_digest(
            draw_digest,
            {
                "draw_indices": draw_indices,
                "replicate_index": replicate_index,
            },
        )
        selected_tuple = tuple(selected)
        if sum((row.weight for row in selected_tuple), Fraction(0, 1)) <= 0:
            replicate_estimates = None
            undefined.append(
                {
                    "draw_group_ids": [row.group_id for row in selected_tuple],
                    "draw_indices": draw_indices,
                    "reason": "self_normalized_denominator_zero",
                    "replicate_index": replicate_index,
                }
            )
        else:
            replicate_estimates = _estimate_channels(selected_tuple)
            if replicate_estimates["victory"]["behavior"] == 0:
                zero_victory_count += 1
            for channel, fields in replicate_estimates.items():
                for field, value in fields.items():
                    values[channel][field].append(value)
        _update_jsonl_digest(
            estimate_digest,
            {
                "estimates": (
                    _exact_estimates_record(replicate_estimates)
                    if replicate_estimates is not None
                    else None
                ),
                "replicate_index": replicate_index,
            },
        )
    checks.require(
        reported.get("draws_sha256") == draw_digest.hexdigest(),
        "bootstrap draw commitment mismatch",
    )
    checks.require(
        reported.get("replicate_estimates_sha256") == estimate_digest.hexdigest(),
        "bootstrap estimate commitment mismatch",
    )
    checks.require(
        reported.get("undefined_replicates") == undefined,
        "bootstrap undefined replicate mismatch",
    )
    checks.require(
        reported.get("zero_victory_replicate_count") == zero_victory_count,
        "zero-victory bootstrap count mismatch",
    )
    ready = not undefined
    blockers = [] if ready else ["bootstrap_undefined_replicates"]
    checks.require(reported.get("ready") is ready, "bootstrap ready mismatch")
    checks.require(reported.get("blockers") == blockers, "bootstrap blockers mismatch")
    expected_intervals = (
        {
            channel: {
                field: _percentile_interval(field_values, confidence)
                for field, field_values in fields.items()
            }
            for channel, fields in values.items()
        }
        if ready
        else {}
    )
    _verify_intervals(
        reported.get("intervals"),
        expected_intervals,
        checks,
    )
    return {
        "confidence": confidence,
        "intervals": expected_intervals,
        "ready": ready,
        "replicate_count": replicate_count,
    }


def _replay_influence(
    trajectories: tuple[_Trajectory, ...],
    full_estimates: Mapping[str, Mapping[str, Fraction]],
    reported: Any,
    checks: _Checks,
) -> dict[str, Any]:
    checks.require(isinstance(reported, Mapping), "influence block missing")
    reported_rows = reported.get("rows")
    checks.require(isinstance(reported_rows, list), "influence rows missing")
    checks.require(
        len(reported_rows) == len(trajectories),
        "influence row count mismatch",
    )
    undefined: list[str] = []
    changes: list[dict[str, dict[str, Fraction]]] = []
    snis_uplifts: list[Fraction] = []
    for excluded_index, excluded in enumerate(trajectories):
        row = reported_rows[excluded_index]
        checks.require(isinstance(row, Mapping), "invalid influence row")
        checks.require(
            row.get("excluded_group_id") == excluded.group_id,
            "influence exclusion order mismatch",
        )
        remaining = trajectories[:excluded_index] + trajectories[excluded_index + 1 :]
        if sum((item.weight for item in remaining), Fraction(0, 1)) <= 0:
            checks.require(row.get("estimates") is None, "undefined influence estimates")
            checks.require(
                row.get("blocker") == "self_normalized_denominator_zero",
                "undefined influence blocker mismatch",
            )
            checks.require(row.get("absolute_changes") == {}, "undefined changes present")
            checks.require(row.get("sign_changes") == {}, "undefined signs present")
            undefined.append(excluded.group_id)
            continue
        estimates = _estimate_channels(remaining)
        _verify_estimates(
            row.get("estimates"),
            estimates,
            checks,
            f"influence:{excluded.group_id}",
        )
        checks.require(row.get("blocker") is None, "defined influence blocker present")
        absolute = {
            channel: {
                field: abs(value - full_estimates[channel][field])
                for field, value in fields.items()
            }
            for channel, fields in estimates.items()
        }
        _verify_nested_fractions(
            row.get("absolute_changes"),
            absolute,
            checks,
            f"influence changes:{excluded.group_id}",
        )
        signs = {
            channel: {
                field: _sign(fields[field]) != _sign(full_estimates[channel][field])
                for field in ("ordinary_uplift", "self_normalized_uplift")
            }
            for channel, fields in estimates.items()
        }
        checks.require(row.get("sign_changes") == signs, "influence sign mismatch")
        changes.append(absolute)
        snis_uplifts.append(estimates["victory"]["self_normalized_uplift"])
    checks.require(
        reported.get("undefined_group_ids") == undefined,
        "influence undefined group mismatch",
    )
    maximum = {
        channel: {
            field: max(row[channel][field] for row in changes)
            for field in _ESTIMATE_FIELDS
        }
        for channel in ("floor_reached", "victory")
    }
    _verify_nested_fractions(
        reported.get("max_absolute_changes"),
        maximum,
        checks,
        "influence maxima",
    )
    return {
        "all_defined": not undefined,
        "victory_snis_uplifts": tuple(snis_uplifts),
    }


def _verify_diagnostics(
    trajectories: tuple[_Trajectory, ...],
    estimates: Mapping[str, Mapping[str, Fraction]],
    reported: Any,
    checks: _Checks,
) -> None:
    checks.require(isinstance(reported, Mapping), "estimator diagnostics missing")
    identity_applicable = all(row.weight == 1 for row in trajectories)
    identity_passed = identity_applicable and all(
        fields["ordinary_is"] == fields["behavior"]
        and fields["self_normalized_is"] == fields["behavior"]
        for fields in estimates.values()
    )
    checks.require(
        reported.get("behavior_identity")
        == {"applicable": identity_applicable, "passed": identity_passed},
        "behavior identity diagnostic mismatch",
    )
    directions = {
        channel: {
            "agree": _sign(fields["ordinary_uplift"])
            == _sign(fields["self_normalized_uplift"]),
            "ordinary_is": _sign(fields["ordinary_uplift"]),
            "self_normalized_is": _sign(fields["self_normalized_uplift"]),
        }
        for channel, fields in estimates.items()
    }
    checks.require(
        reported.get("estimator_direction") == directions,
        "estimator direction diagnostic mismatch",
    )


def _verify_gates(
    calibration: Mapping[str, Any],
    readiness_audit: Mapping[str, Any],
    estimates: Mapping[str, Mapping[str, Fraction]],
    bootstrap: Mapping[str, Any],
    influence: Mapping[str, Any],
    estimate: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, bool]:
    estimator_ready = calibration["gates"]["estimator_validation_ready"] is True
    dataset_ready = (
        readiness_audit.get("passed") is True
        and not readiness_audit.get("overlap_blockers")
    )
    production = (
        bootstrap["replicate_count"] == _PRODUCTION_REPLICATES
        and bootstrap["confidence"] == _PRODUCTION_CONFIDENCE
    )
    blockers: list[str] = []
    if not estimator_ready:
        blockers.append("estimator_validation_not_ready")
    if not dataset_ready:
        blockers.append("dataset_estimation_not_ready")
    if not bootstrap["ready"]:
        blockers.append("bootstrap_undefined_replicates")
    if not production:
        blockers.append("production_bootstrap_contract_not_met")
    blockers = sorted(set(blockers))
    ope_ready = not blockers
    victory = estimates["victory"]
    primary_interval = bootstrap["intervals"].get("victory", {}).get(
        "self_normalized_uplift"
    )
    conditions = {
        "bootstrap_ready": bootstrap["ready"],
        "dataset_estimation_ready": dataset_ready,
        "estimator_validation_ready": estimator_ready,
        "leave_one_out_defined": influence["all_defined"],
        "leave_one_out_victory_snis_positive": (
            influence["all_defined"]
            and all(value > 0 for value in influence["victory_snis_uplifts"])
        ),
        "primary_victory_snis_interval_positive": (
            primary_interval is not None and primary_interval[0] > 0
        ),
        "victory_ordinary_uplift_positive": victory["ordinary_uplift"] > 0,
        "victory_self_normalized_uplift_positive": (
            victory["self_normalized_uplift"] > 0
        ),
        "ope_estimate_ready": ope_ready,
    }
    blocker_by_condition = {
        "bootstrap_ready": "bootstrap_not_ready",
        "dataset_estimation_ready": "dataset_estimation_not_ready",
        "estimator_validation_ready": "estimator_validation_not_ready",
        "leave_one_out_defined": "leave_one_out_undefined",
        "leave_one_out_victory_snis_positive": (
            "leave_one_out_victory_snis_not_positive"
        ),
        "primary_victory_snis_interval_positive": (
            "primary_victory_snis_interval_not_positive"
        ),
        "victory_ordinary_uplift_positive": (
            "victory_ordinary_uplift_not_positive"
        ),
        "victory_self_normalized_uplift_positive": (
            "victory_self_normalized_uplift_not_positive"
        ),
        "ope_estimate_ready": "ope_estimate_not_ready",
    }
    comparison_blockers = sorted(
        {
            blocker_by_condition[name]
            for name, passed in conditions.items()
            if not passed
        }
    )
    policy_ready = not comparison_blockers
    checks.require(estimate.get("blockers") == blockers, "estimate blockers mismatch")
    checks.require(
        estimate.get("comparison")
        == {
            "blockers": comparison_blockers,
            "conditions": conditions,
            "ready": policy_ready,
        },
        "policy comparison evidence mismatch",
    )
    expected_gates = {
        "causal_uplift_ready": False,
        "dataset_estimation_ready": dataset_ready,
        "estimator_validation_ready": estimator_ready,
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
        "ope_estimate_ready": ope_ready,
        "policy_comparison_ready": policy_ready,
    }
    checks.require(estimate.get("gates") == expected_gates, "estimate gates mismatch")
    return {"policy_comparison_ready": policy_ready}


def _verify_calibration_configuration(
    configuration: Mapping[str, Any],
    checks: _Checks,
) -> None:
    for key, expected in {
        "bootstrap_replicates": 500,
        "dataset_count": 200,
        "seed": "noncombat-ope-fixed-coverage-v1",
        "trajectories_per_dataset": 200,
    }.items():
        checks.require(
            configuration.get(key) == expected,
            f"calibration configuration mismatch: {key}",
        )
    for key, expected in {
        "confidence_level": Fraction(19, 20),
        "maximum_absolute_mean_bias": Fraction(1, 50),
        "maximum_coverage": Fraction(99, 100),
        "minimum_coverage": Fraction(9, 10),
    }.items():
        checks.require(
            _reported_fraction(configuration.get(key), checks, key) == expected,
            f"calibration threshold mismatch: {key}",
        )
    fixture = configuration.get("coverage_fixture")
    checks.require(isinstance(fixture, Mapping), "coverage fixture missing")
    for key, expected in {
        "behavior_action_probabilities": (Fraction(1, 2), Fraction(1, 2)),
        "outcome_probabilities": (Fraction(1, 5), Fraction(1, 10)),
        "target_action_probabilities": (Fraction(4, 5), Fraction(1, 5)),
    }.items():
        values = fixture.get(key)
        checks.require(isinstance(values, list), f"coverage fixture missing: {key}")
        actual = tuple(
            _reported_fraction(value, checks, f"coverage fixture:{key}")
            for value in values
        )
        checks.require(actual == expected, f"coverage fixture mismatch: {key}")


def _replay_exact_calibration(exact: Mapping[str, Any], checks: _Checks) -> None:
    reported_checks = exact.get("checks")
    checks.require(isinstance(reported_checks, Mapping), "exact checks missing")

    identity_trajectories = (
        _fixture_trajectory("identity-a", Fraction(1), False, 10),
        _fixture_trajectory("identity-b", Fraction(1), True, 50),
        _fixture_trajectory("identity-c", Fraction(1), False, 20),
        _fixture_trajectory("identity-d", Fraction(1), True, 40),
    )
    identity = reported_checks["behavior_identity"]
    _verify_estimates(
        identity.get("estimates"),
        _estimate_channels(identity_trajectories),
        checks,
        "calibration identity",
    )
    checks.require(identity.get("passed") is True, "identity calibration failed")

    one_step = reported_checks["balanced_one_step_known_truth"]
    one_step_trajectories = (
        _fixture_trajectory("one-a-1", Fraction(3, 2), True, 50),
        _fixture_trajectory("one-a-2", Fraction(3, 2), True, 40),
        _fixture_trajectory("one-b-1", Fraction(1, 2), False, 20),
        _fixture_trajectory("one-b-2", Fraction(1, 2), False, 10),
    )
    one_estimate = _estimate_channels(one_step_trajectories)["victory"]
    for key, expected in {
        "expected_behavior_victory": Fraction(1, 2),
        "expected_target_victory": Fraction(3, 4),
        "observed_ordinary_victory": one_estimate["ordinary_is"],
        "observed_snis_victory": one_estimate["self_normalized_is"],
    }.items():
        _require_fraction_record(one_step.get(key), expected, checks, f"one-step:{key}")
    checks.require(one_step.get("passed") is True, "one-step calibration failed")

    multi = reported_checks["multi_decision_known_truth"]
    ratios = (
        ("multi-aa", (Fraction(3, 2), Fraction(3, 2)), True, 50),
        ("multi-ab", (Fraction(3, 2), Fraction(1, 2)), False, 30),
        ("multi-ba", (Fraction(1, 2), Fraction(3, 2)), False, 20),
        ("multi-bb", (Fraction(1, 2), Fraction(1, 2)), False, 10),
    )
    multi_trajectories = tuple(
        _fixture_trajectory(group_id, first * second, victory, floor)
        for group_id, (first, second), victory, floor in ratios
    )
    multi_rows = multi.get("trajectories")
    checks.require(isinstance(multi_rows, list) and len(multi_rows) == 4, "multi rows")
    for reported, trajectory, (group_id, decision_ratios, _, _) in zip(
        multi_rows,
        multi_trajectories,
        ratios,
    ):
        checks.require(reported.get("group_id") == group_id, "multi group mismatch")
        actual_ratios = tuple(
            _reported_fraction(value, checks, "multi ratio")
            for value in reported.get("decision_ratios", [])
        )
        checks.require(actual_ratios == decision_ratios, "multi ratios mismatch")
        _require_fraction_record(
            reported.get("weight"), trajectory.weight, checks, "multi weight"
        )
    multi_estimate = _estimate_channels(multi_trajectories)["victory"]
    for key, expected in {
        "expected_target_victory": Fraction(9, 16),
        "observed_ordinary_victory": multi_estimate["ordinary_is"],
        "observed_snis_victory": multi_estimate["self_normalized_is"],
    }.items():
        _require_fraction_record(multi.get(key), expected, checks, f"multi:{key}")
    checks.require(multi.get("passed") is True, "multi calibration failed")

    enumeration = reported_checks["bootstrap_exact_enumeration"]
    enumeration_trajectories = (
        _fixture_trajectory("enumeration-a", Fraction(1), False, 10),
        _fixture_trajectory("enumeration-b", Fraction(2), True, 30),
        _fixture_trajectory("enumeration-c", Fraction(3), True, 50),
    )
    exhaustive = {
        draw: _estimate_channels(
            tuple(enumeration_trajectories[index] for index in draw)
        )
        for draw in product(range(3), repeat=3)
    }
    for replicate_index in range(32):
        draw = tuple(
            _hash_draw_index(
                3,
                "calibration-enumeration-v1",
                replicate_index,
                draw_index,
            )
            for draw_index in range(3)
        )
        checks.require(draw in exhaustive, "enumeration draw missing")
        checks.require(
            _estimate_channels(
                tuple(enumeration_trajectories[index] for index in draw)
            )
            == exhaustive[draw],
            "enumeration estimate mismatch",
        )
    checks.require(
        enumeration
        == {
            "enumerated_draw_count": 27,
            "hash_replicate_count": 32,
            "passed": True,
        },
        "enumeration calibration mismatch",
    )
    ordering = reported_checks["ordering_invariance"]
    checks.require(
        _estimate_channels(enumeration_trajectories)
        == _estimate_channels(tuple(reversed(enumeration_trajectories))),
        "estimate ordering mismatch",
    )
    checks.require(
        ordering
        == {
            "estimate_order_invariant": True,
            "interval_order_invariant": True,
            "passed": True,
        },
        "ordering calibration mismatch",
    )


def _replay_coverage_prefix(
    coverage: Mapping[str, Any],
    configuration: Mapping[str, Any],
    replay_count: int,
    checks: _Checks,
    *,
    verify_aggregate: bool,
) -> None:
    checks.require(
        coverage.get("schema_version") == "noncombat-ope-coverage-fixture-v1",
        "coverage schema mismatch",
    )
    checks.require(coverage.get("passed") is True, "coverage gate failed")
    checks.require(coverage.get("blockers") == [], "coverage blockers present")
    checks.require(
        coverage.get("dataset_count") == 200
        and coverage.get("trajectories_per_dataset") == 200
        and coverage.get("bootstrap_replicates") == 500,
        "coverage dimensions mismatch",
    )
    rows = coverage.get("datasets")
    checks.require(isinstance(rows, list) and len(rows) == 200, "coverage rows missing")
    seed = configuration["seed"]
    confidence = _reported_fraction(
        configuration["confidence_level"], checks, "coverage confidence"
    )
    target_truth = Fraction(18, 100)
    uplift_truth = Fraction(3, 100)
    target_points: list[Fraction] = []
    uplift_points: list[Fraction] = []
    target_covered = 0
    uplift_covered = 0
    for dataset_index in range(replay_count):
        trajectories = _coverage_trajectories(seed, dataset_index)
        point = _estimate_channels(trajectories)["victory"]
        intervals = _coverage_intervals(
            trajectories,
            seed=f"{seed}:dataset:{dataset_index}",
            replicate_count=500,
            confidence=confidence,
        )
        target_hit = intervals["target"][0] <= target_truth <= intervals["target"][1]
        uplift_hit = intervals["uplift"][0] <= uplift_truth <= intervals["uplift"][1]
        row = rows[dataset_index]
        checks.require(row.get("dataset_index") == dataset_index, "coverage row order")
        checks.require(row.get("bootstrap_ready") is True, "coverage bootstrap blocked")
        checks.require(
            row.get("undefined_replicate_count") == 0,
            "coverage undefined replicate",
        )
        _require_fraction_record(
            row.get("point_target"),
            point["self_normalized_is"],
            checks,
            "coverage point target",
        )
        _require_fraction_record(
            row.get("point_uplift"),
            point["self_normalized_uplift"],
            checks,
            "coverage point uplift",
        )
        _require_interval_record(
            row.get("target_interval"),
            intervals["target"],
            checks,
            "coverage target interval",
        )
        _require_interval_record(
            row.get("uplift_interval"),
            intervals["uplift"],
            checks,
            "coverage uplift interval",
        )
        checks.require(row.get("target_covered") is target_hit, "target coverage mismatch")
        checks.require(row.get("uplift_covered") is uplift_hit, "uplift coverage mismatch")
        target_points.append(point["self_normalized_is"])
        uplift_points.append(point["self_normalized_uplift"])
        target_covered += int(target_hit)
        uplift_covered += int(uplift_hit)
    if not verify_aggregate:
        return
    mean_target = sum(target_points, Fraction(0, 1)) / 200
    mean_uplift = sum(uplift_points, Fraction(0, 1)) / 200
    target_bias = mean_target - target_truth
    uplift_bias = mean_uplift - uplift_truth
    _verify_coverage_aggregate(
        coverage,
        target_covered,
        uplift_covered,
        mean_target,
        mean_uplift,
        target_bias,
        uplift_bias,
        checks,
    )


def _verify_coverage_aggregate(
    coverage: Mapping[str, Any],
    target_covered: int,
    uplift_covered: int,
    mean_target: Fraction,
    mean_uplift: Fraction,
    target_bias: Fraction,
    uplift_bias: Fraction,
    checks: _Checks,
) -> None:
    checks.require(coverage.get("undefined_dataset_count") == 0, "undefined coverage")
    for key, count in (("target", target_covered), ("uplift", uplift_covered)):
        row = coverage["coverage"][key]
        checks.require(row.get("covered_count") == count, f"{key} coverage count")
        _require_fraction_record(
            row.get("fraction"), Fraction(count, 200), checks, f"{key} coverage"
        )
        checks.require(Fraction(9, 10) <= Fraction(count, 200) <= Fraction(99, 100), f"{key} coverage bounds")
    _require_fraction_record(
        coverage["mean_point_estimate"]["target"],
        mean_target,
        checks,
        "coverage mean target",
    )
    _require_fraction_record(
        coverage["mean_point_estimate"]["uplift"],
        mean_uplift,
        checks,
        "coverage mean uplift",
    )
    _require_fraction_record(
        coverage["bias"]["target"], target_bias, checks, "coverage target bias"
    )
    _require_fraction_record(
        coverage["bias"]["uplift"], uplift_bias, checks, "coverage uplift bias"
    )
    checks.require(abs(target_bias) <= Fraction(1, 50), "target bias limit")
    checks.require(abs(uplift_bias) <= Fraction(1, 50), "uplift bias limit")


def _coverage_trajectories(seed: str, dataset_index: int) -> tuple[_Trajectory, ...]:
    rows: list[_Trajectory] = []
    for trajectory_index in range(200):
        first_action = _hash_trial(
            seed,
            dataset_index,
            trajectory_index,
            "behavior_action",
            Fraction(1, 2),
        )
        victory_probability = Fraction(1, 5) if first_action else Fraction(1, 10)
        victory = _hash_trial(
            seed,
            dataset_index,
            trajectory_index,
            "victory",
            victory_probability,
        )
        group_id = f"coverage-{dataset_index:03d}-{trajectory_index:03d}"
        rows.append(
            _fixture_trajectory(
                group_id,
                Fraction(8, 5) if first_action else Fraction(2, 5),
                victory,
                50 if victory else 10,
            )
        )
    return tuple(rows)


def _coverage_intervals(
    trajectories: tuple[_Trajectory, ...],
    *,
    seed: str,
    replicate_count: int,
    confidence: Fraction,
) -> dict[str, tuple[Fraction, Fraction, int, int]]:
    weight_units = tuple((row.weight * 5).numerator for row in trajectories)
    targets: list[Fraction] = []
    uplifts: list[Fraction] = []
    for replicate_index in range(replicate_count):
        sampled_weight = 0
        weighted_victory = 0
        victories = 0
        for draw_index in range(len(trajectories)):
            index = _hash_draw_index(
                len(trajectories), seed, replicate_index, draw_index
            )
            units = weight_units[index]
            sampled_weight += units
            if trajectories[index].victory:
                victories += 1
                weighted_victory += units
        target = Fraction(weighted_victory, sampled_weight)
        behavior = Fraction(victories, len(trajectories))
        targets.append(target)
        uplifts.append(target - behavior)
    return {
        "target": _percentile_interval(targets, confidence),
        "uplift": _percentile_interval(uplifts, confidence),
    }


def _hash_trial(
    seed: str,
    dataset_index: int,
    trajectory_index: int,
    stream: str,
    probability: Fraction,
) -> bool:
    payload = (
        "noncombat-ope-coverage-fixture-v1\0"
        f"{seed}\0{dataset_index}\0{trajectory_index}\0{stream}"
    ).encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(payload).digest(), "big")
    return bucket % probability.denominator < probability.numerator


def _fixture_trajectory(
    group_id: str,
    weight: Fraction,
    victory: bool,
    floor_reached: int,
) -> _Trajectory:
    return _Trajectory(
        group_id=group_id,
        weight=weight,
        victory=victory,
        floor_reached=floor_reached,
        sample_ids=(f"sample-{group_id}",),
    )


def _require_interval_record(
    reported: Any,
    expected: tuple[Fraction, Fraction, int, int],
    checks: _Checks,
    label: str,
) -> None:
    checks.require(isinstance(reported, Mapping), f"{label} missing")
    lower, upper, lower_index, upper_index = expected
    _require_fraction_record(reported.get("lower"), lower, checks, f"{label}:lower")
    _require_fraction_record(reported.get("upper"), upper, checks, f"{label}:upper")
    checks.require(reported.get("lower_index") == lower_index, f"{label}:lower index")
    checks.require(reported.get("upper_index") == upper_index, f"{label}:upper index")


def _verify_intervals(
    reported: Any,
    expected: Mapping[str, Mapping[str, tuple[Fraction, Fraction, int, int]]],
    checks: _Checks,
) -> None:
    checks.require(isinstance(reported, Mapping), "bootstrap intervals missing")
    checks.require(set(reported) == set(expected), "bootstrap interval channels mismatch")
    for channel, fields in expected.items():
        reported_fields = reported.get(channel)
        checks.require(isinstance(reported_fields, Mapping), "interval channel missing")
        checks.require(set(reported_fields) == set(fields), "interval fields mismatch")
        for field, (lower, upper, lower_index, upper_index) in fields.items():
            row = reported_fields.get(field)
            checks.require(isinstance(row, Mapping), "interval row missing")
            _require_fraction_record(row.get("lower"), lower, checks, "interval lower")
            _require_fraction_record(row.get("upper"), upper, checks, "interval upper")
            checks.require(row.get("lower_index") == lower_index, "lower index mismatch")
            checks.require(row.get("upper_index") == upper_index, "upper index mismatch")


def _verify_nested_fractions(
    reported: Any,
    expected: Mapping[str, Mapping[str, Fraction]],
    checks: _Checks,
    label: str,
) -> None:
    checks.require(isinstance(reported, Mapping), f"{label} missing")
    checks.require(set(reported) == set(expected), f"{label} channels mismatch")
    for channel, fields in expected.items():
        row = reported.get(channel)
        checks.require(isinstance(row, Mapping), f"{label} channel missing")
        checks.require(set(row) == set(fields), f"{label} fields mismatch")
        for field, value in fields.items():
            _require_fraction_record(
                row.get(field), value, checks, f"{label}:{channel}:{field}"
            )


def _percentile_interval(
    values: list[Fraction],
    confidence: Fraction,
) -> tuple[Fraction, Fraction, int, int]:
    ordered = sorted(values)
    alpha = (1 - confidence) / 2
    last = len(ordered) - 1
    lower_position = last * alpha
    upper_position = last * (1 - alpha)
    lower_index = lower_position.numerator // lower_position.denominator
    upper_index = -(-upper_position.numerator // upper_position.denominator)
    return (
        ordered[lower_index],
        ordered[upper_index],
        lower_index,
        upper_index,
    )


def _hash_draw_index(
    trajectory_count: int,
    seed: str,
    replicate_index: int,
    draw_index: int,
) -> int:
    payload = (
        f"{_BOOTSTRAP_SCHEMA}\0{seed}\0{replicate_index}\0{draw_index}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest(), "big") % trajectory_count


_ESTIMATE_FIELDS = (
    "behavior",
    "ordinary_is",
    "ordinary_uplift",
    "self_normalized_is",
    "self_normalized_uplift",
)


def _exact_estimates_record(
    estimates: Mapping[str, Mapping[str, Fraction]],
) -> dict[str, dict[str, dict[str, int]]]:
    return {
        channel: {
            field: {
                "denominator": value.denominator,
                "numerator": value.numerator,
            }
            for field, value in fields.items()
        }
        for channel, fields in sorted(estimates.items())
    }


def _update_jsonl_digest(digest: Any, row: Mapping[str, Any]) -> None:
    digest.update(
        (
            json.dumps(
                row,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )


def _reported_fraction(
    value: Any,
    checks: _Checks,
    label: str,
) -> Fraction:
    checks.require(isinstance(value, Mapping), f"{label} fraction missing")
    numerator = value.get("numerator")
    denominator = value.get("denominator")
    checks.require(type(numerator) is int, f"{label} numerator invalid")
    checks.require(
        type(denominator) is int and denominator > 0,
        f"{label} denominator invalid",
    )
    return Fraction(numerator, denominator)


def _require_fraction_record(
    reported: Any,
    expected: Fraction,
    checks: _Checks,
    label: str,
) -> None:
    actual = _reported_fraction(reported, checks, label)
    checks.require(actual == expected, f"{label} exact value mismatch")
    checks.require(
        reported.get("value") == _finite_float(expected),
        f"{label} display value mismatch",
    )


def _finite_float(value: Fraction) -> float:
    try:
        rendered = float(value)
    except OverflowError:
        rendered = -sys.float_info.max if value < 0 else sys.float_info.max
    if math.isfinite(rendered):
        return rendered
    return math.copysign(sys.float_info.max, rendered)


def _sign(value: Fraction) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_mapping(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except _DuplicateJsonKeyError as exc:
        raise EstimateVerificationError(
            f"duplicate JSON key in {path.name}: {exc.key}"
        ) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EstimateVerificationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EstimateVerificationError(f"{path} must contain a JSON object")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(key)
        result[key] = value
    return result


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independently replay a non-combat OPE estimate."
    )
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--target-manifest", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--estimate", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--skip-full-calibration-replay", action="store_true")
    args = parser.parse_args(argv)
    try:
        audit = verify_estimate_artifact(
            sample_path=args.sample,
            target_manifest_path=args.target_manifest,
            readiness_path=args.readiness,
            calibration_path=args.calibration,
            estimate_path=args.estimate,
            full_calibration_replay=not args.skip_full_calibration_replay,
        )
        args.audit_output.parent.mkdir(parents=True, exist_ok=True)
        args.audit_output.write_text(
            json.dumps(audit, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except (EstimateVerificationError, OSError, UnicodeError, ValueError) as exc:
        print(f"estimate verification failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

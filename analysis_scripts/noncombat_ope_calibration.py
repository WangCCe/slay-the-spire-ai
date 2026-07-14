"""Calibrate the offline non-combat OPE estimator on synthetic fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_ope_estimation import (
    CALIBRATION_ARTIFACT_SCHEMA_VERSION as ESTIMATOR_CALIBRATION_SCHEMA_VERSION,
    OutcomeEstimate,
    WeightedTrajectory,
    bootstrap_trajectory_estimates,
    estimate_outcome_channels,
    estimator_implementation_sha256,
    fraction_record,
    hash_draw_index,
    percentile_interval,
)
from analysis_scripts.noncombat_ope_readiness import _replace_files_transactionally


COVERAGE_FIXTURE_SCHEMA_VERSION = "noncombat-ope-coverage-fixture-v1"
CALIBRATION_ARTIFACT_SCHEMA_VERSION = ESTIMATOR_CALIBRATION_SCHEMA_VERSION


@dataclass(frozen=True)
class CalibrationConfig:
    seed: str = "noncombat-ope-fixed-coverage-v1"
    dataset_count: int = 200
    trajectories_per_dataset: int = 200
    bootstrap_replicates: int = 500
    confidence_level: Fraction = Fraction(95, 100)
    minimum_coverage: Fraction = Fraction(90, 100)
    maximum_coverage: Fraction = Fraction(99, 100)
    maximum_absolute_mean_bias: Fraction = Fraction(2, 100)


def calibration_implementation_sha256() -> str:
    """Return the hash of the calibration implementation itself."""

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def coverage_bootstrap_victory_intervals(
    trajectories: Sequence[WeightedTrajectory],
    *,
    seed: str,
    replicate_count: int,
    confidence_level: Fraction,
) -> dict[str, Any]:
    """Stream the exact victory SNIS intervals used by coverage calibration."""

    ordered = tuple(sorted(trajectories, key=lambda row: row.group_id))
    if not ordered:
        raise ValueError("coverage bootstrap requires trajectories")
    if len({row.group_id for row in ordered}) != len(ordered):
        raise ValueError("coverage bootstrap trajectory ids must be unique")
    weight_units: list[int] = []
    for row in ordered:
        units = row.weight * 5
        if units.denominator != 1 or units <= 0:
            raise ValueError("coverage bootstrap requires positive fifth-unit weights")
        weight_units.append(units.numerator)
    target_values: list[Fraction] = []
    uplift_values: list[Fraction] = []
    trajectory_count = len(ordered)
    for replicate_index in range(replicate_count):
        sampled_weight = 0
        sampled_weighted_victory = 0
        sampled_victory = 0
        for draw_index in range(trajectory_count):
            selected_index = hash_draw_index(
                trajectory_count,
                seed,
                replicate_index,
                draw_index,
            )
            row = ordered[selected_index]
            units = weight_units[selected_index]
            sampled_weight += units
            if row.victory:
                sampled_victory += 1
                sampled_weighted_victory += units
        target = Fraction(sampled_weighted_victory, sampled_weight)
        behavior = Fraction(sampled_victory, trajectory_count)
        target_values.append(target)
        uplift_values.append(target - behavior)
    return {
        "target": percentile_interval(
            target_values,
            confidence_level=confidence_level,
        ),
        "uplift": percentile_interval(
            uplift_values,
            confidence_level=confidence_level,
        ),
    }


def run_coverage_experiment(config: CalibrationConfig) -> dict[str, Any]:
    """Run the deterministic repeated-sample SNIS coverage experiment."""

    _validate_config(config)
    truth_behavior = Fraction(15, 100)
    truth_target = Fraction(18, 100)
    truth_uplift = Fraction(3, 100)
    target_covered_count = 0
    uplift_covered_count = 0
    target_estimates: list[Fraction] = []
    uplift_estimates: list[Fraction] = []
    dataset_rows: list[dict[str, Any]] = []
    undefined_dataset_count = 0

    for dataset_index in range(config.dataset_count):
        trajectories = _coverage_dataset(config, dataset_index)
        point_estimates = estimate_outcome_channels(trajectories)["victory"]
        intervals = coverage_bootstrap_victory_intervals(
            trajectories,
            seed=f"{config.seed}:dataset:{dataset_index}",
            replicate_count=config.bootstrap_replicates,
            confidence_level=config.confidence_level,
        )
        target_interval = intervals["target"]
        uplift_interval = intervals["uplift"]
        target_covered = target_interval.lower <= truth_target <= target_interval.upper
        uplift_covered = uplift_interval.lower <= truth_uplift <= uplift_interval.upper
        target_covered_count += int(target_covered)
        uplift_covered_count += int(uplift_covered)
        target_estimates.append(point_estimates.self_normalized_is)
        uplift_estimates.append(point_estimates.self_normalized_uplift)
        dataset_rows.append(
            {
                "bootstrap_ready": True,
                "dataset_index": dataset_index,
                "point_target": fraction_record(
                    point_estimates.self_normalized_is
                ),
                "point_uplift": fraction_record(
                    point_estimates.self_normalized_uplift
                ),
                "target_covered": target_covered,
                "target_interval": _interval_record(target_interval),
                "undefined_replicate_count": 0,
                "uplift_covered": uplift_covered,
                "uplift_interval": _interval_record(uplift_interval),
            }
        )

    if target_estimates:
        mean_target = sum(target_estimates, Fraction(0, 1)) / len(
            target_estimates
        )
        mean_uplift = sum(uplift_estimates, Fraction(0, 1)) / len(
            uplift_estimates
        )
    else:
        mean_target = Fraction(0, 1)
        mean_uplift = Fraction(0, 1)
    target_bias = mean_target - truth_target
    uplift_bias = mean_uplift - truth_uplift
    target_coverage = Fraction(target_covered_count, config.dataset_count)
    uplift_coverage = Fraction(uplift_covered_count, config.dataset_count)
    blockers: list[str] = []
    if undefined_dataset_count:
        blockers.append("coverage_undefined_bootstrap_dataset")
    if not config.minimum_coverage <= target_coverage <= config.maximum_coverage:
        blockers.append("target_coverage_out_of_bounds")
    if not config.minimum_coverage <= uplift_coverage <= config.maximum_coverage:
        blockers.append("uplift_coverage_out_of_bounds")
    if abs(target_bias) > config.maximum_absolute_mean_bias:
        blockers.append("target_mean_bias_exceeds_limit")
    if abs(uplift_bias) > config.maximum_absolute_mean_bias:
        blockers.append("uplift_mean_bias_exceeds_limit")

    return {
        "bias": {
            "target": fraction_record(target_bias),
            "uplift": fraction_record(uplift_bias),
        },
        "blockers": blockers,
        "bootstrap_replicates": config.bootstrap_replicates,
        "confidence_level": fraction_record(config.confidence_level),
        "coverage": {
            "target": {
                "covered_count": target_covered_count,
                "fraction": fraction_record(target_coverage),
            },
            "uplift": {
                "covered_count": uplift_covered_count,
                "fraction": fraction_record(uplift_coverage),
            },
        },
        "dataset_count": config.dataset_count,
        "datasets": dataset_rows,
        "mean_point_estimate": {
            "target": fraction_record(mean_target),
            "uplift": fraction_record(mean_uplift),
        },
        "passed": not blockers,
        "schema_version": COVERAGE_FIXTURE_SCHEMA_VERSION,
        "seed": config.seed,
        "trajectories_per_dataset": config.trajectories_per_dataset,
        "truth": {
            "behavior_victory": fraction_record(truth_behavior),
            "target_victory": fraction_record(truth_target),
            "uplift_victory": fraction_record(truth_uplift),
        },
        "undefined_dataset_count": undefined_dataset_count,
    }


def build_calibration_artifact(
    config: CalibrationConfig | None = None,
) -> dict[str, Any]:
    """Build one hash-bound calibration artifact without writing it."""

    resolved = config or CalibrationConfig()
    configuration = _config_record(resolved)
    exact = run_exact_calibration_checks()
    coverage = run_coverage_experiment(resolved)
    production_contract = resolved == CalibrationConfig()
    blockers: list[str] = []
    if not exact["passed"]:
        blockers.append("exact_calibration_failed")
    blockers.extend(coverage["blockers"])
    if not production_contract:
        blockers.append("calibration_configuration_not_production_contract")
    blockers = sorted(set(blockers))
    return {
        "blockers": blockers,
        "configuration": configuration,
        "coverage_calibration": coverage,
        "downstream_gates": {
            "causal_uplift_ready": False,
            "formal_noncombat_rl_training_ready": False,
            "live_policy_promotion_ready": False,
        },
        "exact_calibration": exact,
        "gates": {
            "estimator_validation_ready": not blockers,
        },
        "limitations": [
            "Synthetic calibration validates estimator behavior, not policy quality.",
            "Calibration does not authorize causal claims, training, or live promotion.",
        ],
        "schema_version": CALIBRATION_ARTIFACT_SCHEMA_VERSION,
        "source": {
            "calibration_implementation_sha256": (
                calibration_implementation_sha256()
            ),
            "configuration_sha256": _canonical_sha256(configuration),
            "estimator_implementation_sha256": (
                estimator_implementation_sha256()
            ),
            "fixtures_sha256": _canonical_sha256(exact),
        },
    }


def render_calibration_json(artifact: dict[str, Any]) -> str:
    """Render stable LF-terminated calibration JSON."""

    _validate_artifact_shape(artifact)
    return json.dumps(
        artifact,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ) + "\n"


def render_calibration_markdown(artifact: dict[str, Any]) -> str:
    """Render a compact calibration audit for human review."""

    _validate_artifact_shape(artifact)
    coverage = artifact["coverage_calibration"]
    gates = artifact["gates"]
    source = artifact["source"]
    status = "PASS" if gates["estimator_validation_ready"] else "BLOCKED"
    lines = [
        "# Non-combat OPE estimator calibration",
        "",
        f"Status: {status}",
        "",
        "## Source hashes",
        "",
        f"- estimator: `{source['estimator_implementation_sha256']}`",
        f"- calibration: `{source['calibration_implementation_sha256']}`",
        f"- configuration: `{source['configuration_sha256']}`",
        f"- fixtures: `{source['fixtures_sha256']}`",
        "",
        "## Fixed coverage experiment",
        "",
        f"- datasets: {coverage['dataset_count']}",
        f"- trajectories per dataset: {coverage['trajectories_per_dataset']}",
        f"- bootstrap replicates: {coverage['bootstrap_replicates']}",
        "- target coverage: "
        f"{coverage['coverage']['target']['fraction']['value']}",
        "- uplift coverage: "
        f"{coverage['coverage']['uplift']['fraction']['value']}",
        "- target mean bias: "
        f"{coverage['bias']['target']['value']}",
        "- uplift mean bias: "
        f"{coverage['bias']['uplift']['value']}",
        "",
        "## Blockers",
        "",
    ]
    if artifact["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in artifact["blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in artifact["limitations"])
    return "\n".join(lines) + "\n"


def write_calibration_artifacts(
    artifact: dict[str, Any],
    *,
    json_path: Path | str,
    markdown_path: Path | str,
) -> None:
    """Atomically replace a complete calibration JSON/Markdown pair."""

    json_bytes = render_calibration_json(artifact).encode("utf-8")
    markdown_bytes = render_calibration_markdown(artifact).encode("utf-8")
    _replace_files_transactionally(
        (
            (Path(json_path), json_bytes),
            (Path(markdown_path), markdown_bytes),
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic non-combat OPE estimator calibration."
    )
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument(
        "--seed",
        default=CalibrationConfig.seed,
    )
    parser.add_argument(
        "--dataset-count",
        type=int,
        default=CalibrationConfig.dataset_count,
    )
    parser.add_argument(
        "--trajectories-per-dataset",
        type=int,
        default=CalibrationConfig.trajectories_per_dataset,
    )
    parser.add_argument(
        "--bootstrap-replicates",
        type=int,
        default=CalibrationConfig.bootstrap_replicates,
    )
    args = parser.parse_args(argv)
    config = CalibrationConfig(
        seed=args.seed,
        dataset_count=args.dataset_count,
        trajectories_per_dataset=args.trajectories_per_dataset,
        bootstrap_replicates=args.bootstrap_replicates,
    )
    artifact = build_calibration_artifact(config)
    write_calibration_artifacts(
        artifact,
        json_path=args.json_output,
        markdown_path=args.markdown_output,
    )
    return 0 if artifact["gates"]["estimator_validation_ready"] else 2


def run_exact_calibration_checks() -> dict[str, Any]:
    """Run deterministic exactness, enumeration, and ordering checks."""

    identity_trajectories = (
        _trajectory("identity-a", Fraction(1), False, 10),
        _trajectory("identity-b", Fraction(1), True, 50),
        _trajectory("identity-c", Fraction(1), False, 20),
        _trajectory("identity-d", Fraction(1), True, 40),
    )
    identity_estimates = estimate_outcome_channels(identity_trajectories)
    identity_passed = all(
        estimate.ordinary_is == estimate.behavior
        and estimate.self_normalized_is == estimate.behavior
        for estimate in identity_estimates.values()
    )

    one_step_trajectories = (
        _trajectory("one-a-1", Fraction(3, 2), True, 50),
        _trajectory("one-a-2", Fraction(3, 2), True, 40),
        _trajectory("one-b-1", Fraction(1, 2), False, 20),
        _trajectory("one-b-2", Fraction(1, 2), False, 10),
    )
    one_step_estimates = estimate_outcome_channels(one_step_trajectories)
    one_step_victory = one_step_estimates["victory"]
    one_step_passed = (
        one_step_victory.behavior == Fraction(1, 2)
        and one_step_victory.ordinary_is == Fraction(3, 4)
        and one_step_victory.self_normalized_is == Fraction(3, 4)
    )

    multi_rows = (
        ("multi-aa", (Fraction(3, 2), Fraction(3, 2)), True, 50),
        ("multi-ab", (Fraction(3, 2), Fraction(1, 2)), False, 30),
        ("multi-ba", (Fraction(1, 2), Fraction(3, 2)), False, 20),
        ("multi-bb", (Fraction(1, 2), Fraction(1, 2)), False, 10),
    )
    multi_trajectories = tuple(
        _trajectory(group_id, ratios[0] * ratios[1], victory, floor)
        for group_id, ratios, victory, floor in multi_rows
    )
    multi_estimates = estimate_outcome_channels(multi_trajectories)
    multi_victory = multi_estimates["victory"]
    product_checks = tuple(
        trajectory.weight == ratios[0] * ratios[1]
        for trajectory, (_, ratios, _, _) in zip(multi_trajectories, multi_rows)
    )
    multi_passed = (
        all(product_checks)
        and multi_victory.ordinary_is == Fraction(9, 16)
        and multi_victory.self_normalized_is == Fraction(9, 16)
    )

    enumeration_trajectories = (
        _trajectory("enumeration-a", Fraction(1), False, 10),
        _trajectory("enumeration-b", Fraction(2), True, 30),
        _trajectory("enumeration-c", Fraction(3), True, 50),
    )
    exhaustive = {
        draw: _reference_draw_estimates(enumeration_trajectories, draw)
        for draw in product(range(3), repeat=3)
    }
    hash_bootstrap = bootstrap_trajectory_estimates(
        enumeration_trajectories,
        seed="calibration-enumeration-v1",
        replicate_count=32,
    )
    enumeration_passed = all(
        replicate.estimates == exhaustive[replicate.draw_indices]
        for replicate in hash_bootstrap.replicates
    )

    forward_estimates = estimate_outcome_channels(enumeration_trajectories)
    reverse_estimates = estimate_outcome_channels(
        tuple(reversed(enumeration_trajectories))
    )
    reverse_bootstrap = bootstrap_trajectory_estimates(
        tuple(reversed(enumeration_trajectories)),
        seed="calibration-enumeration-v1",
        replicate_count=32,
    )
    estimate_order_invariant = forward_estimates == reverse_estimates
    interval_order_invariant = hash_bootstrap == reverse_bootstrap

    checks = {
        "balanced_one_step_known_truth": {
            "expected_behavior_victory": fraction_record(Fraction(1, 2)),
            "expected_target_victory": fraction_record(Fraction(3, 4)),
            "observed_ordinary_victory": fraction_record(
                one_step_victory.ordinary_is
            ),
            "observed_snis_victory": fraction_record(
                one_step_victory.self_normalized_is
            ),
            "passed": one_step_passed,
        },
        "behavior_identity": {
            "estimates": _serialized_estimates(identity_estimates),
            "passed": identity_passed,
        },
        "bootstrap_exact_enumeration": {
            "enumerated_draw_count": len(exhaustive),
            "hash_replicate_count": len(hash_bootstrap.replicates),
            "passed": enumeration_passed,
        },
        "multi_decision_known_truth": {
            "expected_target_victory": fraction_record(Fraction(9, 16)),
            "observed_ordinary_victory": fraction_record(
                multi_victory.ordinary_is
            ),
            "observed_snis_victory": fraction_record(
                multi_victory.self_normalized_is
            ),
            "passed": multi_passed,
            "trajectories": [
                {
                    "decision_ratios": [
                        fraction_record(ratio) for ratio in ratios
                    ],
                    "group_id": group_id,
                    "weight": fraction_record(trajectory.weight),
                }
                for trajectory, (group_id, ratios, _, _) in zip(
                    multi_trajectories,
                    multi_rows,
                )
            ],
        },
        "ordering_invariance": {
            "estimate_order_invariant": estimate_order_invariant,
            "interval_order_invariant": interval_order_invariant,
            "passed": estimate_order_invariant and interval_order_invariant,
        },
    }
    return {
        "checks": checks,
        "passed": all(check["passed"] for check in checks.values()),
    }


def _trajectory(
    group_id: str,
    weight: Fraction,
    victory: bool,
    floor_reached: int,
) -> WeightedTrajectory:
    return WeightedTrajectory(
        group_id=group_id,
        weight=weight,
        victory=victory,
        floor_reached=floor_reached,
        sample_ids=(f"sample-{group_id}",),
    )


def _reference_draw_estimates(
    trajectories: tuple[WeightedTrajectory, ...],
    draw_indices: tuple[int, ...],
) -> dict[str, OutcomeEstimate]:
    selected = tuple(trajectories[index] for index in draw_indices)
    count = len(selected)
    weight_sum = sum((row.weight for row in selected), Fraction(0, 1))
    result: dict[str, OutcomeEstimate] = {}
    for channel, outcomes in {
        "floor_reached": tuple(
            Fraction(row.floor_reached, 1) for row in selected
        ),
        "victory": tuple(Fraction(int(row.victory), 1) for row in selected),
    }.items():
        behavior = sum(outcomes, Fraction(0, 1)) / count
        weighted = sum(
            (row.weight * outcome for row, outcome in zip(selected, outcomes)),
            Fraction(0, 1),
        )
        ordinary = weighted / count
        self_normalized = weighted / weight_sum
        result[channel] = OutcomeEstimate(
            behavior=behavior,
            ordinary_is=ordinary,
            self_normalized_is=self_normalized,
            ordinary_uplift=ordinary - behavior,
            self_normalized_uplift=self_normalized - behavior,
        )
    return result


def _serialized_estimates(
    estimates: dict[str, OutcomeEstimate],
) -> dict[str, dict[str, dict[str, int | float]]]:
    fields = (
        "behavior",
        "ordinary_is",
        "ordinary_uplift",
        "self_normalized_is",
        "self_normalized_uplift",
    )
    return {
        channel: {
            field: fraction_record(getattr(estimate, field)) for field in fields
        }
        for channel, estimate in sorted(estimates.items())
    }


def _coverage_dataset(
    config: CalibrationConfig,
    dataset_index: int,
) -> tuple[WeightedTrajectory, ...]:
    trajectories: list[WeightedTrajectory] = []
    for trajectory_index in range(config.trajectories_per_dataset):
        selected_first_action = _hash_trial(
            config.seed,
            dataset_index,
            trajectory_index,
            "behavior_action",
            Fraction(1, 2),
        )
        outcome_probability = (
            Fraction(2, 10) if selected_first_action else Fraction(1, 10)
        )
        victory = _hash_trial(
            config.seed,
            dataset_index,
            trajectory_index,
            "victory",
            outcome_probability,
        )
        weight = Fraction(8, 5) if selected_first_action else Fraction(2, 5)
        group_id = f"coverage-{dataset_index:03d}-{trajectory_index:03d}"
        trajectories.append(
            _trajectory(
                group_id,
                weight,
                victory,
                50 if victory else 10,
            )
        )
    return tuple(trajectories)


def _hash_trial(
    seed: str,
    dataset_index: int,
    trajectory_index: int,
    stream: str,
    probability: Fraction,
) -> bool:
    payload = (
        f"{COVERAGE_FIXTURE_SCHEMA_VERSION}\0{seed}\0{dataset_index}\0"
        f"{trajectory_index}\0{stream}"
    ).encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(payload).digest(), "big")
    return bucket % probability.denominator < probability.numerator


def _interval_record(interval: Any) -> dict[str, Any]:
    return {
        "lower": fraction_record(interval.lower),
        "lower_index": interval.lower_index,
        "upper": fraction_record(interval.upper),
        "upper_index": interval.upper_index,
    }


def _config_record(config: CalibrationConfig) -> dict[str, Any]:
    return {
        "bootstrap_replicates": config.bootstrap_replicates,
        "confidence_level": fraction_record(config.confidence_level),
        "coverage_fixture": {
            "behavior_action_probabilities": [
                fraction_record(Fraction(1, 2)),
                fraction_record(Fraction(1, 2)),
            ],
            "outcome_probabilities": [
                fraction_record(Fraction(2, 10)),
                fraction_record(Fraction(1, 10)),
            ],
            "target_action_probabilities": [
                fraction_record(Fraction(8, 10)),
                fraction_record(Fraction(2, 10)),
            ],
        },
        "dataset_count": config.dataset_count,
        "maximum_absolute_mean_bias": fraction_record(
            config.maximum_absolute_mean_bias
        ),
        "maximum_coverage": fraction_record(config.maximum_coverage),
        "minimum_coverage": fraction_record(config.minimum_coverage),
        "seed": config.seed,
        "trajectories_per_dataset": config.trajectories_per_dataset,
    }


def _validate_config(config: CalibrationConfig) -> None:
    if not isinstance(config, CalibrationConfig):
        raise ValueError("calibration config type mismatch")
    if not config.seed:
        raise ValueError("calibration seed must be nonempty")
    for field, value in (
        ("dataset_count", config.dataset_count),
        ("trajectories_per_dataset", config.trajectories_per_dataset),
        ("bootstrap_replicates", config.bootstrap_replicates),
    ):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{field} must be a positive integer")
    if config.bootstrap_replicates > 100_000:
        raise ValueError("bootstrap_replicates exceeds the bounded maximum")
    if not 0 < config.confidence_level < 1:
        raise ValueError("confidence_level must be in (0, 1)")
    if not 0 <= config.minimum_coverage <= config.maximum_coverage <= 1:
        raise ValueError("coverage bounds are invalid")
    if config.maximum_absolute_mean_bias < 0:
        raise ValueError("maximum_absolute_mean_bias cannot be negative")


def _validate_artifact_shape(artifact: dict[str, Any]) -> None:
    if not isinstance(artifact, dict):
        raise ValueError("calibration artifact must be a mapping")
    if artifact.get("schema_version") != CALIBRATION_ARTIFACT_SCHEMA_VERSION:
        raise ValueError("calibration artifact schema mismatch")
    for key in (
        "blockers",
        "configuration",
        "coverage_calibration",
        "downstream_gates",
        "exact_calibration",
        "gates",
        "limitations",
        "source",
    ):
        if key not in artifact:
            raise ValueError(f"calibration artifact missing {key}")
    gates = artifact["gates"]
    if not isinstance(gates, dict) or type(
        gates.get("estimator_validation_ready")
    ) is not bool:
        raise ValueError("calibration artifact gate mismatch")
    if artifact["downstream_gates"] != {
        "causal_uplift_ready": False,
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
    }:
        raise ValueError("calibration downstream gates must remain closed")


def _canonical_sha256(value: dict[str, Any]) -> str:
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


if __name__ == "__main__":
    raise SystemExit(main())

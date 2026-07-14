"""Estimate offline non-combat policy values from verified trajectories."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_ope_readiness import finite_fraction_value
from analysis_scripts.verify_noncombat_ope_artifacts import (
    ArtifactVerificationError,
    verify_artifact_pair,
)


ESTIMATE_ARTIFACT_SCHEMA_VERSION = "noncombat-ope-estimate-v1"
CALIBRATION_ARTIFACT_SCHEMA_VERSION = (
    "noncombat-ope-estimator-calibration-v1"
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class EstimatorInputError(ValueError):
    """Raised when estimator input cannot be accepted without inventing evidence."""


class _DuplicateJsonKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


@dataclass(frozen=True)
class WeightedTrajectory:
    group_id: str
    weight: Fraction
    victory: bool
    floor_reached: int
    sample_ids: tuple[str, ...]


@dataclass(frozen=True)
class OutcomeEstimate:
    behavior: Fraction
    ordinary_is: Fraction
    self_normalized_is: Fraction
    ordinary_uplift: Fraction
    self_normalized_uplift: Fraction


@dataclass(frozen=True)
class EstimatorBundle:
    trajectories: tuple[WeightedTrajectory, ...]
    readiness_audit: Mapping[str, Any]
    calibration: Mapping[str, Any]
    hashes: Mapping[str, str]


def estimator_implementation_sha256() -> str:
    """Return the exact implementation hash used by calibration artifacts."""

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def load_estimator_bundle(
    *,
    sample_path: Path | str,
    target_manifest_path: Path | str,
    readiness_path: Path | str,
    calibration_path: Path | str,
) -> EstimatorBundle:
    """Load one independently replayed, overlap- and calibration-ready bundle."""

    sample_path = Path(sample_path)
    target_manifest_path = Path(target_manifest_path)
    readiness_path = Path(readiness_path)
    calibration_path = Path(calibration_path)
    try:
        readiness_audit = verify_artifact_pair(
            sample_path,
            target_manifest_path,
            readiness_path,
        )
    except (ArtifactVerificationError, OSError, UnicodeError, ValueError) as exc:
        raise EstimatorInputError(f"independent readiness replay failed: {exc}") from exc

    readiness = _load_json_mapping(readiness_path, "readiness artifact")
    calibration = _load_json_mapping(calibration_path, "calibration artifact")
    _validate_calibration(calibration)

    if readiness_audit.get("passed") is not True:
        raise EstimatorInputError("independent readiness replay did not pass")
    if readiness_audit.get("overlap_blockers"):
        raise EstimatorInputError("independent readiness replay found overlap blockers")
    overlap = readiness.get("overlap_screens")
    gates = readiness.get("readiness")
    if not isinstance(overlap, Mapping) or overlap.get("ready") is not True:
        raise EstimatorInputError("readiness artifact is not overlap-ready")
    if not isinstance(gates, Mapping) or gates.get("overlap_ready") is not True:
        raise EstimatorInputError("readiness overlap gate is not ready")

    trajectories = _weighted_trajectories(readiness)
    if not trajectories:
        raise EstimatorInputError("no complete trajectories are available")
    if sum((row.weight for row in trajectories), Fraction(0, 1)) <= 0:
        raise EstimatorInputError("trajectory weight denominator is zero")

    hashes = {
        "calibration_file_sha256": _file_sha256(calibration_path),
        "estimator_implementation_sha256": estimator_implementation_sha256(),
        "readiness_file_sha256": _file_sha256(readiness_path),
        "sample_file_sha256": _file_sha256(sample_path),
        "target_file_sha256": _file_sha256(target_manifest_path),
    }
    return EstimatorBundle(
        trajectories=trajectories,
        readiness_audit=readiness_audit,
        calibration=calibration,
        hashes=hashes,
    )


def estimate_outcome_channels(
    trajectories: Sequence[WeightedTrajectory],
) -> dict[str, OutcomeEstimate]:
    """Compute exact victory and floor estimates from complete trajectories."""

    ordered = _validate_trajectories(trajectories)
    return {
        "victory": _estimate_channel(
            ordered,
            tuple(Fraction(int(row.victory), 1) for row in ordered),
        ),
        "floor_reached": _estimate_channel(
            ordered,
            tuple(Fraction(row.floor_reached, 1) for row in ordered),
        ),
    }


def fraction_record(value: Fraction) -> dict[str, int | float]:
    """Render exact arithmetic with a bounded finite display value."""

    return {
        "denominator": value.denominator,
        "numerator": value.numerator,
        "value": finite_fraction_value(value),
    }


def build_estimator_diagnostics(
    trajectories: Sequence[WeightedTrajectory],
    estimates: Mapping[str, OutcomeEstimate] | None = None,
) -> dict[str, Any]:
    """Report exact identity and estimator-direction diagnostics only."""

    ordered = _validate_trajectories(trajectories)
    resolved = dict(estimates or estimate_outcome_channels(ordered))
    if set(resolved) != {"floor_reached", "victory"}:
        raise EstimatorInputError("both outcome channels are required")
    identity_applicable = all(row.weight == 1 for row in ordered)
    identity_passed = identity_applicable and all(
        estimate.ordinary_is == estimate.behavior
        and estimate.self_normalized_is == estimate.behavior
        for estimate in resolved.values()
    )
    return {
        "behavior_identity": {
            "applicable": identity_applicable,
            "passed": identity_passed,
        },
        "estimator_direction": {
            channel: {
                "agree": _sign(estimate.ordinary_uplift)
                == _sign(estimate.self_normalized_uplift),
                "ordinary_is": _sign(estimate.ordinary_uplift),
                "self_normalized_is": _sign(estimate.self_normalized_uplift),
            }
            for channel, estimate in sorted(resolved.items())
        },
    }


def _estimate_channel(
    trajectories: Sequence[WeightedTrajectory],
    outcomes: Sequence[Fraction],
) -> OutcomeEstimate:
    count = len(trajectories)
    weight_sum = sum((row.weight for row in trajectories), Fraction(0, 1))
    if weight_sum <= 0:
        raise EstimatorInputError("self-normalized estimator denominator is zero")
    outcome_sum = sum(outcomes, Fraction(0, 1))
    weighted_sum = sum(
        (row.weight * outcome for row, outcome in zip(trajectories, outcomes)),
        Fraction(0, 1),
    )
    behavior = outcome_sum / count
    ordinary_is = weighted_sum / count
    self_normalized_is = weighted_sum / weight_sum
    return OutcomeEstimate(
        behavior=behavior,
        ordinary_is=ordinary_is,
        self_normalized_is=self_normalized_is,
        ordinary_uplift=ordinary_is - behavior,
        self_normalized_uplift=self_normalized_is - behavior,
    )


def _sign(value: Fraction) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def _weighted_trajectories(
    readiness: Mapping[str, Any],
) -> tuple[WeightedTrajectory, ...]:
    audit = readiness.get("trajectory_audit")
    diagnostics = readiness.get("diagnostics")
    if not isinstance(audit, Mapping) or not isinstance(diagnostics, Mapping):
        raise EstimatorInputError("readiness trajectory accounting is missing")
    outcome_rows = audit.get("complete_trajectories")
    weight_rows = diagnostics.get("trajectory_weights")
    if not isinstance(outcome_rows, list) or not isinstance(weight_rows, list):
        raise EstimatorInputError("readiness trajectory rows are missing")

    outcomes: dict[str, tuple[bool, int]] = {}
    for row in outcome_rows:
        if not isinstance(row, Mapping):
            raise EstimatorInputError("invalid complete trajectory row")
        group_id = _required_string(row.get("group_id"), "trajectory group_id")
        if group_id in outcomes:
            raise EstimatorInputError(f"duplicate trajectory outcome: {group_id}")
        outcome = row.get("outcome")
        if not isinstance(outcome, Mapping):
            raise EstimatorInputError(f"missing terminal outcome: {group_id}")
        victory = outcome.get("victory")
        floor_reached = outcome.get("floor_reached")
        if type(victory) is not bool:
            raise EstimatorInputError(f"invalid terminal victory: {group_id}")
        if type(floor_reached) is not int or floor_reached < 0:
            raise EstimatorInputError(f"invalid terminal floor: {group_id}")
        outcomes[group_id] = (victory, floor_reached)

    weighted: dict[str, tuple[Fraction, tuple[str, ...]]] = {}
    all_sample_ids: set[str] = set()
    for row in weight_rows:
        if not isinstance(row, Mapping):
            raise EstimatorInputError("invalid trajectory weight row")
        group_id = _required_string(row.get("group_id"), "weight group_id")
        if group_id in weighted:
            raise EstimatorInputError(f"duplicate trajectory weight: {group_id}")
        weight = _fraction_from_record(row.get("weight"), f"weight:{group_id}")
        if weight < 0:
            raise EstimatorInputError(f"negative trajectory weight: {group_id}")
        decisions = row.get("decisions")
        if not isinstance(decisions, list) or not decisions:
            raise EstimatorInputError(f"missing trajectory decisions: {group_id}")
        sample_ids: list[str] = []
        for decision in decisions:
            if not isinstance(decision, Mapping):
                raise EstimatorInputError(f"invalid decision row: {group_id}")
            sample_id = _required_string(decision.get("sample_id"), "sample_id")
            if sample_id in all_sample_ids:
                raise EstimatorInputError(f"duplicate estimator sample: {sample_id}")
            all_sample_ids.add(sample_id)
            sample_ids.append(sample_id)
        weighted[group_id] = (weight, tuple(sample_ids))

    if set(outcomes) != set(weighted):
        missing_weights = sorted(set(outcomes) - set(weighted))
        missing_outcomes = sorted(set(weighted) - set(outcomes))
        raise EstimatorInputError(
            "trajectory outcome/weight keys differ: "
            f"missing_weights={missing_weights}, missing_outcomes={missing_outcomes}"
        )

    expected_count = audit.get("complete_trajectory_count")
    expected_decisions = diagnostics.get("decision_count")
    if type(expected_count) is not int or expected_count != len(outcomes):
        raise EstimatorInputError("complete trajectory count mismatch")
    if type(expected_decisions) is not int or expected_decisions != len(all_sample_ids):
        raise EstimatorInputError("complete decision count mismatch")

    return tuple(
        WeightedTrajectory(
            group_id=group_id,
            weight=weighted[group_id][0],
            victory=outcomes[group_id][0],
            floor_reached=outcomes[group_id][1],
            sample_ids=weighted[group_id][1],
        )
        for group_id in sorted(outcomes)
    )


def _validate_trajectories(
    trajectories: Sequence[WeightedTrajectory],
) -> tuple[WeightedTrajectory, ...]:
    if not trajectories:
        raise EstimatorInputError("at least one complete trajectory is required")
    ordered = tuple(sorted(trajectories, key=lambda row: row.group_id))
    group_ids: set[str] = set()
    sample_ids: set[str] = set()
    for row in ordered:
        if not row.group_id or row.group_id in group_ids:
            raise EstimatorInputError(f"duplicate or empty group_id: {row.group_id}")
        group_ids.add(row.group_id)
        if not isinstance(row.weight, Fraction) or row.weight < 0:
            raise EstimatorInputError(f"invalid trajectory weight: {row.group_id}")
        if type(row.victory) is not bool:
            raise EstimatorInputError(f"invalid victory outcome: {row.group_id}")
        if type(row.floor_reached) is not int or row.floor_reached < 0:
            raise EstimatorInputError(f"invalid floor outcome: {row.group_id}")
        if not row.sample_ids:
            raise EstimatorInputError(f"trajectory has no decisions: {row.group_id}")
        for sample_id in row.sample_ids:
            if not sample_id or sample_id in sample_ids:
                raise EstimatorInputError(f"duplicate or empty sample_id: {sample_id}")
            sample_ids.add(sample_id)
    return ordered


def _validate_calibration(calibration: Mapping[str, Any]) -> None:
    if calibration.get("schema_version") != CALIBRATION_ARTIFACT_SCHEMA_VERSION:
        raise EstimatorInputError("calibration schema mismatch")
    source = calibration.get("source")
    if not isinstance(source, Mapping):
        raise EstimatorInputError("calibration source block is missing")
    for key in (
        "calibration_implementation_sha256",
        "configuration_sha256",
        "estimator_implementation_sha256",
        "fixtures_sha256",
    ):
        value = source.get(key)
        if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
            raise EstimatorInputError(f"invalid calibration hash: {key}")
    if source["estimator_implementation_sha256"] != estimator_implementation_sha256():
        raise EstimatorInputError("stale calibration estimator implementation hash")
    gates = calibration.get("gates")
    if not isinstance(gates, Mapping):
        raise EstimatorInputError("calibration gates are missing")
    if gates.get("estimator_validation_ready") is not True:
        raise EstimatorInputError("calibration is not estimator-validation-ready")
    if calibration.get("blockers") != []:
        raise EstimatorInputError("calibration contains blockers")


def _load_json_mapping(path: Path, description: str) -> dict[str, Any]:
    try:
        data = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except _DuplicateJsonKeyError as exc:
        raise EstimatorInputError(
            f"duplicate JSON key in {description}: {exc.key}"
        ) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EstimatorInputError(f"cannot read {description}: {exc}") from exc
    if not isinstance(data, dict):
        raise EstimatorInputError(f"{description} must be a JSON object")
    return data


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(key)
        result[key] = value
    return result


def _fraction_from_record(value: Any, field: str) -> Fraction:
    if not isinstance(value, Mapping):
        raise EstimatorInputError(f"missing exact fraction: {field}")
    numerator = value.get("numerator")
    denominator = value.get("denominator")
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise EstimatorInputError(f"invalid exact fraction: {field}")
    return Fraction(numerator, denominator)


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise EstimatorInputError(f"missing or invalid {field}")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

from analysis_scripts.noncombat_ope_estimation import (
    CALIBRATION_ARTIFACT_SCHEMA_VERSION,
    WeightedTrajectory,
    build_estimator_diagnostics,
    estimate_outcome_channels,
    estimator_implementation_sha256,
    fraction_record,
    load_estimator_bundle,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS = REPO_ROOT / "reports"


def _write_passing_calibration(path: Path) -> None:
    artifact = {
        "schema_version": CALIBRATION_ARTIFACT_SCHEMA_VERSION,
        "source": {
            "calibration_implementation_sha256": "a" * 64,
            "configuration_sha256": "b" * 64,
            "estimator_implementation_sha256": estimator_implementation_sha256(),
            "fixtures_sha256": "c" * 64,
        },
        "gates": {"estimator_validation_ready": True},
        "blockers": [],
    }
    path.write_text(
        json.dumps(artifact, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_loader_requires_verified_hash_bound_bundle(tmp_path):
    sample_path = (
        REPORTS
        / "known_propensity_exploration_eval_20260714_b3_b7_samples.jsonl"
    )
    target_path = (
        REPORTS / "noncombat_ope_b3_b7_current_deterministic_target_20260714.json"
    )
    readiness_path = (
        REPORTS
        / "noncombat_ope_b3_b7_current_deterministic_readiness_20260714.json"
    )
    calibration_path = tmp_path / "calibration.json"
    _write_passing_calibration(calibration_path)

    bundle = load_estimator_bundle(
        sample_path=sample_path,
        target_manifest_path=target_path,
        readiness_path=readiness_path,
        calibration_path=calibration_path,
    )

    assert bundle.readiness_audit["passed"] is True
    assert len(bundle.trajectories) == 125
    assert sum(len(row.sample_ids) for row in bundle.trajectories) == 1_253
    assert sum(row.weight > 0 for row in bundle.trajectories) == 87
    assert bundle.hashes == {
        "calibration_file_sha256": hashlib.sha256(
            calibration_path.read_bytes()
        ).hexdigest(),
        "estimator_implementation_sha256": estimator_implementation_sha256(),
        "readiness_file_sha256": hashlib.sha256(
            readiness_path.read_bytes()
        ).hexdigest(),
        "sample_file_sha256": (
            "aa61da25c93cdfa24ec57f787fbd41b5e4921c1a1a2bf9cb75f799133159b292"
        ),
        "target_file_sha256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
    }


def test_exact_estimators_preserve_zero_and_extreme_trajectory_weights():
    trajectories = (
        WeightedTrajectory("run-a", Fraction(0), True, 50, ("a",)),
        WeightedTrajectory("run-b", Fraction(2), False, 20, ("b",)),
        WeightedTrajectory("run-c", Fraction(100), True, 30, ("c",)),
    )

    estimates = estimate_outcome_channels(trajectories)

    assert estimates["victory"].behavior == Fraction(2, 3)
    assert estimates["victory"].ordinary_is == Fraction(100, 3)
    assert estimates["victory"].self_normalized_is == Fraction(50, 51)
    assert estimates["victory"].ordinary_uplift == Fraction(98, 3)
    assert estimates["victory"].self_normalized_uplift == Fraction(16, 51)
    assert estimates["floor_reached"].behavior == Fraction(100, 3)
    assert estimates["floor_reached"].ordinary_is == Fraction(3040, 3)
    assert estimates["floor_reached"].self_normalized_is == Fraction(1520, 51)
    assert tuple(row.weight for row in trajectories) == (
        Fraction(0),
        Fraction(2),
        Fraction(100),
    )


def test_behavior_identity_is_exact_on_both_outcome_channels():
    trajectories = (
        WeightedTrajectory("run-a", Fraction(1), False, 10, ("a",)),
        WeightedTrajectory("run-b", Fraction(1), True, 50, ("b",)),
    )

    estimates = estimate_outcome_channels(trajectories)

    for estimate in estimates.values():
        assert estimate.ordinary_is == estimate.behavior
        assert estimate.self_normalized_is == estimate.behavior
        assert estimate.ordinary_uplift == 0
        assert estimate.self_normalized_uplift == 0

    diagnostics = build_estimator_diagnostics(trajectories, estimates)
    assert diagnostics["behavior_identity"] == {
        "applicable": True,
        "passed": True,
    }
    assert diagnostics["estimator_direction"]["victory"] == {
        "agree": True,
        "ordinary_is": "zero",
        "self_normalized_is": "zero",
    }
    assert "policy_comparison_ready" not in diagnostics


def test_estimator_diagnostics_report_direction_disagreement_separately():
    trajectories = (
        WeightedTrajectory("run-a", Fraction(1), True, 50, ("a",)),
        WeightedTrajectory("run-b", Fraction(3), False, 10, ("b",)),
    )
    estimates = estimate_outcome_channels(trajectories)

    diagnostics = build_estimator_diagnostics(trajectories, estimates)

    assert diagnostics["behavior_identity"]["applicable"] is False
    assert diagnostics["estimator_direction"]["victory"] == {
        "agree": False,
        "ordinary_is": "zero",
        "self_normalized_is": "negative",
    }


def test_fraction_rendering_is_finite_without_changing_exact_value():
    value = Fraction(10**10_000, 3)

    rendered = fraction_record(value)

    assert rendered["numerator"] == value.numerator
    assert rendered["denominator"] == value.denominator
    assert math.isfinite(rendered["value"])

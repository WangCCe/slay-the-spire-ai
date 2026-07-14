from fractions import Fraction
import hashlib
import json
from pathlib import Path

from analysis_scripts.noncombat_ope_calibration import (
    CALIBRATION_ARTIFACT_SCHEMA_VERSION,
    CalibrationConfig,
    build_calibration_artifact,
    calibration_implementation_sha256,
    main,
    render_calibration_json,
    render_calibration_markdown,
    run_exact_calibration_checks,
    run_coverage_experiment,
    write_calibration_artifacts,
)
from analysis_scripts.noncombat_ope_estimation import (
    estimator_implementation_sha256,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _fraction(record):
    return Fraction(record["numerator"], record["denominator"])


def test_exact_calibration_checks_cover_identity_and_known_truth():
    result = run_exact_calibration_checks()

    assert result["passed"] is True
    identity = result["checks"]["behavior_identity"]
    assert identity["passed"] is True
    for channel in ("floor_reached", "victory"):
        assert _fraction(identity["estimates"][channel]["behavior"]) == _fraction(
            identity["estimates"][channel]["ordinary_is"]
        )
        assert _fraction(identity["estimates"][channel]["behavior"]) == _fraction(
            identity["estimates"][channel]["self_normalized_is"]
        )

    one_step = result["checks"]["balanced_one_step_known_truth"]
    assert one_step["passed"] is True
    assert _fraction(one_step["expected_behavior_victory"]) == Fraction(1, 2)
    assert _fraction(one_step["expected_target_victory"]) == Fraction(3, 4)
    assert _fraction(one_step["observed_ordinary_victory"]) == Fraction(3, 4)
    assert _fraction(one_step["observed_snis_victory"]) == Fraction(3, 4)


def test_multi_decision_fixture_preserves_exact_trajectory_products():
    result = run_exact_calibration_checks()
    fixture = result["checks"]["multi_decision_known_truth"]

    assert fixture["passed"] is True
    assert tuple(_fraction(row["weight"]) for row in fixture["trajectories"]) == (
        Fraction(9, 4),
        Fraction(3, 4),
        Fraction(3, 4),
        Fraction(1, 4),
    )
    for row in fixture["trajectories"]:
        product = Fraction(1, 1)
        for ratio in row["decision_ratios"]:
            product *= _fraction(ratio)
        assert _fraction(row["weight"]) == product
    assert _fraction(fixture["expected_target_victory"]) == Fraction(9, 16)
    assert _fraction(fixture["observed_ordinary_victory"]) == Fraction(9, 16)
    assert _fraction(fixture["observed_snis_victory"]) == Fraction(9, 16)


def test_hash_bootstrap_matches_exhaustive_draw_lookup_and_ordering():
    result = run_exact_calibration_checks()
    enumeration = result["checks"]["bootstrap_exact_enumeration"]
    ordering = result["checks"]["ordering_invariance"]

    assert enumeration == {
        "enumerated_draw_count": 27,
        "hash_replicate_count": 32,
        "passed": True,
    }
    assert ordering == {
        "estimate_order_invariant": True,
        "interval_order_invariant": True,
        "passed": True,
    }


def _small_config():
    return CalibrationConfig(
        seed="unit-coverage-v1",
        dataset_count=8,
        trajectories_per_dataset=20,
        bootstrap_replicates=32,
    )


def test_coverage_experiment_is_deterministic_and_records_known_truth():
    config = _small_config()

    first = run_coverage_experiment(config)
    second = run_coverage_experiment(config)

    assert first == second
    assert first["dataset_count"] == 8
    assert first["trajectories_per_dataset"] == 20
    assert first["bootstrap_replicates"] == 32
    assert _fraction(first["truth"]["behavior_victory"]) == Fraction(15, 100)
    assert _fraction(first["truth"]["target_victory"]) == Fraction(18, 100)
    assert _fraction(first["truth"]["uplift_victory"]) == Fraction(3, 100)
    for metric in ("target", "uplift"):
        assert 0 <= first["coverage"][metric]["covered_count"] <= 8
        assert _fraction(first["coverage"][metric]["fraction"]) == Fraction(
            first["coverage"][metric]["covered_count"],
            8,
        )


def test_calibration_artifact_is_hash_bound_and_nonproduction_runs_fail_closed():
    config = _small_config()

    first = build_calibration_artifact(config)
    second = build_calibration_artifact(config)

    assert first == second
    assert first["schema_version"] == CALIBRATION_ARTIFACT_SCHEMA_VERSION
    assert first["source"]["estimator_implementation_sha256"] == (
        estimator_implementation_sha256()
    )
    assert first["source"]["calibration_implementation_sha256"] == (
        calibration_implementation_sha256()
    )
    assert first["source"]["configuration_sha256"] == hashlib.sha256(
        (
            json.dumps(
                first["configuration"],
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    assert first["source"]["fixtures_sha256"] == hashlib.sha256(
        (
            json.dumps(
                first["exact_calibration"],
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    assert first["gates"]["estimator_validation_ready"] is False
    assert "calibration_configuration_not_production_contract" in first["blockers"]
    assert first["downstream_gates"] == {
        "causal_uplift_ready": False,
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
    }


def test_calibration_json_markdown_pair_is_deterministic_and_fail_closed(tmp_path):
    artifact = build_calibration_artifact(_small_config())
    json_path = tmp_path / "calibration.json"
    markdown_path = tmp_path / "calibration.md"

    write_calibration_artifacts(
        artifact,
        json_path=json_path,
        markdown_path=markdown_path,
    )
    first_json = json_path.read_bytes()
    first_markdown = markdown_path.read_bytes()
    write_calibration_artifacts(
        artifact,
        json_path=json_path,
        markdown_path=markdown_path,
    )

    assert json_path.read_bytes() == first_json
    assert markdown_path.read_bytes() == first_markdown
    assert first_json == render_calibration_json(artifact).encode("utf-8")
    assert first_markdown == render_calibration_markdown(artifact).encode("utf-8")

    invalid = dict(artifact)
    invalid["schema_version"] = "tampered"
    try:
        write_calibration_artifacts(
            invalid,
            json_path=json_path,
            markdown_path=markdown_path,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid calibration artifact must fail closed")
    assert json_path.read_bytes() == first_json
    assert markdown_path.read_bytes() == first_markdown


def test_calibration_cli_writes_explicit_outputs_and_fails_nonproduction_gate(
    tmp_path,
):
    json_path = tmp_path / "cli-calibration.json"
    markdown_path = tmp_path / "cli-calibration.md"

    exit_code = main(
        [
            "--json-output",
            str(json_path),
            "--markdown-output",
            str(markdown_path),
            "--seed",
            "cli-test-v1",
            "--dataset-count",
            "2",
            "--trajectories-per-dataset",
            "4",
            "--bootstrap-replicates",
            "4",
        ]
    )

    assert exit_code == 2
    artifact = json.loads(json_path.read_text(encoding="utf-8"))
    assert artifact["gates"]["estimator_validation_ready"] is False
    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# Non-combat OPE estimator calibration\n"
    )


def test_hash_bound_implementation_sources_have_checkout_stable_lf_bytes():
    attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "analysis_scripts/noncombat_ope_estimation.py text eol=lf\n" in attributes
    assert "analysis_scripts/noncombat_ope_calibration.py text eol=lf\n" in attributes

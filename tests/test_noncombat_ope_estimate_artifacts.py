import hashlib
import json
from pathlib import Path

import pytest

from analysis_scripts.noncombat_ope_estimate_artifacts import (
    build_estimate_artifact,
    estimate_artifact_implementation_sha256,
    main,
    render_estimate_json,
    render_estimate_markdown,
    write_estimate_artifacts,
)
from analysis_scripts.noncombat_ope_estimation import (
    ESTIMATE_ARTIFACT_SCHEMA_VERSION,
    load_estimator_bundle,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS = REPO_ROOT / "reports"


def _b3_b7_bundle():
    return load_estimator_bundle(
        sample_path=(
            REPORTS
            / "known_propensity_exploration_eval_20260714_b3_b7_samples.jsonl"
        ),
        target_manifest_path=(
            REPORTS
            / "noncombat_ope_b3_b7_current_deterministic_target_20260714.json"
        ),
        readiness_path=(
            REPORTS
            / "noncombat_ope_b3_b7_current_deterministic_readiness_20260714.json"
        ),
        calibration_path=(
            REPORTS / "noncombat_ope_estimator_calibration_20260714.json"
        ),
    )


def test_estimate_artifact_is_deterministic_hash_bound_and_gate_separated():
    bundle = _b3_b7_bundle()

    first = build_estimate_artifact(
        bundle,
        seed="estimate-artifact-unit-v1",
        replicate_count=32,
    )
    second = build_estimate_artifact(
        bundle,
        seed="estimate-artifact-unit-v1",
        replicate_count=32,
    )

    assert first == second
    assert first["schema_version"] == ESTIMATE_ARTIFACT_SCHEMA_VERSION
    assert {
        key: first["source"][key] for key in bundle.hashes
    } == bundle.hashes
    assert first["source"]["estimate_artifact_implementation_sha256"] == (
        estimate_artifact_implementation_sha256()
    )
    assert first["accounting"]["trajectory_count"] == 125
    assert first["accounting"]["decision_count"] == 1_253
    assert first["accounting"]["nonzero_weight_count"] == 87
    assert first["accounting"]["victory_count"] == 1
    assert first["accounting"]["effective_sample_size"] == (
        bundle.readiness_audit["effective_sample_size"]
    )
    assert first["accounting"]["ess_fraction"] == (
        bundle.readiness_audit["ess_fraction"]
    )
    assert first["accounting"]["max_normalized_weight"] == (
        bundle.readiness_audit["max_normalized_weight"]
    )
    assert first["bootstrap"]["effective_replicate_count"] == 32
    assert first["bootstrap"]["production_replicate_count"] == 10_000
    assert len(first["bootstrap"]["draws_sha256"]) == 64
    assert len(first["bootstrap"]["replicate_estimates_sha256"]) == 64
    assert first["gates"] == {
        "causal_uplift_ready": False,
        "dataset_estimation_ready": True,
        "estimator_validation_ready": True,
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
        "ope_estimate_ready": False,
        "policy_comparison_ready": False,
    }
    assert "production_bootstrap_contract_not_met" in first["blockers"]
    assert first["comparison"]["conditions"]
    assert first["comparison"]["ready"] is False


def test_estimate_renderers_are_byte_stable_and_make_no_downstream_claim():
    artifact = build_estimate_artifact(
        _b3_b7_bundle(),
        seed="estimate-render-unit-v1",
        replicate_count=16,
    )

    json_text = render_estimate_json(artifact)
    markdown = render_estimate_markdown(artifact)

    assert json_text == render_estimate_json(json.loads(json_text))
    assert markdown == render_estimate_markdown(json.loads(json_text))
    assert hashlib.sha256(json_text.encode("utf-8")).hexdigest()
    assert "causal effect established" not in markdown.lower()
    assert "training authorized" not in markdown.lower()
    assert "live promotion authorized" not in markdown.lower()
    assert "formal_noncombat_rl_training_ready | BLOCKED" in markdown
    assert "live_policy_promotion_ready | BLOCKED" in markdown


def test_estimate_writer_is_transactional_and_cli_uses_explicit_outputs(tmp_path):
    artifact = build_estimate_artifact(
        _b3_b7_bundle(),
        seed="estimate-writer-unit-v1",
        replicate_count=8,
    )
    json_path = tmp_path / "estimate.json"
    markdown_path = tmp_path / "estimate.md"

    write_estimate_artifacts(
        artifact,
        json_path=json_path,
        markdown_path=markdown_path,
    )
    first_json = json_path.read_bytes()
    first_markdown = markdown_path.read_bytes()
    invalid = dict(artifact)
    invalid["schema_version"] = "tampered"
    with pytest.raises(ValueError):
        write_estimate_artifacts(
            invalid,
            json_path=json_path,
            markdown_path=markdown_path,
        )
    assert json_path.read_bytes() == first_json
    assert markdown_path.read_bytes() == first_markdown

    cli_json = tmp_path / "cli-estimate.json"
    cli_markdown = tmp_path / "cli-estimate.md"
    exit_code = main(
        [
            "--sample",
            str(
                REPORTS
                / "known_propensity_exploration_eval_20260714_b3_b7_samples.jsonl"
            ),
            "--target-manifest",
            str(
                REPORTS
                / "noncombat_ope_b3_b7_current_deterministic_target_20260714.json"
            ),
            "--readiness",
            str(
                REPORTS
                / "noncombat_ope_b3_b7_current_deterministic_readiness_20260714.json"
            ),
            "--calibration",
            str(REPORTS / "noncombat_ope_estimator_calibration_20260714.json"),
            "--seed",
            "estimate-cli-unit-v1",
            "--replicate-count",
            "8",
            "--json-output",
            str(cli_json),
            "--markdown-output",
            str(cli_markdown),
        ]
    )
    assert exit_code == 2
    assert json.loads(cli_json.read_text(encoding="utf-8"))["gates"][
        "ope_estimate_ready"
    ] is False
    assert cli_markdown.exists()


@pytest.mark.parametrize(
    "failure_case",
    [
        "changed_source_bytes",
        "stale_calibration",
        "blocked_overlap",
        "invalid_outcome",
        "zero_denominator",
        "duplicate_calibration_key",
    ],
)
def test_invalid_estimator_input_preserves_prior_artifact_pair(
    tmp_path,
    failure_case,
):
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
    calibration_path = (
        REPORTS / "noncombat_ope_estimator_calibration_20260714.json"
    )
    if failure_case == "changed_source_bytes":
        copied = tmp_path / sample_path.name
        copied.write_bytes(sample_path.read_bytes() + b"\n")
        sample_path = copied
    elif failure_case in {
        "blocked_overlap",
        "invalid_outcome",
        "zero_denominator",
    }:
        readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
        if failure_case == "blocked_overlap":
            readiness["overlap_screens"]["ready"] = False
            readiness["readiness"]["overlap_ready"] = False
        elif failure_case == "invalid_outcome":
            readiness["trajectory_audit"]["complete_trajectories"][0][
                "outcome"
            ]["victory"] = "false"
        else:
            for row in readiness["diagnostics"]["trajectory_weights"]:
                row["weight"] = {"denominator": 1, "numerator": 0, "value": 0.0}
            readiness["diagnostics"]["weight_sum"] = {
                "denominator": 1,
                "numerator": 0,
                "value": 0.0,
            }
        copied = tmp_path / "readiness.json"
        copied.write_text(
            json.dumps(readiness, ensure_ascii=True, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        readiness_path = copied
    else:
        calibration_text = calibration_path.read_text(encoding="utf-8")
        copied = tmp_path / "calibration.json"
        if failure_case == "duplicate_calibration_key":
            copied.write_text(
                '{"schema_version":"duplicate",' + calibration_text[1:],
                encoding="utf-8",
                newline="\n",
            )
        else:
            calibration = json.loads(calibration_text)
            calibration["source"]["estimator_implementation_sha256"] = "0" * 64
            copied.write_text(
                json.dumps(
                    calibration,
                    ensure_ascii=True,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
        calibration_path = copied

    json_output = tmp_path / "prior.json"
    markdown_output = tmp_path / "prior.md"
    json_output.write_bytes(b'{"prior":true}\n')
    markdown_output.write_bytes(b"# prior\n")

    exit_code = main(
        [
            "--sample",
            str(sample_path),
            "--target-manifest",
            str(target_path),
            "--readiness",
            str(readiness_path),
            "--calibration",
            str(calibration_path),
            "--seed",
            "invalid-input-unit-v1",
            "--replicate-count",
            "4",
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
        ]
    )

    assert exit_code == 2
    assert json_output.read_bytes() == b'{"prior":true}\n'
    assert markdown_output.read_bytes() == b"# prior\n"

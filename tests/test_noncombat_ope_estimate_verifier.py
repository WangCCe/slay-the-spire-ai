import ast
import hashlib
import json
from pathlib import Path

import pytest

from analysis_scripts.noncombat_ope_estimate_artifacts import (
    build_estimate_artifact,
    write_estimate_artifacts,
)
from analysis_scripts.noncombat_ope_estimation import load_estimator_bundle
from analysis_scripts.verify_noncombat_ope_estimates import (
    EstimateVerificationError,
    main,
    verify_calibration_artifact,
    verify_estimate_artifact,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS = REPO_ROOT / "reports"
SAMPLE = REPORTS / "known_propensity_exploration_eval_20260714_b3_b7_samples.jsonl"
TARGET = REPORTS / "noncombat_ope_b3_b7_current_deterministic_target_20260714.json"
READINESS = (
    REPORTS / "noncombat_ope_b3_b7_current_deterministic_readiness_20260714.json"
)
CALIBRATION = REPORTS / "noncombat_ope_estimator_calibration_20260714.json"


def _write_estimate(tmp_path, *, replicate_count=32):
    bundle = load_estimator_bundle(
        sample_path=SAMPLE,
        target_manifest_path=TARGET,
        readiness_path=READINESS,
        calibration_path=CALIBRATION,
    )
    artifact = build_estimate_artifact(
        bundle,
        seed="independent-verifier-unit-v1",
        replicate_count=replicate_count,
    )
    json_path = tmp_path / "estimate.json"
    markdown_path = tmp_path / "estimate.md"
    write_estimate_artifacts(
        artifact,
        json_path=json_path,
        markdown_path=markdown_path,
    )
    return json_path


def test_independent_verifier_replays_exact_estimate_without_main_import(tmp_path):
    estimate_path = _write_estimate(tmp_path)

    audit = verify_estimate_artifact(
        sample_path=SAMPLE,
        target_manifest_path=TARGET,
        readiness_path=READINESS,
        calibration_path=CALIBRATION,
        estimate_path=estimate_path,
        full_calibration_replay=False,
    )

    assert audit["passed"] is True
    assert audit["trajectory_count"] == 125
    assert audit["decision_count"] == 1_253
    assert audit["bootstrap_replicate_count"] == 32
    assert audit["calibration_full_replay"] is False
    assert audit["policy_comparison_ready"] is False
    assert audit["check_count"] > 1_000

    verifier_path = (
        REPO_ROOT / "analysis_scripts" / "verify_noncombat_ope_estimates.py"
    )
    assert audit["verifier_implementation_sha256"] == hashlib.sha256(
        verifier_path.read_bytes()
    ).hexdigest()
    verifier_source = verifier_path.read_text(encoding="utf-8")
    assert "import analysis_scripts.noncombat_ope_estimation" not in verifier_source
    assert "from analysis_scripts.noncombat_ope_estimation" not in verifier_source
    assert "import analysis_scripts.noncombat_ope_estimate_artifacts" not in (
        verifier_source
    )
    assert "from analysis_scripts.noncombat_ope_estimate_artifacts" not in (
        verifier_source
    )


def test_estimator_modules_remain_outside_live_agent_import_graph():
    offline_modules = {
        "analysis_scripts.noncombat_ope_calibration",
        "analysis_scripts.noncombat_ope_estimate_artifacts",
        "analysis_scripts.noncombat_ope_estimation",
        "analysis_scripts.verify_noncombat_ope_estimates",
    }
    live_sources = [REPO_ROOT / "main.py", *(REPO_ROOT / "spirecomm").rglob("*.py")]

    for path in live_sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        )
        assert offline_modules.isdisjoint(imports), path


def test_independent_calibration_replay_checks_exact_fixtures_and_dataset_prefix():
    audit = verify_calibration_artifact(CALIBRATION, dataset_limit=2)

    assert audit["passed"] is True
    assert audit["exact_calibration_replayed"] is True
    assert audit["coverage_datasets_replayed"] == 2
    assert audit["full_replay"] is False
    assert audit["check_count"] > 100
    assert audit["verifier_implementation_sha256"] == hashlib.sha256(
        (
            REPO_ROOT
            / "analysis_scripts"
            / "verify_noncombat_ope_estimates.py"
        ).read_bytes()
    ).hexdigest()


@pytest.mark.parametrize(
    "tamper_case",
    [
        "calibration_evidence",
        "point_estimate",
        "bootstrap_draws",
        "interval_endpoint",
        "influence_diagnostic",
        "overlap_metric",
        "downstream_gate",
    ],
)
def test_independent_verifier_rejects_tampered_evidence(tmp_path, tamper_case):
    estimate_path = _write_estimate(tmp_path, replicate_count=16)
    calibration_path = CALIBRATION
    if tamper_case == "calibration_evidence":
        calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
        calibration["coverage_calibration"]["datasets"][0]["target_covered"] = (
            not calibration["coverage_calibration"]["datasets"][0][
                "target_covered"
            ]
        )
        calibration_path = tmp_path / "tampered-calibration.json"
        calibration_path.write_text(
            json.dumps(calibration, ensure_ascii=True, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        estimate = json.loads(estimate_path.read_text(encoding="utf-8"))
        if tamper_case == "point_estimate":
            estimate["estimates"]["victory"]["behavior"]["numerator"] += 1
        elif tamper_case == "bootstrap_draws":
            estimate["bootstrap"]["draws_sha256"] = "0" * 64
        elif tamper_case == "interval_endpoint":
            estimate["bootstrap"]["intervals"]["victory"][
                "self_normalized_uplift"
            ]["lower"]["numerator"] += 1
        elif tamper_case == "influence_diagnostic":
            estimate["influence"]["rows"][0]["sign_changes"]["victory"][
                "self_normalized_uplift"
            ] = not estimate["influence"]["rows"][0]["sign_changes"][
                "victory"
            ]["self_normalized_uplift"]
        elif tamper_case == "overlap_metric":
            estimate["accounting"]["effective_sample_size"]["numerator"] += 1
        else:
            estimate["gates"]["formal_noncombat_rl_training_ready"] = True
        estimate_path.write_text(
            json.dumps(estimate, ensure_ascii=True, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

    with pytest.raises(EstimateVerificationError):
        verify_estimate_artifact(
            sample_path=SAMPLE,
            target_manifest_path=TARGET,
            readiness_path=READINESS,
            calibration_path=calibration_path,
            estimate_path=estimate_path,
            full_calibration_replay=False,
        )


def test_independent_verifier_cli_writes_explicit_audit(tmp_path):
    estimate_path = _write_estimate(tmp_path, replicate_count=8)
    audit_path = tmp_path / "audit.json"

    exit_code = main(
        [
            "--sample",
            str(SAMPLE),
            "--target-manifest",
            str(TARGET),
            "--readiness",
            str(READINESS),
            "--calibration",
            str(CALIBRATION),
            "--estimate",
            str(estimate_path),
            "--audit-output",
            str(audit_path),
            "--skip-full-calibration-replay",
        ]
    )

    assert exit_code == 0
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["passed"] is True
    assert audit["calibration_full_replay"] is False

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from analysis_scripts.verify_noncombat_ope_artifacts import (
    ArtifactVerificationError,
    _Checks,
    _fraction_from_record,
    verify_artifact_pair,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
B2_SAMPLES = REPO_ROOT / "reports" / "known_propensity_exploration_eval_20260714_b2_samples.jsonl"
IDENTITY_TARGET = REPO_ROOT / "reports" / "noncombat_ope_b2_behavior_identity_target_20260714.json"
IDENTITY_READINESS = REPO_ROOT / "reports" / "noncombat_ope_b2_behavior_identity_readiness_20260714.json"
CURRENT_TARGET = REPO_ROOT / "reports" / "noncombat_ope_b2_current_deterministic_target_20260714.json"
CURRENT_READINESS = REPO_ROOT / "reports" / "noncombat_ope_b2_current_deterministic_readiness_20260714.json"


def _canonical_target_hash(target):
    payload = deepcopy(target)
    payload["manifest_hash"] = None
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _write_rebound_identity_bundle(tmp_path, mutate_samples):
    samples = [
        json.loads(line)
        for line in B2_SAMPLES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    mutate_samples(samples)
    sample_path = tmp_path / "samples.jsonl"
    sample_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in samples),
        encoding="utf-8",
    )
    sample_bytes = sample_path.read_bytes()
    sample_sha256 = hashlib.sha256(sample_bytes).hexdigest()

    target = json.loads(IDENTITY_TARGET.read_text(encoding="utf-8"))
    target["source_sample_sha256"] = sample_sha256
    target["manifest_hash"] = _canonical_target_hash(target)
    target_path = tmp_path / "target.json"
    target_text = json.dumps(target, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    target_path.write_bytes(target_text.encode("utf-8"))

    readiness = json.loads(IDENTITY_READINESS.read_text(encoding="utf-8"))
    readiness["source"].update(
        {
            "sample_file": sample_path.name,
            "sample_sha256": sample_sha256,
            "sample_size_bytes": len(sample_bytes),
            "target_manifest_content_sha256": hashlib.sha256(
                target_path.read_bytes()
            ).hexdigest(),
            "target_manifest_hash": target["manifest_hash"],
        }
    )
    readiness_path = tmp_path / "readiness.json"
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
    return sample_path, target_path, readiness_path


def test_independent_verifier_replays_b2_identity_and_current_artifacts():
    identity = verify_artifact_pair(
        B2_SAMPLES,
        IDENTITY_TARGET,
        IDENTITY_READINESS,
    )
    current = verify_artifact_pair(
        B2_SAMPLES,
        CURRENT_TARGET,
        CURRENT_READINESS,
    )

    assert identity["passed"] is True
    assert identity["construction_mode"] == "behavior_identity"
    assert identity["decision_count"] == 230
    assert identity["trajectory_count"] == 25
    assert identity["nonzero_weight_count"] == 25
    assert identity["zero_weight_count"] == 0
    assert identity["identity_invariants_passed"] is True
    assert identity["check_count"] > 2_000

    assert current["passed"] is True
    assert current["construction_mode"] == "current_deterministic"
    assert current["decision_count"] == 230
    assert current["trajectory_count"] == 25
    assert current["nonzero_weight_count"] == 8
    assert current["zero_weight_count"] == 17
    assert current["identity_invariants_passed"] is False
    assert current["check_count"] > 2_000


def test_independent_verifier_rejects_tampered_target_content(tmp_path):
    target = json.loads(IDENTITY_TARGET.read_text(encoding="utf-8"))
    target["entries"][0]["probabilities"][0]["numerator"] = 0
    target_path = tmp_path / "target.json"
    target_path.write_text(json.dumps(target), encoding="utf-8")

    with pytest.raises(ArtifactVerificationError, match="target content hash"):
        verify_artifact_pair(B2_SAMPLES, target_path, IDENTITY_READINESS)


def test_independent_verifier_rejects_duplicate_json_keys(tmp_path):
    target_text = IDENTITY_TARGET.read_text(encoding="utf-8")
    target_path = tmp_path / "target.json"
    target_path.write_text(
        target_text.replace(
            '"schema_version": "noncombat-ope-target-policy-v1"',
            '"schema_version": "noncombat-ope-target-policy-v1",\n'
            '  "schema_version": "noncombat-ope-target-policy-v1"',
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ArtifactVerificationError, match="duplicate JSON key"):
        verify_artifact_pair(B2_SAMPLES, target_path, IDENTITY_READINESS)


def test_independent_verifier_requires_full_behavior_identity_distribution(tmp_path):
    target = json.loads(IDENTITY_TARGET.read_text(encoding="utf-8"))
    target["entries"][0]["probabilities"][0]["numerator"] = 2000
    target["entries"][0]["probabilities"][1]["numerator"] = 8000
    target["manifest_hash"] = _canonical_target_hash(target)
    target_path = tmp_path / "target.json"
    target_text = json.dumps(target, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    target_path.write_bytes(target_text.encode("utf-8"))
    readiness = json.loads(IDENTITY_READINESS.read_text(encoding="utf-8"))
    readiness["source"]["target_manifest_content_sha256"] = hashlib.sha256(
        target_path.read_bytes()
    ).hexdigest()
    readiness["source"]["target_manifest_hash"] = target["manifest_hash"]
    readiness_path = tmp_path / "readiness.json"
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")

    with pytest.raises(
        ArtifactVerificationError,
        match="behavior identity distribution mismatch",
    ):
        verify_artifact_pair(B2_SAMPLES, target_path, readiness_path)


def test_independent_verifier_rejects_tampered_reported_ratio(tmp_path):
    readiness = json.loads(IDENTITY_READINESS.read_text(encoding="utf-8"))
    readiness["diagnostics"]["trajectory_weights"][0]["decisions"][0][
        "ratio"
    ]["numerator"] = 2
    readiness_path = tmp_path / "readiness.json"
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")

    with pytest.raises(ArtifactVerificationError, match="reported decision ratio"):
        verify_artifact_pair(B2_SAMPLES, IDENTITY_TARGET, readiness_path)


@pytest.mark.parametrize(
    "record",
    [
        {"numerator": -1, "denominator": 10},
        {"numerator": 11, "denominator": 10},
    ],
)
def test_probability_fraction_rejects_mass_outside_zero_one(record):
    with pytest.raises(ArtifactVerificationError, match="probability outside zero-one"):
        _fraction_from_record(
            record,
            _Checks(),
            context="target probability",
            probability=True,
        )


def test_independent_verifier_rejects_non_boolean_terminal_victory(tmp_path):
    def mutate(samples):
        samples[0]["outcome"]["victory"] = "false"

    paths = _write_rebound_identity_bundle(tmp_path, mutate)

    with pytest.raises(ArtifactVerificationError, match="victory must be boolean"):
        verify_artifact_pair(*paths)


def test_independent_verifier_rejects_duplicate_trajectory_decision_index(tmp_path):
    def mutate(samples):
        first_by_group = {}
        for sample in samples:
            group_id = sample["trajectory_group_id"]
            if group_id in first_by_group:
                sample["exploration"]["decision_index"] = first_by_group[group_id]
                return
            first_by_group[group_id] = sample["exploration"]["decision_index"]
        raise AssertionError("B2 fixture has no repeated trajectory")

    paths = _write_rebound_identity_bundle(tmp_path, mutate)

    with pytest.raises(ArtifactVerificationError, match="duplicate decision_index"):
        verify_artifact_pair(*paths)


def test_independent_verifier_rejects_run_and_commit_provenance_mismatch(tmp_path):
    def mutate(samples):
        samples[0]["outcome"]["run_file"] = "other.run"
        samples[0]["behavior_policy_commit"] = "b" * 40

    paths = _write_rebound_identity_bundle(tmp_path, mutate)

    with pytest.raises(ArtifactVerificationError, match="source commit provenance mismatch"):
        verify_artifact_pair(*paths)

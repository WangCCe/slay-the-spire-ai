from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import analysis_scripts.noncombat_baseline_floor_readiness as readiness


REPO_ROOT = Path(__file__).resolve().parents[1]


def _canonical_bytes(value):
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value))


def _binding(root, path, evidence_id):
    payload = path.read_bytes()
    return {
        "id": evidence_id,
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _fixture_payloads():
    false_authority = {
        "baseline_floor_authorized": False,
        "formal_rl_readiness_authorized": False,
        "fresh_evidence_authorized": False,
        "gameplay_authorized": False,
        "model_authorized": False,
        "ope_authorized": False,
        "policy_loading_authorized": False,
        "promotion_authorized": False,
        "qualification_authorized": False,
        "reward_authorized": False,
        "target_supported_outcome_authorized": False,
        "training_authorized": False,
    }
    return {
        "formal_readiness": {
            "authority": {"formal_noncombat_rl": False},
            "failed_domains": ["baseline_policy", "outcome_support"],
            "schema_version": "noncombat-formal-rl-readiness-report-v1",
            "verdict": "not_ready_for_bounded_training_proposal",
        },
        "policy_validity": {
            "classification": {
                "quality": "baseline_signal_not_demonstrated",
                "verdict": "study_valid_without_baseline_signal",
            },
            "schema_version": "noncombat-simulator-policy-validity-metrics-v1",
        },
        "warm_start": {
            "classification": {
                "final_test_untouched": True,
                "quality": "baseline_floor_not_demonstrated",
                "verdict": "study_valid_without_baseline_floor",
            },
            "schema_version": "noncombat-simulator-baseline-metrics-artifact-v1",
        },
        "structured_ranker": {
            "classification": {
                "selected_candidate_id": None,
                "verdict": "poc_valid_without_structured_candidate",
            },
            "schema_version": "noncombat-structured-baseline-ranker-metrics-v1",
        },
        "residual_ranker": {
            "classification": {
                "selected_candidate_id": None,
                "verdict": "poc_valid_without_route_card_residual",
            },
            "schema_version": "noncombat-route-card-residual-metrics-v1",
        },
        "teacher_suitability": {
            "critical_failed_check_ids": ["route_reads_survivability"],
            "policy_quality_gate_suitable": False,
            "schema_version": "noncombat-teacher-suitability-v1",
        },
        "current_bridge": {
            "authority": {"baseline_floor_authorized": False},
            "passed_row_count": 4,
            "schema_version": "noncombat-current-policy-simulator-bridge-metrics-v2",
            "stage1_passed": True,
            "stage2": {
                "executed": True,
                "reason": "event_option_semantics_event_unsupported",
            },
            "verdict": "frozen_bridge_structurally_compatible",
        },
        "total_compatibility": {
            "authority": false_authority,
            "completed_seed_count": 0,
            "reason": "event_option_semantics_event_unsupported",
            "schema_version": "noncombat-total-event-native-compatibility-metrics-v1",
            "verdict": "total_event_native_compatibility_failed",
        },
        "reachable_compatibility": {
            "authority": false_authority,
            "completed_seed_rows": 0,
            "reason": "invalid_nonnegative_integer",
            "schema_version": "noncombat-reachable-event-native-compatibility-metrics-v1",
            "verdict": "reachable_event_native_compatibility_failed",
        },
        "formal_reward": {
            "authority": {"formal_noncombat_rl": False},
            "contract_id": "noncombat-formal-reward-contract-v1",
            "reference_labels_excluded": True,
            "schema_version": "noncombat-formal-rl-reward-contract-v1",
            "verdict": "formal_reward_contract_ready",
        },
        "outcome_feasibility": {
            "authority": {"formal_noncombat_rl_training": False},
            "reference_evidence": {
                "reference_comparability": "historical_reference_only",
                "target_supported_victories": 0,
            },
            "result": {"study_feasibility": "not_demonstrated"},
            "schema_version": "noncombat-study-feasibility-v1",
        },
    }


def _write_fixture(root):
    evidence = []
    for evidence_id, payload in _fixture_payloads().items():
        path = root / "evidence" / f"{evidence_id}.json"
        _write_json(path, payload)
        evidence.append(_binding(root, path, evidence_id))

    text_payloads = {
        "reachable_event_repair": (
            "verdict `reachable_event_surface_closed`\n"
            "does not establish a new native compatibility result\n"
        ),
        "remove_sentinel_repair": (
            "`remove_cost == -1` accepted\n"
            "`purge_available == false`\n"
        ),
        "sold_inventory_repair": (
            "`price == -1` omitted\n"
            "does not authorize a third formal native cohort\n"
        ),
        "shop_support_envelope": (
            "`unsupported_shop_courier_restock_semantics`\n"
            "`training_authorized = false`\n"
        ),
    }
    for evidence_id, text in text_payloads.items():
        path = root / "evidence" / f"{evidence_id}.md"
        path.write_text(text, encoding="utf-8", newline="\n")
        evidence.append(_binding(root, path, evidence_id))

    source_path = root / "analysis_scripts" / "audit.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("# fixture analyzer\n", encoding="utf-8", newline="\n")
    source = _binding(root, source_path, "implementation")
    source.pop("id")

    registration = {
        "audit_id": "fixture-baseline-floor-readiness",
        "authority": dict(readiness.NO_AUTHORITY),
        "baseline_floor_contract": {
            check: False for check in readiness.BASELINE_FLOOR_CONTRACT_CHECKS
        },
        "candidate_roles": list(readiness.CANDIDATE_ROLES),
        "evidence": sorted(evidence, key=lambda row: row["id"]),
        "implementation": source,
        "schema_version": readiness.INPUT_SCHEMA_VERSION,
        "unsupported_episode_contract": dict(readiness.UNSUPPORTED_EPISODE_CONTRACT),
    }
    registration_path = root / "reports" / "audit_input.json"
    _write_json(registration_path, registration)
    return registration_path


def test_current_evidence_requires_diagnostic_smoke_and_keeps_authority_closed(
    tmp_path,
):
    registration_path = _write_fixture(tmp_path)

    report = readiness.analyze_registration(registration_path, repo_root=tmp_path)

    assert report["result"] == {
        "blockers": [
            "current_own_trajectory_complete_row_absent",
            *[
                f"baseline_floor_contract_missing:{check}"
                for check in readiness.BASELINE_FLOOR_CONTRACT_CHECKS
            ],
        ],
        "next_prerequisite": "reused_development_seed_current_bridge_smoke",
        "outcome_support_remains_blocked": True,
        "verdict": "diagnostic_smoke_required",
    }
    assert report["structural_evidence"]["completed_current_seed_rows"] == 0
    assert set(report["authority"].values()) == {False}
    current = next(
        row for row in report["candidate_roles"] if row["policy_id"] == "current"
    )
    assert current["status"] == "structural_closure_required"


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("hash", "SHA-256 mismatch"),
        ("candidate_role", "candidate_roles"),
        ("authority", "authority"),
        ("survivor_only", "unsupported_episode_contract"),
    ],
)
def test_registration_drift_and_policy_promotion_fail_closed(
    tmp_path, mutation, match
):
    registration_path = _write_fixture(tmp_path)
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    if mutation == "hash":
        registration["evidence"][0]["sha256"] = "0" * 64
    elif mutation == "candidate_role":
        registration["candidate_roles"][1]["role"] = "eligible_non_teacher"
    elif mutation == "authority":
        registration["authority"]["training_authorized"] = True
    else:
        registration["unsupported_episode_contract"]["drop_allowed"] = True
    _write_json(registration_path, registration)

    with pytest.raises(readiness.AuditInputError, match=match):
        readiness.analyze_registration(registration_path, repo_root=tmp_path)


def test_fixed_verdict_precedence():
    incomplete = {
        check: False for check in readiness.BASELINE_FLOOR_CONTRACT_CHECKS
    }
    complete = {check: True for check in readiness.BASELINE_FLOOR_CONTRACT_CHECKS}

    assert readiness.classify_verdict(False, 0, incomplete) == (
        "no_viable_baseline_candidate",
        "define_non_teacher_baseline_candidate",
    )
    assert readiness.classify_verdict(True, 0, incomplete) == (
        "diagnostic_smoke_required",
        "reused_development_seed_current_bridge_smoke",
    )
    assert readiness.classify_verdict(True, 1, incomplete) == (
        "baseline_floor_contract_required",
        "define_baseline_floor_evaluation_contract",
    )
    assert readiness.classify_verdict(True, 1, complete) == (
        "ready_for_baseline_floor_preregistration",
        "separate_baseline_floor_preregistration",
    )


def test_outputs_are_deterministic_and_strictly_replayable(tmp_path):
    registration_path = _write_fixture(tmp_path)
    json_output = tmp_path / "out" / "audit.json"
    markdown_output = tmp_path / "out" / "audit.md"

    first = readiness.run_audit(
        registration_path,
        json_output,
        markdown_output,
        repo_root=tmp_path,
    )
    first_bytes = (json_output.read_bytes(), markdown_output.read_bytes())
    second = readiness.run_audit(
        registration_path,
        json_output,
        markdown_output,
        repo_root=tmp_path,
        strict=True,
    )

    assert first == second
    assert first_bytes == (json_output.read_bytes(), markdown_output.read_bytes())
    assert b"diagnostic_smoke_required" in first_bytes[0]
    assert b"Planning only" in first_bytes[1]


def test_committed_registration_is_canonical_and_yields_current_verdict():
    registration_path = (
        REPO_ROOT
        / "reports"
        / "noncombat_baseline_floor_readiness_audit_20260803_input.json"
    )
    registration = json.loads(registration_path.read_text(encoding="utf-8"))

    assert registration_path.read_bytes() == _canonical_bytes(registration)
    report = readiness.analyze_registration(
        registration_path,
        repo_root=REPO_ROOT,
    )

    assert len(report["evidence_identity"]["evidence"]) == 15
    assert report["result"]["verdict"] == "diagnostic_smoke_required"
    assert report["result"]["next_prerequisite"] == (
        "reused_development_seed_current_bridge_smoke"
    )
    assert report["structural_evidence"]["completed_current_seed_rows"] == 0


def test_output_collision_with_registered_input_is_rejected(tmp_path):
    registration_path = _write_fixture(tmp_path)
    original = registration_path.read_bytes()

    with pytest.raises(readiness.AuditInputError, match="collides with input"):
        readiness.run_audit(
            registration_path,
            registration_path,
            tmp_path / "audit.md",
            repo_root=tmp_path,
        )

    assert registration_path.read_bytes() == original
    assert not (tmp_path / "audit.md").exists()

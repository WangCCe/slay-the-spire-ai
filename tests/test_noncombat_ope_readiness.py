import json
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import math

import pytest

from analysis_scripts.noncombat_ope_readiness import (
    OUTCOME_CONTRACT_VERSION,
    OpeReadinessError,
    TARGET_POLICY_SCHEMA_VERSION,
    audit_trajectories,
    build_behavior_identity_manifest,
    build_current_deterministic_manifest,
    compute_weight_diagnostics,
    evaluate_identity_self_check,
    evaluate_overlap_screens,
    finite_fraction_value,
    load_canonical_samples,
    validate_target_policy_manifest,
)


SOURCE_COMMIT = "a" * 40


def _sample(
    *,
    run_id="100",
    decision_index=0,
    sample_id=None,
    floor=3,
    floor_reached=16,
    victory=False,
):
    sample_id = sample_id or f"decision-{run_id}-{decision_index}"
    action_id = f"card_reward:take:{run_id}-{decision_index}"
    skip_id = "card_reward:skip"
    return {
        "schema_version": "noncombat-rl-decision-v3",
        "sample_id": sample_id,
        "trajectory_group_id": f"run:{run_id}",
        "trajectory_session_id": f"trajectory-{run_id}",
        "behavior_policy_id": "known-propensity-epsilon-v1:test-session",
        "behavior_policy_commit": SOURCE_COMMIT,
        "behavior_probability_status": "verified_known_propensity",
        "behavior_action_probability": 0.9,
        "category": "card_reward",
        "floor": floor,
        "selected_action_id": action_id,
        "candidate_actions": [
            {
                "action_id": action_id,
                "available": True,
                "executable": True,
                "kind": "take",
                "label": action_id,
                "raw": {},
            },
            {
                "action_id": skip_id,
                "available": True,
                "executable": True,
                "kind": "skip",
                "label": "skip",
                "raw": {},
            },
        ],
        "current_policy_label": {"action_id": action_id, "label": action_id},
        "exploration": {
            "decision_id": sample_id,
            "decision_index": decision_index,
            "state_hash": f"state-{run_id}-{decision_index}",
            "distribution_hash": f"distribution-{run_id}-{decision_index}",
            "trajectory_session_id": f"trajectory-{run_id}",
            "session_id": "test-session",
            "source_commit": SOURCE_COMMIT,
            "baseline_action_id": action_id,
            "alternative_action_id": skip_id,
            "selected_arm": "baseline",
            "selected_probability": {
                "numerator": 9,
                "denominator": 10,
                "value": 0.9,
            },
            "candidate_distribution": [
                {"action_id": action_id, "numerator": 9, "denominator": 10, "value": 0.9},
                {"action_id": skip_id, "numerator": 1, "denominator": 10, "value": 0.1},
            ],
            "replay_status": "valid",
            "confirmation_status": "confirmed",
            "candidate_legality": "valid",
        },
        "outcome": {
            "run_file": f"{run_id}.run",
            "join_status": "matched",
            "included_in_gate": True,
            "victory": victory,
            "floor_reached": floor_reached,
            "killed_by": "Slime Boss" if not victory else "",
            "playtime": 90,
        },
    }


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_loads_canonical_samples_and_orders_complete_trajectories(tmp_path):
    source = tmp_path / "samples.jsonl"
    _write_jsonl(
        source,
        [
            _sample(run_id="200", decision_index=1, floor=7),
            _sample(run_id="100", decision_index=0),
            _sample(run_id="200", decision_index=0, floor=2),
        ],
    )

    samples = load_canonical_samples(source)
    audit = audit_trajectories(samples)

    assert audit.outcome_contract_version == OUTCOME_CONTRACT_VERSION
    assert audit.input_decision_count == 3
    assert audit.complete_trajectory_count == 2
    assert audit.complete_decision_count == 3
    assert audit.blocked_trajectories == ()
    assert [trajectory.group_id for trajectory in audit.trajectories] == [
        "run:100",
        "run:200",
    ]
    assert [
        decision["exploration"]["decision_index"]
        for decision in audit.trajectories[1].decisions
    ] == [0, 1]
    assert audit.trajectories[1].outcome.run_file == "200.run"
    assert audit.trajectories[1].outcome.floor_reached == 16


def test_duplicate_sample_identity_is_invalid():
    first = _sample(run_id="100", decision_index=0, sample_id="duplicate")
    second = _sample(run_id="200", decision_index=0, sample_id="duplicate")

    with pytest.raises(OpeReadinessError, match="duplicate sample_id: duplicate"):
        audit_trajectories((first, second))


def test_duplicate_trajectory_decision_index_is_invalid():
    first = _sample(run_id="100", decision_index=0, sample_id="decision-a")
    second = _sample(run_id="100", decision_index=0, sample_id="decision-b")

    with pytest.raises(
        OpeReadinessError,
        match="run:100: duplicate decision_index: 0",
    ):
        audit_trajectories((first, second))


def test_mixed_censored_and_floor_inconsistent_trajectories_are_blocked():
    mixed_a = _sample(run_id="100", decision_index=0)
    mixed_b = _sample(run_id="100", decision_index=1)
    mixed_b["outcome"]["victory"] = True
    mixed_b["outcome"]["killed_by"] = ""

    censored = _sample(run_id="200")
    censored["outcome"]["included_in_gate"] = False
    censored["outcome"]["join_status"] = "unmatched"

    floor_inconsistent = _sample(run_id="300", floor=17, floor_reached=16)

    audit = audit_trajectories((mixed_a, mixed_b, censored, floor_inconsistent))

    assert audit.complete_trajectory_count == 0
    assert audit.complete_decision_count == 0
    assert [blocked.group_id for blocked in audit.blocked_trajectories] == [
        "run:100",
        "run:200",
        "run:300",
    ]
    assert audit.blocked_trajectories[0].reasons == ("outcome_conflict",)
    assert audit.blocked_trajectories[1].reasons == (
        "outcome_not_included",
        "outcome_not_matched",
    )
    assert audit.blocked_trajectories[2].reasons == (
        "outcome_floor_precedes_decision",
    )


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("victory", 0, "outcome_victory_invalid"),
        ("floor_reached", True, "outcome_floor_reached_invalid"),
        ("playtime", -1, "outcome_playtime_invalid"),
        ("run_file", "other.run", "outcome_run_file_mismatch"),
    ],
)
def test_invalid_terminal_outcome_fields_block_trajectory(field, value, reason):
    sample = _sample()
    sample = deepcopy(sample)
    sample["outcome"][field] = value

    audit = audit_trajectories((sample,))

    assert audit.complete_trajectory_count == 0
    assert audit.blocked_trajectories[0].reasons == (reason,)


def test_behavior_identity_manifest_binds_exact_logged_distributions():
    samples = (
        _sample(run_id="200", decision_index=1),
        _sample(run_id="100", decision_index=0),
    )
    source_sha256 = "b" * 64

    manifest = build_behavior_identity_manifest(
        samples,
        source_sample_sha256=source_sha256,
    )
    validated = validate_target_policy_manifest(
        manifest,
        samples,
        source_sample_sha256=source_sha256,
    )

    assert validated == manifest
    assert manifest["schema_version"] == TARGET_POLICY_SCHEMA_VERSION
    assert manifest["construction_mode"] == "behavior_identity"
    assert manifest["diagnostic_only"] is True
    assert manifest["source_sample_sha256"] == source_sha256
    assert [entry["sample_id"] for entry in manifest["entries"]] == [
        "decision-100-0",
        "decision-200-1",
    ]
    assert manifest["entries"][0]["probabilities"] == [
        {
            "action_id": "card_reward:skip",
            "denominator": 10,
            "numerator": 1,
        },
        {
            "action_id": "card_reward:take:100-0",
            "denominator": 10,
            "numerator": 9,
        },
    ]
    assert manifest["manifest_hash"]


def test_target_manifest_rejects_source_hash_mismatch_and_missing_rows():
    samples = (_sample(),)
    manifest = build_behavior_identity_manifest(
        samples,
        source_sample_sha256="b" * 64,
    )

    with pytest.raises(OpeReadinessError, match="source sample hash mismatch"):
        validate_target_policy_manifest(
            manifest,
            samples,
            source_sample_sha256="c" * 64,
        )

    missing = deepcopy(manifest)
    missing["entries"] = []
    with pytest.raises(OpeReadinessError, match="target entries do not match samples"):
        validate_target_policy_manifest(
            missing,
            samples,
            source_sample_sha256="b" * 64,
        )


def test_target_manifest_rejects_duplicate_entries_and_actions():
    samples = (_sample(),)
    manifest = build_behavior_identity_manifest(
        samples,
        source_sample_sha256="b" * 64,
    )

    duplicate_entry = deepcopy(manifest)
    duplicate_entry["entries"].append(deepcopy(duplicate_entry["entries"][0]))
    with pytest.raises(OpeReadinessError, match="duplicate target sample_id"):
        validate_target_policy_manifest(
            duplicate_entry,
            samples,
            source_sample_sha256="b" * 64,
        )

    duplicate_action = deepcopy(manifest)
    duplicate_action["entries"][0]["probabilities"].append(
        deepcopy(duplicate_action["entries"][0]["probabilities"][0])
    )
    with pytest.raises(OpeReadinessError, match="duplicate target action"):
        validate_target_policy_manifest(
            duplicate_action,
            samples,
            source_sample_sha256="b" * 64,
        )


def test_target_manifest_rejects_changed_support_and_non_normalization():
    samples = (_sample(),)
    manifest = build_behavior_identity_manifest(
        samples,
        source_sample_sha256="b" * 64,
    )

    changed_support = deepcopy(manifest)
    changed_support["entries"][0]["probabilities"][0]["action_id"] = "outside"
    with pytest.raises(OpeReadinessError, match="target support mismatch"):
        validate_target_policy_manifest(
            changed_support,
            samples,
            source_sample_sha256="b" * 64,
        )

    non_normalized = deepcopy(manifest)
    non_normalized["entries"][0]["probabilities"][1]["numerator"] = 8
    with pytest.raises(
        OpeReadinessError,
        match="target probabilities do not sum to one",
    ):
        validate_target_policy_manifest(
            non_normalized,
            samples,
            source_sample_sha256="b" * 64,
        )


def test_current_deterministic_manifest_preserves_label_provenance():
    sample = _sample()

    manifest = build_current_deterministic_manifest(
        (sample,),
        source_sample_sha256="b" * 64,
    )
    validated = validate_target_policy_manifest(
        manifest,
        (sample,),
        source_sample_sha256="b" * 64,
    )

    assert validated == manifest
    assert manifest["construction_mode"] == "current_deterministic"
    assert manifest["diagnostic_only"] is False
    assert manifest["target_policy_commit"] == SOURCE_COMMIT
    [entry] = manifest["entries"]
    assert entry["label_provenance"] == {
        "action_id": "card_reward:take:100-0",
        "label": "card_reward:take:100-0",
        "source_field": "current_policy_label",
    }
    assert entry["probabilities"] == [
        {"action_id": "card_reward:skip", "denominator": 1, "numerator": 0},
        {
            "action_id": "card_reward:take:100-0",
            "denominator": 1,
            "numerator": 1,
        },
    ]


@pytest.mark.parametrize("label", [None, {}, {"action_id": "outside", "label": "outside"}])
def test_current_deterministic_manifest_fails_closed_on_unmapped_label(label):
    sample = _sample()
    sample["current_policy_label"] = label

    with pytest.raises(OpeReadinessError, match="current policy label is unmapped"):
        build_current_deterministic_manifest(
            (sample,),
            source_sample_sha256="b" * 64,
        )


def test_current_target_manifest_rejects_missing_label_provenance():
    sample = _sample()
    manifest = build_current_deterministic_manifest(
        (sample,),
        source_sample_sha256="b" * 64,
    )
    del manifest["entries"][0]["label_provenance"]

    with pytest.raises(OpeReadinessError, match="current label provenance is invalid"):
        validate_target_policy_manifest(
            manifest,
            (sample,),
            source_sample_sha256="b" * 64,
        )


def _select_alternative(sample):
    sample = deepcopy(sample)
    sample["selected_action_id"] = "card_reward:skip"
    sample["behavior_action_probability"] = 0.1
    sample["exploration"]["selected_arm"] = "alternative"
    sample["exploration"]["selected_probability"] = {
        "numerator": 1,
        "denominator": 10,
        "value": 0.1,
    }
    return sample


def test_exact_trajectory_weights_preserve_zero_target_support():
    baseline_0 = _sample(run_id="100", decision_index=0)
    baseline_1 = _sample(run_id="100", decision_index=1)
    alternative = _select_alternative(_sample(run_id="200", decision_index=0))
    samples = (baseline_0, baseline_1, alternative)
    audit = audit_trajectories(samples)
    manifest = build_current_deterministic_manifest(
        samples,
        source_sample_sha256="b" * 64,
    )

    diagnostics = compute_weight_diagnostics(audit, manifest)

    assert diagnostics.trajectory_count == 2
    assert diagnostics.decision_count == 3
    assert diagnostics.nonzero_weight_count == 1
    assert diagnostics.zero_weight_count == 1
    assert diagnostics.weight_sum == Fraction(100, 81)
    assert diagnostics.effective_sample_size == Fraction(1, 1)
    assert diagnostics.ess_fraction == Fraction(1, 2)
    assert diagnostics.max_normalized_weight == Fraction(1, 1)
    first, second = diagnostics.trajectory_weights
    assert first.group_id == "run:100"
    assert [weight.ratio for weight in first.decision_weights] == [
        Fraction(10, 9),
        Fraction(10, 9),
    ]
    assert first.weight == Fraction(100, 81)
    assert second.group_id == "run:200"
    assert second.decision_weights[0].target_probability == Fraction(0, 1)
    assert second.decision_weights[0].ratio == Fraction(0, 1)
    assert second.weight == Fraction(0, 1)
    assert math.isfinite(first.weight_display)


def test_weight_diagnostics_summarize_category_arms_and_outcomes_once_per_run():
    samples = (
        _sample(run_id="100", decision_index=0, floor_reached=10),
        _sample(run_id="100", decision_index=1, floor_reached=10),
        _select_alternative(
            _sample(run_id="200", decision_index=0, floor_reached=20)
        ),
    )
    audit = audit_trajectories(samples)
    manifest = build_current_deterministic_manifest(
        samples,
        source_sample_sha256="b" * 64,
    )

    diagnostics = compute_weight_diagnostics(audit, manifest)

    assert diagnostics.category_arm_support == {
        "card_reward": {
            "alternative": {"decision_count": 1, "trajectory_count": 1},
            "baseline": {"decision_count": 2, "trajectory_count": 1},
        }
    }
    assert diagnostics.outcome_variation == {
        "floor_reached": {"maximum": 20, "minimum": 10, "unique_count": 2},
        "victory": {"false": 2, "true": 0, "unique_count": 1},
    }


def test_fraction_display_is_finite_without_changing_exact_value():
    exact = Fraction(10**1000, 3)

    display = finite_fraction_value(exact)

    assert math.isfinite(display)
    assert display == float.fromhex("0x1.fffffffffffffp+1023")
    assert exact == Fraction(10**1000, 3)


def test_behavior_identity_self_check_matches_exact_weighted_outcomes():
    samples = (
        _sample(run_id="100", floor_reached=10, victory=False),
        _sample(run_id="200", floor_reached=20, victory=True),
    )
    audit = audit_trajectories(samples)
    manifest = build_behavior_identity_manifest(
        samples,
        source_sample_sha256="b" * 64,
    )
    diagnostics = compute_weight_diagnostics(audit, manifest)

    check = evaluate_identity_self_check(audit, manifest, diagnostics)

    assert check.passed is True
    assert check.mismatches == ()
    assert check.unweighted_outcomes == {
        "floor_reached_mean": Fraction(15, 1),
        "victory_mean": Fraction(1, 2),
    }
    assert check.weighted_outcomes == check.unweighted_outcomes


def test_identity_self_check_detects_exact_invariant_mismatch():
    samples = (_sample(),)
    audit = audit_trajectories(samples)
    manifest = build_behavior_identity_manifest(
        samples,
        source_sample_sha256="b" * 64,
    )
    diagnostics = compute_weight_diagnostics(audit, manifest)
    diagnostics = replace(
        diagnostics,
        effective_sample_size=Fraction(1, 2),
    )

    check = evaluate_identity_self_check(audit, manifest, diagnostics)

    assert check.passed is False
    assert check.mismatches == ("effective_sample_size_not_identity",)


def test_overlap_screens_list_observed_and_required_failures():
    samples = (
        _sample(run_id="100", floor_reached=10),
        _sample(run_id="200", floor_reached=20),
    )
    audit = audit_trajectories(samples)
    manifest = build_behavior_identity_manifest(
        samples,
        source_sample_sha256="b" * 64,
    )
    diagnostics = compute_weight_diagnostics(audit, manifest)
    diagnostics = replace(
        diagnostics,
        effective_sample_size=Fraction(1, 2),
        ess_fraction=Fraction(1, 4),
    )

    screen = evaluate_overlap_screens(diagnostics)

    assert screen.ready is False
    assert [blocker.code for blocker in screen.blockers] == [
        "complete_trajectory_count_below_minimum",
        "nonzero_weight_trajectory_count_below_minimum",
        "effective_sample_size_below_minimum",
        "ess_fraction_below_minimum",
        "max_normalized_weight_above_maximum",
        "primary_outcome_degenerate",
    ]
    assert screen.blockers[0].observed == 2
    assert screen.blockers[0].required == 100
    assert screen.blockers[3].observed == Fraction(1, 4)
    assert screen.blockers[3].required == Fraction(1, 2)


def test_overlap_screens_accept_exact_threshold_boundaries_only_as_screening():
    samples = (
        _sample(run_id="100", victory=False),
        _sample(run_id="200", victory=True),
    )
    audit = audit_trajectories(samples)
    manifest = build_behavior_identity_manifest(
        samples,
        source_sample_sha256="b" * 64,
    )
    diagnostics = compute_weight_diagnostics(audit, manifest)
    threshold_diagnostics = replace(
        diagnostics,
        trajectory_count=100,
        nonzero_weight_count=50,
        zero_weight_count=50,
        effective_sample_size=Fraction(50, 1),
        ess_fraction=Fraction(1, 2),
        max_normalized_weight=Fraction(1, 10),
    )

    screen = evaluate_overlap_screens(threshold_diagnostics)

    assert screen.ready is True
    assert screen.blockers == ()
    assert screen.estimator_validation_ready is False

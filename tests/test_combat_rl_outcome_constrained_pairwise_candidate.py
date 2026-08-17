from analysis_scripts.combat_rl_outcome_constrained_pairwise_candidate import (
    _build_batches,
    _eligibility,
    _interpolate_with_parent,
    _td_only_eligibility,
)
import torch

from spirecomm.ai.rl.v2.network import create_dqn_v2


def _baseline():
    return {
        "smooth_l1": 4.0,
        "positive_energy_end_turn_share": 0.70,
        "intervention_executed_over_end_turn_share": 0.02,
    }


def test_eligibility_requires_outcome_and_behavior_improvement():
    metrics = {
        "smooth_l1": 3.9,
        "parent_action_agreement": 0.96,
        "positive_energy_end_turn_share": 0.68,
        "intervention_executed_over_end_turn_share": 0.03,
        "off_target_parent_disagreement_share": 0.02,
    }

    checks = _eligibility(metrics, _baseline())

    assert checks["all_conditions_passed"] is True


def test_eligibility_rejects_td_regression_even_when_behavior_improves():
    metrics = {
        "smooth_l1": 4.1,
        "parent_action_agreement": 0.96,
        "positive_energy_end_turn_share": 0.68,
        "intervention_executed_over_end_turn_share": 0.03,
        "off_target_parent_disagreement_share": 0.02,
    }

    checks = _eligibility(metrics, _baseline())

    assert checks["unseen_smooth_l1_improved"] is False
    assert checks["all_conditions_passed"] is False


def test_eligibility_rejects_off_target_policy_drift():
    metrics = {
        "smooth_l1": 3.9,
        "parent_action_agreement": 0.96,
        "positive_energy_end_turn_share": 0.68,
        "intervention_executed_over_end_turn_share": 0.03,
        "off_target_parent_disagreement_share": 0.04,
    }

    checks = _eligibility(metrics, _baseline())

    assert checks["off_target_parent_disagreement_at_most_0_03"] is False
    assert checks["all_conditions_passed"] is False


def test_parent_interpolation_scales_parameter_delta():
    metadata = {
        "network_type": "standard",
        "continuous_dim": 4,
        "card_vocab": 3,
        "potion_vocab": 3,
        "relic_vocab": 3,
        "action_dim": 2,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
    }
    parent = create_dqn_v2(device="cpu", **metadata)
    trained = create_dqn_v2(device="cpu", **metadata)
    trained.load_state_dict(parent.state_dict())
    with torch.no_grad():
        for value in trained.parameters():
            value.add_(2.0)

    result = _interpolate_with_parent(
        metadata, trained, parent.state_dict(), alpha=0.25
    )

    for name, value in result.state_dict().items():
        expected = parent.state_dict()[name] + 0.25 * (
            trained.state_dict()[name] - parent.state_dict()[name]
        )
        assert torch.equal(value, expected)


def test_td_only_gate_does_not_require_behavioral_surrogate_change():
    metrics = {
        "smooth_l1": 3.9,
        "parent_action_agreement": 0.99,
        "off_target_parent_disagreement_share": 0.01,
        "positive_energy_end_turn_share": 0.70,
        "intervention_executed_over_end_turn_share": 0.0,
    }

    checks = _td_only_eligibility(metrics, _baseline())

    assert checks["all_conditions_passed"] is True


def test_td_only_gate_rejects_parent_drift():
    metrics = {
        "smooth_l1": 3.9,
        "parent_action_agreement": 0.97,
        "off_target_parent_disagreement_share": 0.03,
    }

    checks = _td_only_eligibility(metrics, _baseline())

    assert checks["parent_action_agreement_at_least_0_98"] is False
    assert checks["off_target_parent_disagreement_at_most_0_02"] is False
    assert checks["all_conditions_passed"] is False


def test_full_coverage_batches_visit_every_row_once_per_epoch():
    batches = _build_batches(
        train_count=10,
        batch_size=4,
        updates=99,
        seed=101,
        full_coverage_epochs=1,
    )

    visited = torch.cat(batches)

    assert [len(batch) for batch in batches] == [4, 4, 2]
    assert sorted(visited.tolist()) == list(range(10))


def test_random_batches_remain_deterministic_without_full_coverage():
    left = _build_batches(
        train_count=20,
        batch_size=5,
        updates=3,
        seed=202,
        full_coverage_epochs=0,
    )
    right = _build_batches(
        train_count=20,
        batch_size=5,
        updates=3,
        seed=202,
        full_coverage_epochs=0,
    )

    assert all(torch.equal(a, b) for a, b in zip(left, right))

from analysis_scripts.combat_rl_outcome_constrained_pairwise_candidate import (
    _eligibility,
)


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

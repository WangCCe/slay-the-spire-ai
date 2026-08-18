from analysis_scripts.combat_rl_return_end_turn_trust_candidate import (
    _development_eligibility,
    _select_eligible_weight,
)


def _metrics(**overrides):
    metrics = {
        "smooth_l1": 9.0,
        "one_step_smooth_l1": 4.0,
        "parent_action_agreement": 0.995,
        "off_target_parent_disagreement_share": 0.008,
        "positive_energy_end_turn_count": 101,
    }
    metrics.update(overrides)
    return metrics


def test_development_eligibility_requires_loss_and_behavior_guards():
    baseline = _metrics(
        smooth_l1=10.0,
        one_step_smooth_l1=5.0,
        parent_action_agreement=1.0,
        off_target_parent_disagreement_share=0.0,
        positive_energy_end_turn_count=100,
    )

    passing = _development_eligibility(_metrics(), baseline)
    failing = _development_eligibility(
        _metrics(positive_energy_end_turn_count=102), baseline
    )

    assert passing["all_conditions_passed"] is True
    assert failing["all_conditions_passed"] is False
    assert (
        failing["positive_energy_end_turn_count_increase_at_most_1"] is False
    )


def test_selects_smallest_positive_weight_passing_every_replay():
    configurations = [
        {
            "end_turn_preservation_weight": 0.0,
            "all_development_replays_passed": True,
        },
        {
            "end_turn_preservation_weight": 1.0,
            "all_development_replays_passed": True,
        },
        {
            "end_turn_preservation_weight": 0.5,
            "all_development_replays_passed": True,
        },
        {
            "end_turn_preservation_weight": 0.25,
            "all_development_replays_passed": False,
        },
    ]

    assert _select_eligible_weight(configurations) == 0.5

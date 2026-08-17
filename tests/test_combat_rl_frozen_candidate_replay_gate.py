from analysis_scripts.combat_rl_frozen_candidate_replay_gate import _decision


def test_frozen_candidate_gate_only_passes_all_conditions():
    assert (
        _decision({"all_conditions_passed": True})
        == "eligible_for_bounded_live_gate"
    )
    assert (
        _decision({"all_conditions_passed": False})
        == "not_eligible_for_live_gate"
    )
    assert _decision({}) == "not_eligible_for_live_gate"

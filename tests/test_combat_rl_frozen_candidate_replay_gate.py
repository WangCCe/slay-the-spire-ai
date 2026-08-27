from pathlib import Path

import pytest
import torch

from analysis_scripts.combat_rl_frozen_candidate_replay_gate import (
    _decision,
    _eligibility,
    _validate_parent_provenance,
)


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


def test_frozen_candidate_gate_applies_registered_sequence_guards():
    baseline = {
        "smooth_l1": 10.0,
        "one_step_smooth_l1": 4.0,
        "positive_energy_end_turn_count": 100,
    }
    candidate = {
        "smooth_l1": 9.0,
        "one_step_smooth_l1": 3.9,
        "parent_action_agreement": 0.995,
        "off_target_parent_disagreement_share": 0.005,
        "positive_energy_end_turn_count": 101,
    }

    eligibility = _eligibility(
        candidate,
        baseline,
        parent_action_agreement_min=0.99,
        off_target_parent_disagreement_max=0.01,
        positive_energy_end_turn_count_increase_max=1,
        require_one_step_smooth_l1_improvement=True,
    )

    assert eligibility["all_conditions_passed"] is True
    assert all(eligibility.values())


def test_frozen_candidate_gate_rejects_each_sequence_guard_failure():
    baseline = {
        "smooth_l1": 10.0,
        "one_step_smooth_l1": 4.0,
        "positive_energy_end_turn_count": 100,
    }
    passing = {
        "smooth_l1": 9.0,
        "one_step_smooth_l1": 3.9,
        "parent_action_agreement": 0.995,
        "off_target_parent_disagreement_share": 0.005,
        "positive_energy_end_turn_count": 101,
    }
    failures = {
        "smooth_l1": 10.0,
        "one_step_smooth_l1": 4.0,
        "parent_action_agreement": 0.98,
        "off_target_parent_disagreement_share": 0.02,
        "positive_energy_end_turn_count": 102,
    }

    for field, value in failures.items():
        candidate = {**passing, field: value}
        eligibility = _eligibility(
            candidate,
            baseline,
            parent_action_agreement_min=0.99,
            off_target_parent_disagreement_max=0.01,
            positive_energy_end_turn_count_increase_max=1,
            require_one_step_smooth_l1_improvement=True,
        )
        assert eligibility["all_conditions_passed"] is False


def _checkpoint(value: float) -> dict:
    state = {"weight": torch.tensor([value])}
    return {
        "metadata": {"state": "test"},
        "online_network_state_dict": state,
        "target_network_state_dict": state,
    }


def test_parent_provenance_accepts_bound_weight_equivalent_training_checkpoint(
    tmp_path: Path,
):
    parent = _checkpoint(1.0)
    equivalence_path = tmp_path / "training.pth"
    torch.save(_checkpoint(1.0), equivalence_path)
    import analysis_scripts.combat_rl_frozen_candidate_replay_gate as gate

    equivalence_hash = gate._sha256(equivalence_path)
    proof = _validate_parent_provenance(
        {"training_checkpoint_sha256": equivalence_hash},
        parent,
        parent_hash="a" * 64,
        equivalence_checkpoint_path=equivalence_path,
    )

    assert proof["kind"] == "training_checkpoint_weight_equivalence"
    assert proof["equivalence_checkpoint"]["sha256"] == equivalence_hash


def test_parent_provenance_rejects_non_equivalent_bound_training_checkpoint(
    tmp_path: Path,
):
    equivalence_path = tmp_path / "training.pth"
    torch.save(_checkpoint(2.0), equivalence_path)
    import analysis_scripts.combat_rl_frozen_candidate_replay_gate as gate

    equivalence_hash = gate._sha256(equivalence_path)
    with pytest.raises(ValueError, match="online network differs"):
        _validate_parent_provenance(
            {"training_checkpoint_sha256": equivalence_hash},
            _checkpoint(1.0),
            parent_hash="a" * 64,
            equivalence_checkpoint_path=equivalence_path,
        )

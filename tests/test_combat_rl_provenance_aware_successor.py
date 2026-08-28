from __future__ import annotations

import copy

import pytest
import torch

from analysis_scripts.combat_rl_provenance_aware_successor import (
    _eligibility,
    _fit_candidate,
    _provenance_action_metrics,
    _validate_parity_checkpoint,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


def _metadata() -> dict:
    return {
        "network_type": "standard",
        "continuous_dim": 4,
        "card_vocab": 4,
        "potion_vocab": 4,
        "relic_vocab": 4,
        "action_dim": 3,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
        "rl_space_version": "v2",
    }


def _replay(count: int = 12) -> dict:
    continuous = torch.arange(count * 4).reshape(count, 4).float() / 20.0
    card_ids = torch.ones((count, 1), dtype=torch.long)
    potion_ids = torch.tensor([[1], [2], [0]] * (count // 3), dtype=torch.long)
    relic_ids = torch.tensor([[1], [2], [1]] * (count // 3), dtype=torch.long)
    masks = torch.ones((count, 3), dtype=torch.bool)
    dones = torch.zeros(count, dtype=torch.bool)
    dones[2::3] = True
    return {
        "schema_version": 2,
        "buffer_size": 100,
        "continuous_dim": 4,
        "action_dim": 3,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
        "transition_count": count,
        "source_transition_count": count,
        "truncated": False,
        "continuous": continuous,
        "card_ids": card_ids,
        "potion_ids": potion_ids,
        "relic_ids": relic_ids,
        "action_masks": masks,
        "actions": torch.tensor([0, 1, 2] * (count // 3), dtype=torch.long),
        "rewards": torch.linspace(-2.0, 4.0, count),
        "dones": dones,
        "next_continuous": continuous.flip(0),
        "next_card_ids": card_ids.flip(0),
        "next_potion_ids": potion_ids.flip(0),
        "next_relic_ids": relic_ids.flip(0),
        "next_action_masks": masks.flip(0),
        "anchor_to_executed_action": torch.tensor(
            [False, True, True] * (count // 3), dtype=torch.bool
        ),
    }


def _checkpoint() -> dict:
    metadata = _metadata()
    torch.manual_seed(7)
    network = create_dqn_v2(
        device="cpu",
        **{key: value for key, value in metadata.items() if key != "rl_space_version"},
    )
    state = copy.deepcopy(network.state_dict())
    return {
        "checkpoint_schema_version": 2,
        "checkpoint_kind": "training",
        "metadata": metadata,
        "online_network_state_dict": state,
        "target_network_state_dict": copy.deepcopy(state),
        "optimizer_state_dict": {"state": {}},
        "replay_buffer_state_dict": _replay(),
    }


def test_parity_checkpoint_requires_nonzero_legal_override_provenance():
    checkpoint = _checkpoint()
    metadata, replay, provenance = _validate_parity_checkpoint(
        checkpoint, expected_transition_count=12
    )

    assert metadata["action_dim"] == 3
    assert replay["transition_count"] == 12
    assert provenance == {"direct_count": 4, "override_count": 8}

    without_overrides = copy.deepcopy(checkpoint)
    without_overrides["replay_buffer_state_dict"][
        "anchor_to_executed_action"
    ].zero_()
    with pytest.raises(ValueError, match="both direct and executed-action"):
        _validate_parity_checkpoint(without_overrides, expected_transition_count=12)

    invalid_override = copy.deepcopy(checkpoint)
    invalid_override["replay_buffer_state_dict"]["action_masks"][1, 1] = False
    with pytest.raises(ValueError, match="executed action outside"):
        _validate_parity_checkpoint(invalid_override, expected_transition_count=12)


def test_provenance_metrics_use_executed_labels_only_on_override_rows():
    metrics = _provenance_action_metrics(
        parent_actions=torch.tensor([0, 1, 1, 2]),
        candidate_actions=torch.tensor([0, 2, 1, 0]),
        executed_actions=torch.tensor([0, 2, 0, 0]),
        overrides=torch.tensor([False, True, True, False]),
    )

    assert metrics["anchor_labels"] == [0, 2, 0, 2]
    assert metrics["parent_anchor_label_agreement"] == pytest.approx(0.5)
    assert metrics["candidate_anchor_label_agreement"] == pytest.approx(0.5)
    assert metrics["action_disagreement_share"] == pytest.approx(0.5)
    assert metrics["direct"]["transition_count"] == 2
    assert metrics["override"]["transition_count"] == 2


def test_full_network_fit_is_exactly_repeatable_with_fixed_seed():
    checkpoint = _checkpoint()
    metadata, replay, _ = _validate_parity_checkpoint(
        checkpoint, expected_transition_count=12
    )
    kwargs = {
        "metadata": metadata,
        "parent_state": checkpoint["online_network_state_dict"],
        "target_state": checkpoint["target_network_state_dict"],
        "replay": replay,
        "train_indices": torch.arange(9),
        "learning_rate": 1e-4,
        "batch_size": 4,
        "anchor_weight": 1.0,
        "optimizer_steps": 5,
        "seed": 23,
    }

    first_state, first_training = _fit_candidate(**kwargs)
    second_state, second_training = _fit_candidate(**kwargs)

    assert first_training == second_training
    assert all(
        torch.equal(first_state[name], second_state[name]) for name in first_state
    )
    assert first_training["optimizer_update_count"] == 5
    assert first_training["sampled_override_count"]["maximum"] > 0


def test_eligibility_fails_closed_on_drift_or_anchor_label_regression():
    validation = {
        "parent_smooth_l1": 4.0,
        "candidate_smooth_l1": 3.5,
        "parent_anchor_label_agreement": 0.6,
        "candidate_anchor_label_agreement": 0.61,
        "action_disagreement_share": 0.08,
        "positive_energy_end_turn_count_delta": 1,
    }
    training = {
        "optimizer_update_count": 256,
        "sampled_override_count": {"maximum": 110.0},
        "all_objective_values_finite": True,
    }

    passed = _eligibility(
        validation=validation,
        training=training,
        candidate_round_trip_exact=True,
    )
    assert passed["all_conditions_passed"] is True

    excessive_drift = _eligibility(
        validation={**validation, "action_disagreement_share": 0.16},
        training=training,
        candidate_round_trip_exact=True,
    )
    assert excessive_drift["action_disagreement_at_most_drift_ceiling"] is False
    assert excessive_drift["all_conditions_passed"] is False

    label_regression = _eligibility(
        validation={**validation, "candidate_anchor_label_agreement": 0.59},
        training=training,
        candidate_round_trip_exact=True,
    )
    assert label_regression["validation_anchor_label_agreement_not_reduced"] is False
    assert label_regression["all_conditions_passed"] is False

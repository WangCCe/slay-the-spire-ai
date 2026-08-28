from __future__ import annotations

from types import SimpleNamespace

import torch

from analysis_scripts.combat_rl_guard_aware_counterfactual_audit import (
    HAND_OFFSET,
    behavior_equivalent_actions,
    evaluate_replay,
)
from spirecomm.ai.rl.v2 import action_space
from spirecomm.ai.rl.v2.latent_gated_adapter import ActionSelection
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2


def _state_rows(count: int = 1):
    return {
        "continuous": torch.zeros(count, StateEncoderV2.CONTINUOUS_DIM),
        "card_ids": torch.zeros(count, StateEncoderV2.CARD_SLOTS, dtype=torch.long),
        "potion_ids": torch.zeros(
            count, StateEncoderV2.POTION_SLOTS, dtype=torch.long
        ),
    }


def _equivalent(left, right, rows):
    return behavior_equivalent_actions(
        torch.tensor(left),
        torch.tensor(right),
        continuous=rows["continuous"],
        card_ids=rows["card_ids"],
        potion_ids=rows["potion_ids"],
    ).tolist()


def test_duplicate_cards_with_equal_features_and_target_are_equivalent():
    rows = _state_rows()
    rows["card_ids"][0, 1] = 7
    rows["card_ids"][0, 3] = 7
    feature = torch.arange(StateEncoderV2.HAND_FEATURES)
    for slot in (1, 3):
        start = HAND_OFFSET + slot * StateEncoderV2.HAND_FEATURES
        rows["continuous"][0, start : start + StateEncoderV2.HAND_FEATURES] = feature
    assert _equivalent(
        [action_space.encode_play_card(1, 1)],
        [action_space.encode_play_card(3, 1)],
        rows,
    ) == [True]


def test_duplicate_cards_with_different_target_or_features_are_not_equivalent():
    rows = _state_rows(2)
    rows["card_ids"][:, 1] = 7
    rows["card_ids"][:, 3] = 7
    second_slot = HAND_OFFSET + 3 * StateEncoderV2.HAND_FEATURES
    rows["continuous"][1, second_slot] = 1.0
    assert _equivalent(
        [action_space.encode_play_card(1, 1)] * 2,
        [action_space.encode_play_card(3, 2), action_space.encode_play_card(3, 1)],
        rows,
    ) == [False, False]


def test_duplicate_potions_with_equal_identity_and_target_are_equivalent():
    rows = _state_rows()
    rows["potion_ids"][0, 0] = 11
    rows["potion_ids"][0, 2] = 11
    assert _equivalent(
        [action_space.encode_use_potion(0, 1)],
        [action_space.encode_use_potion(2, 1)],
        rows,
    ) == [True]


def test_different_action_families_are_not_equivalent():
    rows = _state_rows()
    rows["card_ids"][0, 0] = 11
    rows["potion_ids"][0, 0] = 11
    assert _equivalent(
        [action_space.encode_play_card(0, 1)],
        [action_space.encode_use_potion(0, 1)],
        rows,
    ) == [False]


def test_replay_audit_recomputes_parent_without_proposal_field():
    rows = _state_rows(2)
    rows.update(
        {
            "relic_ids": torch.zeros(2, StateEncoderV2.RELIC_SLOTS, dtype=torch.long),
            "action_masks": torch.ones(2, action_space.ACTION_DIM, dtype=torch.bool),
            "executed_actions": torch.tensor([action_space.END_TURN_ACTION, 1]),
            "changed": torch.tensor([False, True]),
        }
    )

    class Adapter:
        config = SimpleNamespace(gate_threshold=0.7)

        @staticmethod
        def select_actions(**_inputs):
            return ActionSelection(
                actions=torch.tensor([action_space.END_TURN_ACTION, 1]),
                parent_actions=torch.tensor(
                    [action_space.END_TURN_ACTION, action_space.END_TURN_ACTION]
                ),
                correction_actions=torch.tensor([1, 1]),
                gate_probabilities=torch.tensor([0.1, 0.9]),
                gate_open=torch.tensor([False, True]),
                telemetry={},
            )

    report = evaluate_replay(Adapter(), rows, thresholds=(0.7,))
    assert report["configured"]["changed_behavior_agreement"] == 1.0
    assert report["configured"]["direct_behavior_preservation"] == 1.0

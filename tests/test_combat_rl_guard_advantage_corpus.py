from __future__ import annotations

import copy

import numpy as np

from analysis_scripts.combat_lightspeed_bridge import MappedCombatState
from analysis_scripts.combat_rl_guard_advantage_corpus import (
    HAND_OFFSET,
    BranchResult,
    canonicalize_actions,
    corpus_sufficiency,
    rollout_branch,
    select_advantage_label,
)
from spirecomm.ai.rl.v2 import action_space
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2
from spirecomm.ai.rl.v2.types import EncodedStateV2


def _mapped() -> MappedCombatState:
    continuous = np.zeros(StateEncoderV2.CONTINUOUS_DIM, dtype=np.float32)
    card_ids = np.zeros(StateEncoderV2.CARD_SLOTS, dtype=np.int64)
    card_ids[1] = card_ids[3] = 7
    features = np.arange(StateEncoderV2.HAND_FEATURES, dtype=np.float32)
    for slot in (1, 3):
        start = HAND_OFFSET + slot * StateEncoderV2.HAND_FEATURES
        continuous[start : start + StateEncoderV2.HAND_FEATURES] = features
    return MappedCombatState(
        state=EncodedStateV2(
            continuous=continuous,
            card_ids=card_ids,
            potion_ids=np.zeros(StateEncoderV2.POTION_SLOTS, dtype=np.int64),
            relic_ids=np.zeros(StateEncoderV2.RELIC_SLOTS, dtype=np.int64),
        ),
        action_mask=np.ones(action_space.ACTION_DIM, dtype=np.bool_),
    )


def _action(index: int, *, kind: str = "play_card"):
    return {
        "action_id": f"action:{index}",
        "available": True,
        "kind": kind,
        "rl_action_index": index,
    }


def test_canonicalization_groups_behavior_equivalent_duplicate_slots():
    first = action_space.encode_play_card(1, 1)
    duplicate = action_space.encode_play_card(3, 1)
    different_target = action_space.encode_play_card(3, 2)
    representatives, mapping = canonicalize_actions(
        [_action(duplicate), _action(different_target), _action(first)], _mapped()
    )
    assert [row["rl_action_index"] for row in representatives] == [first, different_target]
    assert mapping == {first: first, duplicate: first, different_target: different_target}


class _Environment:
    def __init__(self, transitions, *, state=0):
        self.transitions = transitions
        self.state = state

    def clone(self):
        return copy.deepcopy(self)

    def snapshot(self):
        return {"reward": float(self.state)}

    def step(self, action_id):
        self.state = self.transitions[(self.state, action_id)]

    def status(self):
        if self.state == -1:
            return {
                "terminal": False,
                "supported": False,
                "unsupported_reason": "unsupported_test_branch",
            }
        return {
            "terminal": self.state >= 3,
            "supported": True,
            "outcome": "player_victory" if self.state >= 3 else "undecided",
            "unsupported_reason": "",
        }


def _reward(_before, after, **_kwargs):
    return {"total": after["reward"]}


def test_rollout_accumulates_first_and_continuation_rewards():
    environment = _Environment(
        {(0, "action:1"): 1, (1, "action:2"): 2, (2, "action:2"): 3}
    )
    result = rollout_branch(
        environment,
        _action(1),
        source_actions_since_end_turn=0,
        continuation_selector=lambda _environment, _count: _action(2),
        continuation_decisions=2,
        discount=0.5,
        reward_fn=_reward,
    )
    assert result.complete is True
    assert result.terminal is True
    assert result.transition_count == 3
    assert result.total_return == 1 + 0.5 * 2 + 0.25 * 3


def test_rollout_excludes_an_unsupported_branch():
    environment = _Environment({(0, "action:1"): -1})
    result = rollout_branch(
        environment,
        _action(1),
        source_actions_since_end_turn=0,
        continuation_selector=lambda _environment, _count: _action(2),
        continuation_decisions=2,
        discount=0.99,
        reward_fn=_reward,
    )
    assert result.complete is False
    assert result.exclusion_reason == "unsupported_test_branch"


def test_label_tie_breaks_on_lower_action_index_and_excludes_partial_pairs():
    complete = select_advantage_label(
        [
            BranchResult(7, 2.0, 2, False, True),
            BranchResult(1, 2.0, 2, False, True),
            BranchResult(90, 1.0, 2, False, True),
        ],
        guard_action_index=90,
        positive_margin=0.5,
    )
    assert complete["target_action_index"] == 1
    assert complete["target_advantage"] == 1.0
    assert complete["positive"] is True

    excluded = select_advantage_label(
        [
            BranchResult(1, 2.0, 2, False, True),
            BranchResult(90, 1.0, 1, False, False, "unsupported"),
        ],
        guard_action_index=90,
        positive_margin=0.5,
    )
    assert excluded == {"complete": False, "exclusion_reason": "unsupported"}


def test_corpus_sufficiency_requires_both_classes_count_and_target_diversity():
    sufficient = corpus_sufficiency(
        {
            "positive_count": 100,
            "negative_count": 1,
            "positive_target_identity_count": 3,
        },
        {
            "positive_count": 1,
            "negative_count": 1,
            "positive_target_identity_count": 1,
        },
    )
    assert sufficient["all_conditions_passed"] is True

    insufficient = corpus_sufficiency(
        {
            "positive_count": 99,
            "negative_count": 1,
            "positive_target_identity_count": 3,
        },
        {
            "positive_count": 1,
            "negative_count": 0,
            "positive_target_identity_count": 1,
        },
    )
    assert insufficient["all_conditions_passed"] is False
    assert insufficient["decision"] == "corpus_insufficient_stop_before_fit"

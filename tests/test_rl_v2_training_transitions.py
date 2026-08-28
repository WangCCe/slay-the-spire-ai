import math
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION, PLAY_CARD_COUNT
from spirecomm.ai.rl.v2.agent import PendingTransition, RLAgentV2
from spirecomm.ai.rl.v2.id_mapping import IdMapper
from spirecomm.ai.rl.v2.replay_buffer import ReplayBufferV2
from spirecomm.ai.rl.v2.trainer import (
    DQNTrainerV2,
    parent_card_ranking_guard_loss,
    parent_end_turn_margin_guard_loss,
    parent_top_action_margin_guard_loss,
    provenance_balanced_parent_policy_anchor_loss,
)
from spirecomm.communication.action import EndTurnAction


class _Action:
    def __init__(self, index):
        self.index = index


def _margin_guard_q_rows(rows):
    values = torch.zeros((len(rows), END_TURN_ACTION + 2), dtype=torch.float32)
    masks = torch.zeros_like(values, dtype=torch.bool)
    for row_index, (end_q, selected_action, selected_q, end_legal) in enumerate(rows):
        values[row_index, END_TURN_ACTION] = end_q
        values[row_index, selected_action] = selected_q
        masks[row_index, selected_action] = True
        masks[row_index, END_TURN_ACTION] = end_legal
    return values, masks


def test_parent_end_turn_margin_guard_clips_and_filters_rows():
    parent_q, masks = _margin_guard_q_rows(
        (
            (0.0, 1, 0.5, True),
            (0.5, 1, 0.2, True),
            (0.0, 1, 0.5, False),
        )
    )
    candidate_q, _ = _margin_guard_q_rows(
        (
            (0.10, 1, 0.05, True),
            (0.50, 1, 0.20, True),
            (0.00, 1, 0.50, False),
        )
    )
    candidate_q.requires_grad_(True)

    loss, eligible_count, ranking_violation_count = (
        parent_end_turn_margin_guard_loss(
            candidate_q,
            parent_q,
            masks,
            margin_cap=0.1,
        )
    )

    assert eligible_count == 1
    assert ranking_violation_count == 1
    assert loss.item() == pytest.approx(0.15)
    loss.backward()
    assert candidate_q.grad[0, 1].item() < 0.0
    assert candidate_q.grad[0, END_TURN_ACTION].item() > 0.0
    assert torch.count_nonzero(candidate_q.grad[1:]).item() == 0


def test_parent_end_turn_margin_guard_zero_eligible_is_differentiable():
    parent_q, masks = _margin_guard_q_rows(((0.5, 1, 0.2, True),))
    candidate_q = parent_q.clone().requires_grad_(True)

    loss, eligible_count, ranking_violation_count = (
        parent_end_turn_margin_guard_loss(
            candidate_q,
            parent_q,
            masks,
            margin_cap=0.1,
        )
    )

    assert eligible_count == 0
    assert ranking_violation_count == 0
    assert loss.item() == 0.0
    loss.backward()
    assert torch.count_nonzero(candidate_q.grad).item() == 0


def test_parent_card_ranking_guard_clips_and_filters_rows():
    parent_q = torch.zeros((3, END_TURN_ACTION + 2), dtype=torch.float32)
    candidate_q = torch.zeros_like(parent_q)
    masks = torch.zeros_like(parent_q, dtype=torch.bool)

    masks[0, [1, 7, END_TURN_ACTION]] = True
    parent_q[0, 1] = 0.5
    parent_q[0, 7] = 0.3
    candidate_q[0, 1] = 0.0
    candidate_q[0, 7] = 0.2

    masks[1, [2, END_TURN_ACTION]] = True
    parent_q[1, 2] = 0.5
    candidate_q[1, 2] = 0.5

    masks[2, [3, 9, END_TURN_ACTION]] = True
    parent_q[2, 3] = 0.4
    parent_q[2, 9] = 0.4
    candidate_q[2, 3] = 0.4
    candidate_q[2, 9] = 0.4
    candidate_q.requires_grad_(True)

    loss, eligible_count, ranking_violation_count = parent_card_ranking_guard_loss(
        candidate_q,
        parent_q,
        masks,
        margin_cap=0.1,
    )

    assert PLAY_CARD_COUNT == 60
    assert eligible_count == 1
    assert ranking_violation_count == 1
    assert loss.item() == pytest.approx(0.3)
    loss.backward()
    assert candidate_q.grad[0, 1].item() < 0.0
    assert candidate_q.grad[0, 7].item() > 0.0
    assert torch.count_nonzero(candidate_q.grad[1:]).item() == 0


def test_parent_card_ranking_guard_zero_eligible_is_differentiable():
    parent_q = torch.zeros((1, END_TURN_ACTION + 2), dtype=torch.float32)
    masks = torch.zeros_like(parent_q, dtype=torch.bool)
    masks[0, [1, END_TURN_ACTION]] = True
    candidate_q = parent_q.clone().requires_grad_(True)

    loss, eligible_count, ranking_violation_count = parent_card_ranking_guard_loss(
        candidate_q,
        parent_q,
        masks,
        margin_cap=0.1,
    )

    assert eligible_count == 0
    assert ranking_violation_count == 0
    assert loss.item() == 0.0
    loss.backward()
    assert torch.count_nonzero(candidate_q.grad).item() == 0


def test_parent_top_action_margin_guard_protects_parent_end_turn_and_filters_rows():
    parent_q = torch.zeros((3, END_TURN_ACTION + 2), dtype=torch.float32)
    candidate_q = torch.zeros_like(parent_q)
    masks = torch.zeros_like(parent_q, dtype=torch.bool)

    masks[0, [1, END_TURN_ACTION]] = True
    parent_q[0, END_TURN_ACTION] = 0.5
    parent_q[0, 1] = 0.3
    candidate_q[0, END_TURN_ACTION] = 0.0
    candidate_q[0, 1] = 0.2

    masks[1, 2] = True
    parent_q[1, 2] = 0.5
    candidate_q[1, 2] = 0.5

    masks[2, [3, 9]] = True
    parent_q[2, 3] = 0.4
    parent_q[2, 9] = 0.4
    candidate_q[2, 3] = 0.4
    candidate_q[2, 9] = 0.4
    candidate_q.requires_grad_(True)

    loss, eligible_count, ranking_violation_count = (
        parent_top_action_margin_guard_loss(
            candidate_q,
            parent_q,
            masks,
            margin_cap=0.1,
        )
    )

    assert eligible_count == 1
    assert ranking_violation_count == 1
    assert loss.item() == pytest.approx(0.3)
    loss.backward()
    assert candidate_q.grad[0, END_TURN_ACTION].item() < 0.0
    assert candidate_q.grad[0, 1].item() > 0.0
    assert torch.count_nonzero(candidate_q.grad[1:]).item() == 0


def test_parent_top_action_margin_guard_zero_eligible_is_differentiable():
    parent_q = torch.zeros((1, END_TURN_ACTION + 2), dtype=torch.float32)
    masks = torch.zeros_like(parent_q, dtype=torch.bool)
    masks[0, 1] = True
    candidate_q = parent_q.clone().requires_grad_(True)

    loss, eligible_count, ranking_violation_count = (
        parent_top_action_margin_guard_loss(
            candidate_q,
            parent_q,
            masks,
            margin_cap=0.1,
        )
    )

    assert eligible_count == 0
    assert ranking_violation_count == 0
    assert loss.item() == 0.0
    loss.backward()
    assert torch.count_nonzero(candidate_q.grad).item() == 0


def test_parent_top_action_margin_guard_can_filter_to_direct_rows():
    parent_q = torch.tensor(
        [[0.5, 0.2], [0.6, 0.1], [0.4, 0.3]], dtype=torch.float32
    )
    candidate_q = torch.tensor(
        [[0.0, 0.3], [0.0, 0.4], [0.4, 0.3]],
        dtype=torch.float32,
        requires_grad=True,
    )
    masks = torch.ones_like(parent_q, dtype=torch.bool)

    all_loss, all_count, all_violations = parent_top_action_margin_guard_loss(
        candidate_q,
        parent_q,
        masks,
        margin_cap=0.1,
    )
    direct_loss, direct_count, direct_violations = (
        parent_top_action_margin_guard_loss(
            candidate_q,
            parent_q,
            masks,
            margin_cap=0.1,
            eligible_rows=torch.tensor([True, False, True]),
        )
    )

    assert all_count == 3
    assert all_violations == 2
    assert all_loss.item() == pytest.approx(0.3)
    assert direct_count == 2
    assert direct_violations == 1
    assert direct_loss.item() == pytest.approx(0.2)


def test_provenance_balanced_anchor_gives_strata_equal_aggregate_weight():
    q_values = torch.tensor(
        [[3.0, 0.0], [2.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
        dtype=torch.float32,
        requires_grad=True,
    )
    targets = torch.tensor([0, 0, 0, 0], dtype=torch.long)
    overrides = torch.tensor([False, False, False, True])

    loss, telemetry = provenance_balanced_parent_policy_anchor_loss(
        q_values,
        targets,
        overrides,
    )
    direct_loss = torch.nn.functional.cross_entropy(q_values[:3], targets[:3])
    override_loss = torch.nn.functional.cross_entropy(q_values[3:], targets[3:])

    assert telemetry == {
        "direct_count": 3,
        "override_count": 1,
        "direct_loss": pytest.approx(direct_loss.item()),
        "override_loss": pytest.approx(override_loss.item()),
    }
    assert loss.item() == pytest.approx(
        0.5 * (direct_loss.item() + override_loss.item())
    )
    assert loss.item() != pytest.approx(
        torch.nn.functional.cross_entropy(q_values, targets).item()
    )
    loss.backward()
    assert torch.isfinite(q_values.grad).all()


class _ActionEncoder:
    MAX_ACTIONS = 8

    def encode_action(self, action, _game):
        return getattr(action, "index", None)

    def decode_action(self, index, _game):
        return _Action(index)

    def get_action_mask(self, game):
        return game.action_mask


class _StateEncoder:
    def encode(self, game):
        return game.encoded


class _RewardCalculator:
    def calculate_step_reward(self, *, current_game, **_kwargs):
        return current_game.reward

    def reset(self):
        pass


class _Trainer:
    def __init__(self, loss=None):
        self.loss = loss
        self.transitions = []
        self.train_calls = 0
        self.episode_count = 0

    def store_transition(self, **transition):
        self.transitions.append(transition)

    def train_step(self):
        self.train_calls += 1
        return self.loss

    def update_episode_count(self):
        self.episode_count += 1


def _encoded(value):
    return SimpleNamespace(
        continuous=np.array([value], dtype=np.float32),
        card_ids=np.array([value], dtype=np.int64),
        potion_ids=np.array([value], dtype=np.int64),
        relic_ids=np.array([value], dtype=np.int64),
    )


def _game(value, *, floor=1, in_combat=True, reward=0.0):
    mask = np.zeros(_ActionEncoder.MAX_ACTIONS, dtype=bool)
    mask[1:] = True
    return SimpleNamespace(
        in_combat=in_combat,
        screen_type=None,
        player=SimpleNamespace(current_hp=50),
        hand=[],
        action_mask=mask,
        encoded=_encoded(value),
        floor=floor,
        reward=reward,
    )


def _agent(trainer=None):
    agent = RLAgentV2.__new__(RLAgentV2)
    agent.training_mode = True
    agent.trainer = trainer or _Trainer()
    agent.action_encoder = _ActionEncoder()
    agent.state_encoder = _StateEncoder()
    agent.reward_calculator = _RewardCalculator()
    agent.expert_agent = None
    agent.pending_transition = None
    agent.episode_reward = 0.0
    agent.episode_steps = 0
    return agent


def _pending(game, action_index=2):
    return PendingTransition(
        continuous=game.encoded.continuous,
        card_ids=game.encoded.card_ids,
        potion_ids=game.encoded.potion_ids,
        relic_ids=game.encoded.relic_ids,
        action_index=action_index,
        action_mask=game.action_mask.copy(),
        game=game,
        proposed_action_index=action_index,
    )


def test_emitted_guard_replacement_overwrites_pending_action_label():
    game = _game(1)
    agent = _agent()
    agent.pending_transition = _pending(game, action_index=2)

    assert agent.commit_executed_action(game, _Action(6)) is True
    assert agent.pending_transition.action_index == 6
    assert agent.pending_transition.proposed_action_index == 2
    assert agent.pending_transition.anchor_to_executed_action is True


def test_unchanged_emitted_rl_action_keeps_parent_anchor_label():
    game = _game(1)
    trainer = _Trainer(loss=None)
    agent = _agent(trainer)
    agent.pending_transition = _pending(game, action_index=2)

    assert agent.commit_executed_action(game, _Action(2)) is True
    assert agent.pending_transition.action_index == 2
    assert agent.pending_transition.proposed_action_index == 2
    assert agent.pending_transition.anchor_to_executed_action is False

    agent.observe_next_state(_game(2))

    assert trainer.transitions[0]["anchor_to_executed_action"] is False
    assert trainer.transitions[0]["proposed_action_index"] == 2


def test_fallback_emission_without_rl_proposal_uses_executed_action_anchor():
    game = _game(1)
    trainer = _Trainer(loss=None)
    agent = _agent(trainer)

    assert agent.commit_executed_action(game, _Action(6)) is True
    assert agent.pending_transition.action_index == 6
    assert agent.pending_transition.proposed_action_index == -1
    assert agent.pending_transition.anchor_to_executed_action is True

    agent.observe_next_state(_game(2))

    assert trainer.transitions[0]["anchor_to_executed_action"] is True
    assert trainer.transitions[0]["proposed_action_index"] == -1


def test_unencodable_same_state_emission_discards_proposed_transition():
    game = _game(1)
    agent = _agent()
    agent.pending_transition = _pending(game, action_index=2)

    assert agent.commit_executed_action(game, object()) is False
    assert agent.pending_transition is None


def test_illegal_emission_without_rl_proposal_does_not_create_transition():
    game = _game(1)
    agent = _agent()

    assert game.action_mask[0] is np.False_
    assert agent.commit_executed_action(game, _Action(0)) is False
    assert agent.pending_transition is None


def test_terminal_observation_flushes_last_action_without_bootstrap():
    previous = _game(1)
    terminal = _game(2, in_combat=False, reward=-200.0)
    trainer = _Trainer(loss=None)
    agent = _agent(trainer)
    agent.pending_transition = _pending(previous, action_index=4)

    assert agent.observe_next_state(terminal, terminal=True) is None

    assert agent.pending_transition is None
    assert agent.episode_reward == -200.0
    assert agent.episode_steps == 1
    assert trainer.train_calls == 1
    assert len(trainer.transitions) == 1
    transition = trainer.transitions[0]
    assert transition["action"] == 4
    assert transition["reward"] == -200.0
    assert transition["done"] is True
    assert transition["next_continuous"] is None
    assert transition["next_action_mask"].tolist() == [False] * 8


def test_floor_change_flushes_pending_action_without_cross_combat_bootstrap():
    previous = _game(1, floor=21)
    current = _game(2, floor=22, reward=4.0)
    trainer = _Trainer(loss=None)
    agent = _agent(trainer)
    agent.pending_transition = _pending(previous, action_index=4)

    assert agent.observe_next_state(current) is None

    transition = trainer.transitions[0]
    assert transition["done"] is True
    assert transition["next_continuous"] is None
    assert transition["next_card_ids"] is None
    assert transition["next_potion_ids"] is None
    assert transition["next_relic_ids"] is None
    assert transition["next_action_mask"].tolist() == [False] * 8


def test_nonterminal_observation_uses_next_state_and_counts_transition_without_loss():
    previous = _game(1)
    current = _game(2, reward=3.5)
    trainer = _Trainer(loss=None)
    agent = _agent(trainer)
    agent.pending_transition = _pending(previous, action_index=3)

    agent.observe_next_state(current)

    transition = trainer.transitions[0]
    assert transition["done"] is False
    assert transition["next_continuous"].tolist() == [2.0]
    assert transition["next_action_mask"].tolist() == current.action_mask.tolist()
    assert agent.episode_reward == 3.5
    assert agent.episode_steps == 1


def _real_trainer(
    *,
    learning_starts=4,
    parent_policy_anchor_weight=0.0,
    positive_energy_action_imitation_weight=0.0,
    positive_energy_parent_end_turn_imitation_weight=0.0,
    parent_policy_anchor_provenance_balanced=False,
    parent_top_action_margin_guard_weight=0.0,
    parent_top_action_margin_guard_direct_only=False,
    action_dim=2,
):
    return DQNTrainerV2(
        continuous_dim=2,
        action_dim=action_dim,
        card_slots=1,
        potion_slots=1,
        relic_slots=1,
        card_vocab=3,
        potion_vocab=3,
        relic_vocab=3,
        card_embed_dim=2,
        potion_embed_dim=2,
        relic_embed_dim=2,
        batch_size=4,
        learning_starts=learning_starts,
        train_freq=1,
        target_update_freq=8,
        device="cpu",
        parent_policy_anchor_weight=parent_policy_anchor_weight,
        parent_policy_anchor_provenance_balanced=(
            parent_policy_anchor_provenance_balanced
        ),
        parent_top_action_margin_guard_weight=(
            parent_top_action_margin_guard_weight
        ),
        parent_top_action_margin_guard_direct_only=(
            parent_top_action_margin_guard_direct_only
        ),
        positive_energy_action_imitation_weight=(
            positive_energy_action_imitation_weight
        ),
        positive_energy_parent_end_turn_imitation_weight=(
            positive_energy_parent_end_turn_imitation_weight
        ),
    )


def _selection_inputs(trainer):
    return {
        "continuous": np.zeros(2, dtype=np.float32),
        "card_ids": np.zeros(1, dtype=np.int64),
        "potion_ids": np.zeros(1, dtype=np.int64),
        "relic_ids": np.zeros(1, dtype=np.int64),
        "action_mask": np.ones(trainer.action_dim, dtype=bool),
        "training": True,
        "epsilon_override": 0.0,
    }


@pytest.mark.parametrize("initial_training", [True, False])
def test_greedy_action_selection_uses_eval_mode_and_restores_prior_mode(
    monkeypatch,
    initial_training,
):
    trainer = _real_trainer(action_dim=3)
    trainer.online_network.train(initial_training)
    observed_modes = []

    def get_best_action(**kwargs):
        observed_modes.append(trainer.online_network.training)
        assert kwargs["action_mask"].tolist() == [[True, True, True]]
        return torch.tensor([1])

    monkeypatch.setattr(trainer.online_network, "get_best_action", get_best_action)

    assert trainer.select_action(**_selection_inputs(trainer)) == 1
    assert observed_modes == [False]
    assert trainer.online_network.training is initial_training


@pytest.mark.parametrize("initial_training", [True, False])
def test_greedy_action_selection_restores_prior_mode_after_failure(
    monkeypatch,
    initial_training,
):
    trainer = _real_trainer(action_dim=3)
    trainer.online_network.train(initial_training)
    observed_modes = []

    def fail_selection(**_kwargs):
        observed_modes.append(trainer.online_network.training)
        raise RuntimeError("selection failed")

    monkeypatch.setattr(trainer.online_network, "get_best_action", fail_selection)

    with pytest.raises(RuntimeError, match="selection failed"):
        trainer.select_action(**_selection_inputs(trainer))

    assert observed_modes == [False]
    assert trainer.online_network.training is initial_training


def test_zero_epsilon_greedy_selection_is_deterministic_with_dropout():
    trainer = _real_trainer(action_dim=8)
    trainer.online_network.train()
    assert any(
        isinstance(module, torch.nn.Dropout)
        for module in trainer.online_network.modules()
    )
    online_before = {
        key: value.detach().clone()
        for key, value in trainer.online_network.state_dict().items()
    }

    actions = []
    for seed in range(20):
        torch.manual_seed(seed)
        actions.append(trainer.select_action(**_selection_inputs(trainer)))

    assert len(set(actions)) == 1
    assert trainer.online_network.training is True
    assert trainer.target_network.training is False
    assert all(
        torch.equal(trainer.online_network.state_dict()[key], value)
        for key, value in online_before.items()
    )


def test_epsilon_exploration_preserves_network_mode_without_forward(
    monkeypatch,
):
    trainer = _real_trainer(action_dim=3)
    trainer.online_network.train()
    inputs = _selection_inputs(trainer)
    inputs["action_mask"] = np.array([False, True, True], dtype=bool)
    inputs["epsilon_override"] = 1.0

    monkeypatch.setattr(np.random, "random", lambda: 0.0)
    monkeypatch.setattr(np.random, "choice", lambda values: values[-1])

    def unexpected_forward(**_kwargs):
        raise AssertionError("epsilon branch must not evaluate the online network")

    monkeypatch.setattr(trainer.online_network, "get_best_action", unexpected_forward)

    assert trainer.select_action(**inputs) == 2
    assert trainer.online_network.training is True


def _store_real_transition(
    trainer,
    *,
    continuous=None,
    done=False,
    action=0,
    action_mask=None,
    anchor_to_executed_action=False,
):
    if continuous is None:
        continuous = np.zeros(2, dtype=np.float32)
    if action_mask is None:
        action_mask = np.ones(trainer.action_dim, dtype=bool)
    return trainer.store_transition(
        continuous=continuous,
        card_ids=np.zeros(1, dtype=np.int64),
        potion_ids=np.zeros(1, dtype=np.int64),
        relic_ids=np.zeros(1, dtype=np.int64),
        action=action,
        reward=-200.0 if done else 1.0,
        next_continuous=None if done else np.ones(2, dtype=np.float32),
        next_card_ids=None if done else np.zeros(1, dtype=np.int64),
        next_potion_ids=None if done else np.zeros(1, dtype=np.int64),
        next_relic_ids=None if done else np.zeros(1, dtype=np.int64),
        done=done,
        action_mask=action_mask,
        next_action_mask=(
            np.zeros(trainer.action_dim, dtype=bool)
            if done
            else np.ones(trainer.action_dim, dtype=bool)
        ),
        anchor_to_executed_action=anchor_to_executed_action,
    )


def test_rejected_replay_shape_does_not_advance_training_steps():
    trainer = _real_trainer()

    assert _store_real_transition(
        trainer,
        continuous=np.zeros(3, dtype=np.float32),
    ) is False
    assert trainer.total_steps == 0
    assert len(trainer.replay_buffer.buffer) == 0


def test_terminal_all_false_next_mask_produces_finite_loss():
    trainer = _real_trainer()
    for _ in range(4):
        assert _store_real_transition(trainer, done=True) is True

    loss = trainer.train_step()

    assert loss is not None
    assert math.isfinite(loss)


def test_learning_starts_blocks_updates_after_batch_size_is_reached():
    trainer = _real_trainer(learning_starts=5)
    for _ in range(4):
        assert _store_real_transition(trainer) is True

    assert trainer.train_step() is None
    assert len(trainer.optimizer.state) == 0

    assert _store_real_transition(trainer) is True
    assert trainer.train_step() is not None
    assert len(trainer.optimizer.state) > 0


def test_zero_parent_policy_anchor_preserves_td_only_training():
    trainer = _real_trainer()
    for _ in range(4):
        assert _store_real_transition(trainer) is True

    loss = trainer.train_step()

    assert trainer.parent_policy_anchor_network is None
    assert trainer.last_parent_policy_anchor_loss == 0.0
    assert trainer.last_parent_policy_anchor_override_count == 0
    assert loss == pytest.approx(trainer.last_td_loss)


def test_parent_policy_anchor_adds_finite_masked_loss_without_training_anchor():
    trainer = _real_trainer(parent_policy_anchor_weight=0.5)
    trainer.set_parent_policy_anchor(trainer.online_network.state_dict())
    anchor_before = {
        key: value.detach().clone()
        for key, value in trainer.parent_policy_anchor_network.state_dict().items()
    }
    for _ in range(4):
        assert _store_real_transition(trainer) is True

    loss = trainer.train_step()

    assert math.isfinite(loss)
    assert trainer.last_parent_policy_anchor_loss > 0.0
    assert loss == pytest.approx(
        trainer.last_td_loss
        + trainer.parent_policy_anchor_weight
        * trainer.last_parent_policy_anchor_loss
    )
    assert all(
        torch.equal(
            trainer.parent_policy_anchor_network.state_dict()[key], value
        )
        for key, value in anchor_before.items()
    )
    assert all(
        parameter.grad is None
        for parameter in trainer.parent_policy_anchor_network.parameters()
    )


def test_parent_policy_anchor_uses_mixed_executed_and_parent_targets():
    trainer = _real_trainer(parent_policy_anchor_weight=1.0)
    trainer.set_parent_policy_anchor(trainer.online_network.state_dict())
    with torch.no_grad():
        trainer.parent_policy_anchor_network.advantage_stream[-1].bias[1] = 100.0
    anchor_before = {
        key: value.detach().clone()
        for key, value in trainer.parent_policy_anchor_network.state_dict().items()
    }
    for override in (True, True, False, False):
        assert _store_real_transition(
            trainer,
            action=0,
            anchor_to_executed_action=override,
        ) is True

    loss = trainer.train_step()

    assert math.isfinite(loss)
    assert trainer.last_parent_policy_anchor_override_count == 2
    assert trainer.last_parent_policy_anchor_loss > 0.0
    assert all(
        torch.equal(
            trainer.parent_policy_anchor_network.state_dict()[key], value
        )
        for key, value in anchor_before.items()
    )
    assert all(
        parameter.grad is None
        for parameter in trainer.parent_policy_anchor_network.parameters()
    )


def test_provenance_balanced_anchor_reports_component_telemetry():
    trainer = _real_trainer(
        parent_policy_anchor_weight=1.0,
        parent_policy_anchor_provenance_balanced=True,
    )
    trainer.set_parent_policy_anchor(trainer.online_network.state_dict())
    with torch.no_grad():
        trainer.parent_policy_anchor_network.advantage_stream[-1].bias[1] = 100.0
    for override in (True, True, False, False):
        assert _store_real_transition(
            trainer,
            action=0,
            anchor_to_executed_action=override,
        ) is True

    loss = trainer.train_step()

    assert math.isfinite(loss)
    assert trainer.last_parent_policy_anchor_direct_count == 2
    assert trainer.last_parent_policy_anchor_override_count == 2
    assert trainer.last_parent_policy_anchor_direct_loss > 0.0
    assert trainer.last_parent_policy_anchor_override_loss > 0.0
    assert trainer.last_parent_policy_anchor_loss == pytest.approx(
        0.5
        * (
            trainer.last_parent_policy_anchor_direct_loss
            + trainer.last_parent_policy_anchor_override_loss
        )
    )


def test_direct_only_top_action_guard_excludes_override_rows_in_trainer():
    trainer = _real_trainer(
        parent_policy_anchor_weight=1.0,
        parent_top_action_margin_guard_weight=1.0,
        parent_top_action_margin_guard_direct_only=True,
    )
    trainer.set_parent_policy_anchor(trainer.online_network.state_dict())
    with torch.no_grad():
        trainer.parent_policy_anchor_network.advantage_stream[-1].bias[1] = 100.0
    for override in (True, True, False, False):
        assert _store_real_transition(
            trainer,
            action=0,
            anchor_to_executed_action=override,
        ) is True

    loss = trainer.train_step()

    assert math.isfinite(loss)
    assert trainer.last_parent_top_action_margin_guard_eligible_count == 2


def test_parent_policy_anchor_rejects_invalid_executed_action_override_before_update():
    trainer = _real_trainer(parent_policy_anchor_weight=1.0)
    trainer.set_parent_policy_anchor(trainer.online_network.state_dict())
    for _ in range(4):
        assert _store_real_transition(
            trainer,
            action=1,
            action_mask=np.array([True, False], dtype=bool),
            anchor_to_executed_action=True,
        ) is True

    with pytest.raises(ValueError, match="executed-action anchor override is invalid"):
        trainer.train_step()

    assert len(trainer.optimizer.state) == 0


def test_positive_energy_action_imitation_adds_executed_action_loss():
    trainer = _real_trainer(
        action_dim=91,
        positive_energy_action_imitation_weight=0.25,
    )
    for _ in range(4):
        assert _store_real_transition(
            trainer,
            continuous=np.array([0.5, 0.6], dtype=np.float32),
            action=0,
        ) is True

    loss = trainer.train_step()

    assert math.isfinite(loss)
    assert trainer.last_positive_energy_action_imitation_count == 4
    assert trainer.last_positive_energy_action_imitation_loss > 0.0
    assert loss == pytest.approx(
        trainer.last_td_loss
        + trainer.positive_energy_action_imitation_weight
        * trainer.last_positive_energy_action_imitation_loss
    )


def test_positive_energy_action_imitation_ignores_zero_energy_states():
    trainer = _real_trainer(
        action_dim=91,
        positive_energy_action_imitation_weight=0.25,
    )
    for _ in range(4):
        assert _store_real_transition(
            trainer,
            continuous=np.array([0.5, 0.0], dtype=np.float32),
            action=0,
        ) is True

    loss = trainer.train_step()

    assert trainer.last_positive_energy_action_imitation_count == 0
    assert trainer.last_positive_energy_action_imitation_loss == 0.0
    assert loss == pytest.approx(trainer.last_td_loss)


def test_parent_end_turn_imitation_targets_only_parent_end_turn_states():
    trainer = _real_trainer(
        action_dim=91,
        parent_policy_anchor_weight=1.0,
        positive_energy_parent_end_turn_imitation_weight=0.2,
    )
    trainer.set_parent_policy_anchor(trainer.online_network.state_dict())
    with torch.no_grad():
        trainer.parent_policy_anchor_network.advantage_stream[-1].bias[
            END_TURN_ACTION
        ] = 100.0
    for _ in range(4):
        assert _store_real_transition(
            trainer,
            continuous=np.array([0.5, 0.6], dtype=np.float32),
            action=0,
        ) is True

    loss = trainer.train_step()

    assert trainer.last_positive_energy_parent_end_turn_imitation_count == 4
    assert trainer.last_positive_energy_parent_end_turn_imitation_loss > 0.0
    assert loss == pytest.approx(
        trainer.last_td_loss
        + trainer.parent_policy_anchor_weight
        * trainer.last_parent_policy_anchor_loss
        + trainer.positive_energy_parent_end_turn_imitation_weight
        * trainer.last_positive_energy_parent_end_turn_imitation_loss
    )


def test_parent_end_turn_imitation_requires_anchor_and_excludes_other_parent_actions():
    with pytest.raises(ValueError, match="requires a positive parent policy anchor"):
        _real_trainer(positive_energy_parent_end_turn_imitation_weight=0.2)

    trainer = _real_trainer(
        action_dim=91,
        parent_policy_anchor_weight=1.0,
        positive_energy_parent_end_turn_imitation_weight=0.2,
    )
    trainer.set_parent_policy_anchor(trainer.online_network.state_dict())
    with torch.no_grad():
        trainer.parent_policy_anchor_network.advantage_stream[-1].bias[1] = 100.0
    for _ in range(4):
        assert _store_real_transition(
            trainer,
            continuous=np.array([0.5, 0.6], dtype=np.float32),
            action=0,
        ) is True

    trainer.train_step()

    assert trainer.last_positive_energy_parent_end_turn_imitation_count == 0
    assert trainer.last_positive_energy_parent_end_turn_imitation_loss == 0.0


def test_parent_policy_anchor_label_respects_stored_action_mask():
    trainer = _real_trainer(parent_policy_anchor_weight=0.5)
    trainer.set_parent_policy_anchor(trainer.online_network.state_dict())
    with torch.no_grad():
        trainer.parent_policy_anchor_network.advantage_stream[-1].bias[1] = 100.0

    continuous = torch.zeros((1, 2), dtype=torch.float32)
    card_ids = torch.zeros((1, 1), dtype=torch.int64)
    potion_ids = torch.zeros((1, 1), dtype=torch.int64)
    relic_ids = torch.zeros((1, 1), dtype=torch.int64)
    mask = torch.tensor([[True, False]])

    actions = trainer.get_parent_policy_anchor_actions(
        continuous,
        card_ids,
        potion_ids,
        relic_ids,
        mask,
    )

    assert actions.tolist() == [0]


def test_replay_checkpoint_round_trip_keeps_bounded_chronological_tail():
    replay = ReplayBufferV2(
        buffer_size=5,
        continuous_dim=2,
        action_dim=2,
        card_slots=1,
        potion_slots=1,
        relic_slots=1,
    )
    for value in range(8):
        done = value == 7
        assert replay.add(
            continuous=np.array([value, value + 0.5], dtype=np.float32),
            card_ids=np.array([value], dtype=np.int64),
            potion_ids=np.array([value + 1], dtype=np.int64),
            relic_ids=np.array([value + 2], dtype=np.int64),
            action=value % 2,
            reward=float(value),
            next_continuous=None
            if done
            else np.array([value + 1, value + 1.5], dtype=np.float32),
            next_card_ids=None if done else np.array([value + 1], dtype=np.int64),
            next_potion_ids=None if done else np.array([value + 2], dtype=np.int64),
            next_relic_ids=None if done else np.array([value + 3], dtype=np.int64),
            done=done,
            action_mask=np.ones(2, dtype=bool),
            next_action_mask=np.zeros(2, dtype=bool)
            if done
            else np.ones(2, dtype=bool),
            anchor_to_executed_action=bool(value % 2),
            proposed_action_index=(
                -1
                if value == 7
                else (value + 1) % 2
                if value % 2
                else value % 2
            ),
        )

    state = replay.state_dict(max_transitions=3)
    restored = ReplayBufferV2(
        buffer_size=5,
        continuous_dim=2,
        action_dim=2,
        card_slots=1,
        potion_slots=1,
        relic_slots=1,
    )
    restored.load_state_dict(state)

    assert len(restored) == 3
    assert state["schema_version"] == 3
    assert state["source_transition_count"] == 5
    assert state["truncated"] is True
    assert state["anchor_to_executed_action"].tolist() == [True, False, True]
    assert state["proposed_action_indices"].tolist() == [0, 0, -1]
    assert [transition[5] for transition in restored.buffer] == [5.0, 6.0, 7.0]
    assert [transition[13] for transition in restored.buffer] == [True, False, True]
    assert [transition[14] for transition in restored.buffer] == [0, 0, -1]
    assert restored.buffer[-1][10] is True
    assert restored.buffer[-1][6] is None
    assert restored.position == 3


def test_replay_default_override_is_false_and_version1_loads_all_false():
    replay = ReplayBufferV2(
        buffer_size=2,
        continuous_dim=2,
        action_dim=2,
        card_slots=1,
        potion_slots=1,
        relic_slots=1,
    )
    assert replay.add(
        continuous=np.zeros(2, dtype=np.float32),
        card_ids=np.zeros(1, dtype=np.int64),
        potion_ids=np.zeros(1, dtype=np.int64),
        relic_ids=np.zeros(1, dtype=np.int64),
        action=0,
        reward=1.0,
        next_continuous=np.ones(2, dtype=np.float32),
        next_card_ids=np.zeros(1, dtype=np.int64),
        next_potion_ids=np.zeros(1, dtype=np.int64),
        next_relic_ids=np.zeros(1, dtype=np.int64),
        done=False,
        action_mask=np.ones(2, dtype=bool),
        next_action_mask=np.ones(2, dtype=bool),
    )
    assert replay.buffer[0][13] is False
    assert replay.buffer[0][14] == -2

    legacy_state = replay.state_dict()
    legacy_state["schema_version"] = 1
    legacy_state.pop("anchor_to_executed_action")
    legacy_state.pop("proposed_action_indices")
    restored = ReplayBufferV2(
        buffer_size=2,
        continuous_dim=2,
        action_dim=2,
        card_slots=1,
        potion_slots=1,
        relic_slots=1,
    )
    restored.load_state_dict(legacy_state)

    assert restored.buffer[0][13] is False
    assert restored.buffer[0][14] == -2
    assert restored.sample(1)[13].tolist() == [False]
    assert len(restored.sample(1)) == 14
    assert restored.sample(1, include_proposed_action=True)[14].tolist() == [-2]


def test_replay_version2_load_preserves_override_with_unknown_proposal():
    replay = ReplayBufferV2(
        buffer_size=2,
        continuous_dim=2,
        action_dim=2,
        card_slots=1,
        potion_slots=1,
        relic_slots=1,
    )
    assert replay.add(
        continuous=np.zeros(2, dtype=np.float32),
        card_ids=np.zeros(1, dtype=np.int64),
        potion_ids=np.zeros(1, dtype=np.int64),
        relic_ids=np.zeros(1, dtype=np.int64),
        action=1,
        reward=1.0,
        next_continuous=np.ones(2, dtype=np.float32),
        next_card_ids=np.zeros(1, dtype=np.int64),
        next_potion_ids=np.zeros(1, dtype=np.int64),
        next_relic_ids=np.zeros(1, dtype=np.int64),
        done=False,
        action_mask=np.ones(2, dtype=bool),
        next_action_mask=np.ones(2, dtype=bool),
        anchor_to_executed_action=True,
    )
    version2 = replay.state_dict()
    version2["schema_version"] = 2
    version2.pop("proposed_action_indices")

    restored = ReplayBufferV2(
        buffer_size=2,
        continuous_dim=2,
        action_dim=2,
        card_slots=1,
        potion_slots=1,
        relic_slots=1,
    )
    restored.load_state_dict(version2)

    assert restored.buffer[0][13] is True
    assert restored.buffer[0][14] == -2


def test_replay_rejects_inconsistent_known_proposal_identity():
    replay = ReplayBufferV2(
        buffer_size=2,
        continuous_dim=2,
        action_dim=2,
        card_slots=1,
        potion_slots=1,
        relic_slots=1,
    )
    common = {
        "continuous": np.zeros(2, dtype=np.float32),
        "card_ids": np.zeros(1, dtype=np.int64),
        "potion_ids": np.zeros(1, dtype=np.int64),
        "relic_ids": np.zeros(1, dtype=np.int64),
        "action": 0,
        "reward": 1.0,
        "next_continuous": np.ones(2, dtype=np.float32),
        "next_card_ids": np.zeros(1, dtype=np.int64),
        "next_potion_ids": np.zeros(1, dtype=np.int64),
        "next_relic_ids": np.zeros(1, dtype=np.int64),
        "done": False,
        "action_mask": np.ones(2, dtype=bool),
        "next_action_mask": np.ones(2, dtype=bool),
    }
    assert replay.add(
        **common,
        anchor_to_executed_action=False,
        proposed_action_index=-1,
    ) is False
    assert replay.add(
        **common,
        anchor_to_executed_action=False,
        proposed_action_index=0,
    ) is True

    inconsistent = replay.state_dict()
    inconsistent["proposed_action_indices"][0] = 1
    restored = ReplayBufferV2(
        buffer_size=2,
        continuous_dim=2,
        action_dim=2,
        card_slots=1,
        potion_slots=1,
        relic_slots=1,
    )
    with pytest.raises(ValueError, match="proposal identity"):
        restored.load_state_dict(inconsistent)


def _checkpoint_agent(
    *,
    learning_starts=4,
    parent_policy_anchor_weight=0.0,
    positive_energy_action_imitation_weight=0.0,
    positive_energy_parent_end_turn_imitation_weight=0.0,
):
    agent = RLAgentV2.__new__(RLAgentV2)
    agent.device = "cpu"
    agent.training_mode = True
    agent.training = True
    agent.network_type = "dueling"
    agent.trainer = _real_trainer(
        learning_starts=learning_starts,
        parent_policy_anchor_weight=parent_policy_anchor_weight,
        positive_energy_action_imitation_weight=(
            positive_energy_action_imitation_weight
        ),
        positive_energy_parent_end_turn_imitation_weight=(
            positive_energy_parent_end_turn_imitation_weight
        ),
    )
    agent.network = agent.trainer.online_network
    agent.state_encoder = SimpleNamespace(
        feature_dim=2,
        CARD_SLOTS=1,
        POTION_SLOTS=1,
        RELIC_SLOTS=1,
    )
    agent.action_encoder = SimpleNamespace(MAX_ACTIONS=2)
    agent.id_mapper = SimpleNamespace(
        card_vocab_size=3,
        potion_vocab_size=3,
        relic_vocab_size=3,
    )
    return agent


def test_positive_energy_action_imitation_checkpoint_round_trip(tmp_path):
    source = _checkpoint_agent(positive_energy_action_imitation_weight=0.25)
    path = tmp_path / "imitation-resume.pth"
    source.save_model(str(path))

    stored = torch.load(path, map_location="cpu", weights_only=True)
    assert stored["positive_energy_action_imitation_weight"] == pytest.approx(0.25)
    assert (
        stored["training_metrics"][
            "last_positive_energy_action_imitation_count"
        ]
        == 0
    )

    restored = _checkpoint_agent(positive_energy_action_imitation_weight=0.25)
    restored.load_model(str(path))
    assert restored.trainer.positive_energy_action_imitation_weight == pytest.approx(
        0.25
    )

    with pytest.raises(ValueError, match="does not match requested weight"):
        _checkpoint_agent().load_model(str(path))


def test_parent_end_turn_imitation_checkpoint_round_trip(tmp_path):
    source = _checkpoint_agent(
        parent_policy_anchor_weight=1.0,
        positive_energy_parent_end_turn_imitation_weight=0.2,
    )
    source.trainer.set_parent_policy_anchor(source.trainer.online_network.state_dict())
    path = tmp_path / "parent-end-turn-imitation-resume.pth"
    source.save_model(str(path))

    stored = torch.load(path, map_location="cpu", weights_only=True)
    assert stored["positive_energy_parent_end_turn_imitation_weight"] == pytest.approx(
        0.2
    )
    assert (
        stored["training_metrics"][
            "last_positive_energy_parent_end_turn_imitation_count"
        ]
        == 0
    )

    restored = _checkpoint_agent(
        parent_policy_anchor_weight=1.0,
        positive_energy_parent_end_turn_imitation_weight=0.2,
    )
    restored.load_model(str(path))
    assert (
        restored.trainer.positive_energy_parent_end_turn_imitation_weight
        == pytest.approx(0.2)
    )

    with pytest.raises(ValueError, match="does not match requested weight"):
        _checkpoint_agent(parent_policy_anchor_weight=1.0).load_model(str(path))


def _optimizer_step(trainer):
    steps = [
        int(state["step"].item())
        for state in trainer.optimizer.state.values()
        if "step" in state
    ]
    return max(steps) if steps else 0


def test_v2_checkpoint_round_trip_restores_target_replay_optimizer_and_episode(tmp_path):
    source = _checkpoint_agent(learning_starts=6)
    for _ in range(6):
        assert _store_real_transition(source.trainer) is True
        source.trainer.train_step()
    source.trainer.episode_count = 7
    source.trainer.epsilon = 0.42
    with torch.no_grad():
        for parameter in source.trainer.target_network.parameters():
            parameter.add_(0.25)

    path = tmp_path / "v2-resume.pth"
    source.save_model(str(path), episode=999)
    restored = _checkpoint_agent()
    restored.load_model(str(path))

    assert restored.trainer.episode_count == 7
    assert restored.trainer.total_steps == 6
    assert restored.trainer.epsilon == pytest.approx(0.42)
    assert restored.trainer.learning_starts == 6
    assert len(restored.trainer.replay_buffer) == 6
    assert _optimizer_step(restored.trainer) == _optimizer_step(source.trainer)
    assert all(
        torch.equal(restored.trainer.online_network.state_dict()[key], value)
        for key, value in source.trainer.online_network.state_dict().items()
    )
    assert all(
        torch.equal(restored.trainer.target_network.state_dict()[key], value)
        for key, value in source.trainer.target_network.state_dict().items()
    )
    assert any(
        not torch.equal(restored.trainer.target_network.state_dict()[key], value)
        for key, value in restored.trainer.online_network.state_dict().items()
    )

    assert _store_real_transition(restored.trainer) is True
    restored.trainer.train_step()
    assert any(
        not torch.equal(restored.trainer.target_network.state_dict()[key], value)
        for key, value in restored.trainer.online_network.state_dict().items()
    )
    assert _store_real_transition(restored.trainer) is True
    restored.trainer.train_step()
    assert all(
        torch.equal(restored.trainer.target_network.state_dict()[key], value)
        for key, value in restored.trainer.online_network.state_dict().items()
    )


def test_positive_parent_policy_anchor_requires_parent_checkpoint():
    with pytest.raises(ValueError, match="parent checkpoint"):
        RLAgentV2(
            training=True,
            device="cpu",
            parent_policy_anchor_weight=0.25,
        )


def test_boss_min_epsilon_can_be_disabled_for_replay_collection(monkeypatch):
    monkeypatch.setenv("STS_RL_BOSS_MIN_EPSILON", "0")

    agent = RLAgentV2(
        training=False,
        device="cpu",
        id_mapper=IdMapper(card_ids={}, potion_ids={}, relic_ids={}, card_tags={}),
    )

    assert agent.boss_min_epsilon == 0.0


def test_boss_min_epsilon_rejects_invalid_environment(monkeypatch):
    monkeypatch.setenv("STS_RL_BOSS_MIN_EPSILON", "nan")

    with pytest.raises(ValueError, match="boss minimum epsilon"):
        RLAgentV2(
            training=False,
            device="cpu",
            id_mapper=IdMapper(
                card_ids={}, potion_ids={}, relic_ids={}, card_tags={}
            ),
        )


def test_existing_checkpoint_becomes_initial_parent_policy_anchor(tmp_path):
    source = _checkpoint_agent()
    with torch.no_grad():
        for parameter in source.trainer.online_network.parameters():
            parameter.add_(0.125)
    path = tmp_path / "unanchored-parent.pth"
    source.save_model(str(path))

    restored = _checkpoint_agent(parent_policy_anchor_weight=0.25)
    restored.load_model(str(path))

    assert restored.trainer.parent_policy_anchor_network is not None
    assert all(
        torch.equal(
            restored.trainer.parent_policy_anchor_network.state_dict()[key],
            value,
        )
        for key, value in source.trainer.online_network.state_dict().items()
    )
    assert all(
        not parameter.requires_grad
        for parameter in restored.trainer.parent_policy_anchor_network.parameters()
    )


def test_anchored_checkpoint_resume_restores_original_parent_policy(tmp_path):
    source = _checkpoint_agent(parent_policy_anchor_weight=0.25)
    source.trainer.set_parent_policy_anchor(source.trainer.online_network.state_dict())
    anchor_state = {
        key: value.detach().clone()
        for key, value in source.trainer.parent_policy_anchor_network.state_dict().items()
    }
    with torch.no_grad():
        for parameter in source.trainer.online_network.parameters():
            parameter.add_(0.5)
    path = tmp_path / "anchored-resume.pth"
    source.save_model(str(path))

    restored = _checkpoint_agent(parent_policy_anchor_weight=0.25)
    restored.load_model(str(path))

    assert all(
        torch.equal(
            restored.trainer.parent_policy_anchor_network.state_dict()[key],
            value,
        )
        for key, value in anchor_state.items()
    )
    assert any(
        not torch.equal(
            restored.trainer.online_network.state_dict()[key],
            value,
        )
        for key, value in anchor_state.items()
    )


def test_schema2_training_checkpoint_requires_complete_resume_state(tmp_path):
    source = _checkpoint_agent()
    path = tmp_path / "incomplete-v2.pth"
    checkpoint = {
        "checkpoint_schema_version": RLAgentV2.CHECKPOINT_SCHEMA_VERSION,
        "checkpoint_kind": "training",
        "metadata": source._build_metadata().as_dict(),
        "online_network_state_dict": source.network.state_dict(),
        "target_network_state_dict": source.trainer.target_network.state_dict(),
        "replay_buffer_state_dict": source.trainer.replay_buffer.state_dict(),
    }
    torch.save(checkpoint, path)

    with pytest.raises(ValueError, match="missing training state"):
        _checkpoint_agent().load_model(str(path))


def test_legacy_checkpoint_restores_optimizer_and_uses_replay_warmup(tmp_path):
    source = _checkpoint_agent()
    for _ in range(4):
        assert _store_real_transition(source.trainer) is True
        source.trainer.train_step()
    assert _optimizer_step(source.trainer) > 0

    path = tmp_path / "legacy-v2.pth"
    torch.save(
        {
            "metadata": source._build_metadata().as_dict(),
            "rl_space_version": "v2",
            "online_network_state_dict": source.network.state_dict(),
            "optimizer_state_dict": source.trainer.optimizer.state_dict(),
            "episode": 5,
            "epsilon": 0.6,
            "total_steps": 123,
        },
        path,
    )

    restored = _checkpoint_agent(learning_starts=2048)
    restored.load_model(str(path))

    assert restored.trainer.episode_count == 5
    assert restored.trainer.total_steps == 123
    assert restored.trainer.epsilon == pytest.approx(0.6)
    assert restored.trainer.learning_starts == RLAgentV2.CHECKPOINT_REPLAY_LIMIT
    assert len(restored.trainer.replay_buffer) == 0
    assert _optimizer_step(restored.trainer) == _optimizer_step(source.trainer)
    assert all(
        torch.equal(restored.trainer.target_network.state_dict()[key], value)
        for key, value in restored.trainer.online_network.state_dict().items()
    )
    for _ in range(restored.trainer.learning_starts - 1):
        assert _store_real_transition(restored.trainer) is True
    assert restored.trainer.train_step() is None


def test_schema2_weights_checkpoint_loads_for_degraded_training_resume(tmp_path):
    source = _checkpoint_agent()
    source.training_mode = False
    source.training = False
    path = tmp_path / "weights-v2.pth"
    source.save_model(str(path))

    restored = _checkpoint_agent()
    restored.load_model(str(path))

    assert len(restored.trainer.replay_buffer) == 0
    assert restored.trainer.learning_starts == RLAgentV2.CHECKPOINT_REPLAY_LIMIT
    assert all(
        torch.equal(restored.trainer.target_network.state_dict()[key], value)
        for key, value in restored.trainer.online_network.state_dict().items()
    )


def test_unknown_checkpoint_schema_is_rejected(tmp_path):
    source = _checkpoint_agent()
    path = tmp_path / "future-v2.pth"
    torch.save(
        {
            "checkpoint_schema_version": RLAgentV2.CHECKPOINT_SCHEMA_VERSION + 1,
            "checkpoint_kind": "training",
            "metadata": source._build_metadata().as_dict(),
            "online_network_state_dict": source.network.state_dict(),
        },
        path,
    )

    with pytest.raises(ValueError, match="Unsupported checkpoint schema"):
        _checkpoint_agent().load_model(str(path))


def test_episode_count_advances_on_completion_not_reset():
    terminal = _game(2, in_combat=False, reward=-200.0)
    trainer = _Trainer()
    agent = _agent(trainer)

    agent.reset()
    assert trainer.episode_count == 0

    agent.pending_transition = _pending(_game(1))
    agent.finalize_training_episode(terminal)
    assert trainer.episode_count == 1

    agent.reset()
    assert trainer.episode_count == 1


def test_combat_wrapper_binds_the_final_emitted_action():
    calls = []
    wrapper = CombatRLAgent.__new__(CombatRLAgent)
    wrapper.rl_agent = SimpleNamespace(
        commit_executed_action=lambda game, action: calls.append((game, action))
    )
    game = SimpleNamespace(floor=7, turn=3)
    action = EndTurnAction()

    assert wrapper._with_combat_action_context(action, game) is action
    assert calls == [(game, action)]


def test_combat_wrapper_defers_dead_monster_transition_but_flushes_game_over():
    calls = []
    wrapper = CombatRLAgent.__new__(CombatRLAgent)
    wrapper.rl_agent = SimpleNamespace(
        observe_next_state=lambda game, terminal: calls.append((game, terminal))
    )
    dead_transition = SimpleNamespace(
        in_combat=True,
        screen_type=None,
        monsters=[],
    )
    game_over = SimpleNamespace(
        in_combat=False,
        screen_type="GAME_OVER",
        monsters=[],
    )
    reviving_darkling = SimpleNamespace(
        in_combat=True,
        screen_type=None,
        monsters=[SimpleNamespace(half_dead=True)],
    )

    wrapper._observe_rl_training_state(dead_transition)
    wrapper._observe_rl_training_state(reviving_darkling)
    wrapper._observe_rl_training_state(game_over)

    assert calls == [(reviving_darkling, False), (game_over, True)]


def test_abort_training_episode_discards_pending_transition():
    game = _game(1)
    agent = _agent()
    agent.pending_transition = _pending(game)

    agent.abort_training_episode()

    assert agent.pending_transition is None

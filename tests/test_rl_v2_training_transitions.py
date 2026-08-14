import math
from types import SimpleNamespace

import numpy as np

from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.ai.rl.v2.agent import PendingTransition, RLAgentV2
from spirecomm.ai.rl.v2.trainer import DQNTrainerV2
from spirecomm.communication.action import EndTurnAction


class _Action:
    def __init__(self, index):
        self.index = index


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


class _Trainer:
    def __init__(self, loss=None):
        self.loss = loss
        self.transitions = []
        self.train_calls = 0

    def store_transition(self, **transition):
        self.transitions.append(transition)

    def train_step(self):
        self.train_calls += 1
        return self.loss


def _encoded(value):
    return SimpleNamespace(
        continuous=np.array([value], dtype=np.float32),
        card_ids=np.array([value], dtype=np.int64),
        potion_ids=np.array([value], dtype=np.int64),
        relic_ids=np.array([value], dtype=np.int64),
    )


def _game(value, *, in_combat=True, reward=0.0):
    mask = np.zeros(_ActionEncoder.MAX_ACTIONS, dtype=bool)
    mask[1:] = True
    return SimpleNamespace(
        in_combat=in_combat,
        screen_type=None,
        player=SimpleNamespace(current_hp=50),
        hand=[],
        action_mask=mask,
        encoded=_encoded(value),
        reward=reward,
    )


def _agent(trainer=None):
    agent = RLAgentV2.__new__(RLAgentV2)
    agent.training_mode = True
    agent.trainer = trainer or _Trainer()
    agent.action_encoder = _ActionEncoder()
    agent.state_encoder = _StateEncoder()
    agent.reward_calculator = _RewardCalculator()
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
    )


def test_emitted_guard_replacement_overwrites_pending_action_label():
    game = _game(1)
    agent = _agent()
    agent.pending_transition = _pending(game, action_index=2)

    assert agent.commit_executed_action(game, _Action(6)) is True
    assert agent.pending_transition.action_index == 6


def test_unencodable_same_state_emission_discards_proposed_transition():
    game = _game(1)
    agent = _agent()
    agent.pending_transition = _pending(game, action_index=2)

    assert agent.commit_executed_action(game, object()) is False
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


def _real_trainer():
    return DQNTrainerV2(
        continuous_dim=2,
        action_dim=2,
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
        train_freq=1,
        target_update_freq=8,
        device="cpu",
    )


def _store_real_transition(trainer, *, continuous=None, done=False):
    if continuous is None:
        continuous = np.zeros(2, dtype=np.float32)
    return trainer.store_transition(
        continuous=continuous,
        card_ids=np.zeros(1, dtype=np.int64),
        potion_ids=np.zeros(1, dtype=np.int64),
        relic_ids=np.zeros(1, dtype=np.int64),
        action=0,
        reward=-200.0 if done else 1.0,
        next_continuous=None if done else np.ones(2, dtype=np.float32),
        next_card_ids=None if done else np.zeros(1, dtype=np.int64),
        next_potion_ids=None if done else np.zeros(1, dtype=np.int64),
        next_relic_ids=None if done else np.zeros(1, dtype=np.int64),
        done=done,
        action_mask=np.ones(2, dtype=bool),
        next_action_mask=np.zeros(2, dtype=bool) if done else np.ones(2, dtype=bool),
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

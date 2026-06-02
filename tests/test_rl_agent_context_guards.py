from types import SimpleNamespace

import numpy as np

from spirecomm.ai.rl.agent import RLAgent
from spirecomm.communication.action import ConfirmAction, PlayCardAction


class _ActionEncoder:
    USE_POTION_OFFSET = 5
    END_TURN_ACTION = 9

    def get_action_mask(self, _game):
        mask = [False] * 10
        mask[0] = True
        return mask

    def decode_action(self, _action_idx, _game):
        return PlayCardAction(card_index=0)


class _Trainer:
    epsilon = 0.0
    total_steps = 0

    def __init__(self):
        self.last_done = None

    def select_action(self, _state, _mask, training, epsilon_override=None):
        return 0

    def store_transition(self, _state, _action, _reward, _next_state, done, **_kwargs):
        self.last_done = done

    def train_step(self):
        return None


class _RewardCalculator:
    def __init__(self):
        self.action_context = None

    def calculate_step_reward(self, *args, **kwargs):
        self.action_context = kwargs.get("action_context")
        return 0.0


def _game(card):
    return SimpleNamespace(
        screen_type=None,
        in_combat=True,
        floor=1,
        turn=1,
        room_type="Monster",
        player=SimpleNamespace(current_hp=70),
        hand=[card],
    )


def test_rl_action_context_accepts_card_type_attribute_for_played_card():
    agent = RLAgent.__new__(RLAgent)
    agent.state_encoder = SimpleNamespace(encode=lambda _game: np.zeros(3, dtype=float))
    agent.action_encoder = _ActionEncoder()
    agent.reward_calculator = _RewardCalculator()
    agent.trainer = _Trainer()
    agent.training_mode = True
    agent.failed_actions = set()
    agent.consecutive_failures = {}
    agent.last_state_key = None
    agent.last_logged_turn = None
    agent.last_state = np.zeros(3, dtype=float)
    agent.pending_reward_action = 0
    agent.pending_reward_mask = np.array(agent.action_encoder.get_action_mask(None), dtype=bool)
    agent.boss_min_epsilon = 0.0
    card = SimpleNamespace(
        name="Defend",
        card_type="CardType.SKILL",
        is_playable=True,
        has_target=False,
    )
    agent.pending_reward_game = _game(card)
    current_game = _game(card)

    action = agent.get_next_action_in_game(current_game)

    assert isinstance(action, PlayCardAction)
    assert agent.reward_calculator.action_context["played_card_type"] == "SKILL"


def test_rl_agent_terminal_done_accepts_numeric_string_player_hp():
    agent = RLAgent.__new__(RLAgent)
    agent.state_encoder = SimpleNamespace(encode=lambda _game: np.zeros(3, dtype=float))
    agent.action_encoder = _ActionEncoder()
    agent.reward_calculator = _RewardCalculator()
    agent.trainer = _Trainer()
    agent.training_mode = True
    agent.failed_actions = set()
    agent.consecutive_failures = {}
    agent.last_state_key = None
    agent.last_logged_turn = None
    agent.last_state = np.zeros(3, dtype=float)
    agent.pending_reward_action = 0
    agent.pending_reward_mask = np.array(agent.action_encoder.get_action_mask(None), dtype=bool)
    agent.boss_min_epsilon = 0.0
    card = SimpleNamespace(
        name="Defend",
        card_type="CardType.SKILL",
        is_playable=True,
        has_target=False,
    )
    agent.pending_reward_game = _game(card)
    current_game = _game(card)
    current_game.player.current_hp = "0"

    action = agent.get_next_action_in_game(current_game)

    assert isinstance(action, PlayCardAction)
    assert agent.trainer.last_done is True


def test_rl_agent_terminal_check_accepts_decimal_string_player_hp():
    alive_game = SimpleNamespace(
        screen_type=None,
        player=SimpleNamespace(current_hp="12.0"),
    )
    dead_game = SimpleNamespace(
        screen_type=None,
        player=SimpleNamespace(current_hp="0.0"),
    )

    assert RLAgent._is_terminal(alive_game) is False
    assert RLAgent._is_terminal(dead_game) is True


def test_rl_agent_hand_select_confirm_bypass_accepts_string_num_cards():
    from spirecomm.spire.screen import ScreenType

    class ConfirmActionEncoder:
        USE_POTION_OFFSET = 5
        END_TURN_ACTION = 9
        CONFIRM_ACTION = 7

        def get_action_mask(self, _game):
            mask = [False] * 10
            mask[self.CONFIRM_ACTION] = True
            return mask

    agent = RLAgent.__new__(RLAgent)
    agent.state_encoder = SimpleNamespace(encode=lambda _game: np.zeros(3, dtype=float))
    agent.action_encoder = ConfirmActionEncoder()
    agent.training_mode = False
    agent.failed_actions = set()
    agent.consecutive_failures = {}
    agent.last_state_key = None
    agent.last_logged_turn = None
    game = SimpleNamespace(
        screen_type=ScreenType.HAND_SELECT,
        in_combat=True,
        floor=1,
        turn=1,
        screen=SimpleNamespace(
            selected_cards=[SimpleNamespace(name="Strike"), SimpleNamespace(name="Defend")],
            num_cards="2",
            can_pick_zero=False,
        ),
    )

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, ConfirmAction)

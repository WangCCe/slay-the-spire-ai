from types import SimpleNamespace

import numpy as np

from spirecomm.ai.rl.v2 import action_space as space
from spirecomm.ai.rl.v2.action_encoder import ActionEncoderV2
from spirecomm.ai.rl.v2.agent import PendingTransition, RLAgentV2


def _pending_transition(game, action_index, action_mask=None):
    if action_mask is None:
        action_mask = np.zeros(space.ACTION_DIM, dtype=bool)
    return PendingTransition(
        continuous=np.array([], dtype=float),
        card_ids=np.array([], dtype=int),
        potion_ids=np.array([], dtype=int),
        relic_ids=np.array([], dtype=int),
        action_index=action_index,
        action_mask=action_mask,
        game=game,
    )


def test_rl_v2_action_context_accepts_card_type_attribute_for_played_card():
    agent = RLAgentV2.__new__(RLAgentV2)
    agent.action_encoder = ActionEncoderV2()
    card = SimpleNamespace(
        name="Defend",
        card_type="CardType.SKILL",
        is_playable=True,
        has_target=False,
    )
    game = SimpleNamespace(
        hand=[card],
        monsters=[],
        play_available=True,
        end_available=True,
    )
    action_mask = np.zeros(space.ACTION_DIM, dtype=bool)
    action_mask[space.encode_play_card(0, 0)] = True

    context = agent._build_action_context(
        _pending_transition(game, space.encode_play_card(0, 0), action_mask)
    )

    assert context["action_name"] == "PlayCardAction"
    assert context["had_play_options"] is True
    assert context["played_card_type"] == "SKILL"


def test_rl_v2_terminal_check_accepts_string_player_hp():
    alive_game = SimpleNamespace(
        screen_type=None,
        player=SimpleNamespace(current_hp="12"),
    )
    dead_game = SimpleNamespace(
        screen_type=None,
        player=SimpleNamespace(current_hp="0"),
    )

    assert RLAgentV2._is_terminal(alive_game) is False
    assert RLAgentV2._is_terminal(dead_game) is True


def test_rl_v2_terminal_check_accepts_decimal_string_player_hp():
    alive_game = SimpleNamespace(
        screen_type=None,
        player=SimpleNamespace(current_hp="12.0"),
    )
    dead_game = SimpleNamespace(
        screen_type=None,
        player=SimpleNamespace(current_hp="0.0"),
    )

    assert RLAgentV2._is_terminal(alive_game) is False
    assert RLAgentV2._is_terminal(dead_game) is True

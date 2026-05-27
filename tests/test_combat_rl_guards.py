from types import SimpleNamespace

from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.communication.action import (
    CancelAction,
    CardRewardAction,
    EndTurnAction,
    PlayCardAction,
    PotionAction,
)
from spirecomm.spire.card import CardType
from spirecomm.spire.screen import ScreenType


def _agent():
    agent = CombatRLAgent.__new__(CombatRLAgent)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=lambda game: EndTurnAction())
    return agent


def _monster(hp=40, damage=12, index=0, name="Cultist", monster_id="Cultist"):
    return SimpleNamespace(
        name=name,
        monster_id=monster_id,
        current_hp=hp,
        move_adjusted_damage=damage,
        move_hits=1,
        is_gone=False,
        half_dead=False,
        monster_index=index,
    )


def _game(**kwargs):
    defaults = dict(
        screen_type=None,
        in_combat=True,
        potion_available=True,
        play_available=True,
        end_available=True,
        potions=[],
        monsters=[_monster()],
        current_hp=30,
        max_hp=80,
        room_type="Monster",
        player=SimpleNamespace(energy=2),
        hand=[],
        floor=5,
        turn=2,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_potion_guard_uses_damage_potion_in_danger():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[potion], monsters=[_monster(hp=50, damage=20, index=0)])

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_skips_safe_combat():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[potion], monsters=[_monster(hp=20, damage=0, index=0)], current_hp=70)

    assert _agent()._maybe_use_potion_guard(game) is None


def test_energy_guard_replaces_wasteful_end_turn_with_play_card():
    card = SimpleNamespace(is_playable=True, cost=1, has_target=True)
    game = _game(hand=[card], monsters=[_monster(hp=30, damage=8, index=0)])
    agent = _agent()

    assert agent._should_override_wasteful_end_turn(EndTurnAction(), game)
    replacement = agent._get_non_end_turn_fallback(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_wasteful_end_turn_hands_rest_of_turn_to_fallback():
    card = SimpleNamespace(is_playable=True, cost=1, has_target=True)
    game = _game(hand=[card], monsters=[_monster(hp=30, damage=8, index=0)])
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return EndTurnAction()

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    first = agent.get_next_action_in_game(game)
    second = agent.get_next_action_in_game(game)

    assert isinstance(first, PlayCardAction)
    assert isinstance(second, PlayCardAction)
    assert calls == {"rl": 1, "fallback": 2}


def test_awakened_one_power_guard_replaces_rl_power_with_non_power_card():
    demon_form = SimpleNamespace(
        name="Demon Form",
        card_id="Demon Form",
        type=CardType.POWER,
        is_playable=True,
        cost=3,
        has_target=False,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        floor=50,
        turn=3,
        player=SimpleNamespace(energy=3),
        hand=[demon_form, strike],
        monsters=[
            _monster(
                hp=300,
                damage=18,
                index=0,
                name="Awakened One",
                monster_id="AwakenedOne",
            )
        ],
        room_type="MonsterRoomBoss",
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0


def test_card_reward_uses_fallback_even_when_in_combat_flag_is_stale():
    card = SimpleNamespace(name="Pommel Strike")
    fallback_action = CardRewardAction(card)
    agent = _agent()
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda game: fallback_action
    )
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda game: CancelAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = (1, str(ScreenType.CARD_REWARD), 1)
    agent._reward_screen_waited = True
    agent.reward_screen_wait = 0
    game = _game(
        screen_type=ScreenType.CARD_REWARD,
        in_combat=True,
        choice_available=True,
        choice_list=["Pommel Strike", "skip"],
        screen=SimpleNamespace(cards=[card], can_skip=True),
    )

    assert agent.get_next_action_in_game(game) is fallback_action


def test_in_combat_grid_screen_uses_fallback_not_rl():
    fallback_action = PlayCardAction(card_index=0)
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return CancelAction()

    def fallback_decide(_game):
        calls["fallback"] += 1
        return fallback_action

    agent = _agent()
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=fallback_decide,
        _track_game_state=lambda game: None,
    )
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0
    game = _game(
        screen_type=ScreenType.GRID,
        in_combat=True,
        choice_available=True,
        choice_list=["card 1", "card 2", "card 3"],
        screen=SimpleNamespace(cards=[], confirm_up=False),
    )

    assert agent.get_next_action_in_game(game) is fallback_action
    assert calls == {"rl": 0, "fallback": 1}


def test_main_combat_still_uses_rl_context():
    game = _game(screen_type=None, in_combat=True)

    assert _agent()._is_rl_context(game)

from types import SimpleNamespace

from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.communication.action import EndTurnAction, PlayCardAction, PotionAction


def _agent():
    agent = CombatRLAgent.__new__(CombatRLAgent)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=lambda game: EndTurnAction())
    return agent


def _monster(hp=40, damage=12, index=0):
    return SimpleNamespace(
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

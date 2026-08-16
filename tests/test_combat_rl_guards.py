import json
from types import SimpleNamespace

import pytest

from spirecomm.ai.agent import OptimizedAgent
from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.communication.action import (
    CancelAction,
    CardRewardAction,
    EndTurnAction,
    PlayCardAction,
    PotionAction,
    WaitAction,
)
from spirecomm.spire.card import CardType
from spirecomm.spire.character import Intent
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


def test_current_combat_action_allows_clash_with_only_attacks_remaining():
    clash = SimpleNamespace(
        name="Clash",
        card_id="Clash",
        type=CardType.ATTACK,
        cost=0,
        is_playable=True,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        cost=1,
        is_playable=True,
    )
    game = _game(hand=[clash, strike])

    assert _agent()._is_current_combat_action_playable(
        PlayCardAction(card_index=0, target_index=0),
        game,
    )


def test_current_combat_action_rejects_clash_with_skill_remaining():
    clash = SimpleNamespace(
        name="Clash",
        card_id="Clash",
        type=CardType.ATTACK,
        cost=0,
        is_playable=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        cost=1,
        is_playable=True,
    )
    game = _game(hand=[clash, defend])

    assert not _agent()._is_current_combat_action_playable(
        PlayCardAction(card_index=0, target_index=0),
        game,
    )


def test_potion_guard_accepts_missing_can_use_on_damage_potion():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[potion], monsters=[_monster(hp=50, damage=20, index=0)])

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_infers_missing_potion_available_from_usable_potion():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[potion], monsters=[_monster(hp=50, damage=20, index=0)])
    del game.potion_available

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_treats_act1_boss_monster_as_boss_with_generic_room_type():
    potion = SimpleNamespace(
        potion_id="FearPotion",
        name="Fear Potion",
        can_use=True,
        requires_target=True,
        effect_type="debuff_vulnerable",
    )
    game = _game(
        potions=[potion],
        monsters=[
            _monster(
                hp=140,
                damage=0,
                index=0,
                name="Slime Boss",
                monster_id="SlimeBoss",
            )
        ],
        current_hp=65,
        max_hp=80,
        room_type="MonsterRoom",
        floor=16,
        turn=1,
        act=1,
    )

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_uses_get_real_potions_when_raw_potions_are_missing():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[], monsters=[_monster(hp=50, damage=20, index=0)])
    del game.potions
    game.get_real_potions = lambda: [potion]

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_preserves_target_index_when_dead_monster_precedes_target():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    dead = _monster(hp=0, damage=0, index=0)
    live = _monster(hp=50, damage=20, index=1)
    del dead.monster_index
    del live.monster_index
    game = _game(potions=[potion], monsters=[dead, live])

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.target_index == 1


def test_potion_guard_skips_name_only_empty_potion_slot():
    empty_slot = SimpleNamespace(
        name="Potion Slot",
        can_use=True,
        requires_target=False,
    )
    game = _game(
        potions=[empty_slot],
        monsters=[_monster(hp=50, damage=25, index=0)],
    )

    assert _agent()._maybe_use_potion_guard(game) is None


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


def test_potion_guard_accepts_decimal_string_player_hp():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=50, damage=20, index=0)],
        current_hp="30.0",
        max_hp="80.0",
    )

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_saves_healing_potion_when_hp_is_high():
    potion = SimpleNamespace(
        potion_id="BloodPotion",
        name="Blood Potion",
        can_use=True,
        requires_target=False,
        effect_type="heal_percent",
    )
    game = _game(
        potions=[potion],
        monsters=[
            _monster(hp=25, damage=6, index=0),
            _monster(hp=20, damage=5, index=1),
            _monster(hp=18, damage=5, index=2),
        ],
        current_hp=73,
        max_hp=80,
        room_type="MonsterRoom",
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_potion_guard_uses_healing_potion_to_survive_lethal_turn():
    potion = SimpleNamespace(
        potion_id="BloodPotion",
        name="Blood Potion",
        can_use=True,
        requires_target=False,
        effect_type="heal_percent",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=180, damage=24, index=0)],
        current_hp=9,
        max_hp=80,
        room_type="MonsterRoomBoss",
    )

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_potion_guard_saves_energy_potion_on_safe_boss_turn():
    potion = SimpleNamespace(
        potion_id="EnergyPotion",
        name="Energy Potion",
        can_use=True,
        requires_target=False,
        effect_type="energy",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=250, damage=0, index=0, name="The Guardian")],
        current_hp=68,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        turn=1,
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_potion_guard_uses_energy_potion_under_current_turn_pressure():
    potion = SimpleNamespace(
        potion_id="EnergyPotion",
        name="Energy Potion",
        can_use=True,
        requires_target=False,
        effect_type="energy",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=120, damage=32, index=0, name="The Guardian")],
        current_hp=8,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        turn=19,
    )

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_potion_guard_saves_utility_choice_potion_on_safe_boss_turn():
    potion = SimpleNamespace(
        potion_id="AttackPotion",
        name="Attack Potion",
        can_use=True,
        requires_target=False,
        effect_type="card_choice_attack",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=250, damage=0, index=0, name="The Guardian")],
        current_hp=75,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        turn=1,
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_potion_guard_uses_utility_choice_potion_under_current_turn_pressure():
    potion = SimpleNamespace(
        potion_id="ColorlessPotion",
        name="Colorless Potion",
        can_use=True,
        requires_target=False,
        effect_type="card_choice_colorless",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=120, damage=24, index=0, name="Cultist")],
        current_hp=34,
        max_hp=80,
        room_type="MonsterRoom",
        floor=25,
        turn=3,
    )

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_potion_guard_does_not_auto_use_elixir_hand_select_potion():
    potion = SimpleNamespace(
        potion_id="ElixirPotion",
        name="Elixir",
        can_use=True,
        requires_target=False,
        effect_type="exhaust_hand_select",
    )
    game = _game(
        potions=[potion],
        monsters=[
            _monster(hp=52, damage=10, index=0, name="Blue Slaver"),
            _monster(hp=48, damage=10, index=1, name="Red Slaver"),
        ],
        current_hp=46,
        max_hp=85,
        room_type="EventRoom",
        floor=27,
        turn=1,
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_potion_guard_saves_boss_setup_potions_in_healthy_act1_hallway():
    fear = SimpleNamespace(
        potion_id="FearPotion",
        name="Fear Potion",
        can_use=True,
        requires_target=True,
        effect_type="debuff_vulnerable",
    )
    strength = SimpleNamespace(
        potion_id="StrengthPotion",
        name="Strength Potion",
        can_use=True,
        requires_target=False,
        effect_type="buff_strength",
    )
    game = _game(
        potions=[fear, strength],
        monsters=[
            _monster(hp=24, damage=7, index=0, name="Gremlin Wizard"),
            _monster(hp=22, damage=7, index=1, name="Mad Gremlin"),
            _monster(hp=20, damage=7, index=2, name="Fat Gremlin"),
        ],
        current_hp=73,
        max_hp=80,
        room_type="MonsterRoom",
        floor=10,
        act=1,
        turn=1,
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_rl_potion_action_is_blocked_in_low_risk_act1_hallway_before_boss():
    potion = SimpleNamespace(
        potion_id="ExplosivePotion",
        name="Explosive Potion",
        can_use=True,
        requires_target=False,
        effect_type="damage",
    )
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=34, damage=5, index=0, name="Louse")],
        current_hp=70,
        max_hp=80,
        room_type="MonsterRoom",
        floor=10,
        act=1,
        player=SimpleNamespace(energy=3),
        hand=[strike],
    )
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PotionAction(True, potion=potion)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert calls == {"rl": 1, "fallback": 1}


def test_rl_boss_setup_potion_is_blocked_in_healthy_act1_hallway_before_boss():
    potion = SimpleNamespace(
        potion_id="StrengthPotion",
        name="Strength Potion",
        can_use=True,
        requires_target=False,
        effect_type="buff_strength",
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
        potions=[potion],
        monsters=[
            _monster(hp=24, damage=5, index=0, name="Gremlin Wizard"),
            _monster(hp=22, damage=4, index=1, name="Mad Gremlin"),
            _monster(hp=20, damage=4, index=2, name="Fat Gremlin"),
        ],
        current_hp=72,
        max_hp=80,
        room_type="MonsterRoom",
        floor=10,
        act=1,
        player=SimpleNamespace(energy=1),
        hand=[strike],
    )
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PotionAction(True, potion=potion)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert calls == {"rl": 1, "fallback": 1}


def test_rl_elixir_action_is_replaced_even_in_boss_combat():
    potion = SimpleNamespace(
        potion_id="ElixirPotion",
        name="Elixir",
        can_use=True,
        requires_target=False,
        effect_type="exhaust_hand_select",
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
        potions=[potion],
        monsters=[
            _monster(
                hp=98,
                damage=0,
                index=0,
                name="Slime Boss",
                monster_id="SlimeBoss",
            )
        ],
        current_hp=69,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=2,
        player=SimpleNamespace(energy=1),
        hand=[strike],
    )
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PotionAction(True, potion=potion)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert calls == {"rl": 1, "fallback": 1}


def test_rl_elixir_index_action_is_replaced_even_in_boss_combat():
    potion = SimpleNamespace(
        potion_id="ElixirPotion",
        name="Elixir",
        can_use=True,
        requires_target=False,
        effect_type="exhaust_hand_select",
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
        potions=[potion],
        monsters=[
            _monster(
                hp=230,
                damage=7,
                index=0,
                name="Hexaghost",
                monster_id="Hexaghost",
            )
        ],
        current_hp=74,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=2,
        player=SimpleNamespace(energy=3),
        hand=[strike],
    )
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PotionAction(True, potion_index=0)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert calls == {"rl": 1, "fallback": 1}


def test_rl_elixir_replacement_trace_records_final_action_only(monkeypatch, tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("STS_DECISION_TRACE_FILE", str(trace_path))
    potion = SimpleNamespace(
        potion_id="ElixirPotion",
        name="Elixir",
        can_use=True,
        requires_target=False,
        effect_type="exhaust_hand_select",
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
        potions=[potion],
        monsters=[
            _monster(
                hp=230,
                damage=7,
                index=0,
                name="Hexaghost",
                monster_id="Hexaghost",
            )
        ],
        current_hp=74,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=2,
        player=SimpleNamespace(energy=3),
        hand=[strike],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PotionAction(True, potion=potion)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    records = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["action"]["type"] for record in records] == ["PlayCardAction"]
    assert records[0]["action"]["card_index"] == 0


def test_rl_incoming_damage_clamps_negative_live_move_damage_to_zero():
    monster = _monster(hp=25, damage=-1)
    monster.move_hits = 3
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 0


def test_rl_alive_monsters_accepts_numeric_string_hp():
    dead = _monster(hp="0", index=0)
    live = _monster(hp="12", index=1)
    game = _game(monsters=[dead, live])

    assert CombatRLAgent._alive_monsters(game) == [live]


def test_rl_best_monster_index_accepts_numeric_string_hp():
    dead = _monster(hp="0", index=0)
    low = _monster(hp="3", index=1)
    high = _monster(hp="12", index=2)
    game = _game(monsters=[dead, low, high])

    assert CombatRLAgent._best_monster_index(game) == 2


def test_rl_potion_target_index_orders_numeric_string_hp_numerically():
    potion = SimpleNamespace(effect_type="damage")
    low = _monster(hp="9", index=0)
    high = _monster(hp="12", index=1)
    game = _game(monsters=[low, high])

    assert CombatRLAgent._potion_target_index(potion, [low, high], game) == 1


def test_rl_incoming_damage_clamps_negative_live_move_hits_to_one():
    monster = _monster(hp=25, damage=7)
    monster.move_hits = -2
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 7


def test_rl_incoming_damage_accepts_decimal_string_damage_and_hits():
    monster = _monster(hp=25, damage="7.0")
    monster.move_hits = "2.0"
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 14


def test_rl_incoming_damage_ignores_nonfinite_live_move_damage():
    monster = _monster(hp=25, damage=float("inf"))
    monster.move_hits = 2
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 0


def test_rl_incoming_damage_defaults_nonfinite_live_move_hits_to_one():
    monster = _monster(hp=25, damage=7)
    monster.move_hits = float("inf")
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 7


def test_rl_incoming_damage_ignores_non_attack_intents():
    monster = _monster(hp=25, damage=7)
    monster.intent = "Intent.DEBUFF"
    monster.move_hits = 2
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 0


def test_rl_incoming_damage_estimates_unknown_intent_by_act():
    monster = _monster(hp=25, damage=None)
    monster.intent = Intent.UNKNOWN
    game = _game(monsters=[monster], act=2)

    assert CombatRLAgent._incoming_damage(game) == 10


def test_rl_incoming_damage_counts_known_unknown_damage_move():
    monster = _monster(
        hp=30,
        damage=0,
        name="Exploder",
        monster_id="Exploder",
    )
    monster.intent = Intent.UNKNOWN
    monster.move_id = 1
    game = _game(monsters=[monster], act=3)

    assert CombatRLAgent._incoming_damage(game) == 30


def test_rl_incoming_damage_counts_exploder_explosive_power_without_move_id():
    monster = _monster(
        hp=30,
        damage=0,
        name="Exploder",
        monster_id="Exploder",
    )
    monster.intent = Intent.UNKNOWN
    monster.move_id = None
    monster.powers = [SimpleNamespace(power_name="Explosive", amount=1)]
    game = _game(monsters=[monster], act=3)

    assert CombatRLAgent._incoming_damage(game) == 30


def test_rl_end_turn_damage_after_block_counts_exploder_explosive_events():
    first = _monster(hp=25, damage=0, name="Exploder", monster_id="Exploder")
    first.intent = Intent.UNKNOWN
    first.move_id = None
    first.powers = [SimpleNamespace(power_name="Explosive", amount=1)]
    second = _monster(hp=19, damage=0, index=1, name="Exploder", monster_id="Exploder")
    second.intent = Intent.UNKNOWN
    second.move_id = None
    second.powers = [SimpleNamespace(power_name="Explosive", amount=1)]
    game = _game(
        monsters=[first, second],
        current_hp=25,
        player=SimpleNamespace(energy=1, block=8),
        act=3,
    )

    assert CombatRLAgent._end_turn_damage_after_block(0, 0, 8, game) == 52


def test_rl_incoming_damage_ignores_known_no_damage_unknown_moves():
    preparing = _monster(
        hp=99,
        damage=0,
        name="Slime Boss",
        monster_id="Slime_Boss",
    )
    preparing.max_hp = 140
    preparing.intent = Intent.UNKNOWN
    preparing.move_id = 1

    splitting = _monster(
        hp=15,
        damage=0,
        name="Acid Slime (L)",
        monster_id="Acid_Slime_L",
    )
    splitting.max_hp = 65
    splitting.intent = Intent.UNKNOWN
    splitting.move_id = 3

    game = _game(monsters=[preparing, splitting], act=2)

    assert CombatRLAgent._incoming_damage(game) == 0


def test_energy_guard_replaces_wasteful_end_turn_with_play_card():
    card = SimpleNamespace(is_playable=True, cost=1, has_target=True)
    game = _game(hand=[card], monsters=[_monster(hp=30, damage=8, index=0)])
    agent = _agent()

    assert agent._should_override_wasteful_end_turn(EndTurnAction(), game)
    replacement = agent._get_non_end_turn_fallback(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_energy_guard_counts_burn_damage_when_selecting_survival_fallback():
    thunderclap = SimpleNamespace(
        name="Thunderclap",
        card_id="Thunderclap",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    burn = SimpleNamespace(
        name="Burn",
        card_id="Burn",
        type=CardType.STATUS,
        is_playable=False,
        cost=-2,
        has_target=False,
    )
    game = _game(
        hand=[thunderclap, defend, bash, burn],
        monsters=[_monster(hp=184, damage=8, index=0, name="Hexaghost", monster_id="Hexaghost")],
        current_hp=9,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=8,
        player=SimpleNamespace(energy=3, block=0),
    )
    agent = _agent()
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0)
    )

    replacement = agent._get_non_end_turn_fallback(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 1
    assert replacement.target_index is None


def test_survival_guard_counts_havoc_visible_top_skill_block():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_defend = SimpleNamespace(
        name="Defend+",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=8,
        upgrades=1,
    )
    jaw_worm = _monster(hp=42, damage=7, index=0, name="Jaw Worm", monster_id="JawWorm")
    jaw_worm.intent = Intent.ATTACK
    game = _game(
        hand=[strike, havoc],
        draw_pile=[top_defend],
        monsters=[jaw_worm],
        current_hp=7,
        player=SimpleNamespace(energy=1, block=0, powers=[]),
        floor=4,
        turn=2,
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (4, 2)


def test_survival_guard_counts_ornamental_fan_attack_block():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    jaw_worm = _monster(hp=42, damage=4, index=0, name="Jaw Worm", monster_id="JawWorm")
    jaw_worm.intent = Intent.ATTACK
    game = _game(
        hand=[strike],
        monsters=[jaw_worm],
        relics=[
            SimpleNamespace(
                relic_id="Ornamental Fan",
                name="Ornamental Fan",
                counter=2,
            )
        ],
        current_hp=4,
        player=SimpleNamespace(energy=1, block=0, powers=[]),
        floor=4,
        turn=2,
    )

    replacement = _agent()._get_survival_block_replacement(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_survival_guard_treats_tungsten_rod_reduced_incoming_as_nonlethal():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    cultist = _monster(hp=42, damage=3, index=0)
    cultist.intent = Intent.ATTACK
    game = _game(
        hand=[defend],
        monsters=[cultist],
        relics=[SimpleNamespace(name="Tungsten Rod", relic_id="TungstenRod")],
        current_hp=3,
        player=SimpleNamespace(energy=1, block=0, powers=[]),
        floor=4,
        turn=2,
    )

    assert _agent()._get_survival_block_replacement(game) is None


def test_survival_guard_treats_buffered_incoming_as_nonlethal():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    centurion = _monster(hp=42, damage=12, index=0, name="Centurion", monster_id="Centurion")
    centurion.intent = Intent.ATTACK
    game = _game(
        hand=[defend],
        monsters=[centurion],
        current_hp=8,
        player=SimpleNamespace(
            energy=1,
            block=0,
            powers=[SimpleNamespace(power_name="Buffer", amount=1)],
        ),
        floor=29,
        turn=2,
    )

    assert _agent()._get_survival_block_replacement(game) is None


def test_card_hp_loss_is_capped_by_player_intangible():
    hemokinesis_plus = SimpleNamespace(
        name="Hemokinesis+",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        upgrades=1,
    )
    game = _game(
        hand=[hemokinesis_plus],
        current_hp=22,
        player=SimpleNamespace(
            energy=1,
            block=0,
            powers=[
                SimpleNamespace(
                    power_id="IntangiblePlayer",
                    power_name="Intangible",
                    amount=1,
                )
            ],
        ),
    )

    assert CombatRLAgent._card_player_hp_loss(hemokinesis_plus, game) == 1


def test_card_hp_loss_counts_pain_in_hand():
    anger = SimpleNamespace(
        name="Anger+",
        card_id="Anger",
        type=CardType.ATTACK,
        is_playable=True,
        cost=0,
        has_target=True,
        upgrades=1,
    )
    pain = SimpleNamespace(
        name="Pain",
        card_id="Pain",
        type=CardType.CURSE,
        is_playable=False,
        cost=-2,
        has_target=False,
    )
    game = _game(
        hand=[anger, pain],
        current_hp=10,
        player=SimpleNamespace(energy=0, block=0),
    )

    assert CombatRLAgent._card_player_hp_loss(anger, game) == 1


def test_rl_pain_self_lethal_card_is_suppressed():
    pain = SimpleNamespace(
        name="Pain",
        card_id="Pain",
        type=CardType.CURSE,
        is_playable=False,
        cost=-2,
        has_target=False,
    )
    anger = SimpleNamespace(
        name="Anger+",
        card_id="Anger",
        type=CardType.ATTACK,
        is_playable=True,
        cost=0,
        has_target=True,
        upgrades=1,
        damage=8,
    )
    monster = _monster(
        hp=342,
        damage=7,
        index=0,
        name="Time Eater",
        monster_id="TimeEater",
    )
    monster.intent = Intent.ATTACK
    monster.move_hits = 3
    game = _game(
        floor=50,
        turn=8,
        room_type="MonsterRoomBoss",
        current_hp=1,
        max_hp=70,
        player=SimpleNamespace(energy=0, block=16),
        hand=[pain, anger],
        monsters=[monster],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=1, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert action.expected_floor == 50
    assert action.expected_turn == 8


def test_survival_guard_counts_ornamental_fan_from_havoc_top_attack():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=3,
    )
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    jaw_worm = _monster(hp=42, damage=4, index=0, name="Jaw Worm", monster_id="JawWorm")
    jaw_worm.intent = Intent.ATTACK
    game = _game(
        hand=[defend, havoc],
        draw_pile=[top_strike],
        monsters=[jaw_worm],
        relics=[
            SimpleNamespace(
                relic_id="Ornamental Fan",
                name="Ornamental Fan",
                counter=2,
            )
        ],
        current_hp=4,
        player=SimpleNamespace(energy=1, block=0, powers=[]),
        floor=4,
        turn=2,
    )

    replacement = _agent()._get_survival_block_replacement(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 1
    assert replacement.target_index is None


def test_survival_guard_ignores_havoc_top_attack_fan_block_when_entangled():
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        hand=[havoc],
        draw_pile=[top_strike],
        relics=[
            SimpleNamespace(
                relic_id="Ornamental Fan",
                name="Ornamental Fan",
                counter=2,
            )
        ],
        player=SimpleNamespace(
            energy=1,
            block=0,
            powers=[SimpleNamespace(power_name="Entangled", amount=1)],
        ),
    )

    assert CombatRLAgent._survival_block_value_for_game(havoc, game) == 0


def test_survival_guard_ignores_havoc_top_clash_fan_block_when_unplayable():
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_clash = SimpleNamespace(
        name="Clash",
        card_id="Clash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=0,
        has_target=True,
        damage=14,
    )
    game = _game(
        hand=[havoc, defend],
        draw_pile=[top_clash],
        relics=[
            SimpleNamespace(
                relic_id="Ornamental Fan",
                name="Ornamental Fan",
                counter=2,
            )
        ],
        player=SimpleNamespace(energy=1, block=0, powers=[]),
    )

    assert CombatRLAgent._survival_block_value_for_game(havoc, game) == 0


def test_survival_guard_counts_orichalcum_before_replacing_attack():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    jaw_worm = _monster(hp=42, damage=6, index=0, name="Jaw Worm", monster_id="JawWorm")
    jaw_worm.intent = Intent.ATTACK
    game = _game(
        hand=[strike, defend],
        monsters=[jaw_worm],
        relics=[SimpleNamespace(relic_id="Orichalcum", name="Orichalcum")],
        current_hp=6,
        player=SimpleNamespace(energy=1, block=0, powers=[]),
        floor=4,
        turn=2,
    )

    replacement = _agent()._get_survival_action_replacement(
        PlayCardAction(card_index=0, target_index=0),
        game,
    )

    assert replacement is None


def test_survival_guard_counts_havoc_feel_no_pain_block():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_berserk = SimpleNamespace(
        name="Berserk",
        card_id="Berserk",
        type=CardType.POWER,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    snake_plant = _monster(
        hp=79,
        damage=5,
        index=0,
        name="Snake Plant",
        monster_id="SnakePlant",
    )
    snake_plant.intent = Intent.ATTACK
    game = _game(
        hand=[strike, havoc],
        draw_pile=[top_berserk],
        monsters=[snake_plant],
        current_hp=5,
        player=SimpleNamespace(
            energy=1,
            block=0,
            powers=[SimpleNamespace(power_name="Feel No Pain", amount=3)],
        ),
        floor=27,
        turn=1,
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (27, 1)


def test_survival_guard_counts_self_exhaust_feel_no_pain_block():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    shockwave = SimpleNamespace(
        name="Shockwave",
        card_id="Shockwave",
        type=CardType.SKILL,
        is_playable=True,
        cost=2,
        has_target=False,
        exhausts=True,
    )
    snake_plant = _monster(
        hp=79,
        damage=5,
        index=0,
        name="Snake Plant",
        monster_id="SnakePlant",
    )
    snake_plant.intent = Intent.ATTACK
    game = _game(
        hand=[strike, shockwave],
        monsters=[snake_plant],
        current_hp=3,
        player=SimpleNamespace(
            energy=2,
            block=0,
            powers=[SimpleNamespace(power_name="Feel No Pain", amount=3)],
        ),
        floor=27,
        turn=2,
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (27, 2)


def test_survival_guard_applies_current_block_to_burn_plus_damage():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    burn_plus = SimpleNamespace(
        name="Burn+",
        card_id="Burn+",
        type=CardType.STATUS,
        is_playable=False,
        cost=-2,
        has_target=False,
    )
    hexaghost = _monster(hp=55, damage=8, index=0, name="Hexaghost", monster_id="Hexaghost")
    hexaghost.intent = Intent.ATTACK_DEBUFF
    game = _game(
        hand=[strike, defend, burn_plus, burn_plus, burn_plus, burn_plus],
        monsters=[hexaghost],
        current_hp=12,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=12,
        player=SimpleNamespace(energy=1, block=16),
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert agent._fallback_turn_key is None


def test_survival_guard_lets_current_block_absorb_burn_damage():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    burn = SimpleNamespace(
        name="Burn",
        card_id="Burn",
        type=CardType.STATUS,
        is_playable=False,
        cost=-2,
        has_target=False,
    )
    cultist = _monster(hp=48, damage=0, index=0, name="Cultist", monster_id="Cultist")
    cultist.intent = Intent.BUFF
    game = _game(
        hand=[strike, defend, burn],
        monsters=[cultist],
        current_hp=2,
        max_hp=80,
        room_type="MonsterRoom",
        floor=2,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=1, block=2),
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert agent._fallback_turn_key is None


def test_survival_guard_lets_current_block_absorb_decay_damage():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    decay = SimpleNamespace(
        name="Decay",
        card_id="Decay",
        type=CardType.CURSE,
        is_playable=False,
        cost=-2,
        has_target=False,
    )
    slime = _monster(hp=62, damage=0, index=0, name="Acid Slime (L)", monster_id="AcidSlime_L")
    slime.intent = Intent.DEBUFF
    game = _game(
        hand=[strike, defend, decay],
        monsters=[slime],
        current_hp=2,
        max_hp=80,
        room_type="MonsterRoom",
        floor=10,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=1, block=2),
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert agent._fallback_turn_key is None


def test_survival_guard_counts_regret_hand_size_hp_loss_through_block():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    regret = SimpleNamespace(
        name="Regret",
        card_id="Regret",
        type=CardType.CURSE,
        is_playable=False,
        cost=-2,
        has_target=False,
    )
    slime = _monster(hp=62, damage=8, index=0, name="Acid Slime (L)", monster_id="AcidSlime_L")
    slime.intent = Intent.ATTACK
    game = _game(
        hand=[strike, defend, regret],
        monsters=[slime],
        current_hp=5,
        max_hp=80,
        room_type="MonsterRoom",
        floor=10,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=1, block=6),
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (10, 1)


def test_energy_guard_fallback_does_not_spend_potion_on_safe_boss_window():
    potion = SimpleNamespace(
        potion_id="DistilledChaos",
        name="Distilled Chaos",
        can_use=True,
        requires_target=False,
        effect_type="play_top_cards",
    )
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        hand=[strike],
        potions=[potion],
        monsters=[_monster(hp=140, damage=0, index=0, name="Slime Boss", monster_id="SlimeBoss")],
        current_hp=80,
        max_hp=80,
        room_type="MonsterRoom",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=3),
    )
    agent = _agent()
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PotionAction(True, potion=potion)
    )

    assert agent._should_override_wasteful_end_turn(EndTurnAction(), game)
    replacement = agent._get_non_end_turn_fallback(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_energy_guard_takeover_does_not_spend_potion_on_safe_boss_window():
    potion = SimpleNamespace(
        potion_id="AttackPotion",
        name="Attack Potion",
        can_use=True,
        requires_target=False,
        effect_type="card_choice_attack",
    )
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        hand=[strike],
        potions=[potion],
        monsters=[
            _monster(
                hp=240,
                damage=0,
                index=0,
                name="The Guardian",
                monster_id="TheGuardian",
            )
        ],
        current_hp=80,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=2),
    )

    agent = _agent()
    agent._fallback_turn_key = (16, 1)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PotionAction(True, potion=potion)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0


def test_act1_boss_no_pressure_guard_replaces_block_with_attack():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
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
        hand=[defend, strike],
        monsters=[_monster(hp=120, damage=0, index=0, name="Slime Boss", monster_id="SlimeBoss")],
        current_hp=70,
        max_hp=80,
        room_type="MonsterRoom",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=2, block=0),
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0
    assert agent._fallback_turn_key == (16, 1)


def test_act1_boss_no_pressure_guard_keeps_block_for_status_damage():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
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
    burn = SimpleNamespace(
        name="Burn",
        card_id="Burn",
        type=CardType.STATUS,
        is_playable=False,
        cost=-2,
        has_target=False,
    )
    game = _game(
        hand=[defend, strike, burn],
        monsters=[_monster(hp=120, damage=0, index=0, name="Slime Boss", monster_id="SlimeBoss")],
        current_hp=12,
        max_hp=80,
        room_type="MonsterRoom",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=2, block=0),
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index is None
    assert agent._fallback_turn_key is None


def test_act1_boss_no_pressure_guard_applies_during_takeover():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
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
        hand=[defend, strike],
        monsters=[_monster(hp=120, damage=0, index=0, name="Slime Boss", monster_id="SlimeBoss")],
        current_hp=70,
        max_hp=80,
        room_type="MonsterRoom",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=2, block=0),
    )
    agent = _agent()
    agent._fallback_turn_key = (16, 1)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0)
    )
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
    assert agent._fallback_turn_key == (16, 1)


def test_energy_guard_takeover_preserves_hexaghost_setup_priority_when_suppressing_potion():
    potion = SimpleNamespace(
        potion_id="DuplicationPotion",
        name="Duplication Potion",
        can_use=True,
        requires_target=False,
        effect_type="duplicate_next_card",
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    shockwave = SimpleNamespace(
        name="Shockwave",
        card_id="Shockwave",
        type=CardType.SKILL,
        is_playable=True,
        cost=2,
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
        hand=[bash, shockwave, strike],
        potions=[potion],
        monsters=[
            _monster(
                hp=250,
                damage=0,
                index=0,
                name="Hexaghost",
                monster_id="Hexaghost",
            )
        ],
        current_hp=80,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=3),
    )
    game.monsters[0].intent = "Intent.BUFF"

    agent = _agent()
    agent._fallback_turn_key = (16, 1)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PotionAction(True, potion=potion)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None


def test_energy_guard_takeover_replaces_fallback_end_turn_with_playable_card():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    game = _game(
        hand=[strike, defend],
        monsters=[
            _monster(
                hp=158,
                damage=0,
                index=0,
                name="The Guardian",
                monster_id="TheGuardian",
            )
        ],
        current_hp=5,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=5,
        player=SimpleNamespace(energy=3, block=0),
    )
    game.monsters[0].intent = Intent.DEFEND

    agent = _agent()
    agent._fallback_turn_key = (16, 5)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0


def test_energy_guard_takeover_end_turn_queries_fallback_once():
    target = _monster(
        hp=20,
        damage=0,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    target.intent = Intent.DEBUFF
    game = _game(
        hand=[],
        monsters=[target],
        current_hp=30,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=0, block=0),
    )
    fallback_calls = []
    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: (
            fallback_calls.append(_game) or EndTurnAction()
        )
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert fallback_calls == [game]


@pytest.mark.parametrize("ordinary_branch", ["wait", "end_turn", "potion"])
def test_ordinary_non_plan_takeover_replacement_does_not_call_plan_rejector(
    monkeypatch,
    ordinary_branch,
):
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=6,
    )
    target = _monster(
        hp=20,
        damage=0,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    target.intent = Intent.DEBUFF
    game = _game(
        hand=[strike],
        monsters=[target],
        current_hp=30,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=1, block=0),
    )
    if ordinary_branch == "wait":
        fallback_action = PlayCardAction(card_index=0, target_index=0)
    elif ordinary_branch == "end_turn":
        fallback_action = EndTurnAction()
    else:
        fallback_action = PotionAction(True)

    rejected_actions = []
    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: fallback_action,
        is_active_plan_action=lambda _action: False,
        active_plan_kind_for_action=lambda _action: None,
        reject_active_plan_action=lambda action: (
            rejected_actions.append(action) or True
        ),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)
    if ordinary_branch == "wait":
        monkeypatch.setattr(
            agent,
            "_maybe_wait_for_empty_hand_refresh",
            lambda _action, _game: WaitAction(timeout=1),
        )
    elif ordinary_branch == "end_turn":
        monkeypatch.setattr(
            agent,
            "_get_non_end_turn_fallback",
            lambda _game, fallback_action=None: PlayCardAction(
                card_index=0,
                target_index=0,
            ),
        )
    else:
        monkeypatch.setattr(
            agent,
            "_get_energy_guard_takeover_potion_replacement",
            lambda _game: EndTurnAction(),
        )

    agent.get_next_action_in_game(game)

    assert rejected_actions == []
    assert getattr(agent, "_lethal_plan_quarantine_epoch", None) is None


def test_energy_guard_takeover_suppresses_unpayable_cached_card():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    game = _game(
        hand=[defend],
        monsters=[
            _monster(
                hp=240,
                damage=0,
                index=0,
                name="The Guardian",
                monster_id="TheGuardian",
            )
        ],
        current_hp=64,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=0, block=33),
    )
    game.monsters[0].intent = Intent.DEFEND

    agent = _agent()
    agent._fallback_turn_key = (16, 1)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert agent._fallback_turn_key is None


def test_energy_guard_takeover_ends_zero_energy_turn_when_block_already_safe():
    shrug = SimpleNamespace(
        name="Shrug It Off",
        card_id="Shrug It Off",
        type=CardType.SKILL,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    game = _game(
        hand=[shrug],
        monsters=[
            _monster(
                hp=206,
                damage=20,
                index=0,
                name="The Guardian",
                monster_id="TheGuardian",
            )
        ],
        current_hp=35,
        max_hp=90,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=6,
        player=SimpleNamespace(energy=0, block=999),
    )
    game.monsters[0].intent = Intent.ATTACK

    agent = _agent()
    agent._fallback_turn_key = (16, 6)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert agent._fallback_turn_key is None


def test_energy_guard_takeover_repairs_targetless_cached_attack():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        hand=[strike],
        monsters=[
            _monster(
                hp=20,
                damage=0,
                index=0,
                name="The Guardian",
                monster_id="TheGuardian",
            )
        ],
        current_hp=64,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=3,
        player=SimpleNamespace(energy=1, block=0),
    )
    game.monsters[0].intent = Intent.DEFEND

    agent = _agent()
    agent._fallback_turn_key = (16, 3)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert agent._fallback_turn_key is None


def test_energy_guard_takeover_repairs_card_object_attack_before_first_playable_defend():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
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
    stale_strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    acid_slime = _monster(
        hp=7,
        damage=5,
        index=0,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    acid_slime.intent = Intent.ATTACK_DEBUFF
    game = _game(
        hand=[defend, strike, strike, strike],
        monsters=[acid_slime],
        current_hp=73,
        max_hp=80,
        room_type="MonsterRoom",
        floor=4,
        act=1,
        turn=3,
        player=SimpleNamespace(energy=2, block=0),
    )

    agent = _agent()
    agent._fallback_turn_key = (4, 3)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card=stale_strike)
    )
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
    assert agent._fallback_turn_key is None


def test_energy_guard_initial_fallback_repairs_card_object_attack_before_first_playable_defend():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
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
    stale_strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    acid_slime = _monster(
        hp=7,
        damage=5,
        index=0,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    acid_slime.intent = Intent.ATTACK_DEBUFF
    game = _game(
        hand=[defend, strike, strike, strike],
        monsters=[acid_slime],
        current_hp=73,
        max_hp=80,
        room_type="MonsterRoom",
        floor=4,
        act=1,
        turn=3,
        player=SimpleNamespace(energy=2, block=0),
    )

    agent = _agent()
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card=stale_strike)
    )

    action = agent._get_non_end_turn_fallback(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0


def test_energy_guard_takeover_repairs_stale_attack_with_sharp_hide_block():
    anger = SimpleNamespace(
        name="Anger",
        card_id="Anger",
        type=CardType.ATTACK,
        is_playable=True,
        cost=0,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=8,
        upgrades=1,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    guardian = _monster(
        hp=95,
        damage=16,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK_BUFF
    guardian.move_id = 4
    game = _game(
        hand=[anger, defend, strike],
        monsters=[guardian],
        current_hp=16,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=9,
        player=SimpleNamespace(energy=1, block=13),
    )

    agent = _agent()
    agent._fallback_turn_key = (16, 9)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=-1)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key is None


def test_energy_guard_takeover_repairs_missing_target_without_changing_card():
    wound = SimpleNamespace(
        name="Wound",
        card_id="Wound",
        type=CardType.STATUS,
        is_playable=False,
        cost=-2,
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
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    guardian = _monster(
        hp=147,
        damage=20,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK
    game = _game(
        hand=[wound, strike, bash],
        monsters=[guardian],
        current_hp=9,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=10,
        player=SimpleNamespace(energy=2, block=0),
    )

    agent = _agent()
    agent._fallback_turn_key = (16, 10)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=2)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 2
    assert action.target_index == 0
    assert agent._fallback_turn_key is None


def test_energy_guard_takeover_skips_bloodletting_when_hp_loss_would_kill():
    burning_pact = SimpleNamespace(
        name="Burning Pact",
        card_id="Burning Pact",
        type=CardType.SKILL,
        is_playable=False,
        cost=1,
        has_target=False,
    )
    bloodletting = SimpleNamespace(
        name="Bloodletting",
        card_id="Bloodletting",
        type=CardType.SKILL,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    game = _game(
        hand=[burning_pact, bloodletting],
        monsters=[
            _monster(
                hp=24,
                damage=0,
                index=0,
                name="Slaver",
                monster_id="SlaverRed",
            )
        ],
        current_hp=2,
        max_hp=80,
        room_type="MonsterRoomElite",
        floor=13,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=0, block=0),
    )
    game.monsters[0].intent = Intent.STRONG_DEBUFF

    agent = _agent()
    agent._fallback_turn_key = (13, 4)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)


def test_energy_guard_takeover_skips_bloodletting_when_hp_loss_makes_incoming_lethal():
    bloodletting = SimpleNamespace(
        name="Bloodletting",
        card_id="Bloodletting",
        type=CardType.SKILL,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    attacker = _monster(
        hp=40,
        damage=27,
        index=0,
        name="Slaver",
        monster_id="SlaverRed",
    )
    attacker.intent = Intent.ATTACK
    game = _game(
        hand=[bloodletting],
        monsters=[attacker],
        current_hp=26,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=9,
        player=SimpleNamespace(energy=0, block=3),
    )

    agent = _agent()
    agent._fallback_turn_key = (16, 9)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)


def _configure_takeover_agent(agent, fallback_agent, floor=14, turn=4):
    agent._fallback_turn_key = (floor, turn)
    agent.fallback_agent = fallback_agent
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0


class _CachedPlanFallback:
    def __init__(self, actions, plan_kind=None):
        self.actions = list(actions)
        self.index = 0
        self.plan_kind = plan_kind
        self.last_emitted = None
        self.reject_calls = []
        self.calls = 0

    def get_next_action_in_game(self, _game):
        self.calls += 1
        if self.index >= len(self.actions):
            self.last_emitted = EndTurnAction()
            return self.last_emitted
        self.last_emitted = self.actions[self.index]
        self.index += 1
        return self.last_emitted

    def is_active_plan_action(self, action):
        return action is self.last_emitted and self.index > 0

    def active_plan_kind_for_action(self, action):
        return self.plan_kind if self.is_active_plan_action(action) else None

    def reject_active_plan_action(self, action):
        if not self.is_active_plan_action(action):
            return False
        self.reject_calls.append(action)
        self.actions = []
        self.index = 0
        self.last_emitted = None
        self.plan_kind = None
        return True


def test_takeover_replacement_rejects_ordinary_cached_continuation(monkeypatch):
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=6,
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        cost_for_turn=2,
        has_target=True,
        damage=8,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=False,
        block=5,
    )
    first = PlayCardAction(card_index=0, target_index=0)
    stale_followup = PlayCardAction(card_index=1, target_index=0)
    replacement = PlayCardAction(card_index=2)
    fallback = _CachedPlanFallback([first, stale_followup])
    game = _game(
        hand=[strike, bash, defend],
        monsters=[_monster(hp=30, damage=8, index=0)],
        floor=14,
        turn=4,
        player=SimpleNamespace(energy=3, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)
    replacements = iter([replacement, None])
    monkeypatch.setattr(
        agent,
        "_get_slime_split_aoe_survival_replacement",
        lambda _game: next(replacements),
    )

    selected = agent.get_next_action_in_game(game)

    assert selected.card_index == 2
    assert fallback.reject_calls == [first]
    assert fallback.actions == []

    second = agent.get_next_action_in_game(game)
    assert second is not stale_followup
    assert fallback.calls == 2


@pytest.mark.parametrize(
    ("active_plan", "accepted", "expect_reject"),
    [(False, False, False), (True, True, False), (True, False, True)],
)
def test_takeover_finalizer_accepts_or_rejects_once(
    active_plan,
    accepted,
    expect_reject,
):
    emitted = PlayCardAction(card_index=0, target_index=0)
    selected = emitted if accepted else EndTurnAction()
    fallback = _CachedPlanFallback([emitted])
    fallback.last_emitted = emitted if active_plan else None
    fallback.index = 1 if active_plan else 0
    game = _game()
    agent = _agent()
    agent.fallback_agent = fallback

    result = agent._finalize_takeover_action(
        emitted,
        selected,
        game,
        active_plan=active_plan,
        plan_kind=None,
        accepted_plan_action=accepted,
    )

    assert result is selected
    assert len(fallback.reject_calls) == int(expect_reject)


def test_failed_lethal_rejection_quarantine_survives_transient_screen():
    action = PlayCardAction(card_index=0, target_index=0)
    fallback = SimpleNamespace(
        is_active_plan_action=lambda candidate: candidate is action,
        active_plan_kind_for_action=lambda candidate: (
            "lethal" if candidate is action else None
        ),
        reject_active_plan_action=lambda _candidate: False,
    )
    agent = _agent()
    agent.fallback_agent = fallback
    none_screen = _game(floor=14, turn=4, in_combat=True)
    hand_select = _game(floor=14, turn=4, in_combat=True)
    hand_select.screen_type = ScreenType.HAND_SELECT
    next_turn = _game(floor=14, turn=5, in_combat=True)

    assert agent._reject_confirmed_active_plan_action(
        action,
        none_screen,
        plan_kind="lethal",
    ) is False
    assert agent._lethal_plan_precedence_is_quarantined(none_screen) is True
    assert agent._lethal_plan_precedence_is_quarantined(hand_select) is True
    assert agent._lethal_plan_precedence_is_quarantined(none_screen) is True
    assert agent._lethal_plan_precedence_is_quarantined(next_turn) is False


def test_lethal_prefix_normalization_resolves_stale_index_from_planned_card():
    planned_hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    live_hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=False,
        block=5,
    )
    target = _monster(hp=20, damage=0, index=0)
    action = PlayCardAction(card=planned_hemokinesis, target_monster=target)
    action.card_index = 0
    game = _game(
        hand=[defend, live_hemokinesis],
        monsters=[target],
        player=SimpleNamespace(energy=1, block=0),
    )

    normalized = _agent()._active_validated_lethal_prefix_action(
        action,
        game,
        active_plan=True,
        plan_kind="lethal",
    )

    assert isinstance(normalized, PlayCardAction)
    assert normalized.card_index == 1
    assert game.hand[normalized.card_index] is live_hemokinesis
    assert normalized.target_index == 0


def test_takeover_accepts_relocated_lethal_card_and_keeps_continuation():
    planned_hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    live_hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=False,
        block=5,
    )
    target = _monster(hp=20, damage=0, index=0)
    planned_action = PlayCardAction(
        card=planned_hemokinesis,
        target_monster=target,
    )
    planned_action.card_index = 0
    cached_followup = EndTurnAction()
    fallback = _CachedPlanFallback(
        [planned_action, cached_followup],
        plan_kind="lethal",
    )
    game = _game(
        hand=[defend, live_hemokinesis],
        monsters=[target],
        player=SimpleNamespace(energy=1, block=0),
        floor=14,
        turn=4,
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)

    selected = agent.get_next_action_in_game(game)

    assert isinstance(selected, PlayCardAction)
    assert selected.card_index == 1
    assert game.hand[selected.card_index] is live_hemokinesis
    assert selected.target_index == 0
    assert game.monsters[selected.target_index] is target
    assert fallback.calls == 1
    assert fallback.reject_calls == []
    assert fallback.actions == [planned_action, cached_followup]
    assert fallback.index == 1
    assert fallback.plan_kind == "lethal"


def test_unresolved_lethal_card_rejects_plan_before_normal_replacement(monkeypatch):
    unresolved_card = SimpleNamespace(
        name="Missing Lethal Card",
        card_id="MissingLethalCard",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=99,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=False,
        block=5,
    )
    target = _monster(hp=20, damage=8, index=0)
    planned_action = PlayCardAction(card=unresolved_card, target_monster=target)
    planned_action.card_index = 0
    stale_followup = EndTurnAction()
    replacement = PlayCardAction(card_index=0)
    fallback = _CachedPlanFallback(
        [planned_action, stale_followup],
        plan_kind="lethal",
    )
    game = _game(
        hand=[defend],
        monsters=[target],
        player=SimpleNamespace(energy=1, block=0),
        floor=14,
        turn=4,
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)
    normalization_results = []
    normalize = agent._active_validated_lethal_prefix_action

    def record_normalization(*args, **kwargs):
        result = normalize(*args, **kwargs)
        normalization_results.append(result)
        return result

    monkeypatch.setattr(
        agent,
        "_active_validated_lethal_prefix_action",
        record_normalization,
    )
    monkeypatch.setattr(
        agent,
        "_get_slime_split_aoe_survival_replacement",
        lambda _game: replacement,
    )

    selected = agent.get_next_action_in_game(game)

    assert normalization_results == [None]
    assert selected is replacement
    assert fallback.reject_calls == [planned_action]
    assert fallback.actions == []


def test_energy_guard_takeover_preserves_safe_hemokinesis_lethal_prefix(caplog):
    caplog.set_level("INFO")
    hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    headbutt = SimpleNamespace(
        name="Headbutt",
        card_id="Headbutt",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=9,
    )
    attacking_slime = _monster(
        hp=3,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    attacking_slime.intent = Intent.ATTACK_DEBUFF
    debuffing_slime = _monster(
        hp=14,
        damage=0,
        index=1,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    debuffing_slime.intent = Intent.DEBUFF
    lethal_action = PlayCardAction(
        card=hemokinesis,
        target_monster=debuffing_slime,
    )
    rejected_actions = []
    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: lethal_action,
        is_active_plan_action=lambda action: action is lethal_action,
        active_plan_kind_for_action=lambda action: (
            "lethal" if action is lethal_action else None
        ),
        reject_active_plan_action=lambda action: (
            rejected_actions.append(action) or True
        ),
    )
    game = _game(
        hand=[hemokinesis, headbutt],
        monsters=[attacking_slime, debuffing_slime],
        current_hp=3,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=2, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 1
    assert "plan_kind=lethal decision=pass_through" in caplog.text
    assert rejected_actions == []
    assert getattr(agent, "_lethal_plan_quarantine_epoch", None) is None


@pytest.mark.parametrize(
    "early_replacement_method",
    [
        "_get_slime_split_aoe_survival_replacement",
        "_get_slime_split_weak_pressure_replacement",
        "_get_survival_block_replacement",
    ],
)
def test_energy_guard_takeover_lethal_prefix_precedes_early_survival_replacements(
    monkeypatch,
    caplog,
    early_replacement_method,
):
    caplog.set_level("INFO")
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=6,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=False,
        block=5,
    )
    target = _monster(
        hp=6,
        damage=0,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    target.intent = Intent.DEBUFF
    lethal_action = PlayCardAction(card=strike, target_monster=target)
    replacement = PlayCardAction(card_index=1)
    fallback_calls = []
    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: (
            fallback_calls.append(_game) or lethal_action
        ),
        is_active_plan_action=lambda action: action is lethal_action,
        active_plan_kind_for_action=lambda action: (
            "lethal" if action is lethal_action else None
        ),
    )
    game = _game(
        hand=[strike, defend],
        monsters=[target],
        current_hp=30,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=2, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)
    for method_name in (
        "_get_slime_split_aoe_survival_replacement",
        "_get_slime_split_weak_pressure_replacement",
        "_get_survival_block_replacement",
    ):
        monkeypatch.setattr(agent, method_name, lambda _game: None)
    monkeypatch.setattr(
        agent,
        early_replacement_method,
        lambda _game: replacement,
    )
    monkeypatch.setattr(
        agent,
        "_get_single_card_lethal_attack_replacement",
        lambda _game: None,
    )

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert fallback_calls == [game]
    assert "plan_kind=lethal decision=pass_through" in caplog.text


def test_energy_guard_takeover_rejects_self_lethal_lethal_prefix(caplog):
    caplog.set_level("INFO")
    hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    first = _monster(hp=3, damage=8, index=0, name="Spike Slime (M)", monster_id="SpikeSlime_M")
    second = _monster(hp=14, damage=0, index=1, name="Spike Slime (M)", monster_id="SpikeSlime_M")
    first.intent = Intent.ATTACK
    second.intent = Intent.DEBUFF
    lethal_action = PlayCardAction(card=hemokinesis, target_monster=second)

    def fail_rejection(_action):
        raise RuntimeError("rejection unavailable")

    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: lethal_action,
        is_active_plan_action=lambda action: action is lethal_action,
        active_plan_kind_for_action=lambda action: (
            "lethal" if action is lethal_action else None
        ),
        reject_active_plan_action=fail_rejection,
    )
    game = _game(
        hand=[hemokinesis],
        monsters=[first, second],
        current_hp=2,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=1, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert "plan_kind=lethal veto=immediate_self_lethal" in caplog.text


def test_rejected_lethal_prefix_invalidates_cached_plan_across_takeover_calls(
    monkeypatch,
    caplog,
):
    caplog.set_level("INFO")
    hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    headbutt = SimpleNamespace(
        name="Headbutt",
        card_id="Headbutt",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=9,
    )
    first = _monster(
        hp=3,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    first.intent = Intent.ATTACK
    second = _monster(
        hp=14,
        damage=0,
        index=1,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    second.intent = Intent.DEBUFF
    unsafe_prefix = PlayCardAction(card=hemokinesis, target_monster=second)
    cached_followup = PlayCardAction(card=headbutt, target_monster=first)

    fallback = OptimizedAgent.__new__(OptimizedAgent)
    fallback.current_action_sequence = [unsafe_prefix, cached_followup]
    fallback.current_action_index = 0
    fallback.current_plan_signature = SimpleNamespace()
    fallback.current_plan_kind = "lethal"

    def emit_cached_action(_game):
        if fallback.current_action_index >= len(fallback.current_action_sequence):
            return EndTurnAction()
        action = fallback.current_action_sequence[fallback.current_action_index]
        fallback.current_action_index += 1
        return action

    fallback.get_next_action_in_game = emit_cached_action
    game = _game(
        hand=[hemokinesis, headbutt],
        monsters=[first, second],
        current_hp=2,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=2, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)
    monkeypatch.setattr(
        agent,
        "_get_non_end_turn_fallback",
        lambda _game, fallback_action=None: None,
    )

    first_action = agent.get_next_action_in_game(game)
    game.current_hp = 30
    game.hand = [headbutt]
    second_action = agent.get_next_action_in_game(game)

    assert isinstance(first_action, EndTurnAction)
    assert isinstance(second_action, EndTurnAction)
    assert second_action is not cached_followup
    assert fallback.current_plan_kind is None
    assert fallback.current_action_sequence == []
    assert "plan_kind=lethal veto=immediate_self_lethal" in caplog.text
    assert "plan_kind=lethal decision=pass_through" not in caplog.text


@pytest.mark.parametrize("rejection_mode", ["missing", "throwing"])
def test_failed_lethal_rejection_quarantines_precedence_until_next_turn(
    caplog,
    rejection_mode,
):
    caplog.set_level("INFO")
    hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=6,
    )
    attacker = _monster(
        hp=20,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    attacker.intent = Intent.ATTACK
    target = _monster(
        hp=30,
        damage=0,
        index=1,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    target.intent = Intent.DEBUFF
    actions = [
        PlayCardAction(card=hemokinesis, target_monster=target),
        PlayCardAction(card=hemokinesis, target_monster=target),
        PlayCardAction(card=strike, target_monster=attacker),
    ]
    fallback = SimpleNamespace(
        current_plan_kind="lethal",
        current_action_index=0,
        last_emitted_action=None,
    )

    def emit_action(_game):
        action = actions[fallback.current_action_index]
        fallback.current_action_index += 1
        fallback.last_emitted_action = action
        return action

    fallback.get_next_action_in_game = emit_action
    fallback.is_active_plan_action = (
        lambda action: action is fallback.last_emitted_action
    )
    fallback.active_plan_kind_for_action = (
        lambda action: (
            fallback.current_plan_kind
            if fallback.is_active_plan_action(action)
            else None
        )
    )
    if rejection_mode == "throwing":
        fallback.reject_active_plan_action = (
            lambda _action: (_ for _ in ()).throw(
                RuntimeError("rejection unavailable")
            )
        )

    game = _game(
        hand=[hemokinesis],
        monsters=[attacker, target],
        current_hp=2,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=1, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)

    first_action = agent.get_next_action_in_game(game)
    game.current_hp = 3
    second_action = agent.get_next_action_in_game(game)

    game.turn = 5
    game.current_hp = 30
    game.hand = [strike]
    agent._fallback_turn_key = (14, 5)
    third_action = agent.get_next_action_in_game(game)

    assert isinstance(first_action, EndTurnAction)
    assert isinstance(second_action, EndTurnAction)
    assert isinstance(third_action, PlayCardAction)
    assert third_action.card_index == 0
    assert third_action.target_index == 0
    assert caplog.text.count("plan_kind=lethal decision=pass_through") == 1
    assert getattr(agent, "_lethal_plan_quarantine_epoch", None) is None


def test_lethal_plan_quarantine_clears_on_combat_exit():
    agent = _agent()
    agent._lethal_plan_quarantine_epoch = (True, 14, 4)
    game = _game(
        in_combat=False,
        floor=14,
        turn=4,
    )

    agent._refresh_lethal_plan_quarantine(game)

    assert agent._lethal_plan_quarantine_epoch is None


def test_energy_guard_takeover_rejects_sharp_hide_lethal_prefix(caplog):
    caplog.set_level("INFO")
    carnage = SimpleNamespace(
        name="Carnage",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        cost_for_turn=2,
        has_target=True,
        damage=30,
    )
    guardian = _monster(
        hp=20,
        damage=0,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.DEFEND
    guardian.powers = [SimpleNamespace(power_id="SharpHide", amount=3)]
    lethal_action = PlayCardAction(card=carnage, target_monster=guardian)
    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: lethal_action,
        is_active_plan_action=lambda action: action is lethal_action,
        active_plan_kind_for_action=lambda action: (
            "lethal" if action is lethal_action else None
        ),
    )
    game = _game(
        hand=[carnage],
        monsters=[guardian],
        current_hp=3,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=11,
        player=SimpleNamespace(energy=2, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback, floor=16, turn=11)

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert "plan_kind=lethal veto=immediate_self_lethal" in caplog.text


def test_energy_guard_takeover_stale_lethal_target_uses_normal_guard_repair(caplog):
    caplog.set_level("INFO")
    hemokinesis = SimpleNamespace(
        name="Hemokinesis",
        card_id="Hemokinesis",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        damage=15,
    )
    gone_target = _monster(
        hp=0,
        damage=0,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    gone_target.is_gone = True
    live_target = _monster(
        hp=20,
        damage=0,
        index=1,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    live_target.intent = Intent.DEBUFF
    lethal_action = PlayCardAction(card=hemokinesis, target_monster=gone_target)
    rejected_actions = []
    fallback = SimpleNamespace(
        get_next_action_in_game=lambda _game: lethal_action,
        is_active_plan_action=lambda action: action is lethal_action,
        active_plan_kind_for_action=lambda action: (
            "lethal" if action is lethal_action else None
        ),
        reject_active_plan_action=lambda action: (
            rejected_actions.append(action) or True
        ),
    )
    game = _game(
        hand=[hemokinesis],
        monsters=[gone_target, live_target],
        current_hp=30,
        max_hp=80,
        floor=14,
        act=1,
        turn=4,
        player=SimpleNamespace(energy=1, block=0),
    )
    agent = _agent()
    _configure_takeover_agent(agent, fallback)

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 1
    assert "plan_kind=lethal veto=stale_or_unplayable" in caplog.text
    assert "plan_kind=lethal decision=pass_through" not in caplog.text
    assert "Replacing takeover unplayable action" in caplog.text
    assert rejected_actions == [lethal_action]


def test_rl_berserk_is_replaced_when_self_vulnerable_would_amplify_boss_hit():
    thunderclap = SimpleNamespace(
        name="Thunderclap",
        card_id="Thunderclap",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    berserk = SimpleNamespace(
        name="Berserk",
        card_id="Berserk",
        type=CardType.POWER,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    slime_boss = _monster(
        hp=84,
        damage=35,
        index=0,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    slime_boss.intent = Intent.ATTACK
    game = _game(
        hand=[thunderclap, defend, berserk],
        monsters=[slime_boss],
        current_hp=78,
        max_hp=80,
        room_type="MonsterRoom",
        floor=16,
        act=1,
        turn=3,
        player=SimpleNamespace(energy=2, block=0, powers=[]),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=2)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 3)


def test_rl_berserk_is_allowed_without_current_turn_damage_pressure():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    berserk = SimpleNamespace(
        name="Berserk",
        card_id="Berserk",
        type=CardType.POWER,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    slime_boss = _monster(
        hp=140,
        damage=-1,
        index=0,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    slime_boss.intent = Intent.STRONG_DEBUFF
    game = _game(
        hand=[strike, berserk],
        monsters=[slime_boss],
        current_hp=78,
        max_hp=80,
        room_type="MonsterRoom",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=2, block=0, powers=[]),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=1)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert agent._fallback_turn_key is None


def test_energy_guard_takeover_skips_low_hp_bloodletting_filler_without_incoming():
    bloodletting = SimpleNamespace(
        name="Bloodletting",
        card_id="Bloodletting",
        type=CardType.SKILL,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    defend_plus = SimpleNamespace(
        name="Defend+",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=8,
    )
    guardian = _monster(
        hp=74,
        damage=0,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.BUFF
    game = _game(
        hand=[bloodletting, defend_plus],
        monsters=[guardian],
        current_hp=13,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=5,
        player=SimpleNamespace(energy=0, block=0),
    )

    agent = _agent()
    agent._fallback_turn_key = (16, 5)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)


def test_guardian_pressure_counts_second_wind_exhaust_block():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    second_wind = SimpleNamespace(
        name="Second Wind+",
        card_id="Second Wind",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        upgrades=1,
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    guardian = _monster(
        hp=102,
        damage=9,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK
    game = _game(
        hand=[defend, second_wind, bash],
        monsters=[guardian],
        current_hp=15,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=8,
        player=SimpleNamespace(energy=3, block=0),
    )

    action = _agent()._get_guardian_pressure_block_replacement(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1


def test_energy_guard_prefers_slime_split_aoe_when_block_still_dies():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    pommel_strike = SimpleNamespace(
        name="Pommel Strike",
        card_id="Pommel Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=9,
    )
    immolate = SimpleNamespace(
        name="Immolate",
        card_id="Immolate",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=False,
        damage=21,
    )
    sever_soul = SimpleNamespace(
        name="Sever Soul+",
        card_id="Sever Soul",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=22,
    )
    first_attacker = _monster(
        hp=10,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    first_attacker.intent = Intent.ATTACK_DEBUFF
    dead_large = _monster(
        hp=0,
        damage=0,
        index=1,
        name="Spike Slime (L)",
        monster_id="SpikeSlime_L",
    )
    dead_large.is_gone = True
    second_attacker = _monster(
        hp=10,
        damage=8,
        index=2,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    second_attacker.intent = Intent.ATTACK_DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=3,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True
    acid_attacker = _monster(
        hp=36,
        damage=16,
        index=4,
        name="Acid Slime (L)",
        monster_id="AcidSlime_L",
    )
    acid_attacker.intent = Intent.ATTACK
    game = _game(
        floor=16,
        turn=6,
        act=1,
        current_hp=18,
        max_hp=80,
        player=SimpleNamespace(energy=3, block=0),
        hand=[defend, pommel_strike, defend, immolate, sever_soul],
        monsters=[
            first_attacker,
            dead_large,
            second_attacker,
            dead_boss,
            acid_attacker,
        ],
        room_type="MonsterRoomBoss",
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: EndTurnAction())
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert CombatRLAgent._incoming_damage(game) == 32
    assert isinstance(action, PlayCardAction)
    assert action.card_index == 3
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 6)


def test_gremlin_leader_guard_retargets_attack_to_kill_attacking_minion():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    headbutt = SimpleNamespace(
        name="Headbutt",
        card_id="Headbutt",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=9,
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=8,
    )
    twin_strike = SimpleNamespace(
        name="Twin Strike+",
        card_id="Twin Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    demon_form = SimpleNamespace(
        name="Demon Form",
        card_id="Demon Form",
        type=CardType.POWER,
        is_playable=True,
        cost=3,
        has_target=False,
    )
    wizard = _monster(
        hp=21,
        damage=0,
        index=0,
        name="Gremlin Wizard",
        monster_id="GremlinWizard",
    )
    wizard.block = 3
    wizard.intent = Intent.UNKNOWN
    gone_one = _monster(hp=0, damage=0, index=1, name="Gone", monster_id="Gone")
    gone_one.is_gone = True
    sneaky = _monster(
        hp=7,
        damage=12,
        index=2,
        name="Sneaky Gremlin",
        monster_id="GremlinThief",
    )
    sneaky.block = 3
    sneaky.intent = Intent.ATTACK
    gone_three = _monster(hp=0, damage=0, index=3, name="Gone", monster_id="Gone")
    gone_three.is_gone = True
    leader = _monster(
        hp=88,
        damage=12,
        index=4,
        name="Gremlin Leader",
        monster_id="GremlinLeader",
    )
    leader.block = 3
    leader.intent = Intent.ATTACK
    leader.move_hits = 3
    game = _game(
        floor=23,
        turn=4,
        act=2,
        current_hp=65,
        max_hp=75,
        player=SimpleNamespace(energy=3, block=0),
        hand=[defend, headbutt, bash, twin_strike, demon_form],
        monsters=[wizard, gone_one, sneaky, gone_three, leader],
        room_type="MonsterRoomElite",
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(
            card_index=3,
            target_index=4,
        )
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert CombatRLAgent._incoming_damage(game) == 58
    assert isinstance(action, PlayCardAction)
    assert action.card_index == 3
    assert action.target_index == 2
    assert agent._fallback_turn_key == (23, 4)


def test_survival_guard_overrides_rl_attack_when_lethal_block_available():
    slimed = SimpleNamespace(
        name="Slimed",
        card_id="Slimed",
        type=CardType.STATUS,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
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
    uppercut = SimpleNamespace(
        name="Uppercut",
        card_id="Uppercut",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    spike = _monster(
        hp=43,
        damage=16,
        index=0,
        name="Spike Slime (L)",
        monster_id="SpikeSlime_L",
    )
    spike.intent = Intent.ATTACK_DEBUFF
    game = _game(
        hand=[slimed, slimed, defend, strike, uppercut],
        monsters=[spike],
        current_hp=3,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=7,
        player=SimpleNamespace(energy=3, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=4, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 2
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 7)


def test_survival_guard_uses_player_hp_when_game_hp_is_stale():
    battle_trance = SimpleNamespace(
        name="Battle Trance",
        card_id="Battle Trance",
        type=CardType.SKILL,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    pommel_strike = SimpleNamespace(
        name="Pommel Strike+",
        card_id="Pommel Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        upgrades=1,
    )
    book = _monster(
        hp=139,
        damage=18,
        index=0,
        name="Book of Stabbing",
        monster_id="BookOfStabbing",
    )
    book.intent = Intent.ATTACK
    game = _game(
        hand=[battle_trance, defend, pommel_strike],
        monsters=[book],
        current_hp=21,
        max_hp=80,
        room_type="MonsterRoomElite",
        floor=23,
        act=2,
        turn=2,
        player=SimpleNamespace(energy=3, block=0, current_hp=15, max_hp=80),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (23, 2)


def test_guardian_pressure_guard_overrides_rl_attack_when_big_nonlethal_block_available():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    guardian = _monster(
        hp=222,
        damage=32,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK
    game = _game(
        hand=[strike, defend, bash],
        monsters=[guardian],
        current_hp=80,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=2,
        player=SimpleNamespace(energy=3, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 2)


def test_guardian_survival_guard_prioritizes_single_card_lethal_over_block():
    cleave = SimpleNamespace(
        name="Cleave",
        card_id="Cleave",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=False,
        damage=8,
    )
    carnage = SimpleNamespace(
        name="Carnage",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=30,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=6,
    )
    shrug = SimpleNamespace(
        name="Shrug It Off+",
        card_id="Shrug It Off",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=11,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    guardian = _monster(
        hp=12,
        damage=32,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.block = 9
    guardian.intent = Intent.ATTACK
    guardian.powers = [SimpleNamespace(power_id="SharpHide", amount=3)]
    game = _game(
        hand=[cleave, carnage, strike, shrug, defend],
        monsters=[guardian],
        current_hp=5,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=11,
        player=SimpleNamespace(energy=3, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0
    assert agent._fallback_turn_key == (16, 11)


def test_single_card_lethal_guard_skips_guardian_attack_when_sharp_hide_kills_player():
    carnage = SimpleNamespace(
        name="Carnage",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=30,
    )
    guardian = _monster(
        hp=12,
        damage=32,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.block = 9
    guardian.intent = Intent.ATTACK
    guardian.powers = [SimpleNamespace(power_id="SharpHide", amount=3)]
    game = _game(
        hand=[carnage],
        monsters=[guardian],
        current_hp=3,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=11,
        player=SimpleNamespace(energy=3, block=0),
    )

    assert _agent()._get_single_card_lethal_attack_replacement(game) is None


def test_act1_boss_pressure_guard_overrides_hexaghost_attack_for_block():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    strike_plus = SimpleNamespace(
        name="Strike+",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        upgrades=1,
    )
    thunderclap = SimpleNamespace(
        name="Thunderclap",
        card_id="Thunderclap",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend_plus = SimpleNamespace(
        name="Defend+",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=8,
    )
    hexaghost = _monster(
        hp=217,
        damage=4,
        index=0,
        name="Hexaghost",
        monster_id="Hexaghost",
    )
    hexaghost.move_hits = 6
    hexaghost.intent = Intent.ATTACK
    game = _game(
        hand=[defend_plus, defend_plus, strike, thunderclap, strike_plus],
        monsters=[hexaghost],
        current_hp=45,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=2,
        player=SimpleNamespace(energy=3, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=2, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 2)


def test_act1_boss_pressure_guard_prefers_shockwave_over_bash_on_slime_boss_big_hit():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    shockwave = SimpleNamespace(
        name="Shockwave+",
        card_id="Shockwave",
        type=CardType.SKILL,
        is_playable=True,
        cost=2,
        has_target=False,
    )
    slimed = SimpleNamespace(
        name="Slimed",
        card_id="Slimed",
        type=CardType.STATUS,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    slime_boss = _monster(
        hp=105,
        damage=35,
        index=0,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    slime_boss.intent = Intent.ATTACK
    game = _game(
        hand=[defend, defend, bash, shockwave, slimed],
        monsters=[slime_boss],
        current_hp=72,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=3,
        player=SimpleNamespace(energy=3, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=2, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 3
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 3)


def test_act1_boss_pressure_guard_does_not_force_weak_without_incoming():
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    shockwave = SimpleNamespace(
        name="Shockwave+",
        card_id="Shockwave",
        type=CardType.SKILL,
        is_playable=True,
        cost=2,
        has_target=False,
    )
    slime_boss = _monster(
        hp=140,
        damage=0,
        index=0,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    slime_boss.intent = Intent.STRONG_DEBUFF
    game = _game(
        hand=[bash, shockwave],
        monsters=[slime_boss],
        current_hp=72,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=3, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0


def test_potion_fallback_prefers_clothesline_when_weak_plus_block_survives_slime_boss():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    slimed = SimpleNamespace(
        name="Slimed",
        card_id="Slimed",
        type=CardType.STATUS,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    clothesline = SimpleNamespace(
        name="Clothesline",
        card_id="Clothesline",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    slime_boss = _monster(
        hp=96,
        damage=27,
        index=0,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    slime_boss.intent = Intent.ATTACK
    game = _game(
        floor=16,
        turn=7,
        room_type="MonsterRoomBoss",
        current_hp=16,
        max_hp=85,
        player=SimpleNamespace(energy=3, block=0),
        hand=[strike, slimed, defend, clothesline, defend],
        monsters=[slime_boss],
    )
    agent = _agent()
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PotionAction(
            potion=SimpleNamespace(name="Elixir", potion_id="ElixirPotion"),
            potion_index=0,
        )
    )

    action = agent._get_non_potion_fallback(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 3
    assert action.target_index == 0


def test_act1_boss_pressure_guard_overrides_slime_split_bash_for_block():
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend_plus = SimpleNamespace(
        name="Defend+",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=8,
    )
    slimed = SimpleNamespace(
        name="Slimed",
        card_id="Slimed",
        type=CardType.STATUS,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    debuff_slime = _monster(
        hp=21,
        damage=0,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    debuff_slime.intent = Intent.DEBUFF
    second_debuff_slime = _monster(
        hp=21,
        damage=0,
        index=1,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    second_debuff_slime.intent = Intent.DEBUFF
    acid_attacker = _monster(
        hp=60,
        damage=11,
        index=2,
        name="Acid Slime (L)",
        monster_id="AcidSlime_L",
    )
    acid_attacker.intent = Intent.ATTACK_DEBUFF
    game = _game(
        hand=[strike, slimed, bash, defend_plus, strike],
        monsters=[debuff_slime, second_debuff_slime, acid_attacker],
        current_hp=17,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=8,
        player=SimpleNamespace(energy=3, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=2, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 3
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 8)


def test_guardian_takeover_prefers_remaining_block_over_attack_when_low_hp_pressure():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=5,
    )
    guardian = _monster(
        hp=197,
        damage=20,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK
    guardian.move_id = 5
    game = _game(
        hand=[strike, strike, defend],
        monsters=[guardian],
        current_hp=12,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=7,
        player=SimpleNamespace(energy=1, block=10),
    )

    agent = _agent()
    agent._fallback_turn_key = (16, 7)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 2
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 7)


def test_guardian_takeover_ends_when_fallback_attack_only_reduces_sharp_hide_margin():
    anger = SimpleNamespace(
        name="Anger",
        card_id="Anger",
        type=CardType.ATTACK,
        is_playable=True,
        cost=0,
        has_target=True,
    )
    guardian = _monster(
        hp=72,
        damage=8,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK_BUFF
    guardian.move_hits = 2
    guardian.powers = [SimpleNamespace(power_id="SharpHide", amount=3)]
    game = _game(
        hand=[anger, anger, anger],
        monsters=[guardian],
        current_hp=12,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=8,
        player=SimpleNamespace(energy=1, block=10),
    )

    agent = _agent()
    agent._fallback_turn_key = (16, 8)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert agent._fallback_turn_key == (16, 8)


def test_guardian_pressure_guard_counts_havoc_feel_no_pain_block():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_berserk = SimpleNamespace(
        name="Berserk",
        card_id="Berserk",
        type=CardType.POWER,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    guardian = _monster(
        hp=222,
        damage=32,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK
    game = _game(
        hand=[strike, havoc],
        draw_pile=[top_berserk],
        monsters=[guardian],
        current_hp=80,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=3,
        player=SimpleNamespace(
            energy=1,
            block=0,
            powers=[SimpleNamespace(power_name="Feel No Pain", amount=3)],
        ),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 3)


def test_guardian_sharp_hide_guard_blocks_attack_that_would_make_incoming_lethal():
    thunderclap = SimpleNamespace(
        name="Thunderclap",
        card_id="Thunderclap",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    guardian = _monster(
        hp=88,
        damage=9,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK
    guardian.powers = [SimpleNamespace(power_id="SharpHide", amount=3)]
    game = _game(
        hand=[thunderclap, defend],
        monsters=[guardian],
        current_hp=9,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=7,
        player=SimpleNamespace(energy=1, block=2),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 7)


def test_guardian_sharp_hide_guard_infers_roll_attack_reflection_without_power():
    thunderclap = SimpleNamespace(
        name="Thunderclap",
        card_id="Thunderclap",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    guardian = _monster(
        hp=88,
        damage=9,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK
    guardian.move_id = 5
    guardian.powers = []
    game = _game(
        hand=[thunderclap, defend],
        monsters=[guardian],
        current_hp=12,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=8,
        player=SimpleNamespace(energy=1, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 8)


def test_guardian_sharp_hide_guard_infers_attack_buff_reflection_without_power():
    twin_strike = SimpleNamespace(
        name="Twin Strike",
        card_id="Twin Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    guardian = _monster(
        hp=165,
        damage=8,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK_BUFF
    guardian.move_hits = 2
    guardian.powers = []
    game = _game(
        hand=[twin_strike],
        monsters=[guardian],
        current_hp=13,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=5,
        player=SimpleNamespace(energy=2, block=5),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert agent._fallback_turn_key == (16, 5)


def test_guardian_sharp_hide_guard_blocks_immediate_self_lethal_attack_even_when_incoming_already_lethal():
    heavy_blade = SimpleNamespace(
        name="Heavy Blade",
        card_id="Heavy Blade",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=32,
    )
    second_wind = SimpleNamespace(
        name="Second Wind",
        card_id="Second Wind",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    guardian = _monster(
        hp=81,
        damage=16,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK_BUFF
    guardian.move_hits = 2
    guardian.powers = [SimpleNamespace(power_id="SharpHide", amount=3)]
    game = _game(
        hand=[heavy_blade, second_wind],
        monsters=[guardian],
        current_hp=1,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=11,
        player=SimpleNamespace(energy=3, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert agent._fallback_turn_key == (16, 11)


def test_guardian_sharp_hide_guard_blocks_low_margin_attack_before_lethal():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    guardian = _monster(
        hp=117,
        damage=8,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK_BUFF
    guardian.move_hits = 2
    guardian.powers = [SimpleNamespace(power_id="SharpHide", amount=3)]
    game = _game(
        hand=[strike, defend],
        monsters=[guardian],
        current_hp=25,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=13,
        player=SimpleNamespace(energy=1, block=0),
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: EndTurnAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 13)


def test_guardian_sharp_hide_guard_ends_turn_when_attack_only_reduces_survival_margin():
    anger = SimpleNamespace(
        name="Anger",
        card_id="Anger",
        type=CardType.ATTACK,
        is_playable=True,
        cost=0,
        has_target=True,
    )
    guardian = _monster(
        hp=84,
        damage=8,
        index=0,
        name="The Guardian",
        monster_id="TheGuardian",
    )
    guardian.intent = Intent.ATTACK_BUFF
    guardian.move_hits = 2
    guardian.powers = [SimpleNamespace(power_id="SharpHide", amount=3)]
    game = _game(
        hand=[anger],
        monsters=[guardian],
        current_hp=9,
        max_hp=85,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=9,
        player=SimpleNamespace(energy=3, block=14),
    )

    replacement = _agent()._get_guardian_sharp_hide_action_replacement(
        PlayCardAction(card_index=0, target_index=0),
        game,
    )

    assert isinstance(replacement, EndTurnAction)


def test_energy_guard_prioritizes_hexaghost_opening_carnage_over_bash():
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    carnage = SimpleNamespace(
        name="Carnage+",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    shrug = SimpleNamespace(
        name="Shrug It Off",
        card_id="Shrug It Off",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    game = _game(
        hand=[bash, carnage, shrug],
        monsters=[
            _monster(
                hp=250,
                damage=0,
                index=0,
                name="Hexaghost",
                monster_id="Hexaghost",
            )
        ],
        current_hp=80,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        act=1,
        turn=1,
        player=SimpleNamespace(energy=3),
    )
    game.monsters[0].intent = "Intent.BUFF"

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: EndTurnAction())
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0
    assert agent._fallback_turn_key == (16, 1)


def test_energy_guard_targets_name_only_attack_without_has_target():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
    )
    game = _game(hand=[strike], monsters=[_monster(hp=30, damage=8, index=0)])
    agent = _agent()

    replacement = agent._get_non_end_turn_fallback(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_energy_guard_does_not_target_name_only_aoe_with_misleading_flag():
    cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        hand=[cleave],
        monsters=[
            _monster(hp=30, damage=8, index=0),
            _monster(hp=30, damage=8, index=1),
        ],
    )
    agent = _agent()

    replacement = agent._get_non_end_turn_fallback(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index is None


def test_rl_playable_cards_parse_string_turn_cost():
    card = SimpleNamespace(is_playable=True, cost=3, cost_for_turn="2", has_target=True)
    game = _game(hand=[card], player=SimpleNamespace(energy=1))

    assert CombatRLAgent._playable_cards(game, energy=1) == []


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


def test_turn_40_bypasses_rl_for_remainder_of_pathological_combat():
    attack = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        floor=19,
        turn=40,
        hand=[attack],
        monsters=[
            _monster(
                hp=20,
                damage=20,
                index=0,
                name="Spheric Guardian",
                monster_id="SphericGuardian",
            )
        ],
    )
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return EndTurnAction()

    def fallback_decide(_game):
        calls["fallback"] += 1
        return EndTurnAction()

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    first = agent.get_next_action_in_game(game)
    game.turn = 41
    second = agent.get_next_action_in_game(game)

    assert isinstance(first, PlayCardAction)
    assert isinstance(second, PlayCardAction)
    assert first.card_index == 0
    assert first.target_index == 0
    assert calls == {"rl": 0, "fallback": 0}


def test_turn_40_uses_fallback_when_no_attack_is_playable():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    fallback_action = PlayCardAction(card_index=0)
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return EndTurnAction()

    def fallback_decide(_game):
        calls["fallback"] += 1
        return fallback_action

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0
    game = _game(turn=40, hand=[defend])

    assert agent.get_next_action_in_game(game) is fallback_action
    assert calls == {"rl": 0, "fallback": 1}


def test_turn_39_keeps_rl_combat_decision_path():
    attack = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    action = PlayCardAction(card_index=0, target_index=0)
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return action

    def fallback_decide(_game):
        calls["fallback"] += 1
        return EndTurnAction()

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0
    game = _game(turn=39, hand=[attack])

    assert agent.get_next_action_in_game(game) is action
    assert calls == {"rl": 1, "fallback": 0}


def test_wasteful_end_turn_uses_available_commands_when_play_flag_missing():
    card = SimpleNamespace(is_playable=True, cost=1, has_target=True)
    game = _game(
        hand=[card],
        monsters=[_monster(hp=30, damage=8, index=0)],
        available_commands=["play", "end", "wait", "state"],
    )
    del game.play_available
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
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert calls == {"rl": 1, "fallback": 1}


def test_empty_hand_energy_end_turn_waits_for_state_refresh():
    game = _game(
        hand=[],
        monsters=[_monster(hp=21, damage=6, index=0, name="Cultist")],
        current_hp=44,
        max_hp=80,
        floor=1,
        turn=3,
        player=SimpleNamespace(energy=3),
        available_commands=["play", "end", "wait", "state"],
    )
    del game.play_available
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return EndTurnAction()

    def fallback_decide(_game):
        calls["fallback"] += 1
        return EndTurnAction()

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=fallback_decide,
        _track_game_state=lambda game: None,
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)
    second_action = agent.get_next_action_in_game(game)

    assert isinstance(action, WaitAction)
    assert action.timeout == 1
    assert isinstance(second_action, EndTurnAction)
    assert calls == {"rl": 2, "fallback": 0}


def test_empty_hand_energy_potion_waits_for_state_refresh():
    potion = SimpleNamespace(
        potion_id="Fruit Juice",
        name="Fruit Juice",
        can_use=True,
        requires_target=False,
        effect_type="max_hp",
    )
    game = _game(
        hand=[],
        potions=[potion],
        monsters=[_monster(hp=48, damage=0, index=0, name="Cultist")],
        current_hp=71,
        max_hp=80,
        floor=3,
        turn=3,
        player=SimpleNamespace(energy=3),
        available_commands=["play", "potion", "end", "wait", "state"],
    )
    del game.play_available
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PotionAction(True, potion=potion)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return EndTurnAction()

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=fallback_decide,
        _track_game_state=lambda game: None,
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)
    second_action = agent.get_next_action_in_game(game)

    assert isinstance(action, WaitAction)
    assert action.timeout == 1
    assert isinstance(second_action, EndTurnAction)
    assert calls == {"rl": 2, "fallback": 1}


def test_rl_end_turn_action_is_stamped_with_combat_turn_context():
    game = _game(
        floor=20,
        turn=1,
        player=SimpleNamespace(energy=0),
        hand=[],
        monsters=[_monster(hp=24, damage=0, index=0)],
    )
    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: EndTurnAction())
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert action.expected_floor == 20
    assert action.expected_turn == 1


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


def test_awakened_one_power_guard_accepts_decimal_string_card_index():
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
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index="0.0")
    )
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


def test_awakened_one_power_guard_accepts_decimal_string_energy():
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
        player=SimpleNamespace(energy="3.0"),
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


def test_hexaghost_setup_guard_prioritizes_shockwave_over_empty_block():
    true_grit = SimpleNamespace(
        name="True Grit",
        card_id="True Grit",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    shockwave = SimpleNamespace(
        name="Shockwave",
        card_id="Shockwave",
        type=CardType.SKILL,
        is_playable=True,
        cost=2,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    game = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(energy=3),
        hand=[true_grit, shockwave, defend],
        monsters=[
            _monster(
                hp=250,
                damage=0,
                index=0,
                name="Hexaghost",
                monster_id="Hexaghost",
            )
        ],
        room_type="MonsterRoomBoss",
    )
    game.monsters[0].intent = "Intent.BUFF"

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 1)


def test_hexaghost_setup_guard_treats_live_unknown_activate_as_no_damage():
    true_grit = SimpleNamespace(
        name="True Grit",
        card_id="True Grit",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    shockwave = SimpleNamespace(
        name="Shockwave",
        card_id="Shockwave",
        type=CardType.SKILL,
        is_playable=True,
        cost=2,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    game = _game(
        floor=16,
        turn=1,
        act=1,
        player=SimpleNamespace(energy=3),
        hand=[true_grit, shockwave, defend],
        monsters=[
            _monster(
                hp=250,
                damage=5,
                index=0,
                name="Hexaghost",
                monster_id="Hexaghost",
            )
        ],
        room_type="MonsterRoomBoss",
    )
    game.monsters[0].intent = Intent.UNKNOWN
    game.monsters[0].move_id = 5
    game.monsters[0].move_hits = 1

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert CombatRLAgent._incoming_damage(game) == 0
    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 1)


def test_hexaghost_setup_guard_replaces_empty_second_wind_with_attack():
    second_wind = SimpleNamespace(
        name="Second Wind+",
        card_id="Second Wind",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    rampage = SimpleNamespace(
        name="Rampage",
        card_id="Rampage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    rage = SimpleNamespace(
        name="Rage",
        card_id="Rage",
        type=CardType.SKILL,
        is_playable=True,
        cost=0,
        has_target=False,
    )
    game = _game(
        floor=16,
        turn=1,
        act=1,
        player=SimpleNamespace(energy=3),
        hand=[second_wind, rampage, strike, defend, rage],
        monsters=[
            _monster(
                hp=250,
                damage=5,
                index=0,
                name="Hexaghost",
                monster_id="Hexaghost",
            )
        ],
        room_type="MonsterRoomBoss",
    )
    game.monsters[0].intent = Intent.UNKNOWN
    game.monsters[0].move_id = 5
    game.monsters[0].move_hits = 1

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert CombatRLAgent._incoming_damage(game) == 0
    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0
    assert agent._fallback_turn_key == (16, 1)


def test_boss_guard_replaces_empty_second_wind_with_attack():
    second_wind = SimpleNamespace(
        name="Second Wind+",
        card_id="Second Wind",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    headbutt = SimpleNamespace(
        name="Headbutt+",
        card_id="Headbutt",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    bludgeon = SimpleNamespace(
        name="Bludgeon+",
        card_id="Bludgeon",
        type=CardType.ATTACK,
        is_playable=True,
        cost=3,
        has_target=True,
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    game = _game(
        floor=33,
        turn=11,
        act=2,
        current_hp=66,
        max_hp=92,
        player=SimpleNamespace(energy=4, block=0),
        hand=[second_wind, headbutt, bludgeon, bash],
        monsters=[
            _monster(
                hp=188,
                damage=0,
                index=0,
                name="The Champ",
                monster_id="Champ",
            )
        ],
        room_type="MonsterRoomBoss",
    )
    game.monsters[0].intent = Intent.BUFF
    game.monsters[0].move_id = 7

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0
    assert agent._fallback_turn_key == (33, 11)


def test_slime_boss_setup_guard_prioritizes_thunderclap_before_strike():
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    thunderclap = SimpleNamespace(
        name="Thunderclap",
        card_id="Thunderclap",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    iron_wave = SimpleNamespace(
        name="Iron Wave",
        card_id="Iron Wave",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(energy=3),
        hand=[strike, thunderclap, iron_wave],
        monsters=[
            _monster(
                hp=140,
                damage=0,
                index=0,
                name="Slime Boss",
                monster_id="SlimeBoss",
            )
        ],
        room_type="MonsterRoomBoss",
    )
    game.monsters[0].intent = "Intent.BUFF"

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 1)


def test_slime_split_survival_guard_retargets_killable_attacker():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    carnage = SimpleNamespace(
        name="Carnage",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=15,
    )

    first_attacker = _monster(
        hp=10,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    first_attacker.intent = Intent.ATTACK_DEBUFF
    dead_large = _monster(
        hp=0,
        damage=0,
        index=1,
        name="Spike Slime (L)",
        monster_id="SpikeSlime_L",
    )
    dead_large.is_gone = True
    second_attacker = _monster(
        hp=16,
        damage=8,
        index=2,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    second_attacker.intent = Intent.ATTACK_DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=3,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True
    acid_attacker = _monster(
        hp=34,
        damage=11,
        index=4,
        name="Acid Slime (L)",
        monster_id="AcidSlime_L",
    )
    acid_attacker.intent = Intent.ATTACK_DEBUFF

    game = _game(
        floor=16,
        turn=9,
        current_hp=17,
        player=SimpleNamespace(energy=2, block=3),
        hand=[defend, carnage],
        monsters=[first_attacker, dead_large, second_attacker, dead_boss, acid_attacker],
        room_type="MonsterRoomBoss",
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=1, target_index=2)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0
    assert agent._fallback_turn_key == (16, 9)


def test_slime_split_pressure_guard_prefers_shockwave_when_weak_preserves_low_hp_margin():
    slimed = SimpleNamespace(
        name="Slimed",
        card_id="Slimed",
        type=CardType.STATUS,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    bash = SimpleNamespace(
        name="Bash",
        card_id="Bash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=8,
    )
    shockwave = SimpleNamespace(
        name="Shockwave+",
        card_id="Shockwave",
        type=CardType.SKILL,
        is_playable=True,
        cost=2,
        has_target=False,
    )
    infernal_blade = SimpleNamespace(
        name="Infernal Blade",
        card_id="Infernal Blade",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    spike_slime = _monster(
        hp=46,
        damage=0,
        index=0,
        name="Spike Slime (L)",
        monster_id="SpikeSlime_L",
    )
    spike_slime.intent = Intent.DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=1,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True
    acid_slime = _monster(
        hp=55,
        damage=11,
        index=2,
        name="Acid Slime (L)",
        monster_id="AcidSlime_L",
    )
    acid_slime.intent = Intent.ATTACK_DEBUFF
    game = _game(
        floor=16,
        act=1,
        turn=7,
        current_hp=18,
        max_hp=80,
        player=SimpleNamespace(energy=3, block=0),
        hand=[slimed, bash, shockwave, slimed, infernal_blade],
        monsters=[spike_slime, dead_boss, acid_slime],
        room_type="MonsterRoomBoss",
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=1, target_index=2)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 2
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 7)


def test_slime_split_survival_guard_uses_target_vulnerable_attack_damage():
    carnage = SimpleNamespace(
        name="Carnage",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=15,
    )

    vulnerable_attacker = _monster(
        hp=22,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    vulnerable_attacker.intent = Intent.ATTACK_DEBUFF
    vulnerable_attacker.powers = [SimpleNamespace(power_name="Vulnerable", amount=1)]
    current_target = _monster(
        hp=50,
        damage=8,
        index=1,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    current_target.intent = Intent.ATTACK_DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=2,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True

    game = _game(
        floor=16,
        turn=9,
        current_hp=10,
        player=SimpleNamespace(energy=2, block=0, powers=[]),
        hand=[carnage],
        monsters=[vulnerable_attacker, current_target, dead_boss],
        room_type="MonsterRoomBoss",
    )

    replacement = _agent()._get_slime_split_survival_attack_replacement(
        PlayCardAction(card_index=0, target_index=1),
        game,
    )

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_slime_split_survival_guard_counts_strength_for_zero_damage_static_attack():
    headbutt = SimpleNamespace(
        name="Headbutt",
        card_id="Headbutt",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=0,
    )

    strength_killable_attacker = _monster(
        hp=11,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    strength_killable_attacker.intent = Intent.ATTACK_DEBUFF
    current_target = _monster(
        hp=50,
        damage=8,
        index=1,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    current_target.intent = Intent.ATTACK_DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=2,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True

    game = _game(
        floor=16,
        turn=9,
        current_hp=10,
        player=SimpleNamespace(
            energy=1,
            block=0,
            powers=[SimpleNamespace(power_name="Strength", amount=2)],
        ),
        hand=[headbutt],
        monsters=[strength_killable_attacker, current_target, dead_boss],
        room_type="MonsterRoomBoss",
    )

    replacement = _agent()._get_slime_split_survival_attack_replacement(
        PlayCardAction(card_index=0, target_index=1),
        game,
    )

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_slime_split_survival_guard_counts_zero_damage_multi_hit_static_attack():
    twin_strike = SimpleNamespace(
        name="Twin Strike",
        card_id="Twin Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=0,
    )

    strength_killable_attacker = _monster(
        hp=14,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    strength_killable_attacker.intent = Intent.ATTACK_DEBUFF
    current_target = _monster(
        hp=50,
        damage=8,
        index=1,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    current_target.intent = Intent.ATTACK_DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=2,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True

    game = _game(
        floor=16,
        turn=9,
        current_hp=10,
        player=SimpleNamespace(
            energy=1,
            block=0,
            powers=[SimpleNamespace(power_name="Strength", amount=2)],
        ),
        hand=[twin_strike],
        monsters=[strength_killable_attacker, current_target, dead_boss],
        room_type="MonsterRoomBoss",
    )

    replacement = _agent()._get_slime_split_survival_attack_replacement(
        PlayCardAction(card_index=0, target_index=1),
        game,
    )

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_slime_split_survival_guard_uses_stronger_attack_to_kill_attacker():
    strike = SimpleNamespace(
        name="Strike+",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=9,
    )
    second_wind = SimpleNamespace(
        name="Second Wind+",
        card_id="Second Wind",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
        block=0,
    )
    clothesline = SimpleNamespace(
        name="Clothesline",
        card_id="Clothesline",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=12,
    )
    sever_soul = SimpleNamespace(
        name="Sever Soul",
        card_id="Sever Soul",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=16,
    )
    slimed = SimpleNamespace(
        name="Slimed",
        card_id="Slimed",
        type=CardType.STATUS,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    weak_player_killable_attacker = _monster(
        hp=12,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    weak_player_killable_attacker.intent = Intent.ATTACK_DEBUFF
    debuff_slime = _monster(
        hp=22,
        damage=0,
        index=1,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    debuff_slime.intent = Intent.DEBUFF
    acid_attacker = _monster(
        hp=19,
        damage=5,
        index=2,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    acid_attacker.intent = Intent.ATTACK_DEBUFF
    second_acid_attacker = _monster(
        hp=28,
        damage=7,
        index=3,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    second_acid_attacker.intent = Intent.ATTACK_DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=4,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True

    game = _game(
        floor=16,
        turn=11,
        current_hp=20,
        player=SimpleNamespace(
            energy=3,
            block=0,
            powers=[SimpleNamespace(power_name="Weak", amount=1)],
        ),
        hand=[strike, second_wind, clothesline, sever_soul, slimed],
        monsters=[
            weak_player_killable_attacker,
            debuff_slime,
            acid_attacker,
            second_acid_attacker,
            dead_boss,
        ],
        room_type="MonsterRoomBoss",
    )

    replacement = _agent()._get_slime_split_survival_attack_replacement(
        PlayCardAction(card_index=2, target_index=0),
        game,
    )

    assert CombatRLAgent._incoming_damage(game) == 20
    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 3
    assert replacement.target_index == 0


def test_slime_split_survival_guard_combines_weak_and_vulnerable_attack_damage():
    carnage = SimpleNamespace(
        name="Carnage",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=15,
    )

    vulnerable_attacker = _monster(
        hp=16,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    vulnerable_attacker.intent = Intent.ATTACK_DEBUFF
    vulnerable_attacker.powers = [SimpleNamespace(power_name="Vulnerable", amount=1)]
    current_target = _monster(
        hp=50,
        damage=8,
        index=1,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    current_target.intent = Intent.ATTACK_DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=2,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True

    game = _game(
        floor=16,
        turn=9,
        current_hp=10,
        player=SimpleNamespace(
            energy=2,
            block=0,
            powers=[SimpleNamespace(power_name="Weak", amount=1)],
        ),
        hand=[carnage],
        monsters=[vulnerable_attacker, current_target, dead_boss],
        room_type="MonsterRoomBoss",
    )

    replacement = _agent()._get_slime_split_survival_attack_replacement(
        PlayCardAction(card_index=0, target_index=1),
        game,
    )

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_slime_split_survival_guard_uses_paper_phrog_vulnerable_attack_damage():
    carnage = SimpleNamespace(
        name="Carnage",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=15,
    )

    vulnerable_attacker = _monster(
        hp=19,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    vulnerable_attacker.intent = Intent.ATTACK_DEBUFF
    vulnerable_attacker.powers = [SimpleNamespace(power_name="Vulnerable", amount=1)]
    current_target = _monster(
        hp=50,
        damage=8,
        index=1,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    current_target.intent = Intent.ATTACK_DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=2,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True

    game = _game(
        floor=16,
        turn=9,
        current_hp=10,
        player=SimpleNamespace(
            energy=2,
            block=0,
            powers=[SimpleNamespace(power_name="Weak", amount=1)],
        ),
        hand=[carnage],
        monsters=[vulnerable_attacker, current_target, dead_boss],
        room_type="MonsterRoomBoss",
        relics=[SimpleNamespace(relic_id="Paper Phrog", name="Paper Phrog")],
    )

    replacement = _agent()._get_slime_split_survival_attack_replacement(
        PlayCardAction(card_index=0, target_index=1),
        game,
    )

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_slime_split_survival_guard_respects_player_weak_attack_damage():
    carnage = SimpleNamespace(
        name="Carnage",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=15,
    )

    killable_only_without_weak = _monster(
        hp=12,
        damage=8,
        index=0,
        name="Spike Slime (M)",
        monster_id="SpikeSlime_M",
    )
    killable_only_without_weak.intent = Intent.ATTACK_DEBUFF
    current_target = _monster(
        hp=50,
        damage=8,
        index=1,
        name="Acid Slime (M)",
        monster_id="AcidSlime_M",
    )
    current_target.intent = Intent.ATTACK_DEBUFF
    dead_boss = _monster(
        hp=0,
        damage=0,
        index=2,
        name="Slime Boss",
        monster_id="SlimeBoss",
    )
    dead_boss.is_gone = True

    game = _game(
        floor=16,
        turn=9,
        current_hp=10,
        player=SimpleNamespace(
            energy=2,
            block=0,
            powers=[SimpleNamespace(power_name="Weak", amount=1)],
        ),
        hand=[carnage],
        monsters=[killable_only_without_weak, current_target, dead_boss],
        room_type="MonsterRoomBoss",
    )
    agent = _agent()

    replacement = agent._get_slime_split_survival_attack_replacement(
        PlayCardAction(card_index=0, target_index=1),
        game,
    )

    assert replacement is None


def test_survival_attack_damage_counts_mind_blast_draw_pile_with_strength_and_weak():
    mind_blast = SimpleNamespace(
        name="Mind Blast+",
        card_id="Mind Blast",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=0,
    )
    game = _game(
        player=SimpleNamespace(
            energy=1,
            powers=[
                SimpleNamespace(power_name="Strength", amount=2),
                SimpleNamespace(power_name="Weak", amount=1),
            ],
        ),
        draw_pile=[object() for _ in range(9)],
    )

    assert CombatRLAgent._survival_attack_damage(mind_blast, game) == 8


def test_survival_attack_damage_counts_clash_static_damage_when_live_damage_zero():
    clash = SimpleNamespace(
        name="Clash",
        card_id="Clash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=0,
        has_target=True,
        damage=0,
    )
    game = _game(player=SimpleNamespace(energy=1, powers=[]))

    assert CombatRLAgent._survival_attack_damage(clash, game) == 14


def test_survival_attack_damage_counts_perfected_strike_deck_scaling():
    perfected_strike = SimpleNamespace(
        name="Perfected Strike",
        card_id="Perfected Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
        damage=0,
    )
    game = _game(
        player=SimpleNamespace(
            energy=2,
            powers=[SimpleNamespace(power_name="Strength", amount=1)],
        ),
        deck=[
            SimpleNamespace(name="Strike", card_id="Strike_R"),
            SimpleNamespace(name="Strike", card_id="Strike_R"),
            SimpleNamespace(name="Twin Strike", card_id="Twin Strike"),
            SimpleNamespace(name="Perfected Strike", card_id="Perfected Strike"),
        ],
    )

    assert CombatRLAgent._survival_attack_damage(perfected_strike, game) == 15


def test_survival_attack_damage_applies_player_weak_per_hit_for_multi_hit_attack():
    twin_strike = SimpleNamespace(
        name="Twin Strike",
        card_id="Twin Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=5,
    )
    game = _game(
        player=SimpleNamespace(
            energy=1,
            powers=[SimpleNamespace(power_name="Weak", amount=1)],
        ),
    )

    assert CombatRLAgent._survival_attack_damage(twin_strike, game) == 6


def test_double_tap_guard_skips_when_no_attack_can_follow():
    double_tap = SimpleNamespace(
        name="Double Tap",
        card_id="Double Tap",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    game = _game(
        floor=18,
        turn=1,
        player=SimpleNamespace(energy=2),
        hand=[double_tap, defend],
        monsters=[
            _monster(
                hp=35,
                damage=10,
                index=0,
                name="Byrd",
                monster_id="Byrd",
            )
        ],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index is None
    assert agent._fallback_turn_key == (18, 1)


def test_double_tap_guard_allows_attack_followup():
    double_tap = SimpleNamespace(
        name="Double Tap",
        card_id="Double Tap",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
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
        floor=18,
        turn=2,
        player=SimpleNamespace(energy=2),
        hand=[double_tap, strike],
        monsters=[
            _monster(
                hp=35,
                damage=10,
                index=0,
                name="Byrd",
                monster_id="Byrd",
            )
        ],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert agent._fallback_turn_key is None


def test_status_guard_replaces_slimed_when_real_card_is_playable():
    slimed = SimpleNamespace(
        name="Slimed",
        card_id="Slimed",
        type=CardType.STATUS,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    reaper = SimpleNamespace(
        name="Reaper",
        card_id="Reaper",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=False,
    )
    game = _game(
        floor=16,
        turn=8,
        player=SimpleNamespace(energy=3),
        hand=[defend, slimed, slimed, defend, reaper],
        monsters=[
            _monster(
                hp=43,
                damage=0,
                index=0,
                name="Spike Slime (L)",
                monster_id="SpikeSlime_L",
            ),
            _monster(
                hp=43,
                damage=11,
                index=1,
                name="Acid Slime (L)",
                monster_id="AcidSlime_L",
            ),
        ],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=2)
    )
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=4)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 4
    assert action.target_index is None
    assert agent._fallback_turn_key == (16, 8)


def test_first_playable_prefers_real_card_before_slimed():
    slimed = SimpleNamespace(
        name="Slimed",
        card_id="Slimed",
        type=CardType.STATUS,
        is_playable=True,
        cost=1,
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
        player=SimpleNamespace(energy=1),
        hand=[slimed, strike],
        monsters=[_monster(hp=35, damage=12, index=0)],
    )

    action = _agent()._first_playable_card_action(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0


def test_first_playable_keeps_slimed_when_it_is_the_only_playable_card():
    slimed = SimpleNamespace(
        name="Slimed",
        card_id="Slimed",
        type=CardType.STATUS,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    game = _game(
        player=SimpleNamespace(energy=1),
        hand=[slimed],
        monsters=[_monster(hp=35, damage=12, index=0)],
    )

    action = _agent()._first_playable_card_action(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index is None


def test_ethereal_attack_guard_prioritizes_carnage_before_low_value_card():
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
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
    armaments = SimpleNamespace(
        name="Armaments+",
        card_id="Armaments",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    carnage = SimpleNamespace(
        name="Carnage+",
        card_id="Carnage",
        type=CardType.ATTACK,
        is_playable=True,
        cost=2,
        has_target=True,
    )
    game = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(energy=3),
        room_type="MonsterRoomBoss",
        hand=[defend, strike, armaments, carnage],
        monsters=[
            _monster(
                hp=229,
                damage=6,
                index=0,
                name="Hexaghost",
                monster_id="Hexaghost",
            )
        ],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index=1, target_index=0)
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 3
    assert action.target_index == 0
    assert agent._fallback_turn_key == (16, 2)


def test_havoc_guard_replaces_rl_havoc_with_safer_card():
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
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
        player=SimpleNamespace(energy=2),
        hand=[havoc, strike],
        monsters=[
            _monster(
                hp=72,
                damage=12,
                index=0,
                name="Shelled Parasite",
                monster_id="ShelledParasite",
            )
        ],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0
    assert agent._fallback_turn_key == (5, 2)


def test_havoc_guard_allows_visible_top_attack_against_single_monster():
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=6,
    )
    game = _game(
        player=SimpleNamespace(energy=2),
        hand=[havoc, defend],
        draw_pile=[top_strike],
        monsters=[_monster(hp=6, damage=8, index=0)],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert agent._fallback_turn_key is None


def test_havoc_guard_replaces_visible_top_clash_when_non_attack_remains():
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_clash = SimpleNamespace(
        name="Clash",
        card_id="Clash",
        type=CardType.ATTACK,
        is_playable=True,
        cost=0,
        has_target=True,
        damage=14,
    )
    game = _game(
        player=SimpleNamespace(energy=2),
        hand=[havoc, defend],
        draw_pile=[top_clash],
        monsters=[_monster(hp=14, damage=8, index=0)],
    )

    assert _agent()._should_override_risky_havoc(PlayCardAction(card_index=0), game) is True


def test_havoc_guard_does_not_allow_visible_top_attack_when_entangled():
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=6,
    )
    game = _game(
        player=SimpleNamespace(
            energy=2,
            powers=[SimpleNamespace(power_name="Entangled", amount=1)],
        ),
        hand=[havoc, defend],
        draw_pile=[top_strike],
        monsters=[_monster(hp=6, damage=8, index=0)],
    )

    assert _agent()._should_override_risky_havoc(PlayCardAction(card_index=0), game) is True


def test_havoc_guard_allows_visible_top_aoe_attack_against_multiple_monsters():
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_cleave = SimpleNamespace(
        name="Cleave",
        card_id="Cleave",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=False,
        damage=8,
    )
    game = _game(
        player=SimpleNamespace(energy=2),
        hand=[havoc, defend],
        draw_pile=[top_cleave],
        monsters=[_monster(hp=8, damage=6, index=0), _monster(hp=8, damage=6, index=1)],
    )

    assert _agent()._should_override_risky_havoc(PlayCardAction(card_index=0), game) is False


def test_havoc_guard_keeps_visible_top_targeted_attack_multi_monster_conservative():
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    defend = SimpleNamespace(
        name="Defend",
        card_id="Defend_R",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    top_strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
        damage=6,
    )
    game = _game(
        player=SimpleNamespace(energy=2),
        hand=[havoc, defend],
        draw_pile=[top_strike],
        monsters=[_monster(hp=6, damage=6, index=0), _monster(hp=6, damage=6, index=1)],
    )

    assert _agent()._should_override_risky_havoc(PlayCardAction(card_index=0), game) is True


def test_rl_action_log_names_returned_card(caplog):
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        player=SimpleNamespace(energy=2),
        hand=[strike],
        monsters=[_monster(hp=30, damage=8, index=0)],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    with caplog.at_level("INFO", logger="spirecomm.ai.rl.agent"):
        action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert "card=Strike" in caplog.text
    assert "card_index=0" in caplog.text
    assert "target_index=0" in caplog.text
    assert "hand=[Strike]" in caplog.text


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


def test_finished_combat_stale_state_waits_instead_of_playing_card():
    card = SimpleNamespace(is_playable=True, cost=1, has_target=True)
    dead_monsters = [
        _monster(hp=0, index=0, name="Fungi Beast", monster_id="FungiBeast"),
        _monster(hp=0, index=1, name="Fungi Beast", monster_id="FungiBeast"),
    ]
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=fallback_decide,
        _track_game_state=lambda game: None,
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = (5, 1)
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0
    game = _game(
        screen_type=None,
        in_combat=True,
        play_available=True,
        hand=[card],
        monsters=dead_monsters,
        floor=5,
        turn=1,
    )

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, WaitAction)
    assert agent._fallback_turn_key is None
    assert calls == {"rl": 0, "fallback": 0}


def test_half_dead_revive_transition_ends_turn_instead_of_waiting():
    reviving_boss = _monster(
        hp=0,
        index=0,
        name="Awakened One",
        monster_id="AwakenedOne",
    )
    reviving_boss.half_dead = True
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=fallback_decide,
        _track_game_state=lambda game: None,
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = (50, 8)
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0
    game = _game(
        screen_type=None,
        in_combat=True,
        play_available=False,
        end_available=True,
        available_commands=["end", "wait", "state"],
        hand=[],
        monsters=[reviving_boss],
        floor=50,
        turn=8,
    )

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert action.expected_floor == 50
    assert action.expected_turn == 8
    assert agent._fallback_turn_key is None
    assert calls == {"rl": 0, "fallback": 0}


def test_gone_half_dead_awakened_one_revive_transition_ends_turn():
    dead_cultist = _monster(hp=0, index=0, name="Cultist", monster_id="Cultist")
    dead_cultist.is_gone = True
    reviving_boss = _monster(
        hp=0,
        index=1,
        name="Awakened One",
        monster_id="AwakenedOne",
    )
    reviving_boss.is_gone = True
    reviving_boss.half_dead = True
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PlayCardAction(card_index=0, target_index=1)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=1)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=fallback_decide,
        _track_game_state=lambda game: None,
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = (50, 6)
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0
    game = _game(
        screen_type=None,
        in_combat=True,
        play_available=True,
        end_available=True,
        available_commands=["end", "wait", "state"],
        hand=[SimpleNamespace(is_playable=True, cost=0, has_target=False)],
        monsters=[dead_cultist, reviving_boss],
        floor=50,
        turn=6,
    )

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert action.expected_floor == 50
    assert action.expected_turn == 6
    assert agent._fallback_turn_key is None
    assert calls == {"rl": 0, "fallback": 0}


def test_half_dead_awakened_one_revive_transition_ends_turn_with_live_minion():
    live_cultist = _monster(hp=30, index=0, name="Cultist", monster_id="Cultist")
    reviving_boss = _monster(
        hp=0,
        index=1,
        name="Awakened One",
        monster_id="AwakenedOne",
    )
    reviving_boss.is_gone = True
    reviving_boss.half_dead = True
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=fallback_decide,
        _track_game_state=lambda game: None,
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0
    game = _game(
        screen_type=None,
        in_combat=True,
        play_available=True,
        end_available=True,
        available_commands=["end", "wait", "state"],
        hand=[SimpleNamespace(is_playable=True, cost=0, has_target=True)],
        monsters=[live_cultist, reviving_boss],
        floor=50,
        turn=6,
    )

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, EndTurnAction)
    assert action.expected_floor == 50
    assert action.expected_turn == 6
    assert agent._fallback_turn_key is None
    assert calls == {"rl": 0, "fallback": 0}

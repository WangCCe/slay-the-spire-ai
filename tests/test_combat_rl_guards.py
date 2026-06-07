import json
from types import SimpleNamespace

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


def test_survival_guard_treats_decay_damage_as_unblocked_by_current_block():
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
    slime = _monster(hp=62, damage=8, index=0, name="Acid Slime (L)", monster_id="AcidSlime_L")
    slime.intent = Intent.ATTACK
    game = _game(
        hand=[strike, defend, decay],
        monsters=[slime],
        current_hp=4,
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
